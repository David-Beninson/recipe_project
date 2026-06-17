import pytest
from flask import Flask, session
from app.utils.flask_helpers import check_kosher, filter_recipes_list, extract_filter_params

def test_check_kosher_empty():
    assert check_kosher([]) is True

def test_check_kosher_allowed():
    ingredients = [
        {"nameClean": "tomato", "aisle": "Produce"},
        {"nameClean": "garlic", "aisle": "Produce"}
    ]
    assert check_kosher(ingredients) is True

def test_check_kosher_non_kosher_item():
    ingredients = [
        {"nameClean": "pork", "aisle": "Meat"},
        {"nameClean": "garlic", "aisle": "Produce"}
    ]
    assert check_kosher(ingredients) is False

def test_check_kosher_meat_and_dairy():
    ingredients = [
        {"nameClean": "beef", "aisle": "Meat"},
        {"nameClean": "cheese", "aisle": "Dairy"}
    ]
    assert check_kosher(ingredients) is False

def test_filter_recipes_list():
    recipes = [
        {
            "id": 1,
            "title": "Vegetarian Pasta",
            "readyInMinutes": 20,
            "vegetarian": True,
            "vegan": False,
            "glutenFree": True,
            "dishTypes": ["lunch", "dinner"],
            "extendedIngredients": [{"nameClean": "pasta", "aisle": "Pasta"}]
        },
        {
            "id": 2,
            "title": "Pork Chop",
            "readyInMinutes": 45,
            "vegetarian": False,
            "vegan": False,
            "glutenFree": True,
            "dishTypes": ["dinner"],
            "extendedIngredients": [{"nameClean": "pork", "aisle": "Meat"}]
        }
    ]

    # Filter by vegetarian
    res_veg = filter_recipes_list(recipes, vegetarian=True)
    assert len(res_veg) == 1
    assert res_veg[0]["id"] == 1

    # Filter by kosher
    res_kosher = filter_recipes_list(recipes, kosher=True)
    assert len(res_kosher) == 1
    assert res_kosher[0]["id"] == 1

    # Filter by prep time
    res_time = filter_recipes_list(recipes, prep_time=30)
    assert len(res_time) == 1
    assert res_time[0]["id"] == 1

    # Filter by dish type
    res_type = filter_recipes_list(recipes, dish_type="dinner")
    assert len(res_type) == 2

def test_extract_filter_params_defaults():
    app = Flask("test_app")
    app.config["SECRET_KEY"] = "secret"
    with app.test_request_context('/?filter_submitted=on&dish_type=lunch&prep_time=30&vegetarian=on&kosher=on'):
        params = extract_filter_params()
        assert params["dish_type"] == "lunch"
        assert params["prep_time"] == 30
        assert params["vegetarian"] is True
        assert params["vegan"] is False
        assert params["kosher"] is True
