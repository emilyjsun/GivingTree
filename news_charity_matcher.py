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
        
        # Load charities from charities_final.json
        try:
            with open('charities_final.json', 'r') as f:
                data = json.load(f)
                self.charities = data['charities']
                
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
                        mission = charity.get('mission', '')
                        if not mission or mission == "Mission statement not found":
                            print(f"Warning: Missing mission for {charity['name']}")
                            mission = f"This is a charity focused on {charity['name'].lower()}"
                        
                        combined_text = f"{charity['name']}: {mission}"
                        documents.append(combined_text)
                        metadatas.append({
                            "name": charity['name'],
                            "url": charity['url'],
                            "score": charity.get('score', 0),
                            "categories": json.dumps(charity.get('categories', []))  # Store categories in metadata
                        })
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
            print("Error: charities_final.json not found")
            self.charities = []
            
        # Load processed articles history
        try:
            with open('processed_articles.json', 'r') as f:
                self.processed_articles = set(json.load(f))
        except FileNotFoundError:
            self.processed_articles = set()

        # Add categories
        self.CATEGORIES = [
            "Disaster Relief",
            "Education Support",
            "Healthcare Access",
            "Food Security",
            "Refugee Assistance",
            "Child Welfare",
            "Environmental Conservation",
            "Women's Empowerment",
            "Housing & Shelter",
            "Clean Water Access",
            "Mental Health Support",
            "Poverty Alleviation",
            "Human Rights",
            "Community Development"
        ]
        
        # Create categories collection
        self.category_collection = self.chroma_client.get_or_create_collection(
            name="category_embeddings",
            embedding_function=openai_ef
        )
        
        # Initialize categories if empty
        if self.category_collection.count() == 0:
            self.category_collection.add(
                documents=self.CATEGORIES,
                metadatas=[{"category": cat} for cat in self.CATEGORIES],
                ids=[str(i) for i in range(len(self.CATEGORIES))]
            )

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

    def find_similar_charities(self, article, n_results=5):
        """Find charities similar to the article using semantic search."""
        try:
            # First, get the top category for the article
            matching_categories = self.find_matching_categories(article)
            if not matching_categories:
                return []
            
            top_category = matching_categories[0]['category']
            print(f"\nFiltering charities by top category: {top_category}")
            
            # Get all charities that match the category
            category_filtered = []
            for charity in self.charities:  # Use self.charities instead of querying ChromaDB
                charity_categories = charity.get('categories', [])
                if any(cat['category'] == top_category for cat in charity_categories):
                    category_filtered.append({
                        'name': charity['name'],
                        'url': charity['url'],
                        'mission': charity['mission']
                    })
            
            print(f"Found {len(category_filtered)} charities in category '{top_category}'")
            
            if not category_filtered:
                return []
            
            # Now do similarity search between article and filtered charities' missions
            article_text = f"{article['title']} {article.get('description', '')}"
            
            # Create a temporary collection for similarity search
            temp_collection = self.chroma_client.get_or_create_collection(
                name="temp_category_search",
                embedding_function=self.collection._embedding_function
            )
            
            # Add filtered charities to temp collection
            temp_collection.add(
                documents=[c['mission'] for c in category_filtered],
                metadatas=[{'name': c['name'], 'url': c['url']} for c in category_filtered],
                ids=[str(i) for i in range(len(category_filtered))]
            )
            
            # Perform similarity search
            search_results = temp_collection.query(
                query_texts=[article_text],
                n_results=min(n_results, len(category_filtered))
            )
            
            # Format results
            similar_charities = []
            for i in range(len(search_results['ids'][0])):
                charity_data = {
                    'name': search_results['metadatas'][0][i]['name'],
                    'url': search_results['metadatas'][0][i]['url'],
                    'similarity_score': 1 - (search_results['distances'][0][i] / 2)
                }
                similar_charities.append(charity_data)
            
            # Delete temporary collection
            self.chroma_client.delete_collection("temp_category_search")
            
            return similar_charities
            
        except Exception as e:
            print(f"Error in similarity search: {str(e)}")
            return []

    def save_processed_articles(self):
        with open('processed_articles.json', 'w') as f:
            json.dump(list(self.processed_articles), f)

    def is_relevant_article(self, title: str, description: str) -> bool:
        """Use GPT to determine if an article is relevant to charity impact."""
        prompt = f"""Article Title: {title}
Description: {description}

Question: Based on this article's title and description, could this news potentially impact charitable giving, fundraising, or the work of charitable organizations? Answer with only 'yes' or 'no'.

Consider:
- Could this affect people's willingness or ability to donate?
- Might this create new needs for charitable assistance?
- Could this influence how charities operate or deliver services?
- Might this affect specific charitable causes or communities?

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a charity impact analyst. Evaluate if news could affect charitable giving or operations. Answer only 'yes' or 'no'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=5
            )
            
            answer = response.choices[0].message.content.strip().lower()
            is_relevant = answer == 'yes'
            
            print(f"\nArticle: {title[:60]}...")
            print(f"GPT Response: {answer.upper()}")
            
            return is_relevant
            
        except Exception as e:
            print(f"Error checking article relevance: {e}")
            return True  # Default to including article if check fails

    def get_subscribers_for_category(self, category):
        """Get list of subscribers for a category from category_subscribers.json"""
        try:
            with open('category_subscribers.json', 'r') as f:
                subscribers = json.load(f)
                return subscribers.get(category, [])
        except FileNotFoundError:
            print("No subscribers database found")
            return []

    def find_matching_categories(self, article):
        """Find top 3 matching categories for an article."""
        # Combine title and description for better matching
        article_text = f"{article['title']} {article.get('description', '')}"
        
        # Query the category collection
        results = self.category_collection.query(
            query_texts=[article_text],
            n_results=3
        )
        
        # Format results
        categories = []
        distances = results['distances'][0]
        
        # Normalize distances to similarities (0 to 1 range)
        max_distance = max(distances)
        min_distance = min(distances)
        range_distance = max_distance - min_distance if max_distance != min_distance else 1
        
        for i in range(len(distances)):
            category = results['metadatas'][0][i]['category']
            # Convert distance to normalized similarity score
            normalized_similarity = 1 - ((distances[i] - min_distance) / range_distance)
            categories.append({
                'category': category,
                'similarity': normalized_similarity
            })
            
            # Get subscribers for top category
            if i == 0:  # Only for the top category
                subscribers = self.get_subscribers_for_category(category)
                if subscribers:
                    print(f"\n📢 Subscribers for {category}:")
                    print(f"Found {len(subscribers)} subscribers: {subscribers}")
        
        return categories, subscribers

    def get_urgency_score(self, article):
        """Get urgency score from 1-10 for the article using GPT."""
        prompt = f"""Article Title: {article['title']}
Description: {article['description']}

On a scale of 1-10, rate the urgency of this situation in terms of immediate funding needs, where:
1 = No immediate funding urgency
10 = Extremely urgent, immediate funding crucial

Consider factors like:
- Immediate threat to life or well-being
- Time-sensitivity of the situation
- Scale of impact
- Current resource availability
- Vulnerability of affected populations

Provide your response in this exact format:
"Urgency Score: [number 1-10]
Brief Reason: [one-line explanation]"
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at assessing humanitarian and charitable funding urgency. Be objective and analytical in your assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            print(f"Error getting urgency score: {e}")
            return "Urgency Score: N/A\nBrief Reason: Error in assessment"

    def update_user_portfolios(self, subscribers, category, similar_charities, article_urgency):
        """Update user portfolios with relevant charities and scores"""
        try:
            # Parse urgency score from string
            urgency_line = article_urgency.split('\n')[0]
            try:
                urgency_score = float(urgency_line.split(': ')[1])
            except:
                urgency_score = 5.0  # Default if parsing fails
            
            # Load user database
            with open('user_database.json', 'r') as f:
                user_db = json.load(f)
            
            # For each subscriber
            for user_id in subscribers:
                print(f"user_id: {user_id}")
                print(f"Updating portfolio for user {user_id}")
                if user_id not in user_db:
                    continue
                
                # Get existing portfolio
                existing_portfolio = user_db[user_id].get('portfolio', [])
                
                # Calculate relevance scores for each charity
                portfolio_updates = []
                for charity in similar_charities:
                    # Calculate relevance score using:
                    # - Charity similarity score (0-1)
                    # - Article urgency (1-10)
                    # - User's category confidence (0-1)
                    similarity = 1 - charity['similarity_score']  # Convert distance to similarity
                    
                    # Get user's confidence for the category
                    user_categories = user_db[user_id]['categories']
                    category_confidence = 0.5  # Default if category not found
                    for cat, conf in user_categories:
                        if cat == category:
                            category_confidence = float(conf)
                            break
                    
                    # Combine factors into final relevance score
                    relevance = (similarity * 0.4 + 
                               (urgency_score/10) * 0.3 + 
                               category_confidence * 0.3)
                    
                    charity_dict = {
                        'charity_name': charity['name'],
                        'charity_url': charity['url'],
                        'relevance_score': relevance
                    }
                    
                    # Add to portfolio updates with priority (1 - relevance for min heap)
                    portfolio_updates.append((1.0 - relevance, charity_dict))
                
                # Combine existing portfolio with new updates
                combined_portfolio = existing_portfolio + portfolio_updates
                
                # Sort by priority and keep top 10 (or another suitable number)
                user_db[user_id]['portfolio'] = sorted(combined_portfolio, key=lambda x: x[0])[:10]
                
                print(f"\nUpdated portfolio for user {user_id}:")
                for priority, charity in user_db[user_id]['portfolio']:
                    print(f"Charity: {charity['charity_name']}")
                    print(f"Relevance Score: {1.0 - priority:.2%}")  # Convert back to relevance score
                    print("-" * 30)
            
            # Save updated user database
            with open('user_database.json', 'w') as f:
                json.dump(user_db, f, indent=2)
            
        except Exception as e:
            print(f"Error updating user portfolios: {e}")

    def process_feed(self, feed_url):
        """Process RSS feed and find charity matches."""
        try:
            feed = feedparser.parse(feed_url)
            print(f"\nProcessing feed: {feed.feed.title}")
            
            for entry in feed.entries:
                # Skip if already processed
                if entry.link in self.processed_articles:
                    continue
                
                title = entry.get('title', '')
                description = entry.get('description', '')
                
                print("\n" + "="*50)  # Add separator for clarity
                print(f"Processing new article...")
                
                # Use GPT to check relevance
                if not self.is_relevant_article(title, description):
                    print("Skipping article based on GPT response")
                    continue
                
                print("Article deemed relevant - continuing analysis...")
                
                try:
                    # Get full article text
                    article_text = self.get_article_text(entry.link)
                    if not article_text:
                        print("Could not fetch article text - skipping")
                        continue
                    
                    # Create article dict for analysis
                    article = {
                        'title': title,
                        'description': description,
                        'text': article_text,
                        'link': entry.link
                    }
                    
                    # Find matching categories and subscribers
                    matching_categories, subscribers = self.find_matching_categories(article)
                    print("\nMatching Categories:")
                    for i, cat in enumerate(matching_categories, 1):
                        print(f"{i}. {cat['category']}")
                        print(f"   Similarity Score: {cat['similarity']:.4f}")
                    
                    # Find similar charities
                    similar_charities = self.find_similar_charities(article)
                    
                    if similar_charities:
                        print("\nTop Similar Charities:")
                        for i, charity in enumerate(similar_charities, 1):
                            print(f"{i}. {charity['name']}")
                            print(f"   Similarity Score: {charity['similarity_score']:.4f}")
                            print(f"   URL: {charity['url']}\n")
                        
                        # Add similar charities to article before GPT analysis
                        article['similar_charities'] = similar_charities
                        
                    else:
                        print("No similar charities found.")
                    
                    # Add after finding matching categories:
                    print("\nUrgency Assessment:")
                    urgency_result = self.get_urgency_score(article)
                    print(urgency_result)
                    print(f"Updating portfolios for {len(subscribers)} subscribers")
                    self.update_user_portfolios(subscribers, matching_categories[0]['category'],similar_charities, urgency_result)

                    
                    # Mark article as processed
                    self.processed_articles.add(entry.link)
                    self.save_processed_articles()
                    
                except Exception as e:
                    print(f"Error processing article: {e}")
                    continue
                
        except Exception as e:
            print(f"Error processing feed: {e}")

    def run(self, rss_urls, interval=300):  # interval in seconds (default 5 minutes)
        while True:
            try:
                print(f"\nChecking for new articles at {datetime.now()}")
                articles = self.get_rss_feeds(rss_urls)
                
                for article in articles:
                    print("\n" + "="*50)
                    print(f"Processing new article...")
                    
                    # Check if article is relevant using GPT
                    if not self.is_relevant_article(article['title'], article.get('description', '')):
                        print("Skipping article based on GPT response")
                        continue
                    
                    print("Article deemed relevant - continuing analysis...")
                    print(f"\nAnalyzing article: {article['title']}")
                    
                    # Find matching categories and subscribers
                    matching_categories, subscribers = self.find_matching_categories(article)
                    print("\nMatching Categories:")
                    for i, cat in enumerate(matching_categories, 1):
                        print(f"{i}. {cat['category']}")
                        print(f"   Similarity Score: {cat['similarity']:.4f}")
                    
                    # Find similar charities
                    similar_charities = self.find_similar_charities(article)
                    
                    if similar_charities and subscribers:
                        # Get urgency score
                        urgency_result = self.get_urgency_score(article)
                        print("\nUrgency Assessment:")
                        print(urgency_result)
                        
                        # Add similar charities to article before GPT analysis
                        article['similar_charities'] = similar_charities
                        
                        # Update user portfolios
                        self.update_user_portfolios(subscribers, matching_categories[0]['category'],similar_charities, urgency_result)
                    
                    else:
                        print("No similar charities found.")
                    
                    # Mark article as processed
                    self.processed_articles.add(article['link'])
                    self.save_processed_articles()
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Error occurred: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying 