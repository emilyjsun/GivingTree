import chromadb
import json

def migrate_data():
    print("Starting migration...")
    
    try:
        # Initialize ChromaDB client
        print("Connecting to ChromaDB...")
        client = chromadb.HttpClient(
            ssl=True,
            host='api.trychroma.com',
            tenant='06afecae-2671-4d45-ae27-4d721cfbdbf5',
            database='treehacks_charities',
            headers={
                'x-chroma-token': 'ck-4nbKD36SnTF5UGTVJVXaqzy4pigSLSykruJXThE4EpJr'
            }
        )
        
        # Define categories as a dictionary with IDs
        CATEGORIES = {
            "0": "Disaster Relief",
            "1": "Education Support",
            "2": "Healthcare Access",
            "3": "Food Security",
            "4": "Refugee Assistance",
            "5": "Child Welfare",
            "6": "Environmental Conservation",
            "7": "Women's Empowerment",
            "8": "Housing & Shelter",
            "9": "Clean Water Access",
            "10": "Mental Health Support",
            "11": "Poverty Alleviation",
            "12": "Human Rights",
            "13": "Community Development",
            "14": "Animal Welfare"
        }
        
        # Create reverse mapping for easy lookup
        CATEGORY_TO_ID = {v: k for k, v in CATEGORIES.items()}
        
        # 1. Migrate Categories
        print("\nMigrating categories...")
        try:
            client.delete_collection('categories')
            print("Deleted existing categories collection")
        except:
            pass
            
        categories_collection = client.create_collection('categories')
        
        # Add categories
        categories_collection.add(
            documents=list(CATEGORIES.values()),  # Category names as documents
            ids=list(CATEGORIES.keys())  # Using our predefined IDs
        )
        print(f"Added {len(CATEGORIES)} categories")
        
        # 2. Migrate Charities
        print("\nMigrating charities...")
        try:
            client.delete_collection('charities')
            print("Deleted existing charities collection")
        except:
            pass
        
        charities_collection = client.create_collection('charities')
        
        # Load charities from JSON
        print("Loading charities from file...")
        with open('charities_final.json', 'r') as f:
            data = json.load(f)
            charities = data['charities']
        
        # Process charities in batches
        batch_size = 10
        total_charities = len(charities)
        
        for i in range(0, total_charities, batch_size):
            batch = charities[i:i + batch_size]
            
            documents = []
            metadatas = []
            ids = []
            
            for j, charity in enumerate(batch, start=i):
                doc = json.dumps({
                    "name": charity['name'],
                    "mission_statement": charity.get('mission', 'Mission statement not available')
                })
                
                # Get all high-scoring categories (>0.8)
                high_scoring_categories = []
                for cat_info in charity.get('categories', []):
                    category_name = cat_info.get('category')
                    category_score = float(cat_info.get('similarity', 0))
                    if category_score >= 0.8 and category_name in CATEGORY_TO_ID:
                        high_scoring_categories.append(CATEGORY_TO_ID[category_name])
                
                # Default to first category if no high scoring ones found
                if not high_scoring_categories:
                    category_name = charity.get('categories', [{}])[0].get('category', 'Unknown')
                    category_id = CATEGORY_TO_ID.get(category_name, "-1")
                    high_scoring_categories = [category_id]
                
                documents.append(doc)
                metadatas.append({
                    "categories": ",".join(high_scoring_categories)  # All categories with score >= 0.8
                })
                ids.append(str(j))
            
            charities_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"Processed {min(i + batch_size, total_charities)}/{total_charities} charities")
        
        # Verify both migrations
        print("\nVerifying migrations...")
        
        # Test categories
        cat_result = categories_collection.query(
            query_texts=["disaster"],
            n_results=1
        )
        print("\nCategories test query:")
        print(f"Found category: {cat_result['documents'][0][0]} (ID: {cat_result['ids'][0][0]})")
        
        # Test charities
        char_result = charities_collection.query(
            query_texts=["disaster relief"],
            n_results=1
        )
        if char_result['documents'][0]:
            doc = json.loads(char_result['documents'][0][0])
            high_scoring_ids = char_result['metadatas'][0][0]['categories'].split(',')
            
            print("\nCharities test query:")
            print(f"Found charity: {doc['name']}")
            print(f"Mission: {doc['mission_statement'][:100]}...")
            print("High Scoring Categories:")
            for cat_id in high_scoring_ids:
                print(f"- {CATEGORIES.get(cat_id, 'Unknown')} (ID: {cat_id})")
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        migrate_data()
    except Exception as e:
        print(f"Migration failed: {e}")
