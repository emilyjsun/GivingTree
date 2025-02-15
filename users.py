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

    def store_input(self, user_input: str, categories: list):
        """
        Store user input and its categorization in the vector database.
        """
        print("storing input")
        if hash(user_input) not in self.processed_inputs:
            # Generate embedding for user input
            embedding = self.model.encode(user_input).tolist()
            
            # Store in ChromaDB with top category
            self.collection.add(
                documents=[user_input],
                metadatas=[{
                    "primary_category": categories[0][0],
                    "all_categories": ",".join([cat for cat, _ in categories]),
                    "all_scores": ",".join([f"{score:.4f}" for _, score in categories]),
                    "timestamp": datetime.now().isoformat()
                }],
                embeddings=[embedding],
                ids=[str(hash(user_input))]
            )
            
            # Mark as processed
            self.processed_inputs.add(hash(user_input))
            self.save_processed_inputs()

    def process_input(self, user_input: str) -> dict:
        """
        Process a single user input and return results.
        """
        print("processing input")
        categories = self.categorize_input(user_input)
        self.store_input(user_input, categories)
        
        return {
            "input": user_input,
            "categories": categories
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
            print(f"Text: {results['documents'][i]}")
            print(f"Primary Category: {results['metadatas'][i]['primary_category']}")
            
            # Split and display all categories and scores
            categories = results['metadatas'][i]['all_categories'].split(',')
            scores = [float(score) for score in results['metadatas'][i]['all_scores'].split(',')]
            
            print("\nTop 3 Categories:")
            for cat, score in zip(categories, scores):
                print(f"- {cat}: {score:.2%}")
            
            print(f"Timestamp: {results['metadatas'][i]['timestamp']}")
            print("-" * 30)

def main():
    categorizer = CharityInputCategorizer()
    
    print("\nWelcome to the Charity Input Categorizer!")
    print("This system will categorize your input into humanitarian/charity categories.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            print("\n1. Enter new humanitarian concern")
            print("2. View all stored entries")
            print("3. Exit")
            
            choice = input("\nChoose an option (1-3): ")
            
            if choice == "1":
                print("\n" + "-"*50)
                user_input = input("Please describe your humanitarian concern: ")
                
                if not user_input.strip():
                    print("Please enter a valid input.")
                    continue
                    
                # Process input
                result = categorizer.process_input(user_input)
                
                # Display results in a more readable format
                print("\n📊 Top 3 Matching Categories:")
                print("━"*50)
                for i, (category, confidence) in enumerate(result['categories'], 1):
                    print(f"{i}. 🏷️  {category}")
                    print(f"   ✨ Confidence: {confidence:.2%}")
                
            elif choice == "2":
                categorizer.view_database()
                
            elif choice == "3" or choice.lower() == 'quit':
                print("\nThank you for using the Charity Input Categorizer!")
                break
                
            else:
                print("\nInvalid choice. Please try again.")
                
        except Exception as e:
            print(f"\n❌ Error occurred: {str(e)}")
            print("Please try again with a different input.")

if __name__ == "__main__":
    main()