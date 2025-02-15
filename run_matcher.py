from news_charity_matcher import NewsCharityMatcher

# List of RSS feeds to monitor
RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml"
]

def main():
    # Create matcher without passing API key (it will load from .env)
    matcher = NewsCharityMatcher()
    print("Starting News Charity Matcher...")
    matcher.run(RSS_FEEDS)

if __name__ == "__main__":
    main() 