import pandas as pd
import json
from difflib import get_close_matches

def load_charities_json():
    """Load charities from charities.json"""
    with open('charities.json', 'r') as f:
        return json.load(f)['charities']

def load_ratings_csv():
    """Load charities from charity_ratings.csv"""
    return pd.read_csv('charity_ratings.csv')

def find_matching_charities():
    print("Loading charity files...")
    original_charities = load_charities_json()
    rated_charities_df = load_ratings_csv()
    
    # Convert rated charities to list of names
    rated_charity_names = rated_charities_df['name'].tolist()
    
    matched_charities = []
    unmatched_charities = []
    
    print("\nFinding matches...")
    for charity in original_charities:
        # Try to find close matches
        matches = get_close_matches(charity['name'], rated_charity_names, n=1, cutoff=0.8)
        
        if matches:
            matched_name = matches[0]
            score = rated_charities_df[rated_charities_df['name'] == matched_name]['score'].iloc[0]
            
            matched_charity = {
                'name': charity['name'],
                'mission': charity['mission'],
                'url': charity['url'],
                'score': int(score),
                'matched_name': matched_name
            }
            matched_charities.append(matched_charity)
            print(f"Matched: {charity['name']} -> {matched_name}")
        else:
            unmatched_charities.append(charity['name'])
    
    # Save matched charities to new JSON file
    output = {
        'matched_charities': matched_charities,
        'stats': {
            'total_original': len(original_charities),
            'total_rated': len(rated_charity_names),
            'total_matched': len(matched_charities),
            'total_unmatched': len(unmatched_charities)
        }
    }
    
    with open('matched_charities.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print statistics
    print("\nMatching Statistics:")
    print(f"Total original charities: {len(original_charities)}")
    print(f"Total rated charities: {len(rated_charity_names)}")
    print(f"Total matched charities: {len(matched_charities)}")
    print(f"Total unmatched charities: {len(unmatched_charities)}")
    
    # Print first few unmatched charities for review
    if unmatched_charities:
        print("\nFirst 10 unmatched charities:")
        for charity in unmatched_charities[:10]:
            print(f"- {charity}")
    
    print("\nResults saved to matched_charities.json")

if __name__ == "__main__":
    find_matching_charities() 