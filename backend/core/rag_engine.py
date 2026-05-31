import os
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from groq import Groq

# Load environment variables
load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def search_health_guidelines(condition: str, target_calories: int) -> str:
    """Searches the web for dietary guidelines related to a specific condition."""
    if condition.lower() == "none":
        return "No specific medical conditions. General healthy eating applies."
        
    query = f"safe dinner foods for {condition} disease"
    results = ""
    
    try:
        # Using DuckDuckGo to pull the top 3 snippets from the internet
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=3))
            for res in search_results:
                results += f"- {res['body']}\n"
    except Exception as e:
        results = "Could not fetch live web data. Fallback to general medical knowledge."
        
    return results

def get_meal_recommendation(user_profile: dict, remaining_calories: int, user_request: str = "a meal"):
    """Uses RAG to recommend a meal, with smart handling for over-budget scenarios."""
    
    condition = user_profile.get("medical_condition", "None")
    
    print(f"\n[1/2] Searching the internet for '{condition}' guidelines...")
    web_context = search_health_guidelines(condition, remaining_calories)
    
    print("[2/2] Generating personalized recommendation via Groq AI...")
    
    # 🌟 NEW LOGIC: Handle the "Over Budget" Scenario
    if remaining_calories <= 0:
        system_prompt = f"""
        You are an expert clinical nutrition AI. 
        The user wants a recommendation for: "{user_request}"
        
        CRITICAL ALERT: The user has ALREADY MET OR EXCEEDED their daily calorie limit!
        Medical Condition: {condition}
        Location: India
        
        TASK:
        1. Gently and kindly inform them they have hit their calorie goal for today.
        2. Advise them to skip unnecessary snacks.
        3. Since they still need to eat for the rest of the day, recommend 1 or 2 "Damage Control" Indian options—ultra-low-calorie, high-volume foods (like clear vegetable soup, cucumber/tomato kachumber salad, or buttermilk/chaas). 
        4. Explain why these foods will keep them full without ruining their diet, ensuring it is safe for their medical condition.
        """
    else:
        # Standard Prompt
        system_prompt = f"""
        You are an expert clinical nutrition AI. 
        The user wants a recommendation for: "{user_request}"
        
        USER PROFILE:
        - Target Calories for this meal: ~{remaining_calories} kcal
        - Medical Condition: {condition}
        - Location: India (Prefer Indian cuisine)
        
        LIVE INTERNET RESEARCH ON CONDITION:
        {web_context}
        
        TASK:
        Based on the internet research provided, recommend 1 specific, realistic Indian meal that fits the calorie goal. 
        You MUST explain WHY it is safe for their specific condition based on the research.
        Keep your response warm, encouraging, and formatted with bullet points for readability.
        """
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    
    return chat_completion.choices[0].message.content

# --- Test Drive ---
if __name__ == "__main__":
    # Let's simulate a user who has Type 2 Diabetes and needs a 450 calorie dinner
    mock_user_profile = {
        "name": "Rahul",
        "medical_condition": "Type 2 Diabetes"
    }
    target_dinner_calories = 450
    
    recommendation = get_meal_recommendation(mock_user_profile, target_dinner_calories)
    
    print("\n================ AI DOCTOR RESPONSE ================\n")
    print(recommendation)
    print("\n====================================================\n")