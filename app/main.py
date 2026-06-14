import os
from pathlib import Path
from flask import Flask, redirect, url_for, session
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.database import SessionLocal, engine
from app.models import Base, User
from app.blueprints import auth_bp, recipes_bp, ai_bp

# Get absolute paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(recipes_bp)
app.register_blueprint(ai_bp)

def init_db_sync():
    """Initialize database tables synchronously on startup and perform column migrations."""
    try:
        Base.metadata.create_all(engine)
        # Add columns if they do not exist (migrations)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_vegetarian BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_vegan BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_gluten_free BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_kosher BOOLEAN DEFAULT FALSE NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_dish_type VARCHAR DEFAULT '' NOT NULL"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS default_prep_time INTEGER DEFAULT 9999 NOT NULL"))
            conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database once when starting the app
init_db_sync()

@app.context_processor
def inject_user():
    """Inject username and liked recipe IDs into all templates."""
    liked_ids = []
    if 'user_id' in session:
        if 'liked_recipe_ids' in session:
            liked_ids = session['liked_recipe_ids']
        else:
            try:
                with SessionLocal() as db:
                    user_stmt = select(User).filter(User.id == session['user_id']).options(selectinload(User.liked_recipes))
                    user_obj = db.execute(user_stmt).scalars().first()
                    if user_obj:
                        liked_ids = [r.spoonacular_id if r.spoonacular_id else r.id for r in user_obj.liked_recipes]
                        session['liked_recipe_ids'] = liked_ids
            except Exception as e:
                print(f"Error injecting liked ids: {e}")
    return dict(username=session.get('username'), liked_recipe_ids=liked_ids)

@app.route('/')
def index():
    """Redirect to login or home by default."""
    if 'user_id' in session:
        return redirect(url_for('recipes.home'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)