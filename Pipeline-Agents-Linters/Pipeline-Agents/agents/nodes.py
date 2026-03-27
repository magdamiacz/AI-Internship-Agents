# agents/nodes.py
import os
import sys
import json
import re
import subprocess
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, RemoveMessage
from agents.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0)

ALL_PHASES = ["task", "arch", "tech", "code", "review", "docker"]


def _update_pipeline_state(output_dir: str, phase: str):
    """Aktualizuje pipeline_state.json w katalogu projektu."""
    from datetime import date

    state_file = os.path.join(output_dir, "pipeline_state.json")
    project_name = os.path.basename(os.path.abspath(output_dir))

    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            saved = {}
    else:
        saved = {"created_at": str(date.today())}

    saved["project_name"] = project_name
    saved["output_dir"] = output_dir
    saved["last_completed_phase"] = phase
    phases_done = list(set(saved.get("phases_done", []) + [phase]))
    saved["phases_done"] = sorted(phases_done, key=lambda p: ALL_PHASES.index(p) if p in ALL_PHASES else 999)

    os.makedirs(output_dir, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)


def load_project_node(state: AgentState):
    output_dir = state.get("output_dir", "../Culinary-App")

    project_exists = os.path.isdir(output_dir) and any(os.scandir(output_dir))

# Sprawdza czy katalog istnieje i nie jest pusty (ma pliki lub podkatalogi) — to oznacza istniejący projekt do modyfikacji. Jeśli katalog nie istnieje lub jest pusty, to traktujemy to jako nowy projekt do stworzenia.
    if not project_exists:
        print(f"\n[load_project] Projekt nie istnieje w '{output_dir}'. Tryb: CREATE.")
        return {
            "mode": "create",
            "existing_project_files": {},
            "phases_to_run": ALL_PHASES,
        }

    print(f"\n[load_project] Znaleziono istniejący projekt w '{output_dir}'. Tryb: MODIFY.")
    existing_files = {}
    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in ["images", "__pycache__", ".git", ".venv", ".ruff_cache"]]
        for filename in files:
            if filename.endswith((".db", ".png", ".jpg", ".pyc")) or filename == "pipeline_state.json":
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, output_dir).replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_files[rel_path] = f.read()
            except Exception:
                pass

    print(f"[load_project] Wczytano {len(existing_files)} plików: {list(existing_files.keys())}")

    # Użyj faz wstępnie wybranych z CLI (jeśli podane)
    pre_set_phases = state.get("phases_to_run", [])
    if pre_set_phases and all(p in ALL_PHASES for p in pre_set_phases):
        phases = pre_set_phases
        print(f"[load_project] Używam wstępnie wybranych faz: {phases}")
    else:
        print("\nDostępne fazy: task, arch, tech, code, review, docker")
        user_input = input("Od której fazy zacząć? (np. 'code' lub 'code,review,docker', Enter = wszystkie): ").strip().lower()

        if not user_input:
            phases = ALL_PHASES
        else:
            requested = [p.strip() for p in user_input.split(",")]
            start_phase = requested[0] if requested[0] in ALL_PHASES else "task"
            start_idx = ALL_PHASES.index(start_phase)
            phases = ALL_PHASES[start_idx:]

        print(f"[load_project] Fazy do uruchomienia: {phases}")

    return {
        "mode": "modify",
        "existing_project_files": existing_files,
        "phases_to_run": phases,
        "current_phase": phases[0],
    }


def phase_selector_node(state: AgentState):
    mode = state.get("mode", "create")
    if mode == "modify":
        phases = state.get("phases_to_run", ["task"])
        first_phase = phases[0] if phases else "task"
        print(f"\n[phase_selector] Tryb MODIFY — startuję od fazy: '{first_phase}'")
        return {"current_phase": first_phase}
    return {}


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
    with open(state["arch_file"], "r", encoding="utf-8") as f:
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

    mode = state.get("mode", "create")
    existing_files = state.get("existing_project_files", {})

    if mode == "modify" and existing_files:
        existing_files_str = "\n\n".join(
            f"=== {path} ===\n{content}"
            for path, content in existing_files.items()
        )
        prompt = f"""You are a Senior Software Engineer performing a targeted modification of an existing application.

STRICT OUTPUT RULES:
1. Return ONLY a valid JSON object. No markdown, no ```json blocks, no explanation text outside JSON.
2. JSON keys are relative file paths (e.g. "backend/main.py"). Values are COMPLETE file contents as strings.
3. Include ONLY files that need to change. Do NOT include unchanged files.
4. Every file you include MUST contain the complete, runnable content — not diffs, not partial snippets.
5. Escape all special characters properly inside JSON strings (newlines as \\n, quotes as \\").

CHANGE SUMMARY (what to implement):
The task docs and architecture docs describe the required changes. Read them carefully and implement ALL described features.
Key areas to focus on based on architecture:
- Authentication system (register/login endpoints, JWT tokens, bcrypt password hashing)
- User model in database with hashed_password field
- Protected endpoints requiring valid JWT
- Recipe isolation per user (user_id foreign key, filter queries)
- Frontend auth UI (login/register forms, JWT in localStorage, logout)

EXISTING PROJECT FILES (read carefully before making changes):
{existing_files_str}

MODIFICATION INSTRUCTIONS:
1. Read ALL existing files above to understand the current codebase.
2. Identify every file that must change to implement the features described in Task/Arch/Tech docs.
3. For each file that changes: return the COMPLETE new version of that file.
4. Preserve all existing functionality (chat, recipe generation, image generation).
5. Add new functionality WITHOUT breaking existing features.
6. Fix any linter issues (sorted imports, remove unused imports, newline at EOF).

TECHNICAL REQUIREMENTS FOR AUTH:
- backend/database.py: Add User model (id, email unique, hashed_password, created_at). Add user_id FK to Recipe. Add get_user_by_email(), create_user() helpers.
- backend/main.py: Add POST /register (hash with bcrypt, return JWT), POST /login (verify, return JWT). Add get_current_user() dependency using python-jose. Protect /chat and /recipes with Depends(get_current_user). Pass user_id to agent.
- backend/agent.py: Accept user_id param in run_agent(). Pass user_id to save_recipe().
- backend/requirements.txt: Add python-jose[cryptography], passlib[bcrypt], python-multipart.
- frontend/index.html: Add login/register forms shown before chat. Store JWT in localStorage. Send Authorization: Bearer <token> header on /chat requests. Show logout button. After logout, return to login screen.
- README.md: Update setup instructions to include JWT_SECRET env variable.

Task:\n{task_ctx}\nArch:\n{arch_ctx}\nTech:\n{tech_ctx}"""
    else:
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

    # Sprawdź czy ostatnia wiadomość to feedback od użytkownika (nie systemowa)
    messages = state["messages"]
    last_human_feedback = ""
    if messages:
        last_msg = messages[-1]
        content = last_msg.content.strip().lower() if hasattr(last_msg, "content") else ""
        # Jeśli to nie jest akceptacja i nie jest wiadomością startową — to feedback
        is_acceptance = "ok" in content or "akceptuj" in content
        is_start_msg = "kontynuuj" in content or "pracę" in content
        if not is_acceptance and not is_start_msg and len(content) > 5:
            last_human_feedback = messages[-1].content

    if last_human_feedback:
        prompt += f"\n\nUWAGA - FEEDBACK OD UŻYTKOWNIKA DO POPRAWIENIA:\n{last_human_feedback}\n\nMUSISZ uwzględnić powyższy feedback. Zwróć JSON ze wszystkimi plikami które wymagają zmiany."

    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def run_linters(output_dir: str) -> str:
    """Uruchamia lintery (ruff dla Pythona, htmlhint dla HTML) i zwraca wyniki jako tekst."""
    results = []

    # Python (ruff)
    backend_path = os.path.join(output_dir, "backend")
    if os.path.isdir(backend_path):
        try:
            r = subprocess.run(
                ["ruff", "check", backend_path, "--output-format=concise"],
                capture_output=True,
                text=True,
            )
            out = (r.stdout or r.stderr or "").strip()
            results.append(f"### Python (ruff)\n{out if out else 'Brak błędów.'}")
        except FileNotFoundError:
            results.append("### Python (ruff)\nRuff nie jest zainstalowany (pip install ruff).")
        except Exception as e:
            results.append(f"### Python (ruff)\nBłąd: {e}")

    # HTML (htmlhint)
    html_path = os.path.join(output_dir, "frontend", "index.html")
    if os.path.exists(html_path):
        try:
            if sys.platform == "win32":
                r = subprocess.run(
                    f'npx --yes htmlhint "{html_path}"',
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True,
                )
            else:
                r = subprocess.run(
                    ["npx", "--yes", "htmlhint", html_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            out = (r.stdout or r.stderr or "").strip()
            results.append(f"### HTML (htmlhint)\n{out if out else 'Brak błędów.'}")
        except FileNotFoundError:
            results.append("### HTML (htmlhint)\nNode.js/npx nie jest dostępne.")
        except subprocess.TimeoutExpired:
            results.append("### HTML (htmlhint)\nPrzekroczono limit czasu.")
        except Exception as e:
            results.append(f"### HTML (htmlhint)\nBłąd: {e}")

    return "\n\n".join(results) if results else "Brak plików do sprawdzenia."


def review_agent_node(state: AgentState):
    readme_path = state.get("readme_file", "docs/README.md")
    output_dir = state.get("output_dir", "../Culinary-App")

    # Wczytaj README
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_ctx = f.read()
    else:
        fallback_readme = os.path.join(output_dir, "README.md")
        readme_ctx = open(fallback_readme, "r", encoding="utf-8").read() if os.path.exists(fallback_readme) else ""

    # Wczytaj kod projektu do analizy (ograniczony rozmiar)
    project_code_ctx = ""
    code_files_to_review = []
    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in ["images", "__pycache__", ".git", ".venv", ".ruff_cache"]]
        for filename in files:
            if filename.endswith((".py", ".html")):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, output_dir).replace("\\", "/")
                code_files_to_review.append((rel_path, full_path))

    for rel_path, full_path in code_files_to_review[:8]:  # Limit do 8 plików
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            project_code_ctx += f"\n\n=== {rel_path} ===\n{content[:3000]}"  # Limit per file
        except Exception:
            pass

    linter_output = run_linters(output_dir)

    prompt = f"""You are a Strict Code Auditor.
Analyze the generated project code and structure carefully.

README CONTEXT:
{readme_ctx}

PROJECT CODE (key files):
{project_code_ctx}

## Linter results (to the event in case - add section "Errors from linters" in case of occurrence)
{linter_output}

Output Format (Markdown):
# Code Review Report
## Błędy z linterów
(In this section, put the results from linters - ruff, htmlhint - if there are errors to fix)
## Bugs & Security Issues
## Missing Features vs Requirements
## Recommendations"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def docker_agent_node(state: AgentState):
    readme_path = state.get("readme_file", "docs/README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_ctx = f.read()
    else:
        readme_ctx = ""

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
7. Backend needs OPENAI_API_KEY and JWT_SECRET env variables (read from .env file).
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

    mode = state.get("mode", "create")

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

                new_content = str(value)

                if mode == "modify" and os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        existing_content = f.read()
                    if existing_content == new_content:
                        print(f"  [skip] {key} — bez zmian")
                        continue
                    print(f"  [update] {key}")
                else:
                    print(f"  [write] {key}")

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

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
        os.makedirs(output_dir, exist_ok=True)
        try:
            # Próba parsowania JSON — obsługa odpowiedzi z markdown blokami
            cleaned = content.strip()
            # Usuń potencjalne ```json ``` bloki
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

            match = re.search(r'\{[\s\S]*\}', cleaned)
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
            else:
                print("⚠️ Nie znaleziono JSON w odpowiedzi agenta. Treść (pierwsze 1000 znaków):")
                print(content[:1000])
        except json.JSONDecodeError as e:
            print(f"⚠️ Błąd parsowania JSON: {e}")
            print("Treść odpowiedzi agenta (pierwsze 1000 znaków):")
            print(content[:1000])
        except Exception as e:
            print(f"⚠️ Błąd podczas zapisywania kodu: {e}")
        next_phase = "review"

    elif phase == "review":
        with open(state["review_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "docker"

    elif phase == "docker":
        os.makedirs(output_dir, exist_ok=True)
        try:
            cleaned = content.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

            match = re.search(r'\{[\s\S]*\}', cleaned)
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
                            text=True,
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

    # Aktualizuj pipeline_state.json w katalogu projektu
    if phase in ALL_PHASES:
        _update_pipeline_state(output_dir, phase)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id is not None]

    return {
        "messages": delete_messages + [AIMessage(content=f"Zapisano fazę '{phase}'. Następna faza: {next_phase}.")],
        "current_phase": next_phase,
        "draft_content": "",
    }