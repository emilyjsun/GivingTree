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
            
            print(f"Searching for charities with category ID: {category_id}")
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
                    print(f"Charity: {doc['name']}")
                    charity_data = {
                        'name': doc['name'],
                        'mission': doc['mission_statement'],
                        'similarity_score': 1 - (results['distances'][0][i] / 2)
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