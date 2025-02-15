import requests
from bs4 import BeautifulSoup
import json
from typing import List
import re
import unicodedata
from tqdm import tqdm

def get_mission_statement(url: str) -> str:
    """Get mission statement from a charity's page."""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text blocks with class et_pb_text_inner
        mission_blocks = soup.find_all(class_='et_pb_text_inner')
        
        for block in mission_blocks:
            text = block.get_text(strip=True)
            # Look for paragraphs that contain the actual mission statement
            # These often start with "Mission Statement" or contain key phrases
            if 'Mission Statement' in text or 'dedicated to' in text:
                # Clean up the text
                text = text.replace('Mission Statement', '').strip()
                # Remove navigation and UI text
                text = re.sub(r'Solutions.*?About', '', text, flags=re.DOTALL)
                text = re.sub(r'Why Donate.*', '', text, flags=re.DOTALL)
                text = re.sub(r'Learn More.*', '', text, flags=re.DOTALL)
                text = re.sub(r'Website:.*', '', text, flags=re.DOTALL)
                # Remove any remaining navigation items
                text = re.sub(r'\s*\n\s*', ' ', text)  # Replace newlines with spaces
                text = text.strip()
                if len(text) > 50:  # Only return if it's a substantial amount of text
                    return clean_text(text)
        
        return "Mission statement not found"
    except Exception as e:
        print(f"Error fetching mission statement: {e}")
        return "Error fetching mission statement"

def scrape_charities() -> List[dict]:
    """Scrape charity names and mission statements from The Giving Block website."""
    url = "https://thegivingblock.com/resources/nonprofits-accepting-crypto-donations/"
    
    print("Fetching charity list...")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all h4 elements that contain charity names
    charity_headings = soup.find_all(['h4'])
    charities = []
    
    # Get total valid charities for progress bar
    valid_charities = [h for h in charity_headings[2:] 
                      if h.find('a') and len(h.find('a').text.strip()) > 3 
                      and not h.find('a').text.startswith('Read')]
    
    print(f"Found {len(valid_charities)} charities to process")
    
    # Create progress bar
    pbar = tqdm(total=len(valid_charities), desc="Processing charities")
    processed = 0
    
    for heading in charity_headings[2:]:  # Skip first two navigation items
        link = heading.find('a')
        if link:
            charity_name = link.text.strip()
            if charity_name and len(charity_name) > 3 and not charity_name.startswith('Read'):
                href = link.get('href')
                if href:
                    mission = get_mission_statement(href)
                    charities.append({
                        "name": clean_text(charity_name),
                        "url": href,
                        "mission": mission
                    })
                    processed += 1
                    pbar.update(1)
                    
                    # Save progress every 50 charities
                    if processed % 50 == 0:
                        save_charities(charities)
                        pbar.set_postfix({'Saved': processed})
    
    pbar.close()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_charities = []
    for charity in charities:
        if charity['name'] not in seen:
            seen.add(charity['name'])
            unique_charities.append(charity)
            
    return unique_charities

def clean_text(text: str) -> str:
    """Clean text by converting Unicode characters and escape sequences to ASCII equivalents."""
    # First handle explicit Unicode escape sequences (\uXXXX)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', 
                 lambda m: chr(int(m.group(1), 16)).encode('ASCII', 'ignore').decode('ASCII'), 
                 text)
    
    # Normalize Unicode characters to ASCII
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    
    # Clean up any remaining special characters and extra whitespace
    text = text.replace('\\', '').replace('\n', ' ').replace('\r', '')
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = text.strip()
    
    return text

def save_charities(charities: List[dict], filename: str = 'charities.json'):
    """Save the list of charities with their mission statements to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({"charities": charities}, f, indent=2, ensure_ascii=True)

def main():
    print("Scraping charities from The Giving Block...")
    charities = scrape_charities()
    
    print(f"\nFound {len(charities)} charities:")
    for charity in charities:
        print(f"- {charity['name']}")
    
    save_charities(charities)
    print(f"\nSaved charities with mission statements to charities.json")

if __name__ == "__main__":
    main()
