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

tools = [save_recipe_to_json]

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