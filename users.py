from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np
import json
from datetime import datetime

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
                user_input = input("Please describe your humanitarian concern: ")
                
                if not user_input.strip():
                    print("Please enter a valid input.")
                    continue
                
                # Ask about instant updates
                while True:
                    updates_choice = input("Would you like instant updates for this concern? (yes/no): ").lower()
                    if updates_choice in ['yes', 'no']:
                        break
                    print("Please enter 'yes' or 'no'")
                
                # Convert yes/no to true/false
                instant_updates = "true" if updates_choice == "yes" else "false"
                    
                # Process input
                result = categorizer.process_input(user_input, instant_updates)
                
                # Display results in a more readable format
                print("\n📊 Top 3 Matching Categories:")
                print("━"*50)
                for i, (category, confidence) in enumerate(result['categories'], 1):
                    print(f"{i}. 🏷️  {category}")
                    print(f"   ✨ Confidence: {confidence:.2%}")
                
            elif choice == "2":
                categorizer.view_database()
                
            elif choice == "3":
                categorizer.view_category_subscribers()
                
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