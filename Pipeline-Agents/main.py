# main.py
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.state import AgentState
from agents.nodes import (
    supervisor_node, task_agent_node, arch_agent_node,
    tech_agent_node, coder_agent_node, review_agent_node,
    docker_agent_node, save_and_proceed_node
)

load_dotenv()

builder = StateGraph(AgentState)

builder.add_node("supervisor", supervisor_node)
builder.add_node("task_agent", task_agent_node)
builder.add_node("arch_agent", arch_agent_node)
builder.add_node("tech_agent", tech_agent_node)
builder.add_node("coder_agent", coder_agent_node)
builder.add_node("review_agent", review_agent_node)
builder.add_node("docker_agent", docker_agent_node)
builder.add_node("save_and_proceed_node", save_and_proceed_node)
builder.add_node("human_review", lambda x: x)

builder.add_edge(START, "supervisor")

def route_from_supervisor(state: AgentState):
    phase = state.get("current_phase", "task")
    routes = {
        "task": "task_agent", "arch": "arch_agent",
        "tech": "tech_agent", "code": "coder_agent",
        "review": "review_agent", "docker": "docker_agent", "done": END
    }
    return routes.get(phase, END)

builder.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    ["task_agent", "arch_agent", "tech_agent", "coder_agent", "review_agent", "docker_agent", END]
)

for agent in ["task_agent", "arch_agent", "tech_agent", "coder_agent", "review_agent", "docker_agent"]:
    builder.add_edge(agent, "human_review")

def route_after_human(state: AgentState):
    last_msg = state["messages"][-1].content.strip().lower()
    if "ok" in last_msg or "akceptuj" in last_msg:
        return "save_and_proceed_node"
    return "supervisor"

builder.add_conditional_edges("human_review", route_after_human, ["save_and_proceed_node", "supervisor"])
builder.add_edge("save_and_proceed_node", "supervisor")

memory = MemorySaver()

graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["human_review"]
)

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)

    config = {"configurable": {"thread_id": "culinary-app-1"}}

    initial_state = {
        "messages": [HumanMessage(content="""
        Create a complete web application for an AI culinary chatbot.

        FRONTEND (plain HTML/CSS/JS — no frameworks):
        - Single page: index.html with embedded CSS and JS
        - Chat interface: text input, send button, scrollable message history
        - Display bot responses with formatted recipe (ingredients list + numbered steps)
        - Display generated dish image below the recipe (fetch from backend)
        - Responsive, clean design

        BACKEND (FastAPI + Python):
        - File: backend/main.py
        - POST /chat endpoint: accepts JSON {message: str, thread_id: str}
          Returns JSON {response: str, image_path: str | null, recipe_id: int | null}
        - GET /images/{filename} endpoint: serves image files from backend/images/ directory
        - Use LangChain + OpenAI GPT-4o to generate recipes
        - Use DALL-E 3 to generate dish images
        - Save images to: backend/images/{safe_recipe_name}.png
        - CORS enabled for all origins (for local dev)

        DATABASE (SQLite + SQLAlchemy):
        - File: backend/database.py
        - Table 'recipes': id (PK), name (str), ingredients (JSON text), steps (JSON text), created_at (datetime)
        - Table 'images': id (PK), recipe_id (FK -> recipes.id), file_path (str), created_at (datetime)
        - Every generated recipe must be saved to DB
        - Every generated image path must be saved to DB
        - Do NOT use recipe.json files — use DB only

        AGENT LOGIC (backend/agent.py):
        - Wrap GPT-4o LangChain logic for recipe generation
        - Tools: generate_recipe (saves to DB), generate_image (DALL-E 3, saves file + DB record)
        - Return structured data: recipe name, ingredients[], steps[], image_path

        PROJECT STRUCTURE (output as JSON):
        {
          "frontend/index.html": "...",
          "backend/main.py": "...",
          "backend/database.py": "...",
          "backend/agent.py": "...",
          "backend/requirements.txt": "fastapi\\nuvicorn\\nopenai\\nlangchain\\nlangchain-openai\\nsqlalchemy\\npython-dotenv\\npython-multipart\\nrequests",
          "README.md": "..."
        }
        """)],
        "current_phase": "task",
        "task_file": "docs/task_definition.md",
        "arch_file": "docs/architecture.md",
        "tech_file": "docs/technologies.md",
        "review_file": "docs/code_review.md",
        "readme_file": "docs/README.md",
        # ↓ Ścieżka do nowego projektu — dostosuj jeśli Culinary-App jest gdzie indziej
        "output_dir": "../Culinary-App"
    }

    print("🚀 Uruchamiam pipeline dla projektu Culinary-App...")

    for event in graph.stream(initial_state, config, stream_mode="values"):
        if "draft_content" in event and event["draft_content"]:
            print("\n" + "="*50)
            print(f"📄 SZKIC OD AGENTA ({event.get('active_agent', 'unknown')}):")
            print(event["draft_content"])
            print("="*50)

    while True:
        state = graph.get_state(config)
        if state.next:
            user_input = input("\n[AKCJA] Wpisz 'ok' aby zaakceptować, lub podaj uwagi: ")
            graph.update_state(config, {"messages": [HumanMessage(content=user_input)]}, as_node="human_review")

            for event in graph.stream(None, config, stream_mode="values"):
                if "draft_content" in event and event["draft_content"]:
                    print("\n--- NOWY SZKIC ---")
                    print(event["draft_content"])
        else:
            print("\n🎉 Culinary-App wygenerowana pomyślnie!")
            print(f"📁 Kod zapisany w: {initial_state['output_dir']}")
            print("▶️  Następny krok: cd ../Culinary-App/backend && pip install -r requirements.txt && uvicorn main:app --reload")
            break