import feedparser
import requests
from bs4 import BeautifulSoup
import openai
import time
import json
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class NewsCharityMatcher:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.client = openai.OpenAI(api_key=self.api_key)
        self.processed_articles = set()
        
        # Initialize ChromaDB with OpenAI embeddings
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        openai_ef = embedding_functions.DefaultEmbeddingFunction()
        
        # Create/Get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="charity_embeddings",
            embedding_function=openai_ef
        )
        
        # Load charities and add to ChromaDB if empty
        try:
            with open('charities.json', 'r') as f:
                self.charities = json.load(f)['charities']
                
            if self.collection.count() == 0:
                # Process in smaller batches
                batch_size = 50
                for i in range(0, len(self.charities), batch_size):
                    batch = self.charities[i:i + batch_size]
                    
                    # Prepare batch for ChromaDB
                    documents = []
                    metadatas = []
                    ids = []
                    
                    for j, charity in enumerate(batch):
                        # Combine name and mission for better semantic matching
                        combined_text = f"{charity['name']}: {charity['mission']}"
                        documents.append(combined_text)
                        metadatas.append({"name": charity['name'], "url": charity['url']})
                        ids.append(str(i + j))
                    
                    # Add batch to ChromaDB
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"Added batch of {len(documents)} charities to ChromaDB ({i + len(batch)}/{len(self.charities)} total)")
                    time.sleep(1)  # Rate limiting pause
                    
        except FileNotFoundError:
            print("Error: charities.json not found")
            self.charities = []
            
        # Load processed articles history
        try:
            with open('processed_articles.json', 'r') as f:
                self.processed_articles = set(json.load(f))
        except FileNotFoundError:
            self.processed_articles = set()

    def get_rss_feeds(self, rss_urls):
        articles = []
        for url in rss_urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if entry.link not in self.processed_articles:
                        articles.append({
                            'title': entry.title,
                            'description': entry.get('description', ''),
                            'link': entry.link
                        })
            except Exception as e:
                print(f"Error processing RSS feed {url}: {str(e)}")
        return articles

    def find_similar_charities(self, article, n_results=10):
        """Find charities similar to the article using semantic search."""
        query_text = f"{article['title']} {article['description']}"
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            similar_charities = []
            for i in range(len(results['ids'][0])):
                charity_data = {
                    'name': results['metadatas'][0][i]['name'],
                    'url': results['metadatas'][0][i]['url'],
                    'similarity_score': results['distances'][0][i] if 'distances' in results else None
                }
                similar_charities.append(charity_data)
                
            return similar_charities
        except Exception as e:
            print(f"Error in similarity search: {str(e)}")
            return []

    def analyze_article(self, article):
        # Get similar charities
        similar_charities = self.find_similar_charities(article)
        charity_names = [c['name'] for c in similar_charities]
        
        system_message = f"""You are an assistant that MUST ONLY suggest charities from this specific list: {', '.join(charity_names)}."""

        prompt = f"""
        Choose exactly ONE charity from this list that best matches the news article.
        Format your response exactly as: "Charity Name: one-line reason"

        Article Title: {article['title']}
        Article Description: {article['description']}
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content

    def save_processed_articles(self):
        with open('processed_articles.json', 'w') as f:
            json.dump(list(self.processed_articles), f)

    def run(self, rss_urls, interval=300):  # interval in seconds (default 5 minutes)
        while True:
            try:
                print(f"\nChecking for new articles at {datetime.now()}")
                articles = self.get_rss_feeds(rss_urls)
                
                for article in articles:
                    print(f"\nAnalyzing article: {article['title']}")
                    similar_charities = self.find_similar_charities(article)
                    
                    if similar_charities:
                        print("\nTop Similar Charities:")
                        for i, charity in enumerate(similar_charities, 1):
                            print(f"{i}. {charity['name']}")
                            print(f"   Similarity Score: {charity['similarity_score']:.4f}")
                            print(f"   URL: {charity['url']}\n")
                        
                        print("Charity Suggestion from GPT:")
                        suggestion = self.analyze_article(article)
                        print(suggestion)
                    else:
                        print("No similar charities found.")
                    
                    # Mark article as processed
                    self.processed_articles.add(article['link'])
                    self.save_processed_articles()
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Error occurred: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying 