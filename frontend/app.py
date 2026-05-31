import streamlit as st
import sys
import os
from datetime import datetime

# Ensure the frontend can see your backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.nutrition import process_meal_pipeline
from backend.core.rag_engine import get_meal_recommendation

# --- App Configuration ---
st.set_page_config(page_title="AI Clinical Dietitian", page_icon="🥗", layout="wide")

# --- Session State (Memory Initialization) ---
if "profile_set" not in st.session_state:
    st.session_state.profile_set = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "daily_calories" not in st.session_state:
    st.session_state.daily_calories = 0
if "awaiting_recommendation" not in st.session_state:
    st.session_state.awaiting_recommendation = False

# --- Helper Functions: Time-Aware Prompting ---
def get_time_aware_prompt():
    hour = datetime.now().hour
    if hour < 12:
        return "It's morning! What have you consumed for **Breakfast** and your **Morning Snack**?"
    elif hour < 17:
        return "Good afternoon! What have you consumed so far for **Breakfast, Lunch, and Snacks**?"
    else:
        return "Good evening! Let's log your day. What did you have for **Breakfast, Lunch, Dinner, and all Snacks**?"

def get_recommendation_prompt():
    hour = datetime.now().hour
    if hour < 11:
        return "It's morning! Are you looking for a **Morning Snack** idea, or planning ahead for **Lunch**?"
    elif hour < 16:
        return "Good afternoon! Would you like an **Evening Snack** suggestion, or a **Dinner** recipe?"
    else:
        return "Good evening! Are you looking for a light **Dinner** or a healthy **Late-Night Snack**?"


# ==========================================
# PAGE 1: THE SMART ONBOARDING GATE
# ==========================================
if not st.session_state.profile_set:
    st.title("👋 Welcome to your AI Dietitian")
    st.markdown("### Let's build your personalized health profile.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 1. Personal Details")
        user_name = st.text_input("What is your name?")
        medical_condition = st.selectbox(
            "Do you have any specific medical conditions?", 
            ["None", "Type 2 Diabetes", "Hypertension", "PCOS", "Iron Deficiency", "Celiac Disease"]
        )
    
    with col2:
        st.markdown("#### 2. Lifestyle & Calorie Calculator")
        profile_type = st.radio("Select your lifestyle:", ["Average Adult", "Bodybuilder / High-Performance Athlete"])
        
        # Dynamic Calorie Calculation Logic
        recommended_cals = 2000 # Default fallback
        
        if profile_type == "Average Adult":
            gender = st.selectbox("Biological Sex", ["Male", "Female"])
            activity = st.selectbox("Activity Level", ["Sedentary", "Moderately Active"])
            
            if gender == "Female":
                if activity == "Sedentary":
                    recommended_cals = 1600
                else:
                    recommended_cals = 2200
            else: # Male
                if activity == "Sedentary":
                    recommended_cals = 2200
                else:
                    recommended_cals = 2600
            
            st.info(f"💡 Based on clinical averages, a {activity.lower()} {gender.lower()} requires around **{recommended_cals}** calories daily to maintain baseline health.")
            
        else: # Bodybuilder
            recommended_cals = 4000
            st.info("💪 Bodybuilders generally require between **3,500 to 5,000+** calories for muscle synthesis and heavy training recovery. We set a baseline of 4,000.")

        # Allow user to tweak the final calculation
        target_calories = st.number_input(
            "Confirm Your Daily Calorie Goal:", 
            min_value=1000, max_value=8000, value=recommended_cals, step=100
        )
    
    st.divider()
    
    # Save Button
    if st.button("Save Profile & Start Tracking", type="primary", use_container_width=True):
        if user_name.strip() == "":
            st.error("Please enter your name to continue!")
        else:
            st.session_state.user_name = user_name
            st.session_state.medical_condition = medical_condition
            st.session_state.target_calories = target_calories
            st.session_state.profile_set = True
            st.rerun()

# ==========================================
# PAGE 2: THE MAIN DASHBOARD
# ==========================================
else:
    st.title(f"🥗 {st.session_state.user_name}'s Dashboard")
    
    # --- Top Metrics Row ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Daily Goal", f"{st.session_state.target_calories} kcal")
    col2.metric("Consumed Today", f"{st.session_state.daily_calories} kcal")
    remaining = st.session_state.target_calories - st.session_state.daily_calories
    col3.metric("Remaining Budget", f"{remaining} kcal", delta=remaining, delta_color="inverse")
    
    st.divider()

    # --- Quick Action Buttons ---
    st.markdown("### ⚡ Quick Actions")
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📝 Log My Food"):
            prompt = get_time_aware_prompt()
            st.session_state.chat_history.append({"role": "assistant", "content": prompt})
            
    with action_col2:
        if st.button("🔮 What should I eat next?"):
            prompt = get_recommendation_prompt()
            st.session_state.chat_history.append({"role": "assistant", "content": prompt})
            st.session_state.awaiting_recommendation = True
            st.rerun()
                    
    with action_col3:
        if st.button("🩺 Daily Health Plan"):
            condition = st.session_state.medical_condition
            if condition == "None":
                msg = "Since you have no specific medical conditions, focus on a balanced diet: 30% Protein, 40% Carbs, 30% Fats. Keep hitting that daily goal!"
                st.session_state.chat_history.append({"role": "assistant", "content": msg})
            else:
                with st.spinner(f"Generating therapeutic food plan for {condition}..."):
                    plan = get_meal_recommendation({"name": st.session_state.user_name, "medical_condition": condition}, st.session_state.target_calories)
                    st.session_state.chat_history.append({"role": "assistant", "content": f"**Therapeutic Daily Focus for {condition}:**\n\n" + plan})

    st.divider()

    # --- The Chat Interface ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User Input Box
    user_input = st.chat_input("Type your response or ask a question here...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                
                # --- SMART ROUTING LOGIC ---
                wants_recommendation = False
                
                if st.session_state.awaiting_recommendation:
                    wants_recommendation = True
                    st.session_state.awaiting_recommendation = False 
                elif any(word in user_input.lower() for word in ["recommend", "what should i eat", "suggest", "idea"]):
                    wants_recommendation = True

                # ROUTE 1: Recommendation Engine
                if wants_recommendation:
                    profile = {"name": st.session_state.user_name, "medical_condition": st.session_state.medical_condition}
                    remaining_cals = st.session_state.target_calories - st.session_state.daily_calories
                    
                    response = get_meal_recommendation(profile, remaining_cals, user_request=user_input)
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})

                # ROUTE 2: Food Logging Engine
                else:
                    meal_data = process_meal_pipeline(user_input)
                    
                    logged_cals = meal_data["total_calories"]
                    st.session_state.daily_calories += logged_cals
                    
                    reply = f"**Logged successfully!** You consumed **{logged_cals} calories**.\n"
                    reply += f"(Protein: {meal_data['total_protein_g']}g | Carbs: {meal_data['total_carbs_g']}g | Fats: {meal_data['total_fat_g']}g)"
                    
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                    st.rerun()