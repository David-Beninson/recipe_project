# Recipe Search API

A recipe search application built with FastAPI for the backend and Flask for the main frontend page.

This repository includes:
- FastAPI API endpoints for recipe search and ingredient substitutes
- JWT user authentication and signup
- PostgreSQL data storage with SQLAlchemy ORM
- HTTPX integration to call Spoonacular for recipes and substitutes
- Flask-based main page with login/register/home views
- Unit tests for authentication and recipe endpoints

---

## 🚀 Project Summary

This app lets users:
- Create an account and log in
- Search for recipes by ingredients
- Receive ingredient substitute suggestions
- Save search history to the database
- Cache recipes and substitute results for faster future responses

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
│   ├── database.py        # Async SQLAlchemy database initialization
│   ├── fast_api.py        # FastAPI app and route registration
│   ├── main.py            # Flask main page and login/register routes
│   ├── models.py          # SQLAlchemy ORM models for users, recipes, searches, substitutes
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py        # Login endpoint
│   │   ├── recipes.py     # Recipe search and substitutes endpoints
│   │   └── user.py        # Signup endpoint
│   ├── schemas.py         # Pydantic request/response schemas
│   └── utils/
│       ├── __init__.py
│       ├── oauth2.py      # JWT token validation and auth dependency
│       └── password_hashing.py  # Password hashing and verification
├── templates/             # Flask templates and public CSS
│   ├── components/
│   │   ├── home.html
│   │   ├── loggingin.html
│   │   ├── recipe.html
│   │   └── register.html
│   ├── css/
│   │   ├── home.css
│   │   ├── login.css
│   │   └── recipe.css
│   ├── index.html
│   └── styel.css
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
- Python 3.8 or newer
- PostgreSQL database
- Optional: Spoonacular API key for recipe and substitute lookup

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
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

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
- `ingredients` (required): comma-separated ingredient list, e.g. `chicken,rice,garlic`
- `number` (optional): maximum number of recipes to return, default is `5`

Example:

```
GET /recipes/find-by-ingredients?ingredients=chicken,rice&number=5
```

What this endpoint does:
- Creates a new `UserSearch` record for the authenticated user
- Calls Spoonacular using the configured `spoonacular_url`
- Validates each recipe response item against a Pydantic schema
- Caches any new recipe in the local database
- Links the found recipes to the user search record
- Returns the Spoonacular JSON payload

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
- `ingredient` (required): ingredient name to look up substitutions for, e.g. `milk`

Example:

```
GET /recipes/substitutes?ingredient=milk
```

What this endpoint does:
- Checks whether substitute data is already cached in the database
- If cached, returns the cached substitute list immediately
- Otherwise calls Spoonacular substitute API
- Stores the response in `ingredient_substitutes`
- Returns the substitute data

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

---

## 🧠 Database models

The app uses SQLAlchemy ORM models defined in `app.models`.

### Users
- `users` table stores:
  - `id`
  - `user_name` (unique)
  - `password` (bcrypt hashed)

### User searches
- `user_searches` table stores:
  - `id`
  - `user_id` (foreign key to users)
  - `query_ingredients`
  - relationships to saved recipes

### Recipes
- `recipes` table stores:
  - `id`
  - `spoonacular_id` (unique external recipe ID)
  - `title`
  - `raw_data` (JSON payload from Spoonacular)

### Ingredient substitutes
- `ingredient_substitutes` table stores:
  - `id`
  - `ingredient_name` (unique)
  - `substitutes` (JSON list)

---

## 🧪 Testing

Run tests with:

```bash
pytest
```

The test suite includes coverage for:
- user signup and login
- protected route access
- recipe search logic
- substitute endpoint behavior

---

## ⚠️ Notes and best practices

- Use `pip3 install -r requirements.txt` for dependency installation.
- Start the FastAPI backend with `uvicorn app.fast_api:app --host 127.0.0.1 --port 8000 --reload`.
- Start the Flask frontend with `python3 -m app.main`.
- Keep the `.env` file secret and do not commit it.
- If the Spoonacular API limits requests, caching reduces duplicate calls.
- CORS is enabled for all origins in `app.fast_api.py`.

---

## 👥 Authors

- David Beninson 
- Oliver Radivan
