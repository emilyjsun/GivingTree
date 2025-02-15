import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_grade_score(grade):
    """Convert letter grades to numerical scores"""
    grade_map = {
        'A+': 5,
        'A': 4,
        'A-': 3,
        'B+': 2,
        'B': 1,
        'B-': 0,
        'C+': -1,
        'C': -2,
        'C-': -3,
        'D+': -4,
        'D': -5,
        'D-': -6,
        'F+': -7,
        'F': -8,
        'F-': -9
    }
    return grade_map.get(grade.strip(), None)

def scrape_charitywatch():
    base_url = "https://www.charitywatch.org/top-rated-charities/all"
    print("Fetching data from CharityWatch...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        charities = []
        
        # Find all tables
        tables = soup.find_all('table', class_='table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                try:
                    # Find the td elements
                    cols = row.find_all('td')
                    if len(cols) == 2:  # We expect 2 columns: name and grade
                        # Get name from the link inside first td
                        name_td = cols[0].find('a')
                        if name_td:
                            name = name_td.text.strip()
                            # Get grade from second td
                            grade = cols[1].text.strip()
                            score = get_grade_score(grade)
                            
                            if name and grade:
                                charities.append({
                                    'name': name,
                                    'score': score
                                })
                                print(f"Processed: {name} - Grade: {grade}")
                
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
                
                time.sleep(0.1)  # Be polite to the server
        
        if charities:
            # Create DataFrame
            df = pd.DataFrame(charities)
            
            # Save to CSV
            df.to_csv('charity_ratings.csv', index=False)
            print(f"\nSuccessfully scraped {len(charities)} charities")
            print("Data saved to charity_ratings.csv")
            
            # Display first few entries
            print("\nFirst few entries:")
            print(df.head())
        else:
            print("\nNo charities were successfully scraped")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    scrape_charitywatch() 