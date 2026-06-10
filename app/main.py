from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import SessionLocal, engine
from app.models import Base, User, UserSearch, Recipe
from app.utils.oauth2 import create_access_token
import os
import httpx
from functools import wraps
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Get absolute paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database initialization flag
db_initialized = False

def init_db_sync():
    """Initialize database tables synchronously."""
    global db_initialized
    if db_initialized:
        return
    
    try:
        Base.metadata.create_all(engine)
        db_initialized = True
    except Exception as e:
        print(f"Database initialization error: {e}")

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Redirect to login by default."""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    init_db_sync()
    
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))
        
        # Check user in database
        try:
            with SessionLocal() as db:
                stmt = select(User).filter(User.user_name == username)
                user = db.execute(stmt).scalars().first()
                        
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.user_name
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials', 'error')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
        
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and handler - connects to database."""
    init_db_sync()
    
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm')
        
        # Validation
        if not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return redirect(url_for('register'))
        
        # Save user to database
        try:
            with SessionLocal() as db:
                
                stmt = select(User).filter(User.user_name == username)
                result = db.execute(stmt)
                if result.scalars().first():
                    new_user = None
                else:
                    hashed_password = generate_password_hash(password)
                    new_user = User(user_name=username, password=hashed_password)
                    db.add(new_user)
                    db.commit()
            
            if new_user is None:
                flash('Username already exists', 'error')
            else:
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
        
        except Exception as e:
            flash(f'Signup error: {str(e)}', 'error')
        
        return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/home')
@login_required
def home():
    """Home page after login showing previously searched recipes."""
    user_recipes = []
    try:
        with SessionLocal() as db:
            # Load user searches with their cached recipes
            stmt = select(UserSearch).filter(UserSearch.user_id == session['user_id']).options(selectinload(UserSearch.recipes))
            searches = db.execute(stmt).scalars().all()
            
            seen_recipe_ids = set()
            for search_obj in searches:
                for r in search_obj.recipes:
                    if r.spoonacular_id not in seen_recipe_ids:
                        seen_recipe_ids.add(r.spoonacular_id)
                        recipe_data = r.raw_data if r.raw_data else {}
                        # Make sure necessary keys are set
                        recipe_data['id'] = r.spoonacular_id
                        recipe_data['title'] = r.title
                        user_recipes.append(recipe_data)
    except Exception as e:
        print(f"Error fetching user recipes: {e}")
        user_recipes = []
        
    return render_template('home.html', username=session.get('username'), user_recipes=user_recipes)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for recipes page and handler - calls FastAPI backend."""
    recipes = []
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')
        number = request.form.get('number', 10)
        
        if not ingredients:
            flash('Please enter ingredients', 'warning')
            return redirect(url_for('search'))
        
        # Generate JWT token for authenticate with FastAPI
        token = create_access_token(data={"user_id": session['user_id']})
        headers = {"Authorization": f"Bearer {token}"}
        params = {"ingredients": ingredients, "number": number}
        
        try:
            # Call the FastAPI backend service
            with httpx.Client() as client:
                response = client.get("http://127.0.0.1:8000/recipes/find-by-ingredients", headers=headers, params=params, timeout=10.0)
                if response.status_code == 200:
                    recipes = response.json()
                    flash(f'Found {len(recipes)} recipes for: {ingredients}', 'success')
                else:
                    flash(f"Backend API error: {response.text}", "error")
        except Exception as e:
            print(f"Connection error to backend: {e}")
            flash("Failed to connect to backend service.", "error")
    
    return render_template('search.html', recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
@login_required
def cooking_steps(recipe_id):
    """Retrieve recipe details from FastAPI and display cooking steps."""
    try:
        # Fetch detailed recipe information (including instructions and ingredients)
        with httpx.Client() as client:
            response = client.get(f"http://127.0.0.1:8000/recipes/{recipe_id}/information", timeout=10.0)
            if response.status_code == 200:
                recipe = response.json()
                # Ensure the ID matches what templates expect
                recipe['id'] = recipe_id
                return render_template('cooking_steps.html', recipe=recipe)
            else:
                flash('Recipe detail not found on server', 'error')
                return redirect(url_for('home'))
    except Exception as e:
        print(f"Error fetching recipe: {e}")
        flash('Error loading recipe details from backend', 'error')
        return redirect(url_for('home'))

@app.route('/substitutes')
@login_required
def substitutes():
    """Proxy route to call FastAPI substitutes endpoint."""
    ingredient = request.args.get('ingredient')
    if not ingredient:
        return jsonify({"detail": "Missing ingredient parameter"}), 400
        
    try:
        with httpx.Client() as client:
            response = client.get("http://127.0.0.1:8000/recipes/substitutes", params={"ingredient": ingredient}, timeout=10.0)
            return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"Substitutes backend error: {e}")
        return jsonify({"detail": "Failed to retrieve substitutes from backend"}), 500

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)