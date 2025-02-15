import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

@lru_cache(maxsize=100)
def get_mission_statement(url: str) -> str:
    """Get mission statement from a charity's page with caching."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text blocks with class et_pb_text_inner
        mission_blocks = soup.find_all(class_='et_pb_text_inner')
        
        for block in mission_blocks:
            text = block.get_text(strip=True)
            if 'Mission Statement' in text or 'dedicated to' in text:
                # Clean up the text using regex substitutions
                text = re.sub(r'Mission Statement|Solutions.*?About|Why Donate.*|Learn More.*|Website:.*', 
                            '', text, flags=re.DOTALL)
                text = re.sub(r'\s*\n\s*', ' ', text).strip()
                
                if len(text) > 50:
                    return clean_text(text)
        
        return "Mission statement not found"
    except Exception as e:
        return f"Error fetching mission statement: {str(e)}"

def process_charity(heading: BeautifulSoup) -> Dict[str, str]:
    """Process a single charity heading."""
    link = heading.find('a')
    if not link:
        return None
        
    charity_name = link.text.strip()
    if not (charity_name and len(charity_name) > 3 and not charity_name.startswith('Read')):
        return None
        
    href = link.get('href')
    if not href:
        return None
        
    return {
        "name": clean_text(charity_name),
        "url": href,
        "mission": get_mission_statement(href)
    }

def scrape_charities() -> List[dict]:
    """Scrape all charities in parallel."""
    url = "https://thegivingblock.com/resources/nonprofits-accepting-crypto-donations/"
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get all valid charity headings
        charity_headings = [h for i, h in enumerate(soup.find_all('h4')) if i >= 2]
        total_charities = len(charity_headings)
        print(f"Found {total_charities} potential charities to process...")
        
        processed_count = 0
        charities = []
        
        # Process in batches of 50
        for i in range(0, total_charities, 50):
            batch = charity_headings[i:i + 50]
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(process_charity, batch))
                
            # Add valid results to charities list
            valid_results = [c for c in results if c]
            charities.extend(valid_results)
            
            # Update progress
            processed_count += len(batch)
            print(f"Processed {processed_count}/{total_charities} charities... Found {len(charities)} valid entries")
        
        # Remove duplicates
        return list({v['name']: v for v in charities}.values())
        
    except Exception as e:
        print(f"Error scraping charities: {e}")
        return []

def clean_text(text: str) -> str:
    """Clean text efficiently."""
    # Handle Unicode escape sequences
    text = re.sub(r'\\u([0-9a-fA-F]{4})', 
                 lambda m: chr(int(m.group(1), 16)), text)
    
    # Normalize to ASCII
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.replace('\\', '').strip()

def main():
    print("Scraping all charities from The Giving Block...")
    charities = scrape_charities()
    
    if charities:
        print(f"\nFound {len(charities)} charities:")
        for charity in charities:
            print(f"- {charity['name']}")
        
        with open('charities.json', 'w', encoding='utf-8') as f:
            json.dump({"charities": charities}, f, indent=2, ensure_ascii=True)
        print("\nSaved to charities.json")
    else:
        print("No charities found or error occurred")

if __name__ == "__main__":
    main()
