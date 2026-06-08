from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

search_recipes_association = Table(
    'search_results', Base.metadata,
    Column('search_id', Integer, ForeignKey('user_searches.id')),
    Column('recipe_id', Integer, ForeignKey('recipes.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    searches = relationship("UserSearch", back_populates="user")

class UserSearch(Base):
    __tablename__ = "user_searches"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query_ingredients = Column(String, nullable=False)
    
    user = relationship("User", back_populates="searches")
    recipes = relationship("Recipe", secondary=search_recipes_association)

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    spoonacular_id = Column(Integer, unique=True) 
    title = Column(String, nullable=False)
    raw_data = Column(JSON)

class IngredientSubstitute(Base):
    __tablename__ = "ingredient_substitutes"
    id = Column(Integer, primary_key=True)
    ingredient_name = Column(String, unique=True)
    substitutes = Column(JSON)