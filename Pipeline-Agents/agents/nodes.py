# agents/nodes.py
import os
import json
import re
import subprocess
from dotenv import load_dotenv

# Wczytujemy zmienne środowiskowe PRZED importem OpenAI
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, RemoveMessage
from agents.state import AgentState

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def supervisor_node(state: AgentState):
    """Zarządza rozmową i decyduje co dalej - poprawiona logika faz."""
    phase = state.get("current_phase", "task")
    
    # Tworzymy bardzo restrykcyjny prompt, który ignoruje stare prośby w historii
    prompt = f"""You are a Lead Technical Project Manager. 
We are currently in the '{phase}' phase of the project.

CRITICAL INSTRUCTIONS:
1. Your ONLY task is to delegate work to the agent responsible for the CURRENT PHASE: '{phase}'.
2. Even if you see initial requirements in the chat history, DO NOT restart the process.
3. If the last message from the system was about saving data, simply call the agent for '{phase}'.
4. DO NOT ask the user for new requirements.

Current Phase to execute: {phase}."""

    sys_msg = SystemMessage(content=prompt)
    
    # Przekazujemy tylko system prompt i OSTATNIĄ wiadomość, 
    # aby uniknąć czytania całej historii od początku
    last_message = state["messages"][-1] if state["messages"] else ""
    response = llm.invoke([sys_msg, last_message])
    
    return {"messages": [response], "active_agent": phase}

def task_agent_node(state: AgentState):
    prompt = """Role: You are an Expert IT Business Analyst.
Task: Define a clear project specification (MVP).
Output Format (Markdown):
# Task Definition
## Business Goal
## Core Features
## Constraints"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def arch_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f: task_ctx = f.read()
    prompt = f"""You are a Senior System Architect. Design architecture based on requirements.
Task Context:\n{task_ctx}"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def tech_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f: task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f: arch_ctx = f.read()
    prompt = f"""You are a Lead Tech Stack Evaluator. Recommend tech stack.
Task:\n{task_ctx}\nArch:\n{arch_ctx}"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def coder_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f: task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f: arch_ctx = f.read()
    with open(state["tech_file"], "r", encoding="utf-8") as f: tech_ctx = f.read()

    prompt = f"""You are a Senior Software Engineer. Implement the application based on the requirements.

CRITICAL FOLDER STRUCTURE INSTRUCTIONS:
1. You MUST separate the code into two directories: 'frontend' and 'backend'.
2. Every file path (JSON key) for the user interface MUST start with 'frontend/' (e.g., 'frontend/index.html', 'frontend/app.js').
3. Every file path (JSON key) for the server/API MUST start with 'backend/' (e.g., 'backend/main.py', 'backend/requirements.txt').
4. You MUST return the output EXACTLY as a valid JSON object. Do not include Markdown blocks like ```json.
5. You MUST also generate a 'README.md' file at the root level (key: 'README.md') explaining the project.

Task:\n{task_ctx}\nArch:\n{arch_ctx}\nTech:\n{tech_ctx}"""
    
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def review_agent_node(state: AgentState):
    with open(state["readme_file"], "r", encoding="utf-8") as f: readme_ctx = f.read()
    prompt = f"""You are a Strict Code Auditor. 
Analyze the generated code structure. Base your knowledge on the generated README.md file:
README CONTEXT:\n{readme_ctx}

Output Format (Markdown):
# Code Review Report
## Bugs & Security
## Deviations from README"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def docker_agent_node(state: AgentState):
    with open(state["readme_file"], "r", encoding="utf-8") as f: readme_ctx = f.read()
    
    prompt = f"""You are a DevOps Engineer. Containerize the application.
Base your Docker setup on the generated README.md file:
README CONTEXT:\n{readme_ctx}

CRITICAL INSTRUCTIONS:
1. All Docker-related files MUST be placed in a dedicated 'docker' directory.
2. Create a Dockerfile for the frontend (key: 'docker/frontend.Dockerfile').
3. Create a Dockerfile for the backend (key: 'docker/backend.Dockerfile').
4. Create a docker-compose.yml (key: 'docker/docker-compose.yml').
5. DO NOT include the 'version' attribute in docker-compose.yml (it is obsolete).
6. CRITICAL CONTEXT RULE: In docker-compose.yml, your build contexts MUST point to the parent directories:
   context: ../frontend
   dockerfile: ../docker/frontend.Dockerfile
7. CRITICAL COPY RULE: Because the context is already set to '../frontend' or '../backend', inside your Dockerfiles you MUST NOT use 'COPY ./frontend /app'. You MUST use 'COPY . /app' (or 'COPY package.json .' etc) because the build context root is already the component's directory!
8. Return the output EXACTLY as a valid JSON object. Do not include Markdown blocks like ```json."""
    
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def save_and_proceed_node(state: AgentState):
    phase = state["current_phase"]
    content = state["draft_content"]
    next_phase = "done"

    # Upewniamy się, że folder docs/ istnieje
    os.makedirs("docs", exist_ok=True)

    # 🛡️ UNIWERSALNA FUNKCJA ZAPISUJĄCA
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
        with open(state["task_file"], "w", encoding="utf-8") as f: f.write(content)
        next_phase = "arch"
        
    elif phase == "arch":
        with open(state["arch_file"], "w", encoding="utf-8") as f: f.write(content)
        next_phase = "tech"
        
    elif phase == "tech":
        with open(state["tech_file"], "w", encoding="utf-8") as f: f.write(content)
        next_phase = "code"
        
    elif phase == "code":
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                files_dict = json.loads(match.group(0))
                write_files_safely(files_dict)
        except Exception as e:
            print(f"⚠️ Błąd podczas parsowania kodu: {e}")
        next_phase = "review"
        
    elif phase == "review":
        with open(state["review_file"], "w", encoding="utf-8") as f: f.write(content)
        next_phase = "docker"
        
    elif phase == "docker":
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                files_dict = json.loads(match.group(0))
                write_files_safely(files_dict)
                
                print("\n🐳 Uruchamiam Docker Compose z folderu docker/...")
                if os.path.exists("docker/docker-compose.yml"):
                    try:
                        result = subprocess.run(
                            ["docker-compose", "up", "-d", "--build"], 
                            cwd="docker", 
                            check=True,
                            capture_output=True,  
                            text=True             
                        )
                        print("✅ Środowisko uruchomione pomyślnie!")
                        print(result.stdout)
                    except subprocess.CalledProcessError as e:
                        print("\n❌ DOCKER ZGŁOSIŁ BŁĄD BUDOWANIA (SZCZEGÓŁY):")
                        print(e.stderr)
                else:
                    print("⚠️ Plik docker-compose.yml nie został wygenerowany w folderze docker/.")
        except Exception as e:
            print(f"⚠️ Błąd podczas fazy Docker: {e}")
            
        next_phase = "done"

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id is not None]
    
    return {
        "messages": delete_messages + [AIMessage(content=f"Zapisano fazę '{phase}'. Następna faza: {next_phase}.")],
        "current_phase": next_phase,
        "draft_content": "" 
    }