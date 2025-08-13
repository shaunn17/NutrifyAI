import os
import json
import streamlit as st
import pandas as pd
from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from typing import List, Tuple
from utils import compute_macros

st.set_page_config(page_title="AI Healthy Recipe & Macros", page_icon="🥗", layout="centered")

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

# --- UI ---
st.title("🥗 AI‑Powered Healthy Recipe & Macro Calculator")
st.caption("Free AI (Groq Llama‑3.1) + Free USDA FoodData Central = your healthy meal plan.")

default_ing = "chicken breast, quinoa, spinach, olive oil, garlic"
ingredients_input = st.text_area(
    "Enter ingredients you have (comma separated):",
    value=default_ing, height=90, help="Example: chicken breast, quinoa, spinach, olive oil, garlic"
)

colA, colB = st.columns([1,1])
with colA:
    run_btn = st.button("Generate Recipe")
with colB:
    st.write("")

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

    st.subheader("🍽 Recipe")
    st.markdown(f"**{recipe.title}**")
    st.markdown(f"**Servings:** {recipe.servings}")

    st.markdown("**Ingredients (grams):**")
    ing_df = pd.DataFrame([{"Ingredient": i.name, "Grams": i.grams} for i in recipe.ingredients_grams])
    st.dataframe(ing_df, hide_index=True)

    st.markdown("**Steps:**")
    for i, step in enumerate(recipe.steps, start=1):
        st.write(f"{i}. {step}")

    # Compute macros
    with st.spinner("Calculating macros from USDA…"):
        ing_grams: List[Tuple[str, float]] = [(i.name, float(i.grams)) for i in recipe.ingredients_grams]
        per_ing_df, totals = compute_macros(ing_grams)

    st.subheader("📊 Macros by Ingredient (per recipe)")
    if not per_ing_df.empty:
        st.dataframe(per_ing_df, hide_index=True)
    else:
        st.info("No macros found. Try simpler ingredient names (e.g., 'chicken breast' instead of 'free-range chicken').")

    st.subheader("🔢 Total Macros (per recipe)")
    st.write(totals)

    per_serving = {k: round(v / recipe.servings, 2) for k, v in totals.items()} if recipe.servings else totals
    st.subheader("🥄 Macros per Serving")
    st.write(per_serving)

    st.caption("Note: USDA matches are best for generic/raw ingredients. Brand-specific items may vary.")
