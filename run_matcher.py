from news_charity_matcher import NewsCharityMatcher

def main():
    # List of RSS feeds to monitor
    rss_feeds = [
        'http://feeds.reuters.com/reuters/worldNews',
        'http://feeds.reuters.com/Reuters/domesticNews',
        # Add more RSS feeds as needed
    ]
    
    try:
        matcher = NewsCharityMatcher()
        print("Starting charity matcher...")
        matcher.run(rss_feeds)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 