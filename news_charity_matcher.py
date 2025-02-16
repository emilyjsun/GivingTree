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
from web3_utils.interact_with_contract import (
    contract,
    get_user,
    set_charities,
    split_among_charities,
    get_balance_of_user
)

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
        
        # Initialize ChromaDB client
        try:
            self.chroma_client = chromadb.HttpClient(
                ssl=True,
                host='api.trychroma.com',
                tenant='06afecae-2671-4d45-ae27-4d721cfbdbf5',
                database='treehacks_charities',
                headers={
                    'x-chroma-token': os.getenv('CHROMA_API_KEY')
                }
            )
        except Exception as e:
            print(f"Error initializing ChromaDB client: {e}")
            raise RuntimeError(f"Failed to initialize ChromaDB client: {str(e)}")
        
        # Get existing collections
        self.categories_collection = self.chroma_client.get_collection('categories')
        self.charities_collection = self.chroma_client.get_collection('charities')
        
        # Load categories from ChromaDB
        categories_result = self.categories_collection.get()
        self.CATEGORIES = [doc for doc in categories_result['documents']]
        self.category_ids = {cat: id for id, cat in zip(categories_result['ids'], categories_result['documents'])}
    
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

    def find_similar_charities(self, article, n_results=5):
        """Find charities similar to the article using semantic search."""
        try:
            # First, get the top category for the article
            matching_categories, subscribers = self.find_matching_categories(article)
            if not matching_categories:
                return []
            
            top_category = matching_categories[0]['category']
            print(f"\nFiltering charities by top category: {top_category}")
            
            # Get category ID
            category_id = self.category_ids.get(top_category)
            if not category_id:
                print(f"Category ID not found for {top_category}")
                return []
            
            # Query charities collection with category filter
            article_text = f"{article['title']} {article.get('description', '')}"
            results = self.charities_collection.query(
                query_texts=[article_text],
                where={"category_id": {"$eq": category_id}},
                n_results=n_results
            )
            
            similar_charities = []
            if results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = json.loads(results['documents'][0][i])
                    
                    # Get charity's contract balance
                    try:
                        balance = get_balance_of_user(contract, doc['wallet_address'])
                        print(f"Charity {doc['name']} balance: {balance} ETH")
                    except Exception as e:
                        print(f"Error getting charity balance: {e}")
                        balance = 0
                    
                    charity_data = {
                        'name': doc['name'],
                        'mission': doc['mission_statement'],
                        'wallet_address': doc['wallet_address'],
                        'similarity_score': 1 - (results['distances'][0][i] / 2),
                        'current_balance': balance
                    }
                    similar_charities.append(charity_data)
            
            return similar_charities
            
        except Exception as e:
            print(f"Error finding similar charities: {e}")
            return []

    def save_processed_articles(self):
        with open('processed_articles.json', 'w') as f:
            json.dump(list(self.processed_articles), f)


    def is_relevant_article(self, title: str, description: str):
        """Use an AI agent to determine if an article is relevant to charity impact."""
    
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "mark_relevant",
                    "description": "Mark an article as relevant to charity impact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for marking as relevant"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_irrelevant",
                    "description": "Mark an article as irrelevant to charity impact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for marking as irrelevant"}
                        }
                    }
                }
            }
        ]

        is_relevant = False
        completed = False
        messages = [
            {
                "role": "system", 
                "content": """You are a charity impact analyst. Your job is to determine if news articles could affect charitable giving or create needs for charitable work.
                
    Consider:
    - Could this affect people's willingness or ability to donate?
    - Might this create new needs for charitable assistance?
    - Could this influence how charities operate?
    - Might this affect vulnerable populations?

    If you're uncertain, use request_more_info to research the article before deciding.
    Mark articles as relevant if there's any potential charitable impact."""
            },
            {
                "role": "user", 
                "content": f"Analyze this article for charitable impact:\nTitle: {title}\nDescription: {description}"
            }
        ]

        def mark_relevant(reason):
            nonlocal is_relevant, completed
            print(f"Marking as RELEVANT: {reason}")
            is_relevant = True
            completed = True

        def mark_irrelevant(reason):
            nonlocal is_relevant, completed
            print(f"Marking as IRRELEVANT: {reason}")
            is_relevant = False
            completed = True

        def request_more_info(article_title, article_description):
            """Use Perplexity Sonar to get deeper context about an article."""
            try:
                headers = {
                    "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
                    "Content-Type": "application/json"
                }
                
                prompt = f"""
                Research this news article in detail:
                Title: {article_title}
                Description: {article_description}
                
                Please provide:
                1. Background context
                2. More information about the article
                """
                
                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json={
                        "model": "sonar",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a research analyst specializing in analyzing news articles. Provide comprehensive context and analysis."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"Error getting additional information: {response.status_code}"
                    
            except Exception as e:
                return f"Error in research: {str(e)}"

        try:
            while not completed:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments)
                        
                        if tool_call.function.name == "mark_relevant":
                            mark_relevant(args.get("reason", "No reason provided"))
                        
                        elif tool_call.function.name == "mark_irrelevant":
                            mark_irrelevant(args.get("reason", "No reason provided"))
                        
                        elif tool_call.function.name == "request_more_info":
                            more_info = request_more_info(
                                args.get("article_title", title),
                                args.get("article_description", description)
                            )
                            messages.append({
                                "role": "tool",
                                "content": more_info,
                                "tool_call_id": tool_call.id
                            })
            
            return is_relevant
            
        except Exception as e:
            print(f"Error in article relevance check: {e}")
            return True  # Default to including article if check fails

    def find_matching_categories(self, article):
        """Find top 3 matching categories for an article."""
        try:
            # Combine title and description for better matching
            article_text = f"{article['title']} {article.get('description', '')}"
            
            print("\nQuerying categories collection...")
            # Query the category collection
            results = self.categories_collection.query(
                query_texts=[article_text],
                n_results=3
            )
                        
            # Check if we got valid results
            if not results or not results.get('documents') or not results['documents'][0]:
                print("No matching categories found")
                return [], []
            
            # Format results
            categories = []
            distances = results['distances'][0]
            
            # Normalize distances to similarities (0 to 1 range)
            max_distance = max(distances)
            min_distance = min(distances)
            range_distance = max_distance - min_distance if max_distance != min_distance else 1
            
            for i in range(len(distances)):
                category = results['documents'][0][i]  # Get category name directly from documents
                # Convert distance to normalized similarity score
                normalized_similarity = 1 - ((distances[i] - min_distance) / range_distance)
                categories.append({
                    'category': category,
                    'similarity': normalized_similarity
                })
                
                # Get subscribers for top category
                if i == 0:  # Only for the top category
                    subscribers = get_users_for_category(self.postgres_db, category)
            
            print(f"\nMatched categories: {json.dumps(categories, indent=2)}")
            return categories, subscribers
            
        except Exception as e:
            print(f"Error in find_matching_categories: {str(e)}")
            print(f"Article text: {article_text}")
            return [], []

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
        """Update user portfolios and smart contract allocations"""
        try:
            # Get urgency score for the article
            urgency_result = self.get_urgency_score(article)
            print("\nUrgency Assessment:")
            print(urgency_result)
            urgency_score = float(urgency_result.split('\n')[0].split(': ')[1]) if 'Score:' in urgency_result else 5.0
            
            # For each subscriber
            for user in subscribers:
                user_id = user.userid
                wallet_address = user.wallet_address
                print(f"\nAnalyzing portfolio for user {user_id} (wallet: {wallet_address})")
                
                try:
                    # Get user's current contract state
                    contract_user = get_user(contract, wallet_address)
                    print(f"Current contract balance: {contract_user.balance} ETH")
                    
                    # Get charity addresses and calculate new percentages
                    charity_addresses = []
                    charity_percentages = []
                    
                    # Sort charities by combined score (similarity + current balance weight)
                    for charity in similar_charities:
                        charity['combined_score'] = (
                            charity['similarity_score'] * 0.7 +  # 70% weight on similarity
                            (1 / (charity['current_balance'] + 1)) * 0.3  # 30% weight on inverse of current balance
                        )
                    
                    sorted_charities = sorted(similar_charities, key=lambda x: x['combined_score'], reverse=True)
                    
                    # Take top charities and assign percentages based on combined scores
                    total_score = sum(c['combined_score'] for c in sorted_charities)
                    for charity in sorted_charities:
                        charity_addresses.append(charity['wallet_address'])
                        percentage = int((charity['combined_score'] / total_score) * 100)
                        charity_percentages.append(percentage)
                    
                    # Adjust percentages to sum to 100
                    while sum(charity_percentages) < 100:
                        charity_percentages[0] += 1
                    
                    # Update contract with new charity allocations
                    print(f"Updating contract with {len(charity_addresses)} charities")
                    for addr, pct in zip(charity_addresses, charity_percentages):
                        print(f"Charity {addr}: {pct}%")
                    
                    set_charities(contract, wallet_address, charity_addresses, charity_percentages)
                    
                    # If urgency is high, trigger immediate split
                    if urgency_score >= 8.0:
                        print(f"High urgency ({urgency_score}/10) - triggering immediate split")
                        split_among_charities(contract, wallet_address)
                    
                except Exception as e:
                    print(f"Error updating contract for user {user_id}: {e}")
                    continue
            
        except Exception as e:
            print(f"Error in portfolio update: {e}")

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