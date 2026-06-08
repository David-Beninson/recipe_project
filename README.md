# Recipe Search API

A FastAPI backend that allows users to search for recipes by ingredients and get ingredient substitutes. Built with PostgreSQL, SQLAlchemy ORM, and integrates with the Spoonacular API.

---

## 🎯 Project Overview

This is a recipe search application where:
- Users create accounts and log in with JWT authentication
- Authenticated users can search for recipes by ingredients
- The app saves all searches to track user history
- Users can get substitute recommendations for any ingredient
- All recipes and substitutes are cached in the database to reduce API calls

---

## 🛠️ Tech Stack

- **Backend Framework**: FastAPI (async/await with Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (JSON Web Tokens)
- **Password Security**: bcrypt hashing
- **API Integration**: Spoonacular API for recipes and substitutes
- **Async HTTP**: httpx library

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Spoonacular API key (get it from https://spoonacular.com/food-api)

### Steps

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file** in the project root with:
   ```
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

3. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`

4. **Access API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

## 📊 Database Schema

### Users Table
```
users
├── id (Primary Key)
├── user_name (String, Unique)
├── password (String, bcrypt hashed)
└── searches (Relationship → user_searches)
```

### User Searches Table
```
user_searches
├── id (Primary Key)
├── user_id (Foreign Key → users)
├── query_ingredients (String) - the search query
├── user (Relationship → users)
└── recipes (Many-to-Many → recipes)
```

### Recipes Table
```
recipes
├── id (Primary Key)
├── spoonacular_id (Integer, Unique) - external API ID
├── title (String)
└── raw_data (JSON) - complete recipe data from API
```

### Ingredient Substitutes Table
```
ingredient_substitutes
├── id (Primary Key)
├── ingredient_name (String, Unique)
└── substitutes (JSON) - list of alternative ingredients
```

---

## 🔐 Authentication Flow

### 1. Sign Up (Create Account)
**Endpoint**: `POST /sign_up/`

**Request** (JSON body):
```json
{
  "user_name": "john_doe",
  "password": "securepassword123"
}
```

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Frontend notes:**
- Password is hashed with bcrypt before storage
- On success, you immediately get a JWT token (auto-login)
- Store this token for authenticated requests

---

### 2. Login
**Endpoint**: `POST /login/`

**Request** (Form data - use application/x-www-form-urlencoded):
```
username: john_doe
password: securepassword123
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Frontend notes:**
- Use form-data, NOT JSON for login
- Response returns JWT access token
- Token needs to be sent in all authenticated requests

---

### 3. Using the Token

Add the JWT token to the Authorization header in all authenticated requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Example with fetch:**
```javascript
const token = localStorage.getItem('accessToken');
const response = await fetch('/recipes/find-by-ingredients?ingredients=chicken&number=5', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

---

## 🍳 Recipe Search Endpoint

**Endpoint**: `GET /recipes/find-by-ingredients`

**Authentication**: Required ✅

**Query Parameters**:
- `ingredients` (string, required) - Comma-separated ingredient list
  - Example: `"chicken,rice,garlic"`
- `number` (integer, optional) - How many recipes to return
  - Default: 5
  - Example: `10`

**Full URL Example**:
```
GET /recipes/find-by-ingredients?ingredients=chicken,rice&number=10
```

**Response** (200 OK):
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
  },
  {
    "id": 12346,
    "title": "Garlic Chicken Rice",
    "image": "https://spoonacular.com/recipe/...",
    ...
  }
]
```

**What happens**:
1. Your search is saved to the database (logged to your account)
2. API calls Spoonacular to find matching recipes
3. New recipes are cached in our database
4. Already-cached recipes are reused (faster, saves API calls)
5. Returns the recipe list from Spoonacular

**Frontend notes:**
- Each recipe object contains full details from Spoonacular
- `usedIngredients` = ingredients that match your search
- `missedIngredients` = ingredients in the recipe you didn't list
- `unusedIngredients` = extra ingredients from your search not in recipe
- Images are provided in the response

---

## 🥘 Ingredient Substitutes Endpoint

**Endpoint**: `GET /recipes/substitutes`

**Authentication**: Not required ❌

**Query Parameters**:
- `ingredient` (string, required) - The ingredient to find substitutes for
  - Example: `"milk"`

**Full URL Example**:
```
GET /recipes/substitutes?ingredient=milk
```

**Response** (200 OK):
```json
{
  "ingredient": "milk",
  "substitutes": [
    "almond milk",
    "soy milk",
    "coconut milk",
    "oat milk",
    "buttermilk"
  ]
}
```

**What happens**:
1. Check if we already have substitutes cached for this ingredient
2. If cached, return immediately (fast response)
3. If not cached, call Spoonacular API
4. Cache the result for future requests
5. Return the substitute list

**Frontend notes**:
- No authentication needed for this endpoint
- First request might be slightly slower (API call)
- Subsequent requests are instant (from cache)
- Can be used to show "alternatives" dropdown in search

---

## 🧪 Testing the API

### Using cURL

**Sign Up**:
```bash
curl -X POST "http://localhost:8000/sign_up/" \
  -H "Content-Type: application/json" \
  -d '{"user_name": "testuser", "password": "testpass123"}'
```

**Login**:
```bash
curl -X POST "http://localhost:8000/login/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass123"
```

**Search Recipes** (replace TOKEN with actual JWT):
```bash
curl -X GET "http://localhost:8000/recipes/find-by-ingredients?ingredients=chicken&number=5" \
  -H "Authorization: Bearer TOKEN"
```

**Get Substitutes**:
```bash
curl -X GET "http://localhost:8000/recipes/substitutes?ingredient=milk"
```

### Using Swagger UI

Go to `http://localhost:8000/docs` and use the interactive interface.

---

## 📝 Project Structure

```
recipe_project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings from .env
│   ├── database.py          # PostgreSQL connection setup
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Login endpoint
│   │   ├── user.py          # Sign-up endpoint
│   │   └── recipes.py       # Recipe search & substitutes
│   └── utils/
│       ├── __init__.py
│       ├── password_hashing.py   # bcrypt utilities
│       └── oauth2.py             # JWT token logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_recipes.py
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

---

## 🚀 Key Features

✅ **User Authentication**
- JWT-based authentication
- bcrypt password hashing
- Automatic login on sign-up

✅ **Recipe Search**
- Search by multiple ingredients
- Results from Spoonacular API
- Automatic caching to reduce API calls

✅ **Smart Caching**
- Recipes are cached to avoid duplicates
- Ingredient substitutes are cached
- Database stores all user search history

✅ **Async/Await**
- Non-blocking API calls to Spoonacular
- Efficient database queries
- Better performance under load

---

## ⚠️ Important Notes for Frontend

### Token Storage
- Store JWT token in localStorage or sessionStorage
- Include it in every authenticated request
- Implement token refresh if token expires

### Error Handling
- **401 Unauthorized** = Invalid/expired token
- **403 Forbidden** = Invalid credentials
- **502 Bad Gateway** = Spoonacular API error
- **400 Bad Request** = Missing required parameters

### CORS
- CORS is enabled for all origins (`*`)
- You can call this API from any frontend domain

### Rate Limiting
- Spoonacular has API rate limits
- Cached responses bypass these limits
- Consider implementing client-side caching too

---

## 🔧 Troubleshooting

**Issue**: Can't connect to database
- Check `.env` credentials
- Ensure PostgreSQL is running
- Verify database exists

**Issue**: Spoonacular API errors
- Check API key in `.env`
- Verify API key is still active
- Check request parameters format

**Issue**: Token not working
- Ensure token is in `Authorization: Bearer TOKEN` format
- Check if token has expired
- Verify secret_key matches in `.env`

---

## 📖 Example Frontend Flow

1. **User visits app** → Shows sign-up/login page
2. **User signs up** → Receives JWT token
3. **User enters ingredients** → Sends to `/recipes/find-by-ingredients`
4. **App displays recipes** → Shows results with images
5. **User wants alternative** → Calls `/recipes/substitutes`
6. **User searches again** → Shows search history from database

---

## 🎓 Learning Resources

- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy docs: https://docs.sqlalchemy.org/
- Spoonacular API: https://spoonacular.com/food-api
- JWT explanation: https://jwt.io/

---

**Made by**: Your Team  
**Last Updated**: June 2026
