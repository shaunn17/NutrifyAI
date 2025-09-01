import os
import json
import streamlit as st
import pandas as pd
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from typing import List, Tuple, Optional
from utils import compute_macros
from database import RecipeDatabase

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

# Initialize database
@st.cache_resource
def init_database():
    return RecipeDatabase()

db = init_database()

# --- Models for structured output validation ---
class IngredientOut(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    grams: float = Field(..., ge=0, description="Quantity in grams (approx)")

class RecipeOut(BaseModel):
    title: str
    servings: int = Field(..., ge=1, le=12)
    ingredients_grams: List[IngredientOut]
    steps: List[str]
    dietary_restriction: str = "None"
    cuisine_type: Optional[str] = None
    meal_type: Optional[str] = None
    cooking_time: Optional[str] = None
    difficulty_level: Optional[str] = None

# --- Helper to call Groq ---
def generate_recipe_json(ingredients: List[str]) -> RecipeOut:
    """
    Ask the model to produce a structured JSON recipe using ONLY user ingredients,
    with approximate grams for each ingredient.
    """
    client = Groq(api_key=GROQ_API_KEY)

    # system_msg = (
    #     "You are an expert chef and nutritionist with 20+ years of experience. Create delicious, practical recipes "
    #     "ONLY with the ingredients provided. Focus on flavor combinations that actually work together. "
    #     "CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no commentary, no markdown formatting. "
    #     "Return STRICT JSON with keys: title (string), servings (int 1-12), "
    #     "ingredients_grams (list of objects {name, grams}), steps (list of strings), "
    #     "dietary_restriction (string: MUST be one of: 'None', 'Vegetarian', 'Vegan', 'Keto', 'Paleo' - never null or empty), "
    #     "cuisine_type (string: Italian, Asian, Mexican, Mediterranean, American, Indian, French, Thai, or None), "
    #     "meal_type (string: Breakfast, Lunch, Dinner, Snacks, Desserts), "
    #     "cooking_time (string: Quick (15min), Medium (30min), Long (60min+)), "
    #     "difficulty_level (string: Beginner, Intermediate, Advanced). "
    #     "All ingredient quantities MUST have grams; estimate sensible amounts. "
    #     "Do not add ingredients not provided, except basic salt/pepper which you may exclude from macros. "
    #     "RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT."
    # )

    system_msg = (
    "You are a Michelin-starred chef and certified nutritionist. Create exceptional recipes using ONLY the provided ingredients. "
    "Your response must be a single, valid JSON object with no additional text, explanations, or markdown formatting. "
    "Never use code blocks, backticks, or any formatting. Start your response with { and end with }. "
    "Required JSON schema: {title: string, servings: integer 1-12, ingredients_grams: [{name: string, grams: number}], "
    "steps: [string], dietary_restriction: string, cuisine_type: string, meal_type: string, cooking_time: string, difficulty_level: string}. "
    "dietary_restriction must be exactly one of: None, Vegetarian, Vegan, Keto, Paleo. "
    "cuisine_type must be exactly one of: Italian, Asian, Mexican, Mediterranean, American, Indian, French, Thai, None. "
    "meal_type must be exactly one of: Breakfast, Lunch, Dinner, Snacks, Desserts. "
    "cooking_time must be exactly one of: Quick (15min), Medium (30min), Long (60min+). "
    "difficulty_level must be exactly one of: Beginner, Intermediate, Advanced. "
    "All ingredient quantities must be realistic numbers in grams. Use only provided ingredients except optional salt/pepper. "
    "Create balanced, flavorful recipes with proper cooking techniques and clear instructions."
)

    # user_msg = (
    #     "Ingredients: " + ", ".join(ingredients) + "\n\n"
    #     "CRITICAL RULES:\n"
    #     "1) Use ONLY these ingredients (ignore pantry basics like salt/pepper for macros).\n"
    #     "2) Create recipes that make culinary sense - think about flavor profiles and cooking techniques.\n"
    #     "3) Provide realistic grams per ingredient (150-300g protein, 50-150g carbs, 10-30g fats per serving).\n"
    #     "4) Write clear, step-by-step cooking instructions that a home cook can follow.\n"
    #     "5) Consider cooking methods: sauté, roast, grill, bake, etc. - use appropriate techniques.\n"
    #     "6) Balance flavors: sweet, salty, sour, umami - make it taste good!\n"
    #     "7) Servings must be an integer (1-12).\n"
    #     "8) RESPOND WITH ONLY VALID JSON - NO EXPLANATIONS, NO MARKDOWN, NO EXTRA TEXT."
    # )

    user_msg = (
    "Ingredients: " + ", ".join(ingredients) + "\n\n"
    "Create a recipe using ONLY these ingredients. Requirements:\n"
    "1. JSON format only - no markdown, no explanations, no code blocks\n"
    "2. Use all provided ingredients with realistic gram amounts\n"
    "3. Target nutrition per serving: 150-300g protein, 50-150g carbs, 10-30g fats\n"
    "4. Write 4-8 clear cooking steps with proper techniques\n"
    "5. Balance flavors and use appropriate cooking methods\n"
    "6. Ensure recipe is practical for home cooking\n"
    "7. Servings must be integer 1-12\n"
    "8. All string values must match exact schema options\n"
    "9. Start response with { and end with }\n"
    "10. No additional text outside the JSON object"
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

    # Try to extract JSON with improved error handling
    data = None
    
    # First, try to parse the entire content
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        # If that fails, try to find and extract JSON block
        try:
            # Look for JSON between first { and last }
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_content = content[start:end+1]
                data = json.loads(json_content)
            else:
                # Try to find JSON in code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    # Last resort: try to find any valid JSON structure
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                    else:
                        raise ValueError(f"Could not extract valid JSON from response. Error: {e}")
        except json.JSONDecodeError as e2:
            raise ValueError(f"Failed to parse JSON after multiple attempts. Original error: {e}, Secondary error: {e2}")
    
    if data is None:
        raise ValueError("No valid JSON data found in response.")

    # Debug: Print the raw data to see what we're getting
    print(f"DEBUG: Raw dietary_restriction from AI: {data.get('dietary_restriction', 'NOT_FOUND')}")
    
    # Fix dietary_restriction at the data level before Pydantic validation
    if data.get('dietary_restriction') is None or data.get('dietary_restriction') == "":
        data['dietary_restriction'] = "None"
    
    # Validate with pydantic
    recipe = RecipeOut(**data)
    
    # Ensure dietary_restriction is never null or empty
    if recipe.dietary_restriction is None or recipe.dietary_restriction == "" or recipe.dietary_restriction.strip() == "":
        recipe.dietary_restriction = "None"
    
    print(f"DEBUG: Final dietary_restriction: {recipe.dietary_restriction}")
    
    # Additional recipe quality validation
    recipe = validate_recipe_quality(recipe, ingredients)
    
    return recipe

def validate_recipe_quality(recipe: RecipeOut, original_ingredients: List[str]) -> RecipeOut:
    """
    Validate and improve recipe quality by checking for common issues.
    """
    # Check if all original ingredients are used
    original_ingredient_names = [ing.lower().strip() for ing in original_ingredients]
    recipe_ingredient_names = [ing.name.lower().strip() for ing in recipe.ingredients_grams]
    
    # Find missing ingredients
    missing_ingredients = []
    for orig_ing in original_ingredient_names:
        if not any(orig_ing in recipe_ing or recipe_ing in orig_ing for recipe_ing in recipe_ingredient_names):
            missing_ingredients.append(orig_ing)
    
    # Check for unrealistic serving sizes
    total_grams = sum(ing.grams for ing in recipe.ingredients_grams)
    if recipe.servings > 0:
        grams_per_serving = total_grams / recipe.servings
        if grams_per_serving < 100:  # Too small
            recipe.servings = max(1, int(total_grams / 200))
        elif grams_per_serving > 1000:  # Too large
            recipe.servings = max(1, int(total_grams / 500))
    
    # Check for reasonable ingredient quantities
    for ingredient in recipe.ingredients_grams:
        if ingredient.grams > 500:  # Unrealistically large
            ingredient.grams = min(ingredient.grams, 300)
        elif ingredient.grams < 5:  # Unrealistically small
            ingredient.grams = max(ingredient.grams, 10)
    
    return recipe

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* CSS Variables for Design System */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --accent-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --success-gradient: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        --glass-bg: rgba(255, 255, 255, 0.08);
        --glass-border: rgba(255, 255, 255, 0.15);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.8);
        --text-muted: rgba(255, 255, 255, 0.6);
        --shadow-light: 0 4px 20px rgba(0, 0, 0, 0.1);
        --shadow-medium: 0 8px 32px rgba(0, 0, 0, 0.15);
        --shadow-heavy: 0 16px 64px rgba(0, 0, 0, 0.2);
        --border-radius-sm: 8px;
        --border-radius-md: 16px;
        --border-radius-lg: 24px;
        --border-radius-xl: 32px;
        --transition-fast: 0.2s ease;
        --transition-medium: 0.3s ease;
        --transition-slow: 0.5s ease;
    }
    
    /* Main app styling with advanced background */
    .main {
        padding-top: 0;
        background: 
            radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(120, 219, 255, 0.2) 0%, transparent 50%),
            linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        position: relative;
        overflow-x: hidden;
    }
    
    /* Animated background elements */
    .main::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 25% 25%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 75% 75%, rgba(255, 255, 255, 0.05) 0%, transparent 50%);
        animation: backgroundFloat 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes backgroundFloat {
        0%, 100% { transform: translate(0, 0) rotate(0deg); }
        25% { transform: translate(-10px, -10px) rotate(1deg); }
        50% { transform: translate(10px, -5px) rotate(-1deg); }
        75% { transform: translate(-5px, 10px) rotate(0.5deg); }
    }
    
    /* Advanced glassmorphism with multiple layers */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        padding: 2rem;
        border-radius: var(--border-radius-lg);
        text-align: center;
        margin: 1.5rem 0;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-medium);
        transition: all var(--transition-medium);
        position: relative;
        overflow: hidden;
        z-index: 1;
    }
    
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.1) 100%);
        opacity: 0;
        transition: opacity var(--transition-medium);
    }
    
    .glass-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: var(--shadow-heavy);
        border-color: rgba(255, 255, 255, 0.25);
    }
    
    .glass-card:hover::before {
        opacity: 1;
    }
    
    .glass-card::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(from 0deg, transparent, rgba(255,255,255,0.1), transparent);
        animation: rotate 4s linear infinite;
        opacity: 0;
        transition: opacity var(--transition-medium);
    }
    
    .glass-card:hover::after {
        opacity: 1;
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* Hero header with advanced effects */
    .hero-header {
        background: var(--glass-bg);
        backdrop-filter: blur(30px) saturate(200%);
        -webkit-backdrop-filter: blur(30px) saturate(200%);
        padding: 4rem 3rem;
        border-radius: var(--border-radius-xl);
        margin: 2rem 0 3rem 0;
        color: var(--text-primary);
        text-align: center;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-heavy);
        position: relative;
        overflow: hidden;
        z-index: 1;
    }
    
    .hero-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 30% 30%, rgba(255,255,255,0.1) 0%, transparent 50%),
            radial-gradient(circle at 70% 70%, rgba(255,255,255,0.05) 0%, transparent 50%);
        animation: heroShimmer 6s ease-in-out infinite;
    }
    
    @keyframes heroShimmer {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.05); }
    }
    
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: var(--text-primary);
        text-shadow: 0 4px 8px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
        background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleGlow 3s ease-in-out infinite alternate;
    }
    
    @keyframes titleGlow {
        from { filter: drop-shadow(0 0 10px rgba(255,255,255,0.3)); }
        to { filter: drop-shadow(0 0 20px rgba(255,255,255,0.6)); }
    }
    
    .hero-subtitle {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.4rem;
        font-weight: 500;
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
        position: relative;
        z-index: 1;
        letter-spacing: 0.5px;
    }
    
    .hero-description {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        font-weight: 400;
        color: var(--text-muted);
        max-width: 700px;
        margin: 0 auto;
        line-height: 1.7;
        position: relative;
        z-index: 1;
    }
    
    /* Advanced feature styling */
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1.5rem;
        opacity: 0.9;
        position: relative;
        z-index: 1;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
        transition: all var(--transition-medium);
    }
    
    .glass-card:hover .feature-icon {
        transform: scale(1.1) rotate(5deg);
        filter: drop-shadow(0 8px 16px rgba(0,0,0,0.3));
    }
    
    .feature-title {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.75rem;
        font-size: 1.3rem;
        position: relative;
        z-index: 1;
        letter-spacing: 0.5px;
    }
    
    .feature-desc {
        font-family: 'Inter', sans-serif;
        color: var(--text-secondary);
        font-size: 1rem;
        line-height: 1.6;
        position: relative;
        z-index: 1;
    }
    
    /* Revolutionary input styling */
    .stTextArea textarea {
        border-radius: var(--border-radius-md);
        border: 2px solid var(--glass-border);
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        background: var(--glass-bg);
        backdrop-filter: blur(15px) saturate(150%);
        color: var(--text-primary);
        padding: 1rem;
        transition: all var(--transition-medium);
        box-shadow: var(--shadow-light);
    }
    
    .stTextArea textarea:focus {
        border-color: rgba(255, 255, 255, 0.4);
        box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.1), var(--shadow-medium);
        background: rgba(255, 255, 255, 0.12);
        transform: translateY(-2px);
    }
    
    .stTextArea textarea::placeholder {
        color: var(--text-muted);
        font-style: italic;
    }
    
    /* Advanced button styling */
    .stButton button {
        background: var(--glass-bg);
        color: var(--text-primary);
        border: 2px solid var(--glass-border);
        padding: 1rem 2rem;
        border-radius: var(--border-radius-md);
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        transition: all var(--transition-medium);
        backdrop-filter: blur(15px) saturate(150%);
        position: relative;
        overflow: hidden;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        box-shadow: var(--shadow-light);
    }
    
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateY(-3px) scale(1.02);
        box-shadow: var(--shadow-heavy);
        border-color: rgba(255, 255, 255, 0.3);
    }
    
    .stButton button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left var(--transition-slow);
    }
    
    .stButton button:hover::before {
        left: 100%;
    }
    
    /* Advanced recipe cards */
    .recipe-card {
        background: var(--glass-bg);
        backdrop-filter: blur(25px) saturate(180%);
        -webkit-backdrop-filter: blur(25px) saturate(180%);
        padding: 2.5rem;
        border-radius: var(--border-radius-xl);
        margin: 2rem 0;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-heavy);
        position: relative;
        overflow: hidden;
        z-index: 1;
    }
    
    .recipe-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
        animation: borderGlow 3s ease-in-out infinite;
    }
    
    @keyframes borderGlow {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }
    
    /* Advanced macro cards */
    .macro-card {
        background: var(--glass-bg);
        backdrop-filter: blur(20px) saturate(150%);
        color: var(--text-primary);
        padding: 2rem;
        border-radius: var(--border-radius-lg);
        text-align: center;
        margin: 0.75rem;
        border: 1px solid var(--glass-border);
        transition: all var(--transition-medium);
        position: relative;
        overflow: hidden;
    }
    
    .macro-card:hover {
        transform: translateY(-5px) scale(1.05);
        background: rgba(255, 255, 255, 0.12);
        box-shadow: var(--shadow-heavy);
    }
    
    .macro-value {
        font-size: 2.2rem;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        color: var(--text-primary);
        text-shadow: 0 4px 8px rgba(0,0,0,0.3);
        margin-bottom: 0.5rem;
    }
    
    .macro-label {
        font-size: 0.9rem;
        color: var(--text-secondary);
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Advanced sidebar styling */
    .css-1d391kg {
        background: var(--glass-bg);
        backdrop-filter: blur(25px) saturate(180%);
        border-right: 1px solid var(--glass-border);
        box-shadow: var(--shadow-medium);
    }
    
    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Revolutionary animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(50px) scale(0.95);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
    
    .fade-in {
        animation: fadeInUp 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    
    /* Advanced scrollbar */
    ::-webkit-scrollbar {
        width: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--glass-bg);
        border-radius: var(--border-radius-sm);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--glass-border);
        border-radius: var(--border-radius-sm);
        border: 2px solid var(--glass-bg);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.4);
    }
    
    /* Floating particles with advanced physics */
    .particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
    }
    
    .particle {
        position: absolute;
        width: 6px;
        height: 6px;
        background: rgba(255, 255, 255, 0.4);
        border-radius: 50%;
        animation: particleFloat 8s infinite linear;
        box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }
    
    @keyframes particleFloat {
        0% {
            transform: translateY(100vh) translateX(0) rotate(0deg) scale(0);
            opacity: 0;
        }
        10% {
            opacity: 1;
            transform: translateY(90vh) translateX(10px) rotate(36deg) scale(1);
        }
        90% {
            opacity: 1;
            transform: translateY(10vh) translateX(-10px) rotate(324deg) scale(1);
        }
        100% {
            transform: translateY(-10vh) translateX(0) rotate(360deg) scale(0);
            opacity: 0;
        }
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2.5rem;
        }
        
        .hero-subtitle {
            font-size: 1.2rem;
        }
        
        .glass-card {
            padding: 1.5rem;
            margin: 1rem 0;
        }
        
        .recipe-card {
            padding: 2rem;
        }
    }
    
    /* Loading states */
    .loading {
        position: relative;
        overflow: hidden;
    }
    
    .loading::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        animation: loading 1.5s infinite;
    }
    
    @keyframes loading {
        0% { left: -100%; }
        100% { left: 100%; }
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
        <h2 style="color: white; font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 1.8rem; text-shadow: 0 4px 8px rgba(0,0,0,0.3); letter-spacing: 1px;">🍽️ Chef's Tips</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card">
        <div class="feature-icon">🤖</div>
        <div class="feature-title">AI-Powered</div>
        <div class="feature-desc">Advanced Llama-3.1 model creates recipes tailored to your ingredients</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card">
        <div class="feature-icon">📊</div>
        <div class="feature-title">USDA Nutrition</div>
        <div class="feature-desc">Accurate macro data from 200,000+ verified food items</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card">
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
    
    st.markdown("---")
    
    # Database Statistics
    st.markdown("### 📊 **Your Recipe Stats**")
    
    # Get fresh stats if needed
    if st.session_state.get('stats_need_refresh', False):
        # Create fresh database connection for updated stats
        fresh_db = RecipeDatabase()
        stats = fresh_db.get_recipe_stats()
        st.session_state.stats_need_refresh = False  # Reset flag
    else:
        stats = db.get_recipe_stats()
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Recipes", stats['total_recipes'])
            st.metric("Favorites", stats['favorite_recipes'])
        
        with col2:
            st.metric("Avg Rating", f"{stats['average_rating']}/5")
            st.metric("Success Rate", f"{stats['success_rate']}%")
    except Exception as e:
        st.error(f"Database error: {str(e)}")
    
    st.markdown("---")
    
    # Recipe History Section
    if st.button("📚 View Recipe History", use_container_width=True):
        st.session_state.show_history = True
    
    if st.button("⭐ View Favorites", use_container_width=True):
        st.session_state.show_favorites = True
    
    st.markdown("---")
    
    # Recipe Management Section
    st.markdown("### 🗂️ **Recipe Management**")
    
    # Individual recipe deletion
    if st.button("🗑️ Delete Individual Recipe", use_container_width=True):
        st.session_state.show_delete_individual = True
    
    # Clear all recipes with confirmation
    if st.button("💥 Clear All Recipes", use_container_width=True, type="secondary"):
        st.session_state.show_clear_all = True

# --- Feature Cards Section ---
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="glass-card fade-in">
        <div class="feature-icon">🎯</div>
        <div class="feature-title">Personalized</div>
        <div class="feature-desc">Recipes using only YOUR ingredients</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="glass-card fade-in">
        <div class="feature-icon">🥗</div>
        <div class="feature-title">Healthy Focus</div>
        <div class="feature-desc">Optimized for nutrition and wellness</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="glass-card fade-in">
        <div class="feature-icon">📱</div>
        <div class="feature-title">Mobile Ready</div>
        <div class="feature-desc">Perfect for kitchen use on any device</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="glass-card fade-in">
        <div class="feature-icon">💰</div>
        <div class="feature-title">100% Free</div>
        <div class="feature-desc">No subscriptions or hidden costs</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Input Section ---
st.markdown("""
<div style="background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(25px) saturate(180%); padding: 2.5rem; border-radius: 32px; border: 1px solid rgba(255, 255, 255, 0.15); margin: 2rem 0; box-shadow: 0 16px 64px rgba(0, 0, 0, 0.2);">
    <h3 style="color: white; font-family: 'Space Grotesk', sans-serif; margin-bottom: 1rem; font-weight: 600; font-size: 1.5rem; letter-spacing: 0.5px;">
        🛒 What's in your kitchen today?
    </h3>
</div>
""", unsafe_allow_html=True)

default_ing = ""

col1, col2 = st.columns([3, 1])
with col1:
    ingredients_input = st.text_area(
        "Ingredients",
        value=default_ing, 
        height=100, 
        placeholder="Enter your ingredients separated by commas...\nExample: chicken breast, quinoa, spinach, olive oil, garlic",
        help="💡 Tip: Use simple ingredient names for best results!",
        label_visibility="collapsed"
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
            "Surprise Ingredients",
            value=random.choice(surprise_ingredients), 
            height=100, 
            placeholder="Enter your ingredients separated by commas...",
            help="💡 Tip: Use simple ingredient names for best results!",
            key="surprise_ingredients",
            label_visibility="collapsed"
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
        <h2 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 1rem; font-weight: 700; font-size: 2rem; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
            🍽️ {recipe.title}
        </h2>
        <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 1rem; border-radius: 12px; margin-bottom: 1rem; border: 1px solid rgba(255, 255, 255, 0.2);">
            <h3 style="margin: 0; font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 1.1rem;">
                👥 Serves {recipe.servings} people
            </h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display category badges
    if recipe.dietary_restriction or recipe.cuisine_type or recipe.meal_type or recipe.cooking_time or recipe.difficulty_level:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); padding: 1rem; border-radius: 12px; margin-bottom: 1rem; border: 1px solid rgba(255, 255, 255, 0.2);">
            <h4 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.5rem; font-weight: 600; font-size: 1rem;">
                🏷️ Recipe Categories
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Create category badges
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if recipe.dietary_restriction:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <div style="font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">🥗 {recipe.dietary_restriction}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if recipe.cuisine_type:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <div style="font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">🌍 {recipe.cuisine_type}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if recipe.meal_type:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <div style="font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">🍽️ {recipe.meal_type}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col4:
            if recipe.cooking_time:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <div style="font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">⏱️ {recipe.cooking_time}</div>
                </div>
                """, unsafe_allow_html=True)
        
        with col5:
            if recipe.difficulty_level:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
                    <div style="font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">📚 {recipe.difficulty_level}</div>
                </div>
                """, unsafe_allow_html=True)

    # Ingredients section with styled cards
    st.markdown("""
    <div class="recipe-card fade-in">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
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
            <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 1.25rem; border-radius: 12px; 
                        text-align: center; margin: 0.3rem 0; border: 1px solid rgba(255, 255, 255, 0.2); transition: all 0.3s ease;">
                <div style="font-size: 1.4rem; font-weight: 700; color: white; font-family: 'JetBrains Mono', monospace; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">{ingredient.grams}g</div>
                <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.9); font-weight: 500; font-family: 'Inter', sans-serif; margin-top: 0.5rem;">{ingredient.name}</div>
            </div>
            """, unsafe_allow_html=True)

    # Cooking steps with enhanced styling
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 1.5rem;">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
            👨‍🍳 Cooking Instructions
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Display steps with improved visibility
    for i, step in enumerate(recipe.steps, start=1):
        # Create a container for better styling
        with st.container():
            # Step header
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(15px); color: white; padding: 1rem 1.5rem; margin: 1rem 0 0 0; 
                        border-radius: 16px 16px 0 0; border: 1px solid rgba(255, 255, 255, 0.2);">
                <div style="font-weight: 600; font-size: 1.1rem; font-family: 'JetBrains Mono', monospace;">
                    🔸 Step {i}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Step content - escaping HTML characters to prevent issues
            import html
            step_escaped = html.escape(step)
            
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); padding: 1.5rem; margin: 0 0 1.5rem 0; 
                        border-radius: 0 0 16px 16px; border: 1px solid rgba(255, 255, 255, 0.2); border-top: none;">
                <div style="color: rgba(255, 255, 255, 0.9); font-size: 1rem; line-height: 1.7; font-family: 'Inter', sans-serif;">
                    {step_escaped}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Compute macros
    with st.spinner("Calculating macros from USDA…"):
        ing_grams: List[Tuple[str, float]] = [(i.name, float(i.grams)) for i in recipe.ingredients_grams]
        per_ing_df, totals = compute_macros(ing_grams)

    # Macro breakdown by ingredient
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 1.5rem;">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
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
            'Calories': '{:.0f}',
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
    <div class="recipe-card fade-in" style="margin-top: 1.5rem;">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
            🔢 Total Recipe Nutrition
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    macro_cols = st.columns(5)
    macro_colors = [
        "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
        "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
        "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)"
    ]
    
    macro_icons = ["💪", "🌾", "🥑", "🌿", "🔥"]
    macro_names = ["Protein", "Carbs", "Fat", "Fiber", "Calories"]
    
    for idx, (key, value) in enumerate(totals.items()):
        with macro_cols[idx]:
            st.markdown(f"""
            <div style="background: #f8fafc; color: #1e293b; padding: 1.25rem; 
                        border-radius: 8px; text-align: center; margin: 0.5rem 0; 
                        border: 1px solid #e2e8f0;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{macro_icons[idx]}</div>
                <div style="font-size: 1.5rem; font-weight: 600; font-family: 'Inter', sans-serif; color: #0f172a;">{value}g</div>
                <div style="font-size: 0.8rem; color: #64748b; font-family: 'Inter', sans-serif; font-weight: 500;">{macro_names[idx]}</div>
            </div>
            """, unsafe_allow_html=True)

    # Per serving macros
    per_serving = {k: round(v / recipe.servings, 2) for k, v in totals.items()} if recipe.servings else totals
    
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 1.5rem;">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
            🥄 Nutrition Per Serving
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    serving_cols = st.columns(5)
    for idx, (key, value) in enumerate(per_serving.items()):
        with serving_cols[idx]:
            st.markdown(f"""
            <div style="background: white; border: 2px solid {macro_colors[idx].split(',')[0].split('(')[1]}; 
                        padding: 1rem; border-radius: 12px; text-align: center; margin: 0.4rem 0;">
                <div style="font-size: 1.2rem; margin-bottom: 0.4rem;">{macro_icons[idx]}</div>
                <div style="font-size: 1.2rem; font-weight: bold; font-family: 'Poppins', sans-serif; color: #333;">{value}g</div>
                <div style="font-size: 0.75rem; color: #666; font-family: 'Poppins', sans-serif;">{macro_names[idx]} per serving</div>
            </div>
            """, unsafe_allow_html=True)

    # Recipe Quality Feedback
    st.markdown("""
    <div class="recipe-card fade-in" style="margin-top: 1.5rem;">
        <h3 style="color: white; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem; font-weight: 600; font-size: 1.3rem;">
            🎯 Recipe Quality Check
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Check recipe quality
    quality_issues = []
    quality_score = 100
    
    # Check ingredient usage
    original_ingredient_names = [ing.lower().strip() for ing in ingredients]
    recipe_ingredient_names = [ing.name.lower().strip() for ing in recipe.ingredients_grams]
    missing_ingredients = []
    for orig_ing in original_ingredient_names:
        if not any(orig_ing in recipe_ing or recipe_ing in orig_ing for recipe_ing in recipe_ingredient_names):
            missing_ingredients.append(orig_ing)
    
    if missing_ingredients:
        # Create helpful message for missing ingredients
        missing_list = ', '.join(missing_ingredients)
        quality_issues.append(f"⚠️ **Ingredients not used in recipe:** {missing_list}")
        quality_issues.append("💡 **Tip:** Check spelling (e.g., 'broccoli' not 'brocoli') or try simpler ingredient names")
        quality_score -= 20
    
    # Check serving size
    total_grams = sum(ing.grams for ing in recipe.ingredients_grams)
    if recipe.servings > 0:
        grams_per_serving = total_grams / recipe.servings
        if grams_per_serving < 150:
            quality_issues.append("⚠️ **Serving size may be too small** - Consider reducing the number of servings")
            quality_score -= 10
        elif grams_per_serving > 800:
            quality_issues.append("⚠️ **Serving size may be too large** - Consider increasing the number of servings")
            quality_score -= 10
    
    # Check cooking instructions
    if len(recipe.steps) < 3:
        quality_issues.append("⚠️ **Cooking instructions could be more detailed** - Try regenerating for more comprehensive steps")
        quality_score -= 15
    
    # Display quality feedback
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if quality_issues:
            st.warning("**🔍 Recipe Quality Analysis:**")
            for issue in quality_issues:
                st.write(f"• {issue}")
            st.info("💡 **Need help?** Try regenerating with corrected spelling or simpler ingredient names for better results.")
        else:
            st.success("✅ **Recipe looks great!** All quality checks passed.")
    
    with col2:
        if quality_score >= 90:
            st.success(f"**Quality Score: {quality_score}/100** 🌟")
        elif quality_score >= 70:
            st.info(f"**Quality Score: {quality_score}/100** 👍")
        else:
            st.warning(f"**Quality Score: {quality_score}/100** ⚠️")
    
    # Footer note
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px); border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2);">
        <div style="color: rgba(255, 255, 255, 0.9); font-family: 'Inter', sans-serif; font-size: 0.9rem;">
            📝 <strong>Note:</strong> Nutritional data sourced from USDA FoodData Central. 
            Values are estimates based on generic ingredients and may vary with specific brands or preparation methods.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Save recipe to database
    try:
        ingredients_for_db = [{"name": i.name, "grams": float(i.grams)} for i in recipe.ingredients_grams]
        recipe_id = db.save_recipe(
            title=recipe.title,
            servings=recipe.servings,
            ingredients=ingredients_for_db,
            steps=recipe.steps,
            nutrition_per_recipe=totals,
            nutrition_per_serving=per_serving,
            dietary_restriction=recipe.dietary_restriction,
            cuisine_type=recipe.cuisine_type,
            meal_type=recipe.meal_type,
            cooking_time=recipe.cooking_time,
            difficulty_level=recipe.difficulty_level
        )
        
        # Log successful generation
        db.log_recipe_generation(
            input_ingredients=ingredients_input,
            recipe_id=recipe_id,
            success=True
        )
        
        # Store recipe ID in session state for potential rating/favoriting
        st.session_state.current_recipe_id = recipe_id
        
        # Success notification with rating/favorite options
        st.success(f"✅ Recipe saved to database! Recipe ID: {recipe_id[:8]}...")
        
        # Add rating and favorite options for the current recipe
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("### 💫 Rate this recipe:")
        
        with col2:
            rating = st.selectbox(
                "Rating (1-5):",
                options=[0, 1, 2, 3, 4, 5],
                index=0,
                key="current_recipe_rating"
            )
            if rating > 0:
                if db.update_recipe_rating(recipe_id, rating):
                    st.success(f"Rated {rating}/5 ⭐")
                    # Set flag to force stats refresh
                    st.session_state.stats_need_refresh = True
                    st.rerun()
        
        with col3:
            if st.button("🤍 Add to Favorites", key="add_favorite"):
                if db.toggle_favorite(recipe_id):
                    st.success("Added to favorites! 💖")
        
    except Exception as e:
        # Log failed save attempt
        db.log_recipe_generation(
            input_ingredients=ingredients_input,
            success=False,
            error_message=str(e)
        )
        st.warning(f"⚠️ Recipe generated but couldn't save to database: {str(e)}")
    
    # Set recipe generated flag for success animation
    st.session_state.recipe_generated = True
    st.balloons()

# --- Recipe Filtering Section ---
st.markdown("---")
st.markdown("## 🔍 Recipe Filtering & Categories")

# Define available categories
dietary_options = ["All", "None", "Vegetarian", "Vegan", "Keto", "Paleo"]
cuisine_options = ["All", "Italian", "Asian", "Mexican", "Mediterranean", "American", "Indian", "French", "Thai"]
meal_options = ["All", "Breakfast", "Lunch", "Dinner", "Snacks", "Desserts"]
time_options = ["All", "Quick (15min)", "Medium (30min)", "Long (60min+)"]
difficulty_options = ["All", "Beginner", "Intermediate", "Advanced"]

# Create filter columns
col1, col2, col3 = st.columns(3)
col4, col5 = st.columns(2)

with col1:
    selected_dietary = st.selectbox("🥗 Dietary Restriction", dietary_options)
    
with col2:
    selected_cuisine = st.selectbox("🌍 Cuisine Type", cuisine_options)
    
with col3:
    selected_meal = st.selectbox("🍽️ Meal Type", meal_options)
    
with col4:
    selected_time = st.selectbox("⏱️ Cooking Time", time_options)
    
with col5:
    selected_difficulty = st.selectbox("📚 Difficulty Level", difficulty_options)

# Apply filters
if st.button("🔍 Apply Filters", type="primary"):
    # Convert "All" selections to None for database query
    dietary_filter = None if selected_dietary == "All" else selected_dietary
    cuisine_filter = None if selected_cuisine == "All" else selected_cuisine
    meal_filter = None if selected_meal == "All" else selected_meal
    time_filter = None if selected_time == "All" else selected_time
    difficulty_filter = None if selected_difficulty == "All" else selected_difficulty
    
    # Get filtered recipes
    filtered_recipes = db.filter_recipes(
        dietary_restriction=dietary_filter,
        cuisine_type=cuisine_filter,
        meal_type=meal_filter,
        cooking_time=time_filter,
        difficulty_level=difficulty_filter
    )
    
    if filtered_recipes:
        st.success(f"Found {len(filtered_recipes)} recipe(s) matching your criteria!")
        
        # Display filtered recipes
        for recipe in filtered_recipes:
            with st.expander(f"🍽️ {recipe.title} - {recipe.meal_type or 'Meal'}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Servings:** {recipe.servings}")
                    st.write(f"**Ingredients:** {', '.join([ing['name'] for ing in recipe.ingredients])}")
                    
                    # Display category badges
                    if recipe.dietary_restriction or recipe.cuisine_type or recipe.meal_type or recipe.cooking_time or recipe.difficulty_level:
                        st.write("**Categories:**")
                        badges = []
                        if recipe.dietary_restriction:
                            badges.append(f"🥗 {recipe.dietary_restriction}")
                        if recipe.cuisine_type:
                            badges.append(f"🌍 {recipe.cuisine_type}")
                        if recipe.meal_type:
                            badges.append(f"🍽️ {recipe.meal_type}")
                        if recipe.cooking_time:
                            badges.append(f"⏱️ {recipe.cooking_time}")
                        if recipe.difficulty_level:
                            badges.append(f"📚 {recipe.difficulty_level}")
                        
                        st.markdown(" ".join([f"`{badge}`" for badge in badges]))
                
                with col2:
                    # Rating system
                    current_rating = recipe.rating or 0
                    rating = st.selectbox(
                        "Rate this recipe:",
                        options=[0, 1, 2, 3, 4, 5],
                        index=current_rating,
                        key=f"filter_rating_{recipe.id}"
                    )
                    if rating != current_rating and rating > 0:
                        if db.update_recipe_rating(recipe.id, rating):
                            st.success("Rating updated!")
                            # Set flag to force stats refresh
                            st.session_state.stats_need_refresh = True
                            st.rerun()
                
                with col3:
                    # Favorite toggle
                    fav_text = "💖 Unfavorite" if recipe.is_favorite else "🤍 Favorite"
                    if st.button(fav_text, key=f"filter_fav_{recipe.id}"):
                        if db.toggle_favorite(recipe.id):
                            st.success("Favorite status updated!")
                            st.rerun()
                
                # Show nutrition summary
                if recipe.nutrition_per_serving:
                    st.write("**Nutrition per serving:**")
                    nut_cols = st.columns(5)
                    nutrients = ["Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Calories"]
                    for i, nutrient in enumerate(nutrients):
                        if nutrient in recipe.nutrition_per_serving:
                            unit = "g" if nutrient != "Calories" else "cal"
                            nut_cols[i].metric(
                                nutrient.replace(" (g)", ""), 
                                f"{recipe.nutrition_per_serving[nutrient]}{unit}"
                            )
    else:
        st.info("No recipes found matching your criteria. Try adjusting your filters or generate some new recipes!")

# Recipe History and Favorites Sections
if st.session_state.get('show_history', False):
    st.markdown("---")
    st.markdown("## 📚 Recipe History")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Search recipes:", placeholder="Search by title or ingredient...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Close History"):
            st.session_state.show_history = False
            st.rerun()
    
    try:
        if search_query:
            recipes = db.search_recipes(search_query)
        else:
            recipes = db.get_all_recipes(limit=10)
        
        if recipes:
            for recipe in recipes:
                with st.expander(f"🍽️ {recipe.title} - {recipe.created_at[:10]}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Servings:** {recipe.servings}")
                        st.write(f"**Ingredients:** {', '.join([ing['name'] for ing in recipe.ingredients])}")
                        
                        # Display category badges
                        if recipe.dietary_restriction or recipe.cuisine_type or recipe.meal_type or recipe.cooking_time or recipe.difficulty_level:
                            st.write("**Categories:**")
                            badges = []
                            if recipe.dietary_restriction:
                                badges.append(f"🥗 {recipe.dietary_restriction}")
                            if recipe.cuisine_type:
                                badges.append(f"🌍 {recipe.cuisine_type}")
                            if recipe.meal_type:
                                badges.append(f"🍽️ {recipe.meal_type}")
                            if recipe.cooking_time:
                                badges.append(f"⏱️ {recipe.cooking_time}")
                            if recipe.difficulty_level:
                                badges.append(f"📚 {recipe.difficulty_level}")
                            
                            st.markdown(" ".join([f"`{badge}`" for badge in badges]))
                    
                    with col2:
                        # Rating system
                        current_rating = recipe.rating or 0
                        rating = st.selectbox(
                            "Rate this recipe:",
                            options=[0, 1, 2, 3, 4, 5],
                            index=current_rating,
                            key=f"rating_{recipe.id}"
                        )
                        if rating != current_rating and rating > 0:
                            if db.update_recipe_rating(recipe.id, rating):
                                st.success("Rating updated!")
                                # Set flag to force stats refresh
                                st.session_state.stats_need_refresh = True
                                st.rerun()
                    
                    with col3:
                        # Favorite toggle
                        fav_text = "💖 Unfavorite" if recipe.is_favorite else "🤍 Favorite"
                        if st.button(fav_text, key=f"fav_{recipe.id}"):
                            if db.toggle_favorite(recipe.id):
                                st.success("Favorite status updated!")
                                st.rerun()
                    
                    # Show nutrition summary
                    if recipe.nutrition_per_serving:
                        st.write("**Nutrition per serving:**")
                        nut_cols = st.columns(5)
                        nutrients = ["Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Calories"]
                        for i, nutrient in enumerate(nutrients):
                            if nutrient in recipe.nutrition_per_serving:
                                unit = "g" if nutrient != "Calories" else "cal"
                                nut_cols[i].metric(
                                    nutrient.replace(" (g)", ""), 
                                    f"{recipe.nutrition_per_serving[nutrient]}{unit}"
                                )
        else:
            st.info("No recipes found. Generate some recipes first!")
            
    except Exception as e:
        st.error(f"Error loading recipe history: {str(e)}")

if st.session_state.get('show_favorites', False):
    st.markdown("---")
    st.markdown("## ⭐ Favorite Recipes")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Close Favorites"):
            st.session_state.show_favorites = False
            st.rerun()
    
    try:
        favorites = db.get_favorites()
        
        if favorites:
            for recipe in favorites:
                with st.expander(f"⭐ {recipe.title} - Rating: {recipe.rating or 'Not rated'}/5"):
                    st.write(f"**Created:** {recipe.created_at[:10]}")
                    st.write(f"**Servings:** {recipe.servings}")
                    st.write(f"**Ingredients:** {', '.join([ing['name'] for ing in recipe.ingredients])}")
                    
                    # Display category badges
                    if recipe.dietary_restriction or recipe.cuisine_type or recipe.meal_type or recipe.cooking_time or recipe.difficulty_level:
                        st.write("**Categories:**")
                        badges = []
                        if recipe.dietary_restriction:
                            badges.append(f"🥗 {recipe.dietary_restriction}")
                        if recipe.cuisine_type:
                            badges.append(f"🌍 {recipe.cuisine_type}")
                        if recipe.meal_type:
                            badges.append(f"🍽️ {recipe.meal_type}")
                        if recipe.cooking_time:
                            badges.append(f"⏱️ {recipe.cooking_time}")
                        if recipe.difficulty_level:
                            badges.append(f"📚 {recipe.difficulty_level}")
                        
                        st.markdown(" ".join([f"`{badge}`" for badge in badges]))
                    
                    # Show steps
                    st.write("**Cooking Steps:**")
                    for i, step in enumerate(recipe.steps, 1):
                        st.write(f"{i}. {step}")
                    
                    # Show nutrition
                    if recipe.nutrition_per_serving:
                        st.write("**Nutrition per serving:**")
                        nut_cols = st.columns(5)
                        nutrients = ["Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Calories"]
                        for i, nutrient in enumerate(nutrients):
                            if nutrient in recipe.nutrition_per_serving:
                                unit = "g" if nutrient != "Calories" else "cal"
                                nut_cols[i].metric(
                                    nutrient.replace(" (g)", ""), 
                                    f"{recipe.nutrition_per_serving[nutrient]}{unit}"
                                )
        else:
            st.info("No favorite recipes yet. Mark some recipes as favorites!")
            
    except Exception as e:
        st.error(f"Error loading favorite recipes: {str(e)}")

# --- Recipe Management Sections ---

# Individual Recipe Deletion
if st.session_state.get('show_delete_individual', False):
    st.markdown("---")
    st.markdown("## 🗑️ Delete Individual Recipe")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Close Deletion"):
            st.session_state.show_delete_individual = False
            st.rerun()
    
    try:
        all_recipes = db.get_all_recipes(limit=50)
        
        if all_recipes:
            st.warning("⚠️ **Warning:** Deleting a recipe is permanent and cannot be undone!")
            
            # Create a list of recipe options for selection
            recipe_options = [f"{recipe.title} ({recipe.created_at[:10]})" for recipe in all_recipes]
            recipe_ids = [recipe.id for recipe in all_recipes]
            
            selected_recipe_index = st.selectbox(
                "Select a recipe to delete:",
                options=range(len(recipe_options)),
                format_func=lambda x: recipe_options[x],
                key="delete_recipe_select"
            )
            
            if selected_recipe_index is not None:
                selected_recipe = all_recipes[selected_recipe_index]
                
                # Show recipe details before deletion
                st.markdown("### Recipe Details:")
                st.write(f"**Title:** {selected_recipe.title}")
                st.write(f"**Created:** {selected_recipe.created_at[:10]}")
                st.write(f"**Servings:** {selected_recipe.servings}")
                st.write(f"**Ingredients:** {', '.join([ing['name'] for ing in selected_recipe.ingredients])}")
                
                # Confirmation button
                if st.button("🗑️ Delete This Recipe", type="primary"):
                    if db.delete_recipe(selected_recipe.id):
                        st.success(f"✅ Recipe '{selected_recipe.title}' deleted successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete recipe. Please try again.")
        else:
            st.info("No recipes found to delete. Generate some recipes first!")
            
    except Exception as e:
        st.error(f"Error loading recipes for deletion: {str(e)}")

# Clear All Recipes
if st.session_state.get('show_clear_all', False):
    st.markdown("---")
    st.markdown("## 💥 Clear All Recipes")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Cancel"):
            st.session_state.show_clear_all = False
            st.rerun()
    
    try:
        stats = db.get_recipe_stats()
        
        st.error("🚨 **DANGER ZONE** 🚨")
        st.markdown("""
        **This action will permanently delete:**
        - All saved recipes
        - All recipe history
        - All ratings and favorites
        - All user preferences
        
        **This action cannot be undone!**
        """)
        
        st.markdown(f"**Current Database Stats:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Recipes", stats['total_recipes'])
        with col2:
            st.metric("Favorites", stats['favorite_recipes'])
        with col3:
            st.metric("Total History", stats['total_attempts'])
        
        # Confirmation input
        confirmation = st.text_input(
            "Type 'DELETE ALL' to confirm:",
            placeholder="Type exactly: DELETE ALL",
            key="clear_all_confirmation"
        )
        
        if confirmation == "DELETE ALL":
            if st.button("💥 CONFIRM DELETE ALL RECIPES", type="primary"):
                if db.clear_all_recipes():
                    st.success("✅ All recipes and history cleared successfully!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Failed to clear recipes. Please try again.")
        elif confirmation:
            st.warning("❌ Please type 'DELETE ALL' exactly to confirm.")
            
    except Exception as e:
        st.error(f"Error accessing database: {str(e)}")

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
