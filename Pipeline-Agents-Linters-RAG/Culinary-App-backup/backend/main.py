from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from agent import run_agent
from database import init_db, get_all_recipes, get_recipe_by_id

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@app.on_event("startup")
async def startup_event():
    os.makedirs('./images', exist_ok=True)
    init_db()

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        result = run_agent(request.message, request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{filename}")
async def get_image(filename: str):
    file_path = f'./images/{filename}'
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")

@app.get("/recipes")
async def list_recipes():
    try:
        return get_all_recipes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: int):
    try:
        recipe = get_recipe_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))