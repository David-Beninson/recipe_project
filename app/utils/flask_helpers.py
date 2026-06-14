from functools import wraps
from flask import session, flash, redirect, url_for

nonKosherItems=[
    # Seafood (No fins and scales)
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

    # Land Animals (Do not both chew cud and have cloven hooves)
    "pork",
    "bacon",
    "ham",
    "rabbit",
    "camel",
    "horse",
    "wild boar",

    # Birds of Prey & Scavengers
    "eagle",
    "vulture",
    "owl",
    "raven",
    "ostrich",

    # Insects & Creeping Things
    "ants",
    "flies",
    "snails",
    "slugs",

    # Disallowed Mixtures & Byproducts
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
    """
    Checks if the list of ingredients contains any non-kosher items 
    or mixtures of meat and dairy products.
    """
    global nonKosherItems
    isMeat = False
    isDairy = False

    # If there are no ingredients, it is considered kosher by default.
    if not ingredients:
        return True

    # Iterate through each ingredient to inspect its category (aisle) and name.
    for ing in ingredients:
        # Extract the aisle/category and clean name of the ingredient, handling both dicts and objects.
        aisle = ing.get('aisle', '').lower() if isinstance(ing, dict) else getattr(ing, 'aisle', '').lower()
        name_clean = ing.get('nameClean', '').lower() if isinstance(ing, dict) else getattr(ing, 'nameClean', '').lower()

        # Check if the ingredient belongs to the meat or poultry aisle.
        if "meat" in aisle or "poultry" in aisle:
            isMeat = True
        # Check if the ingredient belongs to the dairy or cheese aisle.
        elif "dairy" in aisle or "cheese" in aisle:
            isDairy = True

        # If the clean name of the ingredient is in the list of known non-kosher items, reject it.
        if name_clean in nonKosherItems:
            return False

    # In kosher dietary laws, mixing meat and dairy products in the same recipe is forbidden.
    if isMeat and isDairy:
        return False

    # If no non-kosher ingredients or dairy-meat combinations were found, the recipe is kosher.
    return True
        

def filter_recipes_list(recipes, dish_type=None, prep_time=None, vegetarian=False, vegan=False, gluten_free=False, kosher=False):
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

        if kosher:
            r_ingredients = r.get('extendedIngredients') or r.get('ingredients') or []
            if not check_kosher(r_ingredients):
                match = False

        if match:
            filtered.append(r)
    return filtered

def extract_filter_params():
    """Extract standard recipe filter parameters from flask request.args/form."""
    from flask import request
    
    source = request.form if request.method == 'POST' else request.args
    
    dish_type = source.get('dish_type', '')
    prep_time_str = source.get('prep_time', '')
    prep_time = int(prep_time_str) if prep_time_str and prep_time_str.isdigit() else 9999
    
    vegetarian = source.get('vegetarian') in ('on', 'true')
    vegan = source.get('vegan') in ('on', 'true')
    gluten_free = source.get('gluten_free') in ('on', 'true')
    kosher = source.get('kosher') in ('on', 'true')
    
    return {
        'dish_type': dish_type,
        'prep_time': prep_time,
        'vegetarian': vegetarian,
        'vegan': vegan,
        'gluten_free': gluten_free,
        'kosher': kosher
    }