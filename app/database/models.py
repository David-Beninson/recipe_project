from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from .connection import Base

# Many-to-many association table linking searches to recipes
# This allows us to track which recipes were found in each search
search_recipes_association = Table(
    'search_results', Base.metadata,
    Column('search_id', Integer, ForeignKey('user_searches.id')),
    Column('recipe_id', Integer, ForeignKey('recipes.id'))
)

# Many-to-many association table linking users to liked recipes
user_liked_recipes_association = Table(
    'user_liked_recipes', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('recipe_id', Integer, ForeignKey('recipes.id', ondelete='CASCADE'))
)


class User(Base):
    """User account model - stores username and password."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    
    # Default search preferences
    default_vegetarian = Column(Boolean, default=False, nullable=False)
    default_vegan = Column(Boolean, default=False, nullable=False)
    default_gluten_free = Column(Boolean, default=False, nullable=False)
    default_kosher = Column(Boolean, default=False, nullable=False)
    default_dish_type = Column(String, default="", nullable=False)
    default_prep_time = Column(Integer, default=9999, nullable=False)

    # Relationship to all searches performed by this user
    searches = relationship("UserSearch", back_populates="user")
    custom_recipes = relationship("Recipe", back_populates="user")
    liked_recipes = relationship("Recipe", secondary=user_liked_recipes_association, back_populates="liked_by_users")


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
    """Recipe model - stores recipes fetched from Spoonacular API or added by users."""
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    # External ID from Spoonacular API (unique to prevent duplicates)
    spoonacular_id = Column(Integer, unique=True, nullable=True) 
    title = Column(String, nullable=False)
    # Complete recipe data from the API stored as JSON
    raw_data = Column(JSON)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="custom_recipes")
    liked_by_users = relationship("User", secondary=user_liked_recipes_association, back_populates="liked_recipes")


class IngredientSubstitute(Base):
    """Ingredient substitutes model - caches substitute suggestions from Spoonacular API."""
    __tablename__ = "ingredient_substitutes"
    id = Column(Integer, primary_key=True)
    # The ingredient we're storing substitutes for
    ingredient_name = Column(String, unique=True)
    # List of substitute ingredients stored as JSON
    substitutes = Column(JSON)
