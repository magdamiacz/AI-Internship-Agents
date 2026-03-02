# agents/nodes.py
import os
import json
import re
import subprocess
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, RemoveMessage
from agents.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0)


def supervisor_node(state: AgentState):
    phase = state.get("current_phase", "task")

    prompt = f"""You are a Lead Technical Project Manager.
We are currently in the '{phase}' phase of the project.

CRITICAL INSTRUCTIONS:
1. Your ONLY task is to delegate work to the agent responsible for the CURRENT PHASE: '{phase}'.
2. Even if you see initial requirements in the chat history, DO NOT restart the process.
3. If the last message from the system was about saving data, simply call the agent for '{phase}'.
4. DO NOT ask the user for new requirements.

Current Phase to execute: {phase}."""

    sys_msg = SystemMessage(content=prompt)
    last_message = state["messages"][-1] if state["messages"] else ""
    response = llm.invoke([sys_msg, last_message])

    return {"messages": [response], "active_agent": phase}


def task_agent_node(state: AgentState):
    prompt = """Role: You are an Expert IT Business Analyst.
Task: Define a clear project specification (MVP) for a culinary chatbot web application.
Output Format (Markdown):
# Task Definition
## Business Goal
## Core Features
## Constraints"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def arch_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f:
        task_ctx = f.read()
    prompt = f"""You are a Senior System Architect. Design architecture based on requirements.
The system is: HTML/JS frontend + FastAPI backend + SQLite database + OpenAI (GPT-4o + DALL-E 3).
Task Context:\n{task_ctx}"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def tech_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f:
        task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f:
        arch_ctx = f.read()
    prompt = f"""You are a Lead Tech Stack Evaluator. Recommend and justify the tech stack.
Stack is fixed: HTML/CSS/JS (frontend), FastAPI + SQLAlchemy + SQLite (backend), OpenAI API.
Task:\n{task_ctx}\nArch:\n{arch_ctx}"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def coder_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f:
        task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f:
        arch_ctx = f.read()
    with open(state["tech_file"], "r", encoding="utf-8") as f:
        tech_ctx = f.read()

    prompt = f"""You are a Senior Software Engineer. Implement the full application.

STRICT OUTPUT RULES:
1. Return ONLY a valid JSON object. No markdown, no ```json blocks, no explanation text.
2. JSON keys are file paths. Values are complete file contents as strings.
3. Use these EXACT keys:
   - "frontend/index.html"   → full HTML/CSS/JS single-file chat UI
   - "backend/main.py"       → FastAPI app with /chat and /images endpoints
   - "backend/database.py"   → SQLAlchemy models: Recipe, Image tables (SQLite)
   - "backend/agent.py"      → LangChain GPT-4o agent with DALL-E 3 image tool
   - "backend/requirements.txt" → pip dependencies
   - "README.md"             → project documentation

IMPLEMENTATION REQUIREMENTS:

frontend/index.html:
- Single HTML file with all CSS and JS embedded (no external files)
- Chat UI: message history div, text input, Send button
- On send: POST to http://localhost:8000/chat with {{message, thread_id}}
- Display assistant response as formatted text
- If response contains image_path, display image via GET http://localhost:8000/images/{{filename}}
- Clean, modern design with CSS

backend/main.py:
- FastAPI app with CORS (allow all origins)
- POST /chat: receives {{message: str, thread_id: str}}, calls agent, returns {{response: str, image_path: str|null, recipe_id: int|null}}
- GET /images/{{filename}}: serves files from ./images/ directory using FileResponse
- On startup: create DB tables (call database.init_db())
- Create ./images/ directory on startup if not exists

backend/database.py:
- SQLAlchemy with SQLite (file: culinary.db)
- Model Recipe: id, name, ingredients (Text/JSON), steps (Text/JSON), created_at
- Model Image: id, recipe_id (ForeignKey), file_path, created_at
- Function init_db(): creates all tables
- Function save_recipe(name, ingredients, steps) -> Recipe
- Function save_image(recipe_id, file_path) -> Image

backend/agent.py:
- LangChain ChatOpenAI gpt-4o with tool use
- Tool generate_image: takes recipe_name + visual_description, calls DALL-E 3, saves PNG to ./images/{{safe_name}}.png, saves path to DB via save_image(), returns file path
- Main function run_agent(message: str, thread_id: str) -> dict with keys: response, image_path, recipe_id
- When recipe is generated: save to DB via save_recipe(), then call generate_image tool
- Return image filename (not full path) so frontend can construct the URL

Task:\n{task_ctx}\nArch:\n{arch_ctx}\nTech:\n{tech_ctx}"""

    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def review_agent_node(state: AgentState):
    with open(state["readme_file"], "r", encoding="utf-8") as f:
        readme_ctx = f.read()
    prompt = f"""You are a Strict Code Auditor.
Analyze the generated project structure and code quality.
README CONTEXT:\n{readme_ctx}

Output Format (Markdown):
# Code Review Report
## Bugs & Security Issues
## Missing Features vs Requirements
## Recommendations"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def docker_agent_node(state: AgentState):
    with open(state["readme_file"], "r", encoding="utf-8") as f:
        readme_ctx = f.read()

    prompt = f"""You are a DevOps Engineer. Containerize the culinary chatbot application.
README CONTEXT:\n{readme_ctx}

CRITICAL INSTRUCTIONS:
1. All Docker files go in 'docker/' directory.
2. Keys in output JSON:
   - "docker/frontend.Dockerfile"
   - "docker/backend.Dockerfile"  
   - "docker/docker-compose.yml"
3. Do NOT include 'version' in docker-compose.yml (obsolete).
4. In docker-compose.yml build contexts point to parent dirs:
   frontend: context: ../frontend
   backend:  context: ../backend
5. Inside Dockerfiles use 'COPY . /app' (context is already the component dir).
6. Backend container must expose port 8000, frontend must expose port 80.
7. Backend needs OPENAI_API_KEY env variable (read from .env file).
8. Return ONLY valid JSON object, no markdown blocks."""

    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def save_and_proceed_node(state: AgentState):
    phase = state["current_phase"]
    content = state["draft_content"]
    next_phase = "done"

    os.makedirs("docs", exist_ok=True)

    # Katalog wyjściowy dla wygenerowanego projektu (domyślnie ../Culinary-App)
    output_dir = state.get("output_dir", "../Culinary-App")

    def write_files_safely(data_dict, base_path=""):
        for key, value in data_dict.items():
            full_path = os.path.join(base_path, key)
            if isinstance(value, dict):
                os.makedirs(full_path, exist_ok=True)
                write_files_safely(value, full_path)
            else:
                dir_name = os.path.dirname(full_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(str(value))

    if phase == "task":
        with open(state["task_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "arch"

    elif phase == "arch":
        with open(state["arch_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "tech"

    elif phase == "tech":
        with open(state["tech_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "code"

    elif phase == "code":
        # ↓ Zapisuje do Culinary-App/ zamiast bieżącego folderu
        os.makedirs(output_dir, exist_ok=True)
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                files_dict = json.loads(match.group(0))
                write_files_safely(files_dict, base_path=output_dir)
                print(f"\n✅ Kod zapisany do: {output_dir}")

                # Kopiuj README.md do docs/ żeby review_agent mógł go przeczytać
                readme_src = os.path.join(output_dir, "README.md")
                if os.path.exists(readme_src):
                    with open(readme_src, "r", encoding="utf-8") as f:
                        readme_content = f.read()
                    with open(state["readme_file"], "w", encoding="utf-8") as f:
                        f.write(readme_content)
        except Exception as e:
            print(f"⚠️ Błąd podczas parsowania kodu: {e}")
            print("Treść odpowiedzi agenta:")
            print(content[:500])
        next_phase = "review"

    elif phase == "review":
        with open(state["review_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "docker"

    elif phase == "docker":
        os.makedirs(output_dir, exist_ok=True)
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                files_dict = json.loads(match.group(0))
                write_files_safely(files_dict, base_path=output_dir)

                docker_compose_path = os.path.join(output_dir, "docker", "docker-compose.yml")
                print(f"\n🐳 Uruchamiam Docker Compose z: {docker_compose_path}")

                if os.path.exists(docker_compose_path):
                    docker_dir = os.path.join(output_dir, "docker")
                    try:
                        result = subprocess.run(
                            ["docker-compose", "up", "-d", "--build"],
                            cwd=docker_dir,
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        print("✅ Docker uruchomiony pomyślnie!")
                        print(result.stdout)
                    except subprocess.CalledProcessError as e:
                        print("\n❌ BŁĄD DOCKER:")
                        print(e.stderr)
                else:
                    print(f"⚠️ Nie znaleziono docker-compose.yml w {docker_dir}")
        except Exception as e:
            print(f"⚠️ Błąd podczas fazy Docker: {e}")

        next_phase = "done"

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id is not None]

    return {
        "messages": delete_messages + [AIMessage(content=f"Zapisano fazę '{phase}'. Następna faza: {next_phase}.")],
        "current_phase": next_phase,
        "draft_content": ""
    }