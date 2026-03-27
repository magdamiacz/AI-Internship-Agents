from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from openai import OpenAI
from database import save_recipe, save_image
from dotenv import load_dotenv
import requests
import re
import os

load_dotenv()

# ── Narzędzia ──────────────────────────────────────────────────────────────

@tool
def generate_dish_image(recipe_name: str, visual_description: str) -> str:
    """
    Generuje zdjęcie dania przy użyciu DALL-E 3 i zapisuje je lokalnie.
    Wywołaj to narzędzie po każdym wygenerowanym przepisie.
    """
    client = OpenAI()

    prompt = (
        f"Professional food photography, highly detailed, appetizing, "
        f"cinematic lighting, restaurant quality. "
        f"Dish: {recipe_name}. Description: {visual_description}."
    )

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
    file_path = f"./images/{filename}"

    os.makedirs("./images", exist_ok=True)
    img_data = requests.get(image_url).content
    with open(file_path, 'wb') as f:
        f.write(img_data)

    return filename  # zwracamy tylko nazwę pliku, nie pełną ścieżkę


# ── Graf LangGraph ──────────────────────────────────────────────────────────

tools = [generate_dish_image]
llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

system_prompt = SystemMessage(content="""
Jesteś ekspertem kulinarnym i asystentem szefa kuchni.
Rozmawiaj TYLKO o jedzeniu, gotowaniu i przepisach.

Gdy użytkownik poprosi o przepis:
1. Podaj przepis w formacie:
   NAZWA: <nazwa dania>
   SKŁADNIKI: <składnik1>, <składnik2>, ...
   KROKI: 1. <krok1> 2. <krok2> ...
2. Wywołaj narzędzie generate_dish_image z nazwą dania i krótkim opisem wizualnym.
3. Poinformuj użytkownika że przepis i zdjęcie zostały zapisane.
""")

class State(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot_node(state: State):
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph = graph_builder.compile()


# ── Funkcja pomocnicza do parsowania przepisu ───────────────────────────────

def parse_recipe_from_response(text: str):
    """Wyciąga nazwę, składniki i kroki z odpowiedzi agenta."""
    name, ingredients, steps = "Nieznane danie", [], []

    name_match = re.search(r'NAZWA:\s*(.+)', text)
    if name_match:
        name = name_match.group(1).strip()

    ingredients_match = re.search(r'SKŁADNIKI:\s*(.+)', text)
    if ingredients_match:
        ingredients = [i.strip() for i in ingredients_match.group(1).split(',')]

    steps_match = re.search(r'KROKI:\s*(.+)', text, re.DOTALL)
    if steps_match:
        raw_steps = steps_match.group(1).strip()
        steps = re.split(r'\d+\.', raw_steps)
        steps = [s.strip() for s in steps if s.strip()]

    return name, ingredients, steps


# ── Główna funkcja wywoływana przez FastAPI ─────────────────────────────────

def run_agent(message: str, thread_id: str) -> dict:
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread_id}}
    )

    # Ostatnia wiadomość tekstowa od agenta
    final_response = ""
    image_filename = None

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
            final_response = msg.content
            break

    # Szukamy nazwy pliku zwróconej przez narzędzie generate_dish_image
    for msg in result["messages"]:
        if hasattr(msg, "name") and msg.name == "generate_dish_image":
            content = msg.content
            if isinstance(content, str) and content.endswith(".png"):
                image_filename = content

    # Zapis do bazy danych
    recipe_id = None
    if final_response:
        name, ingredients, steps = parse_recipe_from_response(final_response)
        if ingredients or steps:
            recipe = save_recipe(name, ingredients, steps)
            recipe_id = recipe.id
            if image_filename:
                save_image(recipe_id, f"./images/{image_filename}")

    return {
        "response": final_response,
        "image_path": image_filename,  # sama nazwa pliku, np. "tiramisu.png"
        "recipe_id": recipe_id
    }