from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np
import json
from datetime import datetime
from queue import PriorityQueue
import heapq

class User:
    def __init__(self, uid, wallet_address, categories=None, instant_updates=False):
        self.uid = uid
        self.wallet_address = wallet_address
        self.categories = categories or []  # List of (category, confidence) tuples
        self.instant_updates = instant_updates
        self.portfolio = []  # List of (priority, charity) tuples for heapq

    def to_dict(self):
        return {
            "uid": self.uid,
            "wallet_address": self.wallet_address,
            "categories": [(cat, float(conf)) for cat, conf in self.categories],
            "instant_updates": self.instant_updates,
            "portfolio": [(float(pri), char) for pri, char in self.portfolio],
        }

    @classmethod
    def from_dict(cls, data):
        user = cls(data['uid'], data['wallet_address'])
        user.categories = [(cat, float(conf)) for cat, conf in data['categories']]
        user.instant_updates = data['instant_updates']
        user.portfolio = [(float(pri), char) for pri, char in data['portfolio']]
        return user

class UserDatabase:
    def __init__(self, filename='user_database.json'):
        self.filename = filename
        self.users = self.load_database()

    def load_database(self):
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                return {uid: User.from_dict(user_data) for uid, user_data in data.items()}
        except FileNotFoundError:
            return {}

    def save_database(self):
        with open(self.filename, 'w') as f:
            json.dump({uid: user.to_dict() for uid, user in self.users.items()}, f, indent=2)

    def add_user(self, wallet_address, categories, instant_updates):
        uid = f"user_{int(datetime.now().timestamp())}_{hash(wallet_address) % 10000:04d}"
        user = User(uid, wallet_address, categories, instant_updates)
        self.users[uid] = user
        self.save_database()
        return uid

    def update_user_portfolio(self, uid, charities):
        """Update user's charity portfolio with priority queue"""
        if uid in self.users:
            # Clear existing portfolio
            self.users[uid].portfolio = []
            # Add new charities with priorities
            for priority, charity in charities:
                heapq.heappush(self.users[uid].portfolio, (float(priority), charity))
            self.save_database()

    def get_user(self, uid):
        return self.users.get(uid)

    def get_users_by_category(self, category):
        """Get all users interested in a specific category"""
        return [user for user in self.users.values() 
                if any(cat == category for cat, _ in user.categories)]

class CharityInputCategorizer:
    def __init__(self):
        print("initializing")
        
        # Simplified categories list
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

        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./vector_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name="user_inputs",
            metadata={"description": "User input categorization"}
        )
        
        # Initialize category embeddings
        self.category_embeddings = self._generate_category_embeddings()
        
        # Load processed inputs history
        self.processed_inputs = self._load_processed_inputs()

        # Initialize category subscribers database
        self.category_subscribers = self._load_category_subscribers()

    def _generate_category_embeddings(self):
        """Generate embeddings for categories"""
        print("generating category embeddings")
        return self.model.encode(self.CATEGORIES)

    def _load_processed_inputs(self):
        print("loading processed inputs")
        try:
            with open('processed_inputs.json', 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()

    def save_processed_inputs(self):
        print("saving processed inputs")
        with open('processed_inputs.json', 'w') as f:
            json.dump(list(self.processed_inputs), f)

    def _load_category_subscribers(self):
        """Load or initialize category subscribers database"""
        print("loading category subscribers")
        try:
            with open('category_subscribers.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Initialize empty subscriber lists for each category
            return {category: [] for category in self.CATEGORIES}

    def save_category_subscribers(self):
        """Save category subscribers to file"""
        print("saving category subscribers")
        with open('category_subscribers.json', 'w') as f:
            json.dump(self.category_subscribers, f)

    def categorize_input(self, user_input: str) -> list:
        """
        Categorize user input using similarity search against categories.
        Returns top 3 categories with their similarity scores.
        """
        # Generate embedding for user input
        print("generating input embedding")
        input_embedding = self.model.encode(user_input)
        
        # Calculate similarities
        print("calculating similarities")
        similarities = np.dot(self.category_embeddings, input_embedding)
        
        # Get top 3 indices
        top_indices = np.argsort(similarities)[-3:][::-1]
        
        # Get top 3 categories and scores
        results = []
        for idx in top_indices:
            category = self.CATEGORIES[idx]
            score = float(similarities[idx])
            results.append((category, score))
        
        print("returning top 3 categories and similarity scores")
        return results

    def store_input(self, user_input: str, categories: list, instant_updates: str = 'false'):
        """Store user input and update category subscribers"""
        print("storing input")
        
        # Generate a unique user ID (using timestamp + random number for uniqueness)
        user_id = f"user_{int(datetime.now().timestamp())}_{hash(user_input) % 10000:04d}"
        
        if user_id not in self.processed_inputs:
            # Store in ChromaDB
            embedding = self.model.encode(user_input).tolist()
            self.collection.add(
                documents=[user_input],
                metadatas=[{
                    "primary_category": categories[0][0],
                    "all_categories": ",".join([cat for cat, _ in categories]),
                    "all_scores": ",".join([f"{score:.4f}" for _, score in categories]),
                    "timestamp": datetime.now().isoformat(),
                    "instant_updates": instant_updates,
                    "user_id": user_id  # Store the user ID in metadata
                }],
                embeddings=[embedding],
                ids=[user_id]  # Use user_id as the document ID
            )
            
            # Update category subscribers with user ID
            for category, _ in categories:
                if user_id not in self.category_subscribers[category]:
                    self.category_subscribers[category].append(user_id)
            self.save_category_subscribers()
            
            # Mark as processed
            self.processed_inputs.add(user_id)
            self.save_processed_inputs()
            
            return user_id  # Return the generated user ID

    def process_input(self, user_input: str, instant_updates: str = 'false') -> dict:
        """
        Process a single user input and return results.
        """
        print("processing input")
        categories = self.categorize_input(user_input)
        user_id = self.store_input(user_input, categories, instant_updates)
        
        return {
            "user_id": user_id,
            "input": user_input,
            "categories": categories,
            "instant_updates": instant_updates
        }

    def view_database(self):
        """Display all entries in the vector database"""
        print("\n📊 Database Contents:")
        print("━" * 50)
        
        # Get all entries from the collection
        results = self.collection.get()
        
        if not results['ids']:
            print("Database is empty.")
            return
        
        # Display each entry
        for i in range(len(results['ids'])):
            print(f"\nEntry {i+1}:")
            print(f"User ID: {results['ids'][i]}")
            print(f"Input: {results['documents'][i]}")
            print(f"Primary Category: {results['metadatas'][i]['primary_category']}")
            print(f"Instant Updates: {'✅' if results['metadatas'][i]['instant_updates'] == 'true' else '❌'}")
            
            # Split and display all categories and scores
            categories = results['metadatas'][i]['all_categories'].split(',')
            scores = [float(score) for score in results['metadatas'][i]['all_scores'].split(',')]
            
            print("\nTop 3 Categories:")
            for cat, score in zip(categories, scores):
                print(f"- {cat}: {score:.2%}")
            
            print(f"Timestamp: {results['metadatas'][i]['timestamp']}")
            print("-" * 30)

    def view_category_subscribers(self):
        """Display subscribers for each category"""
        print("\n📋 Category Subscribers:")
        print("━" * 50)
        
        for category in self.CATEGORIES:
            subscriber_count = len(self.category_subscribers[category])
            print(f"\n{category}:")
            if subscriber_count == 0:
                print("  No subscribers")
            else:
                print(f"  {subscriber_count} subscribers:")
                # Get subscriber details from ChromaDB
                for user_id in self.category_subscribers[category]:
                    try:
                        result = self.collection.get(ids=[user_id])
                        if result['documents']:
                            print(f"  - User ID: {user_id}")
                            print(f"    Input: {result['documents'][0]}")
                    except Exception as e:
                        print(f"  - Error retrieving subscriber {user_id}: {str(e)}")

def main():
    categorizer = CharityInputCategorizer()
    user_db = UserDatabase()
    
    print("\nhello")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            print("\n1. Enter new humanitarian concern")
            print("2. View all stored entries")
            print("3. View category subscribers")
            print("4. Exit")
            
            choice = input("\nChoose an option (1-4): ")
            
            if choice == "1":
                print("\n" + "-"*50)
                wallet_address = input("Please enter your wallet address: ")
                user_input = input("Please describe your humanitarian concern: ")
                
                if not user_input.strip() or not wallet_address.strip():
                    print("Please enter valid input and wallet address.")
                    continue
                
                # Ask about instant updates
                while True:
                    updates_choice = input("Would you like instant updates for this concern? (yes/no): ").lower()
                    if updates_choice in ['yes', 'no']:
                        break
                    print("Please enter 'yes' or 'no'")
                
                # Process input
                result = categorizer.process_input(user_input)
                
                # Add user to database
                uid = user_db.add_user(
                    wallet_address=wallet_address,
                    categories=result['categories'],
                    instant_updates=(updates_choice == 'yes')
                )
                
                # Display results
                print(f"\n🆔 User ID: {uid}")
                print("\n📊 Top 3 Matching Categories:")
                print("━"*50)
                for i, (category, confidence) in enumerate(result['categories'], 1):
                    print(f"{i}. 🏷️  {category}")
                    print(f"   ✨ Confidence: {confidence:.2%}")
                
            elif choice == "2":
                print("\n📊 User Database Contents:")
                print("━" * 50)
                for uid, user in user_db.users.items():
                    print(f"\nUser ID: {uid}")
                    print(f"Wallet: {user.wallet_address}")
                    print("Categories:")
                    for category, confidence in user.categories:
                        print(f"  - {category}: {confidence:.2%}")
                    print(f"Instant Updates: {'✅' if user.instant_updates else '❌'}")
                    if user.portfolio:
                        print("Charity Portfolio:")
                        for priority, charity in sorted(user.portfolio):
                            print(f"  - {charity}: {priority:.2f}")
                    print("-" * 30)
                
            elif choice == "3":
                category = input("Enter category to view subscribers: ")
                users = user_db.get_users_by_category(category)
                print(f"\nSubscribers for {category}:")
                for user in users:
                    print(f"User ID: {user.uid}")
                    print(f"Wallet: {user.wallet_address}")
                    confidence = next(conf for cat, conf in user.categories if cat == category)
                    print(f"Confidence: {confidence:.2%}")
                    print("-" * 30)
                
            elif choice == "4" or choice.lower() == 'quit':
                print("\nquitting")
                break
                
            else:
                print("\nInvalid choice. Please try again.")
                
        except Exception as e:
            print(f"\n❌ Error occurred: {str(e)}")
            print("Please try again with a different input.")

if __name__ == "__main__":
    main()