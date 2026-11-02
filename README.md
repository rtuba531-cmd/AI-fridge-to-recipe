# Fridge to Recipe Planner

Enter the ingredients you have in your fridge and get recipe suggestions you can cook with them. Built with Streamlit and Gemini Flash.

## Features

- Type or paste ingredients (comma or line separated), or use the quick-add buttons
- Filter by diet, cuisine, max cooking time, servings and number of recipes
- Option to assume basic pantry staples (oil, salt, spices)
- Option to allow only recipes that need no extra shopping
- Each recipe shows time, difficulty, calories, ingredients, steps, a tip, and anything you would need to buy
- Save any recipe as a text file

## Requirements

- Python 3.9 or newer
- A Gemini API key (free from [Google AI Studio](https://aistudio.google.com))

## Setup

1. Create and activate a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Provide your API key using one of these options:

   - Environment variable:

     ```bash
     export GEMINI_API_KEY="your-key"     # Windows PowerShell: $env:GEMINI_API_KEY="your-key"
     ```

   - Streamlit secrets: create `.streamlit/secrets.toml` containing:

     ```toml
     GEMINI_API_KEY = "your-key"
     ```

   - Or paste the key into the sidebar when the app is running.

## Run

```bash
streamlit run app.py
```

The app opens at http://localhost:8501.

## How it works

1. Your ingredients and preferences are turned into a prompt.
2. The prompt is sent to Gemini Flash with a Pydantic schema, so the model returns structured JSON.
3. The JSON is parsed into `Recipe` objects and shown as cards.

## Configuration

The default model is set at the top of `app.py`:

```python
DEFAULT_MODEL = "gemini-3.8-flash"
```

To use a different Gemini Flash model without editing code, set `GEMINI_MODEL` in your environment or in Streamlit Secrets:

```toml
GEMINI_MODEL = "gemini-3.8-flash"
```

Google retires older models over time. If you see a 404 "model is no longer available" error, set this to the model name the error message recommends.

## Project structure

```
fridge-recipe-planner/
├── app.py             # Streamlit UI and Gemini logic
├── requirements.txt   # Python dependencies
└── README.md
```

## Security

Never commit your API key. If you use `.streamlit/secrets.toml`, add it to `.gitignore`.

## Troubleshooting

- **"Add your Gemini API key"**: set `GEMINI_API_KEY` or enter it in the sidebar.
- **Model not found errors**: update `MODEL_NAME` to a Flash model available to your key.
- **Empty or odd results**: check that the ingredients are real foods, and loosen the time limit or turn off "no extra shopping".

## Ideas for future work

- Upload a fridge photo and detect ingredients with Gemini's vision support
- Favorites and a shopping list for missing ingredients
- A "use up soon" field to prioritise ingredients that spoil quickly
- 
