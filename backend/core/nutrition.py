import os
import json
import requests
from dotenv import load_dotenv
from groq import Groq # Make sure this is imported

# Import the parser function you built in Module 1
from backend.core.llm_parser import parse_user_food_input

# 1. Load the environment variables from your .env file
load_dotenv()

USDA_API_KEY = os.environ.get("USDA_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# 2. DEFINE CLIENT GLOBALLY HERE (This fixes the NameError!)
client = Groq(api_key=GROQ_API_KEY)

def convert_quantity_to_grams(food_name: str, quantity: str) -> float:
    """Uses Groq to estimate the absolute weight in grams for relative terms."""
    system_prompt = """
    You are an expert nutritional weight estimator. Convert the given food and quantity into an approximate weight in grams.
    Provide ONLY a valid JSON object containing a single key "weight_grams" with a float value. Do not include any explanation.
    Example: 
    Input: food="coke", quantity="1 can (330ml)" -> Output: {"weight_grams": 330.0}
    Input: food="paneer tikka roll", quantity="2 pieces" -> Output: {"weight_grams": 400.0}
    """
    
    try:
        # Now 'client' is fully visible to this function
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"food='{food_name}', quantity='{quantity}'"}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result = json.loads(completion.choices[0].message.content)
        return float(result.get("weight_grams", 100.0))
    except Exception as e:
        print(f"Gram estimation failed, using fallback. Error: {e}")
        return 100.0 # Default fallback factor if API fails

def fetch_food_macros_usda(food_name: str):
    """Hits the USDA FoodData Central API to get macros per 100g."""
    api_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={food_name}&pageSize=1"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("foods") and len(data["foods"]) > 0:
            top_result = data["foods"][0]
            nutrients = top_result.get("foodNutrients", [])
            
            def extract_nutrient(keyword):
                for n in nutrients:
                    if keyword.lower() in n.get("nutrientName", "").lower():
                        return float(n.get("value", 0.0))
                return 0.0
                
            return {
                "calories_per_100g": extract_nutrient("Energy"),
                "protein_per_100g": extract_nutrient("Protein"),
                "carbs_per_100g": extract_nutrient("Carbohydrate"),
                "fat_g_per_100g": extract_nutrient("Total lipid")
            }
    return {"calories_per_100g": 0, "protein_per_100g": 0, "carbs_per_100g": 0, "fat_g_per_100g": 0}

def process_meal_pipeline(raw_user_text: str):
    """The complete pipeline executing processing steps sequentially."""
    print("\n[1/4] Parsing user input text via LLM...")
    llm_json_string = parse_user_food_input(raw_user_text)
    meal_data = json.loads(llm_json_string)
    
    meal_totals = {
        "meal_logged": meal_data.get("meal_logged", "Unknown"),
        "total_calories": 0.0,
        "total_protein_g": 0.0,
        "total_carbs_g": 0.0,
        "total_fat_g": 0.0,
        "items": []
    }
    
    print("[2/4] Standardizing portions to gram units...")
    print("[3/4] Fetching base macro balances from USDA database...")
    for item in meal_data.get('foods', []):
        name = item['name']
        qty = item['quantity']
        
        # 1. NEW: Extract the smart search term (fallback to original name if it fails)
        search_term = item.get('database_search_term', name)
        
        # 2. Determine weight scaling factor (we still calculate weight based on the original name/qty)
        calculated_weight = convert_quantity_to_grams(name, qty)
        multiplier = calculated_weight / 100.0
        
        # 3. UPDATED: Grab base values using the SMART term instead of the raw name
        base_macros = fetch_food_macros_usda(search_term)
        
        # 4. Compute exact final quantities
        item_calories = base_macros["calories_per_100g"] * multiplier
        item_protein = base_macros["protein_per_100g"] * multiplier
        item_carbs = base_macros["carbs_per_100g"] * multiplier
        item_fat = base_macros["fat_g_per_100g"] * multiplier
        
        meal_totals["items"].append({
            "name": name,
            "logged_quantity": qty,
            "estimated_weight_g": calculated_weight,
            "calories": round(item_calories, 1),
            "protein_g": round(item_protein, 1),
            "carbs_g": round(item_carbs, 1),
            "fat_g": round(item_fat, 1)
        })
        
        # Add to the grand totals
        meal_totals["total_calories"] += item_calories
        meal_totals["total_protein_g"] += item_protein
        meal_totals["total_carbs_g"] += item_carbs
        meal_totals["total_fat_g"] += item_fat
        
        meal_totals["total_calories"] += item_calories
        meal_totals["total_protein_g"] += item_protein
        meal_totals["total_carbs_g"] += item_carbs
        meal_totals["total_fat_g"] += item_fat

    # Round totals for presentation cleanliness
    meal_totals["total_calories"] = round(meal_totals["total_calories"], 1)
    meal_totals["total_protein_g"] = round(meal_totals["total_protein_g"], 1)
    meal_totals["total_carbs_g"] = round(meal_totals["total_carbs_g"], 1)
    meal_totals["total_fat_g"] = round(meal_totals["total_fat_g"], 1)
    
    print("[4/4] Macro calculations finalized!\n")
    return meal_totals

if __name__ == "__main__":
    test_input = "I ate 2 paneer tikka rolls and drank a coke"
    final_result = process_meal_pipeline(test_input)
    print(json.dumps(final_result, indent=4))