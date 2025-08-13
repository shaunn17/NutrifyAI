import os
import re
import requests
import pandas as pd
from typing import Dict, List, Tuple, Optional

USDA_API_KEY = os.environ.get("USDA_API_KEY") or os.environ.get("usda_api_key")

# Target nutrient names in USDA
NUTRIENT_KEYS = {
    "protein": "Protein",
    "carbs": "Carbohydrate, by difference",
    "fat": "Total lipid (fat)",
    "fiber": "Fiber, total dietary",
}

def _first(lst, default=None):
    return lst[0] if lst else default

def search_food_fdc_id(query: str) -> Optional[int]:
    """
    Find the most relevant USDA FDC ID for a food name.
    Strategy:
      - Search FDC with pageSize=1 to grab the top match.
    """
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"query": query, "pageSize": 1, "api_key": USDA_API_KEY}
    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        foods = data.get("foods", [])
        if not foods:
            return None
        return foods[0].get("fdcId")
    except Exception:
        return None

def get_food_nutrients_per_100g(fdc_id: int) -> Optional[Dict[str, float]]:
    """
    Return grams of protein/carbs/fat/fiber **per 100 g** for an FDC ID if possible.
    USDA 'foodNutrients' amounts are commonly per 100g for Foundation/Survey data.
    """
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": USDA_API_KEY}
    try:
        res = requests.get(url, params=params, timeout=20)
        res.raise_for_status()
        data = res.json()
    except Exception:
        return None

    result = {"Protein (g)": 0.0, "Carbs (g)": 0.0, "Fat (g)": 0.0, "Fiber (g)": 0.0}

    nutrients = data.get("foodNutrients", []) or []
    for n in nutrients:
        nutrient_name = (n.get("nutrient") or {}).get("name", "")
        amount = n.get("amount", None)
        if amount is None:
            continue
        if nutrient_name == NUTRIENT_KEYS["protein"]:
            result["Protein (g)"] = float(amount)
        elif nutrient_name == NUTRIENT_KEYS["carbs"]:
            result["Carbs (g)"] = float(amount)
        elif nutrient_name == NUTRIENT_KEYS["fat"]:
            result["Fat (g)"] = float(amount)
        elif nutrient_name == NUTRIENT_KEYS["fiber"]:
            result["Fiber (g)"] = float(amount)

    return result

def scale_macros(per100g: Dict[str, float], grams: float) -> Dict[str, float]:
    """Scale 100g macros by the provided grams."""
    factor = grams / 100.0 if grams else 0.0
    return {
        "Protein (g)": round(per100g.get("Protein (g)", 0.0) * factor, 2),
        "Carbs (g)": round(per100g.get("Carbs (g)", 0.0) * factor, 2),
        "Fat (g)": round(per100g.get("Fat (g)", 0.0) * factor, 2),
        "Fiber (g)": round(per100g.get("Fiber (g)", 0.0) * factor, 2),
    }

def compute_macros(ingredient_grams: List[Tuple[str, float]]) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    ingredient_grams: [(ingredient_name, grams), ...]
    Returns (df_per_ingredient, totals_dict) where totals are per recipe.
    """
    rows = []
    for name, grams in ingredient_grams:
        fdc_id = search_food_fdc_id(name)
        if not fdc_id:
            rows.append({
                "Ingredient": name, "Grams": grams,
                "Protein (g)": 0, "Carbs (g)": 0, "Fat (g)": 0, "Fiber (g)": 0,
                "Note": "No USDA match"
            })
            continue

        per100 = get_food_nutrients_per_100g(fdc_id) or {}
        scaled = scale_macros(per100, grams)
        rows.append({
            "Ingredient": name, "Grams": grams,
            **scaled, "Note": ""
        })

    df = pd.DataFrame(rows)
    if df.empty:
        totals = {"Protein (g)": 0.0, "Carbs (g)": 0.0, "Fat (g)": 0.0, "Fiber (g)": 0.0}
        return df, totals

    totals = {
        "Protein (g)": round(df["Protein (g)"].sum(), 2),
        "Carbs (g)": round(df["Carbs (g)"].sum(), 2),
        "Fat (g)": round(df["Fat (g)"].sum(), 2),
        "Fiber (g)": round(df["Fiber (g)"].sum(), 2),
    }
    return df, totals
