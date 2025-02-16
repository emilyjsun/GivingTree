import json
import openai
from dotenv import load_dotenv
import os

class CharityCategorizer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.client = openai.OpenAI(api_key=self.api_key)
        
        self.CATEGORIES = [
            "Disaster Relief",
            "Education Support",
            "Healthcare Access",
            "Food Security",
            "Refugee Assistance",
            "Child Welfare",
            "Environmental Conservation",
            "Women's Empowerment",
            "Housing & Shelter",
            "Clean Water Access",
            "Mental Health Support",
            "Poverty Alleviation",
            "Human Rights",
            "Community Development"
        ]
    
    def analyze_charity(self, charity):
        """Use AI to analyze charity and determine top 3 matching categories with scores."""
        prompt = f"""
As a charity categorization expert, analyze this charity and determine its top 3 most relevant categories.

CHARITY INFORMATION:
Name: {charity['name']}
Mission: {charity['mission']}

AVAILABLE CATEGORIES:
{'\n'.join(f'- {cat}' for cat in self.CATEGORIES)}

Consider:
1. The charity's primary focus and mission
2. Direct and indirect impacts
3. Target beneficiaries
4. Methods of intervention
5. Scope of work

Provide your analysis in this exact format:
CATEGORIES:
category1||similarity_score
category2||similarity_score
category3||similarity_score

Notes:
- Scores must be between 0 and 1
- Only use categories from the provided list
- Score should reflect how central that category is to the charity's mission
- Explain your reasoning after the recommendations
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing charitable organizations and categorizing their work. You understand the nuances of how charities can span multiple categories and can identify primary and secondary focus areas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Parse categories and scores
            categories = []
            response_text = response.choices[0].message.content
            
            if "CATEGORIES:" in response_text:
                category_section = response_text.split("CATEGORIES:")[1].split("\n\n")[0]
                for line in category_section.strip().split("\n"):
                    if "||" in line:
                        category, score = line.split("||")
                        try:
                            categories.append({
                                'category': category.strip(),
                                'similarity': float(score.strip())
                            })
                        except:
                            continue
            
            return categories
            
        except Exception as e:
            print(f"Error analyzing charity {charity['name']}: {e}")
            return []
    
    def categorize_charities(self):
        """Update categories in charities_final.json using AI analysis"""
        print("Loading charities_final.json...")
        try:
            # Load existing charities_final.json
            try:
                with open('charities_final.json', 'r') as f:
                    final_data = json.load(f)
                    charities = final_data['charities']
            except FileNotFoundError:
                print("charities_final.json not found, creating new file...")
                with open('matched_charities.json', 'r') as f:
                    data = json.load(f)
                    charities = data['matched_charities']
                    final_data = {
                        "charities": charities,
                        "stats": data.get('stats', {})
                    }
            
            total_charities = len(charities)
            print(f"Found {total_charities} charities to categorize")
            
            # Process each charity
            for i, charity in enumerate(charities, 1):
                print(f"\nProcessing charity {i}/{total_charities}: {charity['name']}")
                
                # Get AI categorization
                categories = self.analyze_charity(charity)
                
                # Update only the categories field
                charity['categories'] = categories
                
                # Print results
                print("Assigned Categories:")
                for j, cat in enumerate(categories, 1):
                    print(f"{j}. {cat['category']}")
                    print(f"   Similarity Score: {cat['similarity']:.4f}")
            
            # Save updated data back to file
            print("\nSaving updated charities_final.json...")
            with open('charities_final.json', 'w') as f:
                json.dump(final_data, f, indent=2)
            
            print("Categorization complete!")
            print(f"Total charities processed: {total_charities}")
            
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    categorizer = CharityCategorizer()
    categorizer.categorize_charities() 