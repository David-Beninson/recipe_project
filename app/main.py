from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import SessionLocal, engine
from app.models import Base, User
import os
from functools import wraps
from pathlib import Path
from sqlalchemy import select

# Get absolute paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'templates'

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
    
    return render_template('components/loggingin.html')

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
    
    return render_template('components/register.html')

@app.get("/home")
def home_page():
    return FileResponse("frontend/client/home.html")

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)