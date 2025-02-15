import json
import chromadb
from chromadb.utils import embedding_functions
import os

class CharityCategorizer:
    def __init__(self):
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
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./category_db")
        openai_ef = embedding_functions.DefaultEmbeddingFunction()
        
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
    
    def find_matching_categories(self, charity):
        """Find top 3 matching categories for a charity."""
        # Combine charity info for matching
        charity_text = f"{charity['name']}: {charity['mission']}"
        
        # Query the category collection
        results = self.category_collection.query(
            query_texts=[charity_text],
            n_results=3
        )
        
        # Format results
        categories = []
        
        # ChromaDB returns distances by default now
        distances = results['distances'][0]
        
        for i in range(len(distances)):
            category = results['metadatas'][0][i]['category']
            # Convert Euclidean distance to a similarity score
            distance = distances[i]
            similarity = max(0, min(1, 1 - (distance / 2)))  # Normalize to 0-1 range
            
            categories.append({
                'category': category,
                'similarity': similarity
            })
        
        return categories
    
    def categorize_charities(self):
        """Create charities_final.json with categorized charities"""
        print("Loading matched_charities.json...")
        try:
            with open('matched_charities.json', 'r') as f:
                data = json.load(f)
            
            total_charities = len(data['matched_charities'])
            print(f"Found {total_charities} charities to categorize")
            
            # Create new data structure for final output
            final_data = {
                "charities": [],
                "stats": data.get('stats', {})  # Preserve stats if they exist
            }
            
            # Process each charity
            for i, charity in enumerate(data['matched_charities'], 1):
                print(f"\nProcessing charity {i}/{total_charities}: {charity['name']}")
                
                # Find matching categories
                categories = self.find_matching_categories(charity)
                
                # Create new charity entry with all existing data plus categories
                final_charity = {
                    'name': charity['name'],
                    'mission': charity['mission'],
                    'url': charity['url'],
                    'score': charity['score'],
                    'categories': categories
                }
                
                final_data['charities'].append(final_charity)
                
                # Print results
                print("Matched Categories:")
                for j, cat in enumerate(categories, 1):
                    print(f"{j}. {cat['category']}")
                    print(f"   Similarity Score: {cat['similarity']:.4f}")
            
            # Save to new file
            print("\nSaving charities_final.json...")
            with open('charities_final.json', 'w') as f:
                json.dump(final_data, f, indent=2)
            
            print("Categorization complete!")
            print(f"Total charities processed: {total_charities}")
            
        except FileNotFoundError:
            print("Error: matched_charities.json not found")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    categorizer = CharityCategorizer()
    categorizer.categorize_charities() 