"""Fridge to Recipe Planner
Streamlit UI + Gemini Flash (google-genai SDK) with structured JSON output.

Run:  streamlit run app.py
"""

import os
from typing import List

import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

MODEL_NAME = "gemini-2.5-flash"  # swap for any newer Flash model you have access to

# ----------------------------------------------------------------------------
# Structured output schema
# ----------------------------------------------------------------------------


class Recipe(BaseModel):
    name: str
    description: str = Field(description="One appealing sentence about the dish")
    cuisine: str
    prep_time_minutes: int
    cook_time_minutes: int
    difficulty: str = Field(description="Easy, Medium, or Hard")
    servings: int
    calories_per_serving: int = Field(description="Rough estimate")
    ingredients_from_fridge: List[str] = Field(
        description="Ingredients from the user's list used in this recipe, with quantities"
    )
    pantry_staples_used: List[str] = Field(
        description="Basic staples used (oil, salt, spices...) with quantities"
    )
    missing_ingredients: List[str] = Field(
        description="Anything needed that the user did NOT list. Empty if none."
    )
    steps: List[str]
    tip: str = Field(description="One short chef tip")


class RecipeList(BaseModel):
    recipes: List[Recipe]


# ----------------------------------------------------------------------------
# Gemini helpers
# ----------------------------------------------------------------------------


def get_api_key() -> str:
    """Look for the key in Streamlit secrets, env var, then the sidebar."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets.toml file
    return os.getenv("GEMINI_API_KEY", "")


def build_prompt(ingredients, allow_staples, diet, cuisine, max_time, servings, count, strict):
    staples_rule = (
        "You may assume the user has basic pantry staples: salt, pepper, cooking oil, "
        "water, sugar, flour and common dried spices. List them under pantry_staples_used."
        if allow_staples
        else "Do NOT assume any pantry staples. Only use the listed ingredients (plus water)."
    )
    match_rule = (
        "Every recipe must be fully cookable from the listed ingredients. "
        "missing_ingredients must be empty."
        if strict
        else "Prefer recipes cookable from the list. If a recipe needs at most 2 extra "
        "ingredients, put them in missing_ingredients."
    )
    return f"""You are a practical home-cooking assistant.

The user's fridge contains: {", ".join(ingredients)}.

Suggest {count} different recipes.
- {staples_rule}
- {match_rule}
- Dietary preference: {diet}. Respect it strictly.
- Cuisine preference: {cuisine}.
- Total time (prep + cook) must be at most {max_time} minutes.
- Each recipe serves {servings}; scale quantities accordingly.
- Make the recipes meaningfully different from each other (different method or style).
- Steps should be short, clear and in order.
- Use as many of the listed ingredients as sensible, prioritising ones that spoil quickly.
- Ignore any item in the list that is not edible food."""


def generate_recipes(api_key: str, prompt: str) -> List[Recipe]:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecipeList,
            temperature=0.8,
        ),
    )
    parsed = response.parsed
    if parsed is None:  # fall back to manual parsing
        parsed = RecipeList.model_validate_json(response.text)
    return parsed.recipes


def parse_ingredients(raw: str) -> List[str]:
    """Split on commas/newlines, trim, lowercase, de-duplicate while keeping order."""
    parts = [p.strip().lower() for chunk in raw.splitlines() for p in chunk.split(",")]
    seen, result = set(), []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

st.set_page_config(page_title="Fridge to Recipe", page_icon="🥕", layout="wide")

st.title("What can I cook tonight?")
st.caption("List what's in your fridge. Get recipes you can make with it.")

with st.sidebar:
    st.header("Settings")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input(
            "Gemini API key",
            type="password",
            help="Get a free key at aistudio.google.com. Or set GEMINI_API_KEY.",
        )
    else:
        st.success("API key loaded")

    diet = st.selectbox(
        "Diet",
        ["No restriction", "Vegetarian", "Vegan", "Halal", "Gluten-free", "Dairy-free", "Low-carb", "High-protein"],
    )
    cuisine = st.selectbox(
        "Cuisine",
        ["Any", "Pakistani / South Asian", "Italian", "Mexican", "Chinese", "Middle Eastern", "Mediterranean", "American"],
    )
    max_time = st.slider("Max total time (minutes)", 10, 120, 45, step=5)
    servings = st.number_input("Servings", 1, 12, 2)
    count = st.slider("Number of recipes", 1, 5, 3)
    allow_staples = st.toggle("Assume pantry staples (oil, salt, spices)", value=True)
    strict = st.toggle("Only recipes with no extra shopping", value=False)

# --- Ingredient input ---
if "ingredients_text" not in st.session_state:
    st.session_state.ingredients_text = ""

QUICK_ADD = ["eggs", "tomatoes", "onions", "chicken", "rice", "spinach", "potatoes", "cheese", "yogurt", "bell pepper"]

st.subheader("Your ingredients")
st.text_area(
    "Type or paste ingredients, separated by commas or new lines",
    key="ingredients_text",
    height=120,
    placeholder="eggs, spinach, leftover rice, tomatoes, cheddar...",
)

def add_ingredient(item: str) -> None:
    """Button callback: runs before the rerun, so it can safely edit the widget's state."""
    current = parse_ingredients(st.session_state.ingredients_text)
    if item not in current:
        current.append(item)
    st.session_state.ingredients_text = ", ".join(current)


st.write("Quick add:")
cols = st.columns(len(QUICK_ADD))
for col, item in zip(cols, QUICK_ADD):
    col.button(
        item,
        key=f"qa_{item}",
        use_container_width=True,
        on_click=add_ingredient,
        args=(item,),
    )

ingredients = parse_ingredients(st.session_state.ingredients_text)
if ingredients:
    st.write(f"**{len(ingredients)} ingredients:** " + ", ".join(ingredients))

go = st.button("Find recipes", type="primary", disabled=not ingredients)

# --- Generate ---
if go:
    if not api_key:
        st.error("Add your Gemini API key in the sidebar to continue.")
    else:
        prompt = build_prompt(
            ingredients, allow_staples, diet, cuisine, max_time, servings, count, strict
        )
        with st.spinner("Looking through your fridge..."):
            try:
                st.session_state.recipes = generate_recipes(api_key, prompt)
            except Exception as e:
                st.session_state.recipes = None
                st.error(f"Couldn't get recipes: {e}")

# --- Results ---
recipes = st.session_state.get("recipes")
if recipes:
    st.divider()
    st.subheader(f"{len(recipes)} recipes for you")
    for i, r in enumerate(recipes):
        with st.container(border=True):
            st.markdown(f"### {r.name}")
            st.write(r.description)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total time", f"{r.prep_time_minutes + r.cook_time_minutes} min")
            m2.metric("Difficulty", r.difficulty)
            m3.metric("Servings", r.servings)
            m4.metric("Calories / serving", f"~{r.calories_per_serving}")

            left, right = st.columns(2)
            with left:
                st.markdown("**From your fridge**")
                for item in r.ingredients_from_fridge:
                    st.markdown(f"- {item}")
                if r.pantry_staples_used:
                    st.markdown("**Pantry staples**")
                    for item in r.pantry_staples_used:
                        st.markdown(f"- {item}")
                if r.missing_ingredients:
                    st.warning("You'll need to buy: " + ", ".join(r.missing_ingredients))
                else:
                    st.success("Nothing extra to buy")
            with right:
                st.markdown("**Method**")
                for n, step in enumerate(r.steps, 1):
                    st.markdown(f"{n}. {step}")
                st.info(r.tip)

            # Download as text
            text = (
                f"{r.name}\n{r.description}\n\n"
                f"Ingredients:\n- " + "\n- ".join(r.ingredients_from_fridge + r.pantry_staples_used + r.missing_ingredients)
                + "\n\nMethod:\n" + "\n".join(f"{n}. {s}" for n, s in enumerate(r.steps, 1))
                + f"\n\nTip: {r.tip}\n"
            )
            st.download_button("Save recipe", text, file_name=f"{r.name}.txt", key=f"dl_{i}")
