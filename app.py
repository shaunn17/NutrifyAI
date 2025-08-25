import os
import json
import streamlit as st
import pandas as pd
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from typing import List, Tuple
from utils import compute_macros

st.set_page_config(
    page_title="AI Healthy Recipe & Macros", 
    page_icon="🥗", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Secrets (set in Streamlit Cloud or .streamlit/secrets.toml locally) ---
GROQ_API_KEY = st.secrets.get("groq_api_key")
USDA_API_KEY = st.secrets.get("usda_api_key")

# Make USDA key available to utils.py
if USDA_API_KEY:
    os.environ["USDA_API_KEY"] = USDA_API_KEY
    os.environ["usda_api_key"] = USDA_API_KEY

# --- Models for structured output validation ---
class IngredientOut(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    grams: float = Field(..., ge=0, description="Quantity in grams (approx)")

class RecipeOut(BaseModel):
    title: str
    servings: int = Field(..., ge=1, le=12)
    ingredients_grams: List[IngredientOut]
    steps: List[str]

# --- Helper to call Groq ---
def generate_recipe_json(ingredients: List[str]) -> RecipeOut:
    """
    Ask the model to produce a structured JSON recipe using ONLY user ingredients,
    with approximate grams for each ingredient.
    """
    client = Groq(api_key=GROQ_API_KEY)

    system_msg = (
        "You are a nutritionist-chef. Create a healthy, tasty recipe ONLY with the ingredients provided. "
        "Return STRICT JSON with keys: title (string), servings (int 1-12), "
        "ingredients_grams (list of objects {name, grams}), and steps (list of strings). "
        "All ingredient quantities MUST have grams; estimate sensible amounts. "
        "Do not add ingredients not provided, except basic salt/pepper which you may exclude from macros."
    )

    user_msg = (
        "Ingredients: " + ", ".join(ingredients) + "\n\n"
        "Rules:\n"
        "1) Use only these ingredients (ignore pantry basics for macros).\n"
        "2) Provide realistic grams per ingredient so totals are ~400-700g per serving for a meal.\n"
        "3) Servings must be an integer.\n"
        "4) Output VALID JSON only. No extra commentary."
    )

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.6,
        max_tokens=700,
    )

    content = resp.choices[0].message.content.strip()

    # Try to extract JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: attempt to find JSON block
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(content[start:end+1])
        else:
            raise ValueError("Model did not return valid JSON.")

    # Validate with pydantic
    return RecipeOut(**data)

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    /* Main app styling */
    .main {
        padding-top: 2rem;
    }
    
    /* Custom header styling */
    .hero-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .hero-title {
        font-family: 'Poppins', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .hero-subtitle {
        font-family: 'Poppins', sans-serif;
        font-size: 1.2rem;
        font-weight: 300;
        opacity: 0.9;
        margin-bottom: 1rem;
    }
    
    .hero-description {
        font-family: 'Poppins', sans-serif;
        font-size: 1rem;
        font-weight: 400;
        opacity: 0.8;
        max-width: 600px;
        margin: 0 auto;
    }
    
    /* Feature cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    
    .feature-title {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .feature-desc {
        font-family: 'Poppins', sans-serif;
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Input styling */
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        font-family: 'Poppins', sans-serif;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
    }
    
    /* Button styling */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Results styling */
    .recipe-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-top: 5px solid #667eea;
    }
    
    .macro-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .macro-value {
        font-size: 2rem;
        font-weight: 700;
        font-family: 'Poppins', sans-serif;
    }
    
    .macro-label {
        font-size: 0.9rem;
        opacity: 0.9;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .fade-in {
        animation: fadeInUp 0.6s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# --- Hero Header Section ---
st.markdown("""
<div class="hero-header fade-in">
    <div class="hero-title">🥗 AI Chef & Nutrition Coach</div>
    <div class="hero-subtitle">Transform Your Ingredients into Healthy Masterpieces</div>
    <div class="hero-description">
        Powered by advanced AI and USDA nutritional data, create personalized recipes 
        from your available ingredients with complete macro breakdowns for optimal health.
    </div>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h2 style="color: white; font-family: 'Poppins', sans-serif;">🍽️ Chef's Tips</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🤖</div>
        <div class="feature-title">AI-Powered</div>
        <div class="feature-desc">Advanced Llama-3.1 model creates recipes tailored to your ingredients</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📊</div>
        <div class="feature-title">USDA Nutrition</div>
        <div class="feature-desc">Accurate macro data from 200,000+ verified food items</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">⚡</div>
        <div class="feature-title">Lightning Fast</div>
        <div class="feature-desc">Get your recipe and nutrition facts in seconds</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    ### 💡 **Pro Tips:**
    
    **🥩 Proteins:** chicken breast, salmon, tofu, eggs, greek yogurt
    
    **🌾 Carbs:** quinoa, brown rice, sweet potato, oats
    
    **🥬 Veggies:** spinach, broccoli, bell peppers, tomatoes
    
    **🥑 Healthy Fats:** olive oil, avocado, nuts, seeds
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 🎯 **Best Results:**
    - Use 4-8 ingredients
    - Include a protein source
    - Add healthy fats
    - Keep ingredient names simple
    """)

# --- Feature Cards Section ---
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="feature-card fade-in">
        <div class="feature-icon">🎯</div>
        <div class="feature-title">Personalized</div>
        <div class="feature-desc">Recipes using only YOUR ingredients</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card fade-in">
        <div class="feature-icon">🥗</div>
        <div class="feature-title">Healthy Focus</div>
        <div class="feature-desc">Optimized for nutrition and wellness</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card fade-in">
        <div class="feature-icon">📱</div>
        <div class="feature-title">Mobile Ready</div>
        <div class="feature-desc">Perfect for kitchen use on any device</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card fade-in">
        <div class="feature-icon">💰</div>
        <div class="feature-title">100% Free</div>
        <div class="feature-desc">No subscriptions or hidden costs</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# --- Input Section ---
st.markdown("""
<div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); margin: 2rem 0;">
    <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
        🛒 What's in your kitchen today?
    </h3>
</div>
""", unsafe_allow_html=True)

default_ing = "chicken breast, quinoa, spinach, olive oil, garlic"

col1, col2 = st.columns([3, 1])
with col1:
    ingredients_input = st.text_area(
        "",
        value=default_ing, 
        height=100, 
        placeholder="Enter your ingredients separated by commas...\nExample: chicken breast, quinoa, spinach, olive oil, garlic",
        help="💡 Tip: Use simple ingredient names for best results!"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 Create My Recipe", type="primary", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎲 Surprise Me!", use_container_width=True):
        surprise_ingredients = [
            "salmon, sweet potato, asparagus, olive oil, lemon",
            "ground turkey, bell peppers, black beans, avocado, lime",
            "tofu, broccoli, brown rice, sesame oil, ginger",
            "eggs, spinach, mushrooms, cheese, herbs",
            "chicken thighs, zucchini, tomatoes, basil, garlic"
        ]
        import random
        ingredients_input = st.text_area(
            "",
            value=random.choice(surprise_ingredients), 
            height=100, 
            placeholder="Enter your ingredients separated by commas...",
            help="💡 Tip: Use simple ingredient names for best results!",
            key="surprise_ingredients"
        )

if run_btn:
    if not GROQ_API_KEY or not USDA_API_KEY:
        st.error("Please add your `groq_api_key` and `usda_api_key` in **Secrets** to run.")
        st.stop()

    ingredients = [s.strip() for s in ingredients_input.split(",") if s.strip()]
    if not ingredients:
        st.warning("Please enter at least one ingredient.")
        st.stop()

    with st.spinner("Asking the chef…"):
        try:
            recipe = generate_recipe_json(ingredients)
        except (ValidationError, ValueError) as e:
            st.error(f"Recipe generation failed: {e}")
            st.stop()

    # Display Recipe in a beautiful card
    st.markdown(f"""
    <div class="recipe-card fade-in">
        <h2 style="color: #667eea; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            🍽️ {recipe.title}
        </h2>
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem;">
            <h3 style="margin: 0; font-family: 'Poppins', sans-serif;">
                👥 Serves {recipe.servings} people
            </h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ingredients section with styled cards
    st.markdown("""
    <div class="recipe-card fade-in">
        <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            🛒 Ingredients & Quantities
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    ing_df = pd.DataFrame([{"Ingredient": i.name, "Grams": i.grams} for i in recipe.ingredients_grams])
    
    # Create ingredient cards
    ing_cols = st.columns(min(3, len(recipe.ingredients_grams)))
    for idx, ingredient in enumerate(recipe.ingredients_grams):
        with ing_cols[idx % 3]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); 
                        color: white; padding: 1rem; border-radius: 10px; 
                        text-align: center; margin: 0.5rem 0;">
                <div style="font-size: 1.5rem; font-weight: bold;">{ingredient.grams}g</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">{ingredient.name}</div>
            </div>
            """, unsafe_allow_html=True)

    # Cooking steps with enhanced styling
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 2rem;">
        <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            👨‍🍳 Cooking Instructions
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    for i, step in enumerate(recipe.steps, start=1):
        st.markdown(f"""
        <div style="background: white; border-left: 4px solid #667eea; 
                    padding: 1rem; margin: 1rem 0; border-radius: 0 10px 10px 0; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="color: #667eea; font-weight: bold; font-size: 1.1rem;">
                Step {i}
            </div>
            <div style="margin-top: 0.5rem; line-height: 1.6;">
                {step}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Compute macros
    with st.spinner("Calculating macros from USDA…"):
        ing_grams: List[Tuple[str, float]] = [(i.name, float(i.grams)) for i in recipe.ingredients_grams]
        per_ing_df, totals = compute_macros(ing_grams)

    # Macro breakdown by ingredient
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 2rem;">
        <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            📊 Nutritional Breakdown by Ingredient
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    if not per_ing_df.empty:
        # Create styled dataframe
        styled_df = per_ing_df.style.format({
            'Protein (g)': '{:.1f}',
            'Carbs (g)': '{:.1f}',
            'Fat (g)': '{:.1f}',
            'Fiber (g)': '{:.1f}',
            'Grams': '{:.0f}'
        }).set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#667eea'), ('color', 'white'), ('font-family', 'Poppins')]},
            {'selector': 'td', 'props': [('font-family', 'Poppins')]},
        ])
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
    else:
        st.markdown("""
        <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 10px; padding: 1rem; margin: 1rem 0;">
            <div style="color: #856404; font-family: 'Poppins', sans-serif;">
                💡 <strong>Tip:</strong> No nutrition data found. Try simpler ingredient names 
                (e.g., 'chicken breast' instead of 'free-range organic chicken').
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Total macros with beautiful cards
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 2rem;">
        <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            🔢 Total Recipe Nutrition
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    macro_cols = st.columns(4)
    macro_colors = [
        "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
        "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
    ]
    
    macro_icons = ["💪", "🌾", "🥑", "🌿"]
    macro_names = ["Protein", "Carbs", "Fat", "Fiber"]
    
    for idx, (key, value) in enumerate(totals.items()):
        with macro_cols[idx]:
            st.markdown(f"""
            <div style="background: {macro_colors[idx]}; color: white; padding: 1.5rem; 
                        border-radius: 15px; text-align: center; margin: 0.5rem 0; 
                        box-shadow: 0 5px 15px rgba(0,0,0,0.2);">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{macro_icons[idx]}</div>
                <div style="font-size: 2rem; font-weight: bold; font-family: 'Poppins', sans-serif;">{value}g</div>
                <div style="font-size: 0.9rem; opacity: 0.9; font-family: 'Poppins', sans-serif;">{macro_names[idx]}</div>
            </div>
            """, unsafe_allow_html=True)

    # Per serving macros
    per_serving = {k: round(v / recipe.servings, 2) for k, v in totals.items()} if recipe.servings else totals
    
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 2rem;">
        <h3 style="color: #333; font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
            🥄 Nutrition Per Serving
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    serving_cols = st.columns(4)
    for idx, (key, value) in enumerate(per_serving.items()):
        with serving_cols[idx]:
            st.markdown(f"""
            <div style="background: white; border: 2px solid {macro_colors[idx].split(',')[0].split('(')[1]}; 
                        padding: 1.5rem; border-radius: 15px; text-align: center; margin: 0.5rem 0;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{macro_icons[idx]}</div>
                <div style="font-size: 1.5rem; font-weight: bold; font-family: 'Poppins', sans-serif; color: #333;">{value}g</div>
                <div style="font-size: 0.8rem; color: #666; font-family: 'Poppins', sans-serif;">{macro_names[idx]} per serving</div>
            </div>
            """, unsafe_allow_html=True)

    # Footer note
    st.markdown("""
    <div style="background: #e8f4f8; border-radius: 10px; padding: 1rem; margin: 2rem 0; text-align: center;">
        <div style="color: #31708f; font-family: 'Poppins', sans-serif; font-size: 0.9rem;">
            📝 <strong>Note:</strong> Nutritional data sourced from USDA FoodData Central. 
            Values are estimates based on generic ingredients and may vary with specific brands or preparation methods.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Set recipe generated flag for success animation
    st.session_state.recipe_generated = True
    st.balloons()

# Footer with additional features
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; padding: 3rem 2rem; border-radius: 20px; 
            text-align: center; margin: 3rem 0;">
    <h2 style="font-family: 'Poppins', sans-serif; margin-bottom: 1rem;">
        🚀 Ready to Cook Something Amazing?
    </h2>
    <p style="font-family: 'Poppins', sans-serif; opacity: 0.9; font-size: 1.1rem;">
        Transform any combination of ingredients into a delicious, healthy meal with AI precision!
    </p>
    <div style="margin-top: 2rem;">
        <div style="display: inline-block; margin: 0 1rem;">
            <div style="font-size: 2rem;">🤖</div>
            <div style="font-size: 0.9rem;">AI-Powered</div>
        </div>
        <div style="display: inline-block; margin: 0 1rem;">
            <div style="font-size: 2rem;">⚡</div>
            <div style="font-size: 0.9rem;">Lightning Fast</div>
        </div>
        <div style="display: inline-block; margin: 0 1rem;">
            <div style="font-size: 2rem;">🎯</div>
            <div style="font-size: 0.9rem;">Personalized</div>
        </div>
        <div style="display: inline-block; margin: 0 1rem;">
            <div style="font-size: 2rem;">💯</div>
            <div style="font-size: 0.9rem;">100% Free</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
