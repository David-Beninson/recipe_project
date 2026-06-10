# Recipe Search API

A recipe search application built with FastAPI for the backend and Flask for the main frontend page.

This repository includes:
- FastAPI API endpoints for recipe search, ingredient substitutes, and custom recipes
- Async database operations using SQLAlchemy ORM and PostgreSQL
- JWT user authentication and signup
- HTTPX integration to call Spoonacular for recipes and substitutes
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
- Save search history and cache recipe details/ingredient substitutes in the database
- View saved searches and custom recipes on their personalized home dashboard

The project is split into two main parts:
- `app.fast_api`: the FastAPI backend
- `app.main`: the Flask web frontend

---

## 🗂️ Project Structure

```
recipe_project/
├── app/
│   ├── __init__.py
│   ├── config.py          # Load .env settings
│   ├── database.py        # Async/Sync SQLAlchemy database initialization
│   ├── fast_api.py        # FastAPI app and route registration
│   ├── main.py            # Flask main page and routes
│   ├── models.py          # SQLAlchemy ORM models (User, Recipe, UserSearch, IngredientSubstitute)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py        # Login endpoint
│   │   ├── recipes.py     # Recipe searches, custom recipes, and substitutes
│   │   └── user.py        # Signup endpoint
│   ├── schemas.py         # Pydantic request/response schemas
│   └── utils/
│       ├── __init__.py
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
│       └── recipe.html     # Recipe card renderer macro
├── static/
│   └── css/
│       ├── style.css      # Core variables, layout, and global styles
│       ├── auth.css       # Styling and glow effects for auth forms
│       ├── home.css       # Dashboards and card grids layout
│       └── search.css     # Search and filter specific styling
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_recipes.py
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
```

> The application loads settings from `.env` using Pydantic settings.

---

## ▶️ Run the application

### FastAPI backend

Start the backend with:

```bash
uvicorn app.fast_api:app --host 127.0.0.1 --port 8000 --reload
```

This starts the API server on `http://127.0.0.1:8000`.

Documentation:

* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`

### Flask frontend page

Start the Flask frontend with:

```bash
python3 -m app.main
```

By default, the Flask page runs on `http://127.0.0.1:5000`.

---

## 🔒 Authentication

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
* Validates each recipe response item against a Pydantic schema
* Caches any new recipe in the local database
* Links the found recipes to the user search record
* Returns the Spoonacular JSON payload

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

---

## 🧠 Database models

The app uses SQLAlchemy ORM models defined in `app.models`.

### Users

* `users` table stores:
  * `id`
  * `user_name` (unique)
  * `password` (bcrypt hashed)
  * `custom_recipes` (relationship linking to custom recipes created by this user)

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

* **home.html**: User's recipe collection.
* **search.html**: Search interface.
* **cooking_steps.html**: Detailed view.
* **login.html** / **register.html**: Auth pages (no navbar).

### Components

* **components/recipe.html**: Contains `render_recipes()` macro.

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

* David Beninson
* Oliver Radivan