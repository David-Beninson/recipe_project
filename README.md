# Recipe Search API with AI Chef

A recipe search and AI-assisted kitchen helper application built with FastAPI for the backend and Flask for the main frontend page.

This repository includes:
- FastAPI API endpoints for recipe search, ingredient substitutes, custom recipes, and AI integrations
- Async database operations using SQLAlchemy ORM and PostgreSQL
- JWT user authentication and signup
- HTTPX integration to call Spoonacular for recipes and substitutes
- LLM Integration (OpenAI-compatible completions API like Qwen 2.5) for smart recipe generation and adaptive ingredient substitutions
- Flask-based web frontend with modern pages and modular styling
- Jinja2 layout inheritance and template components
- Unit tests for authentication and recipe endpoints

---

## 🚀 Project Summary

This app lets users:
- Create an account and log in
- Search for recipes by ingredients with a configurable quantity limit (1-5 recipes)
- Receive ingredient substitute suggestions dynamically in the UI by clicking ingredients
- Save custom user recipes (with custom ingredient quantities and instructions) to their profile
- **Show All Recipes**: Browse all saved/cached recipes in the database directly from the home page tab with full filtering capabilities
- **Chef-AI Custom Recipe Generation (with active filters)**: Ask AI to generate a completely new recipe from scratch based on entered ingredients while respecting active filters (kosher, prep time, vegan, vegetarian, gluten-free)
- **AI Ingredient Substitution**: Interactively swap specific ingredients in any recipe with smart alternatives recommended by AI
- **Quick AI Suggestions**: Get a rapid, context-aware 1-2 sentence substitute recommendation for any recipe ingredient
- Save search history and cache recipe details/ingredient substitutes in the database
- View saved searches and custom recipes on their personalized home dashboard

The project is split into two main parts:
- `app.fast_api`: the FastAPI backend
- `app.main`: the Flask web frontend

---

## ⚡ Performance & Frontend Architecture

To keep the user interface responsive and reduce server load, several performance optimizations and architectural improvements are implemented:

* **Optimistic UI Updates**: Toggling recipe likes updates the heart icon state and active counters instantly. The server request runs in the background; if the request fails, the interface rolls back to its original state automatically.
* **Session Caching**: Liked recipe IDs are cached in the Flask user session on login and dynamically updated. This eliminates database query overhead from the `inject_user` context processor on every single template rendering and page navigation.
* **Batched Database Operations (SQL `IN`)**: Replaced loop-based individual queries with single batched queries when checking cached recipe existences, significantly reducing database network roundtrips.
* **Modular External Scripts**: All inline script tags were removed from HTML files and separated into dedicated modules under `static/js/`, ensuring cleaner markup, better browser cache utilization, and modular code management.

---

## 🗂️ Project Structure

```
recipe_project/
├── app/
│   ├── __init__.py
│   ├── config.py          # Load .env settings
│   ├── database.py        # Async/Sync SQLAlchemy database initialization
│   ├── fast_api.py        # FastAPI app and route registration
│   ├── main.py            # Flask entry point and blueprint registration
│   ├── models.py          # SQLAlchemy ORM models (User, Recipe, UserSearch, IngredientSubstitute)
│   ├── blueprints/        # Flask Blueprints
│   │   ├── __init__.py    # Export blueprints
│   │   ├── ai.py          # AI integration routes (generate recipe, substitute ingredients)
│   │   ├── auth.py        # Auth routes (login, register, logout)
│   │   └── recipes.py     # Recipe routes (home, search, add, details, like, substitutes)
│   ├── routers/           # FastAPI Routers
│   │   ├── __init__.py
│   │   ├── ai.py          # FastAPI AI router for generating and substituting recipes
│   │   ├── auth.py        # Login endpoint
│   │   ├── recipes.py     # Recipe searches, custom recipes, and substitutes
│   │   ├── services.py    # Backend services, API requests, caching, and database logic
│   │   └── user.py        # Signup endpoint
│   ├── schemas.py         # Pydantic request/response schemas
│   └── utils/
│       ├── __init__.py
│       ├── flask_helpers.py # Flask authentication and filtering helper functions
│       ├── oauth2.py      # JWT token validation and auth dependency
│       └── password_hashing.py  # Password hashing and verification
├── templates/
│   ├── base.html          # Base layout template with navigation
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── home.html          # User dashboard showing searched and custom recipes
│   ├── cooking_steps.html # Recipe details and interactive ingredients
│   ├── search.html        # Recipe search page
│   └── components/
│       ├── add_recipe.html # Custom recipe form component
│       ├── ai.html         # Reusable components for AI recipe generation and substitution
│       ├── filters.html    # Recipe search filters component
│       └── recipe.html     # Recipe card renderer macro
├── static/
│   ├── favicon.ico        # Site icon / favicon
│   ├── css/
│   │   ├── ai.css         # Styles for AI components and selection mode
│   │   ├── filters.css    # Styles for recipe search filters
│   │   ├── style.css      # Core variables, layout, and global styles
│   │   ├── auth.css       # Styling and glow effects for auth forms
│   │   ├── home.css       # Dashboards and card grids layout
│   │   └── search.css     # Search and filter specific styling
│   └── js/
│       ├── main.js        # Global/main script (optimistic likes, AJAX requests)
│       ├── auth.js        # Password visibility toggle helper logic
│       ├── recipe-builder.js # Ingredient list builder and drag & drop logic
│       └── cooking-steps.js  # Substitutes and selection mode handlers
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_recipes.py
│   ├── test_latency.py        # DB and Spoonacular API latency test utility
│   └── test_pooler_latency.py # DB pooler connection latency test utility
├── example.env
├── requirements.txt
└── README.md
```

---

## 📦 Installation

### Prerequisites

* Python 3.8 or newer
* PostgreSQL database
* Optional: Spoonacular API key for recipe and substitute lookup

### Install dependencies

```bash
pip3 install -r requirements.txt
```

### Environment variables

Copy `example.env` to a new `.env` file in the project root and update the values:

```env
database_hostname=localhost
database_port=5432
database_username=your_db_user
database_password=your_db_password
database_name=recipe_db
secret_key=your_secret_key_for_jwt
algorithm=HS256
spoonacular_api_key=your_spoonacular_api_key
spoonacular_url=https://api.spoonacular.com/recipes/findByIngredients
AI_URL=http://localhost:11434/chat/completions
BACKEND_URL=http://127.0.0.1:8000
```

> The application loads settings from `.env` using Pydantic settings.

---

## ▶️ Run the application

### FastAPI backend

Start the backend with:

```bash
uvicorn app.fast_api:app --host 127.0.0.1 --port 8000 --reload
```

This starts the API server on the host/port you configure (defaults to `http://127.0.0.1:8000` via `BACKEND_URL`).

Documentation (when running on localhost:8000):

* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`

### Flask frontend page

Start the Flask frontend with:

```bash
python3 -m app.main
```

By default, the Flask page runs on `http://127.0.0.1:5000`.

---

## ‿ Authentication

### Signup endpoint

`POST /sign_up/`

Request body (JSON):

```json
{
  "user_name": "john_doe",
  "password": "securepassword123"
}
```

Response:

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

### Login endpoint

`POST /login/`

Login uses form data with `application/x-www-form-urlencoded`:

```
username=john_doe
password=securepassword123
```

Response:

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

### Protected endpoints

Protected endpoints require the JWT token inside the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

The backend validates the token using the `get_current_user` dependency in `app.utils.oauth2`.

---

## 🍳 API Endpoints

### 1. Search recipes by ingredients

`GET /recipes/find-by-ingredients`

Requires authentication.

Query parameters:

* `ingredients` (required): comma-separated ingredient list, e.g. `chicken,rice,garlic`
* `number` (optional): maximum number of recipes to return (configured in search page between 1 and 5, default is 1)

Example:
```
GET /recipes/find-by-ingredients?ingredients=chicken,rice&number=1
```

What this endpoint does:

* Creates a new `UserSearch` record for the authenticated user
* Calls Spoonacular using the configured `spoonacular_url`
* Calls Spoonacular `informationBulk` endpoint to retrieve details (cook time, dish types, and dietary preferences)
* Validates each recipe response item against a Pydantic schema
* Caches any new recipe in the local database with full details (including instructions)
* Links the found recipes to the user search record
* Returns the enhanced Spoonacular JSON payload containing prep time, dish types, and dietary flags for filtering

Example response:

```json
[
  {
    "id": 12345,
    "title": "Chicken and Rice Stir-Fry",
    "image": "https://spoonacular.com/recipe/...",
    "usedIngredients": [
      {
        "id": 5006,
        "name": "chicken",
        "original": "2 chicken breasts"
      }
    ],
    "missedIngredients": [],
    "unusedIngredients": []
  }
]
```

### 2. Ingredient substitutes

`GET /recipes/substitutes`

Does not require authentication.

Query parameters:

* `ingredient` (required): ingredient name to look up substitutions for, e.g. `milk`
* `amount` (optional): numeric quantity of the ingredient to substitute
* `unit` (optional): measurement unit (e.g. `cups`, `grams`)

Example:

```
GET /recipes/substitutes?ingredient=milk&amount=1&unit=cup
```

What this endpoint does:

* Formulates a cache key by combining the lowercase, trimmed `ingredient`, optional `amount`, and optional `unit` (e.g. `"milk_1.0_cup"` or `"milk"`)
* Checks whether substitute data is already cached in the `ingredient_substitutes` table under the generated cache key
* If cached, returns the cached substitute list immediately
* Otherwise, queries the Spoonacular substitute API
* Caches the list of substitutes in `ingredient_substitutes` under the cache key
* Returns the substitute data

Example response:

```json
{
  "ingredient": "milk",
  "substitutes": [
    "almond milk",
    "soy milk",
    "oat milk"
  ]
}
```

### 3. Add custom recipe

`POST /recipes/custom`

Requires authentication.

Request body (JSON, matches `CustomRecipeCreate` Pydantic schema):

```json
{
  "title": "Grandma's Tomato Soup",
  "ingredients": [
    {
      "name": "tomato",
      "originalAmount": "4 large tomatoes",
      "qty": 4.0,
      "unitString": "large tomatoes",
      "usedQty": 4.0
    }
  ],
  "instructions": "<p>Boil tomatoes, blend, and serve hot.</p>",
  "image": ""
}
```

Response:

```json
{
  "id": 1,
  "title": "Grandma's Tomato Soup"
}
```

### 4. Like / Favorite a recipe

`POST /recipes/{recipe_id}/like`

Requires authentication.

Toggles the liked status of a recipe for the authenticated user.

Response:

```json
{
  "status": "liked",
  "likes": 6
}
```

### 5. Generate custom recipe with AI

`POST /ai/generate`

Requires authentication.

Request body (JSON):

```json
{
  "ingredients": "chicken, broccoli, cheese"
}
```

Response:

```json
{
  "id": 42,
  "title": "Creamy AI Garlic Chicken & Broccoli"
}
```

### 6. Substitute recipe ingredient with AI

`POST /ai/substitute/{recipe_id}`

Requires authentication.

Request body (JSON):

```json
{
  "ingredient_to_replace": "heavy cream"
}
```

Response:

```json
{
  "id": 43,
  "title": "Adapted Creamy AI Garlic Chicken & Broccoli"
}
```

### 7. Get quick ingredient substitute recommendation

`GET /ai/quick-substitute`

Requires authentication.

Query parameters:

* `recipe_id` (required): the database/spoonacular ID of the recipe
* `ingredient` (required): the ingredient to replace

Example:
```
GET /ai/quick-substitute?recipe_id=42&ingredient=milk
```

Response:

```json
{
  "recommendation": "Use 1 cup of almond milk mixed with a tablespoon of lemon juice as a dairy-free substitute for regular milk."
}
```

---

## 🤖 Chef-AI Frontend Interactions & Database Browse

The frontend integrates these AI and database capabilities smoothly in the UI:
1. **Show All Database Recipes**: A dedicated tab "All Recipes" on the personalized home dashboard. It retrieves all cached and custom recipes from the database, allowing users to browse them in one place.
2. **Global Filtering & AI Recipe Generation**: The search page and the personalized home dashboard share powerful filters (dietary flags like Kosher, Veg, Gluten-free, prep time, and dish types). The home dashboard features a **"Chef-AI Custom Recipe" generator card** that generates new recipes based on entered ingredients while respecting active filters (kosher, prep time, vegan, vegetarian, gluten-free).
3. **Ingredient Selection Mode**: Inside the Cooking Steps page, users can click "Select Multiple Ingredients to Replace with AI" to toggle checkbox selection mode, highlight ingredients, and request an adapted recipe version.
4. **Quick Substitutes Box**: Clicking an ingredient displays standard substitutes, alongside an "Ask AI for Substitute" button that queries the AI and displays a 1-2 sentence contextual suggestion in real-time.

---

## 🧠 Database models

The app uses SQLAlchemy ORM models defined in `app.models`.

### Users

* `users` table stores:
  * `id`
  * `user_name` (unique)
  * `password` (bcrypt hashed)
  * `custom_recipes` (relationship linking to custom recipes created by this user)
  * `liked_recipes` (relationship linking to recipes liked by this user)

### User searches

* `user_searches` table stores:
  * `id`
  * `user_id` (foreign key to users)
  * `query_ingredients`
  * relationships to saved recipes

### Recipes

* `recipes` table stores:
  * `id`
  * `spoonacular_id` (unique external recipe ID, optional/nullable for custom user recipes)
  * `title`
  * `raw_data` (JSON payload from Spoonacular or custom user input)
  * `user_id` (foreign key to users, nullable, linking custom recipes to their creator)
  * `liked_by_users` (relationship linking to users who liked this recipe)

### User Liked Recipes

* `user_liked_recipes` table:
  * many-to-many association table containing `user_id` and `recipe_id`

### Ingredient substitutes

* `ingredient_substitutes` table stores:
  * `id`
  * `ingredient_name` (unique)
  * `substitutes` (JSON list)

---

## 🧪 Testing

Run tests with:

```bash
pytest
```

The test suite covers user signup/login, protected route access, search logic, and substitute endpoint behavior.

---

## 🎨 Template Structure (Jinja2)

The application uses Jinja2 template inheritance.

### Base Template

* **base.html**: Contains navigation bar, metadata, CSS links, and block placeholders. All pages extend this.

### Page Templates

* **home.html**: User's recipe collection (featuring My Recipes, Liked Recipes, and All Recipes tabs).
* **login.html** / **register.html**: Auth pages (no navbar).

### Components

* **components/recipe.html**: Contains `render_recipes()` macro.
* **components/filters.html**: Contains `render_filters()` macro for dietary, prep time, and dish type filters.
* **components/ai.html**: Contains macros for AI recipe generation and quick/multi ingredient substitution.

### Usage Example

```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}
{% endblock %}

```

---

## ⚠️ Best Practices

* Keep the `.env` file secret and do not commit it.
* Use caching to reduce duplicate Spoonacular API calls.
* CORS is enabled for all origins in `app.fast_api.py`.


---

## ⚠️ Notes and best practices

- Use `pip3 install -r requirements.txt` for dependency installation.
- Start the FastAPI backend with `uvicorn app.fast_api:app --host 127.0.0.1 --port 8000 --reload`.
- Start the Flask frontend with `python3 -m app.main`.
---

## 👥 Authors

* [David Beninson](https://github.com/David-Beninson)
* [Oliver Radivan](https://github.com/oliverradivan)
