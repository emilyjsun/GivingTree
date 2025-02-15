import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from news_charity_matcher import NewsCharityMatcher
import time
from dotenv import load_dotenv

def test_single_article():
    print("Initializing NewsCharityMatcher...")
    matcher = NewsCharityMatcher()
    
    # Test article
    test_article = {
        'title': "Climate Change: Global Temperatures Hit New Record High",
        'description': "Scientists report unprecedented global temperature increases, raising concerns about environmental impact.",
        'link': "test_link"
    }
    
    print("\nCollection Info:")
    print(f"Total charities in collection: {matcher.collection.count()}")
    
    print("\nTest Article:")
    print(f"Title: {test_article['title']}")
    print(f"Description: {test_article['description']}")
    
    # Add delay before querying
    time.sleep(1)
    
    print("\nQuerying for similar charities...")
    try:
        results = matcher.collection.query(
            query_texts=[f"{test_article['title']} {test_article['description']}"],
            n_results=5,
            include=["metadatas", "distances"]
        )
        
        print("\nTop 5 Similar Charities:")
        for i in range(len(results['metadatas'][0])):
            charity = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            print(f"\n{i+1}. {charity['name']}")
            print(f"   URL: {charity['url']}")
            print(f"   Similarity Score: {1 - distance:.4f}")
        
        # Add delay before GPT analysis
        time.sleep(5)  # Wait 20 seconds before GPT call
        
        print("\nGPT Charity Analysis:")
        suggestion = matcher.analyze_article(test_article)
        print(suggestion)
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        if "rate_limit" in str(e).lower():
            print("\nRate limit reached. Please wait 20 seconds and try again.")

if __name__ == "__main__":
    test_single_article() 