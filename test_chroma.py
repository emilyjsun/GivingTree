# pip install chromadb

import chromadb
from chromadb.utils import embedding_functions

print("Starting Chroma Client")

try:
    # Use PersistentClient for local storage
    client = chromadb.PersistentClient(path="./test_db")
    
    # Create embedding function
    basic_ef = embedding_functions.DefaultEmbeddingFunction()
    
    # Create or get collection with embedding function
    collection = client.get_or_create_collection(
        name="fruit",
        embedding_function=basic_ef
    )
    
    print("Connected to local ChromaDB ✅")
    
    print("\nAdding documents...")
    collection.add(
        ids=['1', '2', '3'],
        documents=['apple', 'oranges', 'pineapple']
    )
    
    print("\nQuerying collection...")
    result = collection.query(
        query_texts=['hawaii'],
        n_results=1
    )
    print("Query result:", result)

except Exception as e:
    print(f"❌ Error: {str(e)}")
finally:
    print("\nTest completed")
  