# Recipe Search App with AI Chef

A recipe search and AI-assisted kitchen helper built with **Flask**, **Jinja2**, **SQLAlchemy**, and **HTMX** for seamless partial page updates.

---

## Key Features

### Recipe Search & Customization
- **Smart Search**: Search for recipes by ingredients with a configurable quantity limit (1–5 results).
- **Dashboard Tabs**: Browse recipes via dedicated tabs — *Searched*, *My Recipes*, *Liked*, *All Recipes*.
- **Filter Bar**: Filter by dish type, max cooking time, and dietary flags (Vegetarian, Vegan, Gluten-Free, Kosher).
- **Default Filter Settings**: Persistent default preferences saved per user and auto-applied to searches.
- **Recipe Builder**: Create and edit custom recipes with drag-and-drop ingredient management, rich text instructions, and image upload.
- **Like System**: Toggle recipe likes with optimistic UI updates — instant feedback, auto-rollback on failure.

### AI Integrations
- **Custom Recipe Generation**: Generate a new recipe from available ingredients, respecting active dietary filters.
- **Adaptive Ingredient Substitution**: Select ingredients and let AI remake the recipe around alternatives.
- **Quick AI Suggestions**: Get a rapid substitute recommendation for any single ingredient.

### Partial Page Updates (HTMX)
- Navigation between Home, Search, and Settings swaps only the `#page-content` div — no full browser refresh.
- Tab switching within the dashboard reloads only recipe content.
- Animated loading bar + spinner appear during any HTMX request.
- Smooth fade-in transition on every content swap.

---

## Architecture

The application follows a **Flask Service-Layer pattern**:

| Layer | Location | Responsibility |
|---|---|---|
| Routes | `app/blueprints/` | HTTP request/response, session handling |
| Services | `app/services/` | Business logic, DB access, external API calls |
| Templates | `templates/` | Jinja2 layout inheritance + reusable macros |
| Partials | `templates/partials/` | HTMX-swappable content fragments |

Routes detect `HX-Request: true` headers and return lightweight partials instead of full pages when called via HTMX.

### Performance
- **Optimistic UI**: Like toggle updates instantly; reverts on server error.
- **Session Caching**: Liked recipe IDs cached in Flask session to avoid repeated DB queries.
- **Local Fallback Search**: Falls back to cached DB recipes if Spoonacular is unavailable.
- **Pessimistic Connection Ping**: `pool_pre_ping=True` handles idle database timeouts.

---

## Project Structure

```
recipe_project/
├── app/
│   ├── config.py                   # Pydantic settings loaded from .env
│   ├── main.py                     # Flask entry point, blueprint registration, DB init
│   ├── database/
│   │   ├── connection.py           # SQLAlchemy engine and SessionLocal factory
│   │   └── models.py               # ORM models: User, Recipe, UserSearch, IngredientSubstitute
│   ├── blueprints/
│   │   ├── ai.py                   # AI routes: generate, substitute, quick-substitute
│   │   ├── auth.py                 # Auth routes: login, register, logout
│   │   └── recipes.py              # Recipe routes: home, search, CRUD, like, settings
│   ├── services/
│   │   ├── ai_service.py           # AI recipe generation and substitution logic
│   │   └── recipe_service.py       # Recipe search, caching, CRUD, Spoonacular integration
│   └── utils/
│       ├── flask_helpers.py        # login_required decorator, filter & kosher helpers
│       └── password_hashing.py
├── templates/
│   ├── base.html                   # Base layout: navbar, flash messages, HTMX loader
│   ├── login.html                  # Login page (standalone, no nav)
│   ├── register.html               # Registration page (standalone, no nav)
│   ├── home.html                   # Dashboard shell (extends base, includes partial)
│   ├── search.html                 # Search page shell (extends base, includes partial)
│   ├── settings.html               # Settings page shell (extends base, includes partial)
│   ├── cooking_steps.html          # Recipe detail: ingredients, substitutes, instructions
│   ├── partials/                   # HTMX content fragments (no base layout)
│   │   ├── home_content.html       # Dashboard: tabs, filter bar, recipe grid
│   │   ├── search_content.html     # Search form, filters, AI generator, results
│   │   └── settings_content.html   # Dietary preference settings form
│   └── components/                 # Jinja2 macros
│       ├── add_recipe.html         # Recipe builder form
│       ├── ai.html                 # AI generation and substitution widgets
│       ├── filters.html            # Filter dropdowns and checkboxes
│       └── recipe.html             # Recipe card renderer (2-col grid)
├── static/
│   ├── favicon.ico
│   ├── css/
│   │   ├── style.css               # Main entry point (imports all modules)
│   │   ├── base.css                # Design tokens, reset, navbar, HTMX loader, flash
│   │   ├── components.css          # Buttons, forms, badges, alerts
│   │   ├── home.css                # Sticky subnav, filter bar, recipe grid, dropdown
│   │   └── auth.css                # Auth page styles (standalone, imports base.css)
│   └── js/
│       ├── main.js                 # Optimistic likes, recipe card expand, AI filter submit
│       ├── auth.js                 # Password visibility toggle
│       ├── recipe-builder.js       # Drag-and-drop ingredient builder
│       └── cooking-steps.js        # Substitute fetch, AI selection mode
├── tests/
│   ├── test_auth.py
│   ├── test_flask_blueprints.py
│   ├── test_helpers.py
│   ├── test_real_ai.py
│   └── test_services.py
├── example.env
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### Prerequisites
- **Python 3.8+**
- **PostgreSQL** (local or cloud)
- **Spoonacular API Key**

### Step 1: Clone and Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Environment Configuration

Copy `example.env` → `.env` and fill in your credentials:

```env
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_NAME=recipe_db
SECRET_KEY=your_secret_key
SPOONACULAR_API_KEY=your_spoonacular_api_key
SPOONACULAR_URL=https://api.spoonacular.com/recipes/findByIngredients
AI_URL=http://localhost:11434/chat/completions
```

> Settings are validated at startup via Pydantic Settings.

---

## Running the Application

```bash
python3 -m app.main
```

Available at `http://127.0.0.1:5000`.

---

## Authentication

Session-based with Werkzeug password hashing.

| Route | Method | Description |
|---|---|---|
| `/register` | GET / POST | Create account with username + hashed password |
| `/login` | GET / POST | Store `user_id` + `username` in Flask session |
| `/logout` | GET | Clear session, redirect to login |

All recipe and AI routes are protected by the `@login_required` decorator.

---

## Routes Reference

### Recipe Routes

| Route | Method | Description |
|---|---|---|
| `/home` | GET | Dashboard: tabs, filters, recipe grid |
| `/search` | GET / POST | Search recipes by ingredients |
| `/recipe/<id>` | GET | Recipe details and cooking steps |
| `/recipe/<id>/like` | POST | Toggle like/unlike (AJAX) |
| `/recipe/<id>/edit` | GET / POST | Edit a custom recipe |
| `/add_recipe` | POST | Save a new custom recipe |
| `/substitutes` | GET | Fetch ingredient substitutes |
| `/settings` | GET | View dietary preference settings |
| `/update_settings` | POST | Save dietary preference settings |

### AI Routes

| Route | Method | Description |
|---|---|---|
| `/ai/generate-ai` | POST | Generate a new recipe from ingredients |
| `/ai/recipe/<id>/substitute-ai` | POST | Remake recipe with swapped ingredients |
| `/ai/quick-substitute` | GET | One-sentence AI substitute suggestion |

---

## Database Models

| Model | Table | Description |
|---|---|---|
| `User` | `users` | Credentials + dietary preference defaults |
| `UserSearch` | `user_searches` | Search history with ingredient queries |
| `Recipe` | `recipes` | Unified table for Spoonacular + custom recipes |
| `IngredientSubstitute` | `ingredient_substitutes` | Local cache for substitute lookups |

Relationships: User → many UserSearches → many Recipes (many-to-many via `search_results`). User → many liked Recipes (many-to-many via `user_liked_recipes`).

---

## Frontend

### UI Design
- **Font**: Inter (Google Fonts)
- **Color tokens**: CSS custom properties defined in `base.css` `:root` — `--red`, `--violet`, `--surface`, `--border`, `--shadow-*`, `--r-*`, `--nav-height`
- **Navbar**: Glassmorphism (`backdrop-filter: blur(16px)`) sticky header at `z-index: 500`
- **Recipe Layout**: 2-column CSS grid (`display: grid; grid-template-columns: repeat(2, 1fr)`) that collapses to 1 column on mobile
- **Recipe Dropdown**: Styled expand panel with likes pill, 2-column ingredient list, and action buttons
- **Sticky Subnav**: Tab bar + compact filter bar stick together below the main nav (`top: var(--nav-height)`) while the recipe grid scrolls freely underneath
- **Filter Bar**: Compact inline row (no heading, smaller inputs/pills) — lives inside the sticky subnav, not in the scrollable content
- **Transitions**: `page-in` fade on every HTMX content swap, `tab-in` animation on tab switch, animated top progress bar + spinner during requests

### CSS Modules
| File | Contents |
|---|---|
| `base.css` | Design tokens (`:root`), reset, navbar, HTMX loader, flash messages, page transitions |
| `components.css` | Buttons, form inputs, badges, difficulty tags, no-results state |
| `home.css` | Sticky subnav, compact filter bar, 2-col recipe grid, styled dropdown, recipe builder |
| `auth.css` | Auth pages — standalone, radial-gradient background, shadow-lg card |
| `style.css` | Entry point: `@import`s all modules + page-level styles (search, settings, cooking steps, AI widgets) |

### HTMX Partial Rendering
Pages that support partial swap:

| URL | Partial template | Full template |
|---|---|---|
| `/home` | `partials/home_content.html` | `home.html` |
| `/search` | `partials/search_content.html` | `search.html` |
| `/settings` | `partials/settings_content.html` | `settings.html` |

Detection: `request.headers.get('HX-Request') == 'true'` in each Flask route.

---

## Testing

```bash
pytest tests/test_flask_blueprints.py -v
```

Tests use an **in-memory SQLite database** and mock all external API calls (Spoonacular, AI). Covers: auth flows, recipe CRUD, like toggle, search, settings update, AI generation and substitution.

---

## Notes

- Never commit `.env` to source control — use `example.env` as the template.
- Install `pytest-mock` if not already present (`pip install pytest-mock`).
- The caching layer reduces Spoonacular API calls; keep the database active to benefit.

---

## Authors

- [**David Beninson**](https://github.com/David-Beninson)
- [**Oliver Radivan**](https://github.com/oliverradivan)
