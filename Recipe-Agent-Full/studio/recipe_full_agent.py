import os
import json
import base64
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

import requests
import re
from openai import OpenAI

load_dotenv()

@tool
def save_recipe_to_json(recipe_name: str, ingredients: list[str], steps: list[str], filename: str = "recipe.json"):
    """
    Zapisuje wygenerowany przepis kulinarny do pliku JSON.
    Użyj tego narzędzia za każdym razem, gdy użytkownik otrzyma nowy przepis.
    """
    recipe_data = {
        "nazwa_przepisu": recipe_name,
        "skladniki": ingredients,
        "kroki_przygotowania": steps
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(recipe_data, f, ensure_ascii=False, indent=4)
        
    return f"Przepis '{recipe_name}' został pomyślnie zapisany w pliku {filename}!"

@tool
def generate_recipe_image(recipe_name: str, visual_description: str) -> str:
    """
    Generuje apetyczne zdjęcie gotowego dania za pomocą DALL-E 3 na podstawie jego nazwy i opisu wizualnego, 
    a następnie zapisuje je na dysku lokalnym.
    Użyj tego narzędzia za każdym razem, gdy wygenerujesz nowy przepis, aby stworzyć jego wizualizację.
    """
    client = OpenAI() 
    
    prompt = (
        f"Professional food photography, highly detailed, appetizing, cinematic lighting, "
        f"restaurant quality. Dish: {recipe_name}. Description: {visual_description}."
    )
    
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', recipe_name).lower()
        filename = f"{safe_name}.png"
        
        img_data = requests.get(image_url).content
        with open(filename, 'wb') as handler:
            handler.write(img_data)
            
        return f"Zdjęcie dla '{recipe_name}' zostało pomyślnie wygenerowane i zapisane w pliku {filename}!"
    except Exception as e:
        return f"Wystąpił błąd podczas generowania zdjęcia: {str(e)}"

tools = [save_recipe_to_json, generate_recipe_image]

def encode_image(image_path: str) -> str:
    """Koduje obraz do formatu base64."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

class State(TypedDict):
    messages: Annotated[list, add_messages]

system_prompt = SystemMessage(content="""
Jesteś ekspertem kulinarnym i asystentem szefa kuchni.
Masz zakaz rozmawiania na tematy inne niż jedzenie, gotowanie, przepisy i kuchnia. Jeśli użytkownik zapyta o coś innego, grzecznie odmów i zaproponuj rozmowę o jedzeniu.

Twoje zadania:
1. Jeśli użytkownik poprosi o przepis lub wyśle zdjęcie dania do rozpoznania, zawsze podawaj instrukcje w następującej strukturze:
   - Składniki (z dokładnymi miarami, np. gramy, mililitry, sztuki).
   - Kroki przygotowania (ponumerowane, jasne i logiczne).
2. Za każdym razem, gdy podajesz nowy przepis, wywołaj narzędzie 'save_recipe_to_json', aby zapisać ten przepis do pliku.
3. Po zapisaniu przepisu, OBOWIĄZKOWO wywołaj narzędzie 'generate_recipe_image', aby wygenerować i zapisać zdjęcie tego dania. Jako 'visual_description' przekaż krótki, apetyczny opis wyglądu potrawy.
4. Na koniec poinformuj użytkownika o zapisaniu przepisu i zdjęcia na dysku.

Formatuj odpowiedź czytelnie używając Markdown.
""")

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    messages = [system_prompt] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

app = graph_builder.compile()