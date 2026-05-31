import os
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_meal_context():
    """Determines the current meal window based on system time."""
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 11:
        return "Breakfast"
    elif 11 <= current_hour < 16:
        return "Lunch"
    elif 16 <= current_hour < 19:
        return "Evening Snacks"
    else:
        return "Dinner"

def parse_user_food_input(user_raw_text: str):
    meal_type = get_meal_context()
    
    system_prompt = f"""
    You are an expert nutritional data extractor.
    The current meal window based on the user's time is: {meal_type}.
    
    Analyze the user's input text and extract all food items along with their quantities.
    CRITICAL: You must also generate a 'database_search_term'. This should be a highly descriptive, generic name optimized for a scientific food database. 
    Examples: 
    - "coke" -> "regular cola soda with sugar"
    - "roti" -> "whole wheat flatbread"
    - "paneer tikka" -> "indian cheese paneer cooked"
    
    You must output your response as a valid JSON object matching this structure:
    {{
        "meal_logged": "{meal_type}",
        "foods": [
            {{
                "name": "original text", 
                "database_search_term": "optimized search name",
                "quantity": "estimated unit/quantity"
            }}
        ]
    }}
    """

    # Calling Groq using Llama 3.3 for high-speed JSON generation
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_raw_text}
        ],
        model="llama-3.3-70b-versatile", # <--- UPDATE THIS LINE
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    return chat_completion.choices[0].message.content

# Test execution block (Only runs if you execute this specific file directly)
if __name__ == "__main__":
    sample_input = "I ate 2 paneer tikka rolls and drank a coke"
    print("Testing Parser...")
    print(parse_user_food_input(sample_input))