from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select
from app.database import SessionLocal
from app.database import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            with SessionLocal() as db:
                stmt = select(User).filter(User.user_name == username)
                user = db.execute(stmt).scalars().first()
                        
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.user_name
                flash('Login successful!', 'success')
                return redirect(url_for('recipes.home'))
            else:
                flash('Invalid credentials', 'error')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
        
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and handler - connects to database."""
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm')
        
        # Validation
        if not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return redirect(url_for('auth.register'))
        
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
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            flash(f'Signup error: {str(e)}', 'error')
        
        return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.login'))
