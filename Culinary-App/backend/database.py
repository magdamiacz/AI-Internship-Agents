
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

DATABASE_URL = "sqlite:///culinary.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ingredients = Column(Text)
    steps = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Image(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    recipe = relationship("Recipe", back_populates="images")

Recipe.images = relationship("Image", order_by=Image.id, back_populates="recipe")


def init_db():
    Base.metadata.create_all(bind=engine)


def save_recipe(name, ingredients, steps):
    db = SessionLocal()
    recipe = Recipe(name=name, ingredients=json.dumps(ingredients), steps=json.dumps(steps))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    db.close()
    return recipe


def save_image(recipe_id, file_path):
    db = SessionLocal()
    image = Image(recipe_id=recipe_id, file_path=file_path)
    db.add(image)
    db.commit()
    db.refresh(image)
    db.close()
    return image
