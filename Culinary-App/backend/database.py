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
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, index=True)
    ingredients = Column(Text)
    steps       = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)
    images      = relationship("Image", order_by="Image.id", back_populates="recipe")

class Image(Base):
    __tablename__ = 'images'
    id         = Column(Integer, primary_key=True, index=True)
    recipe_id  = Column(Integer, ForeignKey('recipes.id'))
    file_path  = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    recipe     = relationship("Recipe", back_populates="images")

def init_db():
    Base.metadata.create_all(bind=engine)

def save_recipe(name, ingredients, steps):
    db = SessionLocal()
    recipe = Recipe(
        name=name,
        ingredients=json.dumps(ingredients, ensure_ascii=False),
        steps=json.dumps(steps, ensure_ascii=False)
    )
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

def _recipe_to_dict(r):
    image_filename = None
    if r.images:
        image_filename = r.images[0].file_path.replace('./images/', '').replace('images/', '')
    return {
        "id": r.id,
        "name": r.name,
        "ingredients": json.loads(r.ingredients) if r.ingredients else [],
        "steps": json.loads(r.steps) if r.steps else [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "image_path": image_filename
    }

def get_all_recipes():
    db = SessionLocal()
    recipes = db.query(Recipe).order_by(Recipe.created_at.desc()).all()
    result = [_recipe_to_dict(r) for r in recipes]
    db.close()
    return result

def get_recipe_by_id(recipe_id: int):
    db = SessionLocal()
    r = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    result = _recipe_to_dict(r) if r else None
    db.close()
    return result