from functools import wraps
from flask import session, flash, redirect, url_for

nonKosherItems=[
    # --- Seafood (No fins and scales) ---
    "shrimp",
    "lobster",
    "crab",
    "clams",
    "oysters",
    "mussels",
    "squid",
    "octopus",
    "shark",
    "catfish",
    "eel",

    # --- Land Animals (Do not both chew cud and have cloven hooves) ---
    "pork",
    "bacon",
    "ham",
    "rabbit",
    "camel",
    "horse",
    "wild boar",

    # --- Birds of Prey & Scavengers ---
    "eagle",
    "vulture",
    "owl",
    "raven",
    "ostrich",

    # --- Insects & Creeping Things ---
    "ants",
    "flies",
    "snails",
    "slugs",

    # --- Disallowed Mixtures & Byproducts ---
    "cheeseburger",             # Mixing meat and dairy
    "chicken parmesan",          # Mixing poultry and dairy
    "gelatin",                  # If derived from non-kosher animals (like pork)
    "lard",                     # Pig fat
    "tallow",                   # Unrefined beef/mutton fat (unless certified kosher)
    "rennet",                   # Animal enzyme used in cheese (unless certified microbial/kosher)
]


def login_required(f):
    """Decorator to require login for Flask routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def check_kosher(ingredients: list):
    global nonKosherItems
    isMeat= False
    isDairy= False
    hasNonKosher= False

    for ingredient in ingredients:
        if ingredient.aisle == "meat":
            isMeat = True
        elif ingredient.aisle == "dairy":
            isDairy = True
        if ingredient.nameClean in nonKosherItems:
            return False 
            break

    return True
        

def filter_recipes_list(recipes, dish_type=None, prep_time=None, vegetarian=False, vegan=False, gluten_free=False, kosher=True):
    """Filter recipe list based on dish type, cooking time, and dietary requirements."""
    filtered = []
    for r in recipes:
        # Get ready in minutes
        r_prep = r.get('readyInMinutes')
        if r_prep is None:
            r_prep = r.get('ready_in_minutes')
        if r_prep is None:
            r_prep = 9999
            
        # Get dish types
        r_types = r.get('dishTypes')
        if r_types is None:
            r_types = r.get('dish_types')
        if r_types is None:
            r_types = []
        # Normalise to lowercase strings
        r_types = [str(t).lower() for t in r_types]
        
        # Get flags
        r_veg = r.get('vegetarian', False)
        r_vegan = r.get('vegan', False)
        r_gf = r.get('glutenFree')
        if r_gf is None:
            r_gf = r.get('gluten_free', False)
            
        # Match checks
        match = True
        if dish_type and not any(dish_type.lower() in t for t in r_types):
            match = False
        if prep_time is not None and r_prep > prep_time:
            match = False
        if vegetarian and not r_veg:
            match = False
        if vegan and not r_vegan:
            match = False
        if gluten_free and not r_gf:
            match = False
            
        if match:
            filtered.append(r)
    return filtered