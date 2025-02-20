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
from pg_module import (
    get_charities_for_category,
    get_users_for_category,
    get_names_of_charities,
    get_addresses_of_charities,
    CharityAddress
)
import os
from web3_utils.interact_with_contract import get_user, set_charities, contract, split_among_charities


from pg_module.models import UserCategory

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class NewsCharityMatcher:
    def __init__(self, postgres_db):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = openai.OpenAI(api_key=self.api_key)
        self.processed_articles = set()
        self.postgres_db = postgres_db

        # Initialize ChromaDB client
        try:
            self.chroma_client = chromadb.HttpClient(
                ssl=True,
                host="api.trychroma.com",
                tenant="06afecae-2671-4d45-ae27-4d721cfbdbf5",
                database="treehacks_charities",
                headers={"x-chroma-token": os.getenv("CHROMA_API_KEY")},
            )
        except Exception as e:
            print(f"Error initializing ChromaDB client: {e}")
            raise RuntimeError(f"Failed to initialize ChromaDB client: {str(e)}")

        # Get existing collections
        self.categories_collection = self.chroma_client.get_collection("categories")
        self.charities_collection = self.chroma_client.get_collection("charities")

        # Load categories from ChromaDB
        categories_result = self.categories_collection.get()
        self.CATEGORIES = [doc for doc in categories_result["documents"]]
        self.category_ids = {
            cat: id
            for id, cat in zip(categories_result["ids"], categories_result["documents"])
        }

        # Load processed articles history
        try:
            with open("processed_articles.json", "r") as f:
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
                        articles.append(
                            {
                                "title": entry.title,
                                "description": entry.get("description", ""),
                                "link": entry.link,
                            }
                        )
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

            top_category = matching_categories[0]["category"]
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
                n_results=n_results,
            )

            similar_charities = []
            if results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    doc = json.loads(results["documents"][0][i])
                    print(f"Charity: {doc['name']}")
                    charity_data = {
                        "name": doc["name"],
                        "mission": doc["mission_statement"],
                        "similarity_score": 1 - (results["distances"][0][i] / 2),
                    }
                    similar_charities.append(charity_data)

            return similar_charities

        except Exception as e:
            print(f"Error finding similar charities: {e}")
            return []

    def save_processed_articles(self):
        with open("processed_articles.json", "w") as f:
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
                            "reason": {
                                "type": "string",
                                "description": "Reason for marking as relevant",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_irrelevant",
                    "description": "Mark an article as irrelevant to charity impact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Reason for marking as irrelevant",
                            }
                        },
                    },
                },
            },
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
    Mark articles as relevant if there's any potential charitable impact.""",
            },
            {
                "role": "user",
                "content": f"Analyze this article for charitable impact:\nTitle: {title}\nDescription: {description}",
            },
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
                    "Content-Type": "application/json",
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
                                "content": "You are a research analyst specializing in analyzing news articles. Provide comprehensive context and analysis.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return (
                        f"Error getting additional information: {response.status_code}"
                    )

            except Exception as e:
                return f"Error in research: {str(e)}"

        try:
            while not completed:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
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
                                args.get("article_description", description),
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "content": more_info,
                                    "tool_call_id": tool_call.id,
                                }
                            )

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
                query_texts=[article_text], n_results=3
            )

            # Check if we got valid results
            if (
                not results
                or not results.get("documents")
                or not results["documents"][0]
            ):
                print("No matching categories found")
                return [], []

            # Format results
            categories = []
            distances = results["distances"][0]

            # Normalize distances to similarities (0 to 1 range)
            max_distance = max(distances)
            min_distance = min(distances)
            range_distance = (
                max_distance - min_distance if max_distance != min_distance else 1
            )

            for i in range(len(distances)):
                category = results["documents"][0][
                    i
                ]  # Get category name directly from documents
                # Convert distance to normalized similarity score
                normalized_similarity = 1 - (
                    (distances[i] - min_distance) / range_distance
                )
                categories.append(
                    {"category": category, "similarity": normalized_similarity}
                )

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
                    {
                        "role": "system",
                        "content": "You are an expert at assessing humanitarian and charitable funding urgency. Be objective and analytical in your assessment.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            result = response.choices[0].message.content.strip()
            return result

        except Exception as e:
            print(f"Error getting urgency score: {e}")
            return "Urgency Score: N/A\nBrief Reason: Error in assessment"

    def update_user_portfolios(
        self, subscribers: list[UserCategory], category, similar_charities, article
    ):
        """Update user portfolios using an AI portfolio manager"""
        try:
            # Get urgency score for the article
            urgency_result = self.get_urgency_score(article)
            print("\nUrgency Assessment:")
            print(urgency_result)
            urgency_score = (
                float(urgency_result.split("\n")[0].split(": ")[1])
                if "Score:" in urgency_result
                else 5.0
            )

            # For each subscriber
            for user in subscribers:
                user_id = user.userid
                print(f"\nAnalyzing portfolio for user {user_id}")

                user_object = get_user(contract, user_id)
                if not user_object:
                    print(f"User {user_id} not found in database")
                    continue
                portfolio_addresses = user_object.addresses
                portfolio_percentages = user_object.percentages

                # Get the names of the charities

                portfolio_charity_names = get_names_of_charities(self.postgres_db, portfolio_addresses)

                # TODO: Add mission statements of the charities, not just their names

                # Agentic loop
                new_charity_names = portfolio_charity_names
                new_charity_percents = portfolio_percentages
                has_changed = False
                running = True

                def keep_portfolio():
                    nonlocal running
                    running = False
                    if has_changed:
                        # TODO: fetch new charity addresses
                        new_charity_addresses: list[CharityAddress] = get_addresses_of_charities(self.postgres_db, new_charity_names)

                        new_charity_addresses.sort(key = lambda x: new_charity_names.index(x.name))

                        set_charities(
                            contract,
                            user_id,
                            new_charity_addresses,
                            new_charity_percents,
                        )
                        print(f"Updated portfolio for user {user_id}")

                    return "Keeping the current portfolio without changes"

                def update_portfolio(new_charities, new_percents):
                    nonlocal new_charity_names, new_charity_percents, has_changed
                    new_charity_names = new_charities
                    new_charity_percents = new_percents
                    has_changed = True
                    return f"Portfolio updated with new charities and percentages:\n{convert_charity_list_to_text()}"

                def send_money():
                    nonlocal running
                    print(f"Sending money to charities in portfolio for user {user_id}")
                    split_among_charities(contract, user_id)
                    running = False
                    return "Money sent to charities in portfolio"

                def convert_charity_list_to_text():
                    if not new_charity_names:
                        return "No charities in the portfolio"
                    return "\n".join(
                        [
                            f"{name} ({percent}%)"
                            for name, percent in zip(
                                new_charity_names, new_charity_percents
                            )
                        ]
                    )

                # Agentic loop

                messages = [
                    {
                        "role": "system",
                        "content": f"User {user_id}, you are a portfolio manager for a charity impact fund. Your job is to manage the fund's portfolio of charities to maximize social impact. You have the following charities in your portfolio:\n{convert_charity_list_to_text()}",
                    },
                    {
                        "role": "user",
                        "content": "Analyze the portfolio and make any necessary changes based on the article and the new charities. Call the 'keep_portfolio' function if you want to keep the current portfolio without changes, the 'update_portfolio' function if you want to update the portfolio with new charities and percentages, or the 'send_money' function if you want to send money to the charities in the portfolio. Make sure the charity percentages sum to 100, and end the conversation by calling the 'keep_portfolio' function.",
                    },
                    {
                        "role": "system",
                        "content": f"Article Title: {article['title']}\nDescription: {article.get('description', '')}\nCategory: {category}\nUrgency Score: {urgency_score}\nSimilar Charities:\n{json.dumps(similar_charities, indent=2)}",
                    },
                ]

                while running:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        tools=[
                            {
                                "type": "function",
                                "function": {
                                    "name": "keep_portfolio",
                                    "description": "Keep the current portfolio without changes",
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "update_portfolio",
                                    "description": "Update the portfolio with new charities and percentages",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "new_charities": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                            "new_percents": {
                                                "type": "array",
                                                "items": {"type": "number"},
                                            },
                                        },
                                    },
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "send_money",
                                    "description": "Send money to charities in the portfolio",
                                },
                            },
                        ],
                        tool_choice="auto",
                    )

                    message = response.choices[0].message
                    messages.append(message)

                    for tool_call in message.tool_calls:
                        args = json.loads(tool_call.function.arguments)

                        if tool_call.function.name == "keep_portfolio":
                            result = keep_portfolio()
                        elif tool_call.function.name == "update_portfolio":
                            result = update_portfolio(
                                args.get("new_charities", []),
                                args.get("new_percents", []),
                            )
                        elif tool_call.function.name == "send_money":
                            result = send_money()

                        messages.append(
                            {
                                "role": "tool",
                                "content": result,
                                "tool_call_id": tool_call.id,
                            }
                        )

                print(f"Portfolio updated for user {user_id}")

        except Exception as e:
            print(f"Error updating user portfolios: {e}")

    def run(self, rss_urls, interval=300):  # interval in seconds (default 5 minutes)
        while True:
            try:
                print(f"\nChecking for new articles at {datetime.now()}")
                articles = self.get_rss_feeds(rss_urls)

                for article in articles:
                    print("\n" + "=" * 50)
                    print(f"Processing new article...")

                    # Check if article is relevant using GPT
                    if not self.is_relevant_article(
                        article["title"], article.get("description", "")
                    ):
                        print("Skipping article based on GPT response")
                        continue

                    print("Article deemed relevant - continuing analysis...")
                    print(f"\nAnalyzing article: {article['title']}")

                    # Find matching categories and subscribers
                    matching_categories, subscribers = self.find_matching_categories(
                        article
                    )
                    print("\nMatching Categories:")
                    for i, cat in enumerate(matching_categories, 1):
                        print(f"{i}. {cat['category']}")
                        print(f"   Similarity Score: {cat['similarity']:.4f}")

                    # Find similar charities
                    similar_charities = self.find_similar_charities(article)

                    if similar_charities and subscribers:
                        # Update user portfolios
                        self.update_user_portfolios(
                            subscribers,
                            matching_categories[0]["category"],
                            similar_charities,
                            article,
                        )

                    else:
                        print("No similar charities found.")

                    # Mark article as processed
                    self.processed_articles.add(article["link"])
                    self.save_processed_articles()

                time.sleep(interval)

            except Exception as e:
                print(f"Error occurred: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
