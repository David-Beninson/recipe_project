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

## 🚀 Key Features

### 🔍 Recipe Search & Customization
- **Smart Search**: Search for recipes by ingredients with a configurable quantity limit (1-5 recipes).
- **Culinary Preferences & Settings**: Dedicated user settings profile to set defaults (Vegetarian, Vegan, Gluten-Free, Kosher, max prep time) that automatically apply to searches.
- **Recipe Management**: Create, view, edit, and delete custom user recipes with base64 image uploads and previews.
- **Dashboard & History**: Track search history and browse saved recipes via dedicated tabs ("My Recipes" vs. "Searched Recipes").

### Chef-AI Integrations
- **Custom Recipe Generation**: Ask AI to generate a completely new recipe from scratch based on available ingredients while respecting active dietary filters.
- **AI Ingredient Substitution**: Interactively select and swap multiple ingredients in any recipe with smart alternatives recommended by AI.
- **Quick AI Suggestions**: Get a rapid, context-aware 1-2 sentence substitute recommendation for any recipe ingredient instantly.

---

## ⚡ Architecture & Performance Optimizations

To keep the user interface responsive and reduce server load, the application implements several architectural best practices:

* **Optimistic UI Updates**: Toggling recipe likes updates the interface instantly in the background, with an automatic rollback mechanism if the server request fails.
* **Efficient Session Caching**: Liked recipe IDs are cached in the Flask user session upon login to eliminate database query overhead on page navigation.
* **Optimized Database Access**: Utilizes batched database operations (SQL `IN` clauses) instead of loop-based individual queries to minimize database network roundtrips.
* **Resilient Connection Pooling**: Configured with pessimistic connection pre-pinging (`pool_pre_ping=True`) to handle serverless database idle timeouts seamlessly.

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


## 🗂️ Project Architecture & Structure

The project is split into two main operational parts:
- `app.fast_api`: The FastAPI backend serving async endpoints, database logic, and AI integrations.
- `app.main`: The Flask web frontend rendering templates and handling user sessions.


```
recipe_project/
├── app/
│   ├── __init__.py
│   ├── config.py          # Load .env settings
│   ├── database.py        # Async/Sync SQLAlchemy database initialization
│   ├── fast_api.py        # FastAPI app and route registration
│   ├── main.py            # Flask entry point and blueprint registration
│   ├── schemas.py         # Pydantic request/response schemas
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
│   └── utils/
│       ├── __init__.py
│       ├── flask_helpers.py
│       ├── oauth2.py      
│       └── password_hashing.py  
├── templates/
│   ├── base.html          # Base layout template with navigation
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── home.html          # User dashboard showing searched and custom recipes
│   ├── settings.html      # Standalone settings page for default preferences
│   ├── cooking_steps.html # Recipe details and interactive ingredients
│   ├── search.html        # Recipe search page
│   └── components/
│       ├── add_recipe.html # Custom recipe form component
│       ├── ai.html         # Reusable components for AI recipe generation and substitution
│       ├── filters.html    # Recipe search filters component
│       └── recipe.html     # Recipe card renderer macro
├── static/
│   ├── favicon.ico       
│   ├── css/
│   │   ├── style.css      
│   │   └── auth.css     
│   └── js/
│       ├── main.js        # Global/main script (optimistic likes, AJAX requests)
│       ├── auth.js        # Password visibility toggle helper logic
│       ├── recipe-builder.js # Ingredient list builder and drag & drop logic
│       └── cooking-steps.js  # Substitutes and selection mode handlers
├── tests/
│   ├── __init__.py
│   ├── conftest.py
|   ├── test_ai.py
|   ├── test_auth.py
|   ├── test_db_ssl.py
|   ├── test_latency.py
|   ├── test_pooler_latency.py
│   ├── test_recipes.py
│   └── test_user_settings.py 
├── example.env
├── requirements.txt
└── README.md
```

---

## 📦 Installation & Setup

### Prerequisites
- **Python**: Version 3.8 or newer
- **PostgreSQL**: Local or cloud-hosted database instance
- **Spoonacular API Key**: Optional, required for external recipe and substitute lookups

### Step 1: Clone and Install Dependencies
It is highly recommended to use a virtual environment:

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  

# Install required packages
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Copy `example.env` to a new `.env` file in the project root and update the configuration variables with your credentials:

```env
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_NAME=recipe_db
SECRET_KEY=your_secret_key_for_jwt
ALGORITHM=HS256
SPOONACULAR_API_KEY=your_spoonacular_api_key
SPOONACULAR_URL=https://api.spoonacular.com/recipes/findByIngredients
AI_URL=http://localhost:11434/chat/completions
BACKEND_URL=http://127.0.0.1:8000
```
> *Note: Settings are automatically loaded and validated at runtime using Pydantic Settings.*
---

## ▶️ Running the Application

To run the complete application, you need to start both the FastAPI backend and the Flask frontend server.

### 1. Start the FastAPI Backend

```bash
uvicorn app.fast_api:app --host 127.0.0.1 --port 8000 --reload
```

The API server will be available at `http://127.0.0.1:8000`. You can explore and test the endpoints directly using the built-in interactive documentation:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

### 2. Start the Flask Frontend
In a new terminal window (with your virtual environment activated), start the web controller:
```bash
python3 -m app.main
```
The frontend web application will be accessible via your browser at `http://127.0.0.1:5000`.

---

## 🔒 Authentication Flow

All user management endpoints handle encryption and validation. Protected endpoints require a valid JSON Web Token (JWT).

### Sign Up Endpoint
`POST /sign_up/`

**Request Body (JSON):**
```json
{
  "user_name": "john_doe",
  "password": "securepassword123"
}
```

**Response (JSON):**
```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

### Login Endpoint
`POST /login/`

**Request Body (`application/x-www-form-urlencoded`):**

```
username=john_doe
password=securepassword123
```

**Response (JSON):**
```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

### Accessing Protected Endpoints
To query protected routes on the FastAPI backend, include the retrieved token in the `Authorization` header:
```http
Authorization: Bearer <jwt_token>
```
## 🍳 API Endpoints Reference

All endpoints below reside on the FastAPI backend server. Routes requiring authentication expect a valid JWT token in the header: `Authorization: Bearer <jwt_token>`.

### 🔍 Recipe & Substitute Endpoints

#### 1. Search Recipes by Ingredients
* **Route**: `GET /recipes/find-by-ingredients`
* **Authentication**: Required
* **Query Parameters**:
  * `ingredients` (Required): Comma-separated list (e.g., `chicken,rice,garlic`)
  * `number` (Optional): Maximum number of recipes to return (Default: 1)
* **Description**: Logs the user search history, queries Spoonacular for matching recipes, fetches bulk details (dietary preferences, cook times), caches new discoveries locally, and returns an enhanced recipe payload.

**Example Request:**
```http
GET /recipes/find-by-ingredients?ingredients=chicken,rice&number=1
```
**Example Response:**
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

#### 2. Get Ingredient Substitutes
* **Route**: `GET /recipes/substitutes`
* **Authentication**: Optional
* **Query Parameters**:
  * `ingredient` (Required): Target ingredient name (e.g., `milk`)
  * `amount` (Optional): Numeric quantity
  * `unit` (Optional): Measurement unit (e.g., `cup`)
* **Description**: Checks the local database cache first. If a match is found, it returns the cached alternatives instantly; otherwise, it fetches results from Spoonacular and updates the local cache.

**Example Response:**
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

#### 3. Add Custom Recipe
* **Route**: `POST /recipes/custom`
* **Authentication**: Required
* **Description**: Saves a user-created recipe along with specific ingredient measurements, HTML formatting instructions, and optional base64 image data to their personal profile.

**Request Body (JSON):**
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

#### 4. Like / Favorite a Recipe
* **Route**: `POST /recipes/{recipe_id}/like`
* **Authentication**: Required
* **Description**: Toggles the favorite/liked status of a cached recipe for the authenticated user and returns the updated global like counter.

---

### Chef-AI Endpoints

#### 5. Generate Custom Recipe with AI
* **Route**: `POST /ai/generate`
* **Authentication**: Required
* **Description**: Instructs the LLM to generate a completely new, structured recipe using the submitted ingredients while conforming to the user's active dietary filters.

**Request Body (JSON):**
```json
{
  "ingredients": "chicken, broccoli, cheese"
}
```

#### 6. Substitute Multiple Ingredients with AI
* **Route**: `POST /ai/substitute/{recipe_id}`
* **Authentication**: Required
* **Description**: Creates an adapted copy of an existing recipe, rewriting instructions and ingredients by swapping requested items with AI-suggested alternatives.

**Request Body (JSON):**
```json
{
  "ingredient_to_replace": "heavy cream"
}
```

#### 7. Get Quick AI Suggestion
* **Route**: `GET /ai/quick-substitute`
* **Authentication**: Required
* **Query Parameters**: `recipe_id`, `ingredient`
* **Description**: Returns a context-aware, rapid 1-2 sentence culinary substitution tip for a specific ingredient inside a recipe layout without full-page updates.

**Example Response:**
```json
{
  "recommendation": "Use 1 cup of almond milk mixed with a tablespoon of lemon juice as a dairy-free substitute for regular milk."
}
```

---

### ⚙️ User Settings Endpoints

#### 8. Get User Default Preferences
* **Route**: `GET /users/settings`
* **Authentication**: Required
* **Description**: Retrieves the authenticated user's default profile configurations (dietary rules, default dish styles, and max preparation times).

#### 9. Update User Default Preferences
* **Route**: `PUT /users/settings`
* **Authentication**: Required
* **Description**: Updates and overrides the default settings dictionary for the authenticated profile.

---

## 🧠 Database Architecture & Models

The application utilizes SQLAlchemy ORM for database modeling and management. The schema includes the following core models:

### 👤 Users (`users`)
* Stores user credentials and linked profiles.
* Fields: `id`, `user_name` (unique), and `password` (bcrypt hashed).
* Relationships: One-to-many with custom recipes and many-to-many with favorited/liked recipes.

### 🔍 User Searches (`user_searches`)
* Logs historical searches to populate the dashboard.
* Fields: `id`, `user_id` (foreign key), and `query_ingredients` (string).

### 🍳 Recipes (`recipes`)
* Unified table storing both cached third-party recipes and user-generated custom recipes.
* Fields: `id`, `spoonacular_id` (nullable external ID), `title`, `raw_data` (JSON block containing full details/instructions), and `user_id` (nullable owner ID for custom recipes).

### ❤️ User Liked Recipes (`user_liked_recipes`)
* Many-to-many junction/association table linking user profiles (`user_id`) to their favorited recipe cards (`recipe_id`).

### 🧪 Ingredient Substitutes (`ingredient_substitutes`)
* Local lookup cache to reduce redundant third-party API payloads.
* Fields: `id`, `ingredient_name` (unique cache key), and `substitutes` (JSON array of safe alternatives).

---

## 🧪 Automated Testing Suite

The project includes an automated test suite powered by `pytest` to validate authentication states, route security boundaries, and search utility functionality.

To execute the full test suite, run:
```bash
pytest
```
*The configuration details, isolation cleanups, and standard client mock fixtures reside inside `tests/conftest.py`.*

---

## 🎨 Frontend Template Structure (Jinja2)

The user interface follows a modular component-driven architecture using Jinja2 layouts and template macros.

### 🏛️ Layout Baseline
* **`base.html`**: The structural backbone containing standard headers, metadata, conditional navigation bars, global toast notification blocks, and asset link setups.

### 📄 View Views
* **`home.html`**: The personalized cockpit layout utilizing tab matrices ("Searched History", "My Recipes", and "Liked Recipes").
* **`search.html`**: The main discovery view managing criteria setups, filter triggers, and custom generation.
* **`settings.html`**: A dedicated panel for editing profile defaults and dietary constraints.
* **`login.html` / `register.html`**: Isolated workflow views (rendering without global navigation headers).

### ⚙️ Component Macros (`templates/components/`)
* **`recipe.html`**: Contains the `render_recipes()` grid system card layout maker.
* **`filters.html`**: Contains the `render_filters()` macro managing dietary flags, cooking intervals, and course categories.
* **`ai.html`**: Contains the modular `render_ai_generator()`, `render_ai_filter_generator()`, and substitute macros.

---

## Performance Considerations

To maintain application integrity and reduce operational latency, ensure adherence to the following guidelines:

* **Credential Security**: Never commit the configuration `.env` file to source control. A template is provided in `example.env` for local adjustments.
* **API Rate Limiting**: The built-in caching system for recipes and ingredients automatically decreases redundant third-party network payloads to Spoonacular. Keep the database active to leverage this.
* **Cross-Origin Requests**: CORS (Cross-Origin Resource Sharing) is currently configured in `app/fast_api.py` to allow cross-communication during local development modes.

---

## 👥 Authors & Contributors

This system was designed and maintained by:

* **David Beninson** - [GitHub Profile](https://github.com/David-Beninson)
* **Oliver Radivan** - [GitHub Profile](https://github.com/oliverradivan)
