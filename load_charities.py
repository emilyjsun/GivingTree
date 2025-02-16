import chromadb
import json

def load_charities_to_chroma():
    print("Starting Chroma Client")
    
    # Initialize ChromaDB client
    client = chromadb.HttpClient(
        ssl=True,
        host='api.trychroma.com',
        tenant='06afecae-2671-4d45-ae27-4d721cfbdbf5',
        database='test',
        headers={
            'x-chroma-token': 'ck-4nbKD36SnTF5UGTVJVXaqzy4pigSLSykruJXThE4EpJr'
        }
    )
    
    # Create or get collection
    collection = client.get_or_create_collection('charities')
    
    # Load charities from JSON
    with open('charities_final.json', 'r') as f:
        data = json.load(f)
        charities = data['charities']
    
    # Prepare documents for batch insertion
    documents = []
    metadatas = []
    ids = []
    
    print(f"Processing {len(charities)} charities...")
    
    for i, charity in enumerate(charities):
        # Create document with name and mission
        doc = json.dumps({
            "name": charity['name'],
            "mission_statement": charity.get('mission', 'Mission statement not available')
        })
        
        documents.append(doc)
        metadatas.append({"category": charity.get('categories', [{}])[0].get('category', 'Unknown')})
        ids.append(str(i))
    
    # Add to ChromaDB
    print("Adding to ChromaDB...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Successfully added {len(documents)} charities to ChromaDB")
    
    # Test query to verify
    result = collection.query(
        query_texts=["disaster relief"],
        n_results=1
    )
    print("\nTest query result:")
    print(result)

if __name__ == "__main__":
    load_charities_to_chroma() 