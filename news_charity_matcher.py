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
from pg_module import get_charities_for_category, get_users_for_category
import os

from pg_module.models import UserCategory

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class NewsCharityMatcher:
    def __init__(self, postgres_db):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.client = openai.OpenAI(api_key=self.api_key)
        self.processed_articles = set()
        self.postgres_db = postgres_db
        
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
            "Community Development",
            "Animal Welfare"
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
            matching_categories, subscribers = self.find_matching_categories(article)
            if not matching_categories:
                return []
            
            top_category = matching_categories[0]['category']
            print(f"\nFiltering charities by top category: {top_category}")
            
            # Get all charities that match the category
            category_filtered = get_charities_for_category(self.postgres_db, top_category)
            
            print(f"Found {len(category_filtered)} charities in category '{top_category}'")
            
            if not category_filtered:
                print("No charities found in this category")
                return []
            
            # Now do similarity search between article and filtered charities' missions
            article_text = f"{article['title']} {article.get('description', '')}"
            similar_charities = []
            
            # Create a temporary collection for similarity search
            temp_collection = self.chroma_client.get_or_create_collection(
                name="temp_category_search",
                embedding_function=self.collection._embedding_function
            )
            
            try:
                # Add filtered charities to temp collection
                temp_collection.add(
                    documents=[c.mission for c in category_filtered],
                    metadatas=[{'name': c.name, 'url': c.url, 'mission': c.mission} for c in category_filtered],
                    ids=[str(i) for i in range(len(category_filtered))]
                )
                
                print(f"Added {len(category_filtered)} charities to temp collection")
                
                # Perform similarity search
                search_results = temp_collection.query(
                    query_texts=[article_text],
                    n_results=min(n_results, len(category_filtered))
                )
                
                print(f"Query results: {len(search_results['ids'][0])} matches found")
                
                # Process results
                if len(search_results['ids'][0]) > 0:
                    for i in range(len(search_results['ids'][0])):
                        charity_data = {
                            'name': search_results['metadatas'][0][i]['name'],
                            'url': search_results['metadatas'][0][i]['url'],
                            'mission': search_results['metadatas'][0][i]['mission'],
                            'similarity_score': 1 - (search_results['distances'][0][i] / 2)
                        }
                        similar_charities.append(charity_data)
                    print(f"Processed {len(similar_charities)} charity matches")
                else:
                    print("No matches found in similarity search")
                
            except Exception as e:
                print(f"Error during similarity search: {e}")
            finally:
                # Delete temporary collection
                try:
                    self.chroma_client.delete_collection("temp_category_search")
                    print("Temporary collection deleted")
                except Exception as e:
                    print(f"Error deleting temporary collection: {e}")
            
            return similar_charities
            
        except Exception as e:
            print(f"Error in overall process: {e}")
            print(f"Article text: {article_text[:100]}...")
            print(f"Category filtered charities: {len(category_filtered)}")
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
                model="gpt-4o-mini",
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
                subscribers = get_users_for_category(self.postgres_db, category)
                    
        
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

    def update_user_portfolios(self, subscribers: list[UserCategory], category, similar_charities, article):
        """Update user portfolios using an AI portfolio manager"""
        try:
            # Get urgency score for the article
            urgency_result = self.get_urgency_score(article)
            print("\nUrgency Assessment:")
            print(urgency_result)
            urgency_score = float(urgency_result.split('\n')[0].split(': ')[1]) if 'Score:' in urgency_result else 5.0
            
            # Load user database
            with open('user_database.json', 'r') as f:
                user_db = json.load(f)
            
            # For each subscriber
            for user in subscribers:
                user_id = user.userid
                print(f"\nAnalyzing portfolio for user {user_id}")

                if user_id not in user_db:
                    continue
                
                # Get user's current portfolio and preferences
                current_portfolio = user_db[user_id].get('portfolio', [])
                user_categories = user_db[user_id]['categories']
                
                # Prepare context for AI portfolio manager
                portfolio_prompt = f"""
As an experienced charity donation portfolio manager, analyze this situation and optimize the portfolio.

ARTICLE CONTEXT:
Title: {article['title']}
Description: {article['description']}
Category: {category}
Urgency Level: {urgency_score}/10

USER PROFILE:
Current Portfolio (max 10 charities):
{[f"- {name}: {score:.2%}" for name, score in current_portfolio]}

Category Preferences: {user_categories}

AVAILABLE CHARITIES TO CONSIDER:
{[f"- {c['name']}\nMission: {c['mission'][:200]}...\nSimilarity Score: {c['similarity_score']:.2f}" for c in similar_charities]}

TASK:
1. Analyze the potential impact of new charities compared to existing portfolio
2. Consider:
   - Article's urgency ({urgency_score}/10)
   - User's category preferences
   - Portfolio diversity
   - Charity mission alignment
   - Current portfolio composition
3. If portfolio is full (10 charities), decide if any new charities should replace existing ones

Provide your recommendations in this exact format:
PORTFOLIO_UPDATE:
KEEP:
charity_name1||relevance_score
charity_name2||relevance_score
[list charities to keep]

ADD:
charity_name3||relevance_score
charity_name4||relevance_score
[list new charities to add]

REMOVE:
charity_name5||previous_score
charity_name6||previous_score
[list charities to remove if needed]

Notes:
- Relevance scores must be between 0 and 1
- Total portfolio size cannot exceed 10 charities
- Only recommend removing charities if new ones would significantly improve the portfolio
- Explain your reasoning after the recommendations
"""

                try:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are an experienced charity donation portfolio manager with expertise in impact investing and charitable giving. Your goal is to help users maintain well-balanced, impactful charitable portfolios that align with their interests and current events. Make strategic decisions about portfolio composition."},
                            {"role": "user", "content": portfolio_prompt}
                        ],
                        temperature=0.3
                    )
                    
                    # Parse AI recommendations
                    recommendations = response.choices[0].message.content
                    keep_charities = []
                    add_charities = []
                    remove_charities = set()
                    
                    # Parse sections
                    if "PORTFOLIO_UPDATE:" in recommendations:
                        sections = recommendations.split("PORTFOLIO_UPDATE:")[1].split("\n\n")
                        for section in sections:
                            if section.startswith("KEEP:"):
                                for line in section.split("\n")[1:]:
                                    if "||" in line:
                                        name, score = line.split("||")
                                        try:
                                            keep_charities.append((name.strip(), float(score.strip())))
                                        except:
                                            continue
                            elif section.startswith("ADD:"):
                                for line in section.split("\n")[1:]:
                                    if "||" in line:
                                        name, score = line.split("||")
                                        try:
                                            add_charities.append((name.strip(), float(score.strip())))
                                        except:
                                            continue
                            elif section.startswith("REMOVE:"):
                                for line in section.split("\n")[1:]:
                                    if "||" in line:
                                        name, _ = line.split("||")
                                        remove_charities.add(name.strip())
                    
                    # Build new portfolio
                    new_portfolio = []
                    
                    # Add kept charities
                    for charity in current_portfolio:
                        if charity[0] not in remove_charities:
                            new_portfolio.append(charity)
                    
                    # Add new charities
                    new_portfolio.extend(add_charities)
                    
                    # Sort and limit to top 10
                    user_db[user_id]['portfolio'] = sorted(
                        new_portfolio, 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10]
                    
                    # Print updates
                    print(f"\nPortfolio updates for user {user_id}:")
                    if remove_charities:
                        print("\nRemoved charities:")
                        for name in remove_charities:
                            print(f"- {name}")
                    
                    if add_charities:
                        print("\nAdded charities:")
                        for name, score in add_charities:
                            print(f"- {name} ({score:.2%})")
                    
                    print("\nFinal Portfolio:")
                    for charity_name, relevance in user_db[user_id]['portfolio']:
                        print(f"Charity: {charity_name}")
                        print(f"Relevance Score: {relevance:.2%}")
                        print("-" * 30)
                    
                except Exception as e:
                    print(f"Error in AI portfolio analysis: {e}")
                    continue
            
            # Save updated user database
            with open('user_database.json', 'w') as f:
                json.dump(user_db, f, indent=2)
            
        except Exception as e:
            print(f"Error updating user portfolios: {e}")

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
                        # Update user portfolios
                        self.update_user_portfolios(subscribers, matching_categories[0]['category'],similar_charities, article)
                    
                    else:
                        print("No similar charities found.")
                    
                    # Mark article as processed
                    self.processed_articles.add(article['link'])
                    self.save_processed_articles()
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Error occurred: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying