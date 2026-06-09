from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

# Many-to-many association table linking searches to recipes
# This allows us to track which recipes were found in each search
search_recipes_association = Table(
    'search_results', Base.metadata,
    Column('search_id', Integer, ForeignKey('user_searches.id')),
    Column('recipe_id', Integer, ForeignKey('recipes.id'))
)


class User(Base):
    """User account model - stores username and password."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    # Relationship to all searches performed by this user
    searches = relationship("UserSearch", back_populates="user")


class UserSearch(Base):
    """Tracks each search a user performs - stores the ingredients they searched for."""
    __tablename__ = "user_searches"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    # The ingredients string that was searched for
    query_ingredients = Column(String, nullable=False)
    
    # Relationships to connect with User and Recipe models
    user = relationship("User", back_populates="searches")
    recipes = relationship("Recipe", secondary=search_recipes_association)


class Recipe(Base):
    """Recipe model - stores recipes fetched from Spoonacular API."""
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    # External ID from Spoonacular API (unique to prevent duplicates)
    spoonacular_id = Column(Integer, unique=True) 
    title = Column(String, nullable=False)
    # Complete recipe data from the API stored as JSON
    raw_data = Column(JSON)


class IngredientSubstitute(Base):
    """Ingredient substitutes model - caches substitute suggestions from Spoonacular API."""
    __tablename__ = "ingredient_substitutes"
    id = Column(Integer, primary_key=True)
    # The ingredient we're storing substitutes for
    ingredient_name = Column(String, unique=True)
    # List of substitute ingredients stored as JSON
    substitutes = Column(JSON)