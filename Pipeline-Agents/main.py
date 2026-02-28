import os
import json
import subprocess  
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import RemoveMessage

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_phase: str
    active_agent: str
    draft_content: str

    task_file: str
    arch_file: str
    tech_file: str
    code_file: str
    review_file: str
    docker_file: str

def supervisor_node(state: AgentState):
    """Zarządza rozmową i decyduje co dalej."""
    phase = state.get("current_phase", "task")
    prompt = f"""Role: You are a Lead Technical Project Manager (Supervisor) orchestrating a team of AI agents.
Context: We are building a software project through a multi-agent pipeline. The current active phase is: '{phase}'.
Task: Manage the conversation between the human user and the AI team. 
Constraints:
1. If the human asks a direct question, answer it concisely and politely.
2. If the human provides requirements or says "go ahead", instruct the agent responsible for the '{phase}' phase to generate a draft.
3. DO NOT generate project drafts, code, or architecture yourself. Your job is purely to manage communication and delegate.

Current Phase: {phase}."""
    sys_msg = SystemMessage(content=prompt)
    response = llm.invoke([sys_msg] + state["messages"])
    return {"messages": [response], "active_agent": phase}

def task_agent_node(state: AgentState):
    """1. Agent definiujący zadanie."""
    prompt = """Role: You are an Expert IT Business Analyst and Product Owner.
Task: Elicit requirements from the user and define a clear, actionable project specification.
Constraints:
1. Be highly assertive and realistic. 
2. Push back on overly ambitious, vague, or unrealistic requests. 
3. Propose a strict Minimum Viable Product (MVP). 
4. Do not include technical stack choices yet.

Output Format: You MUST format your response exactly using the following Markdown structure:
# Task Definition
## Business Goal
## Core Features
## Constraints & Limitations
"""
    sys_msg = SystemMessage(content=prompt)
    response = llm.invoke([sys_msg] + state["messages"])
    return {"draft_content": response.content}

def arch_agent_node(state: AgentState):
    """2. Agent architektury."""
    with open (state["task_file"], "r", encoding="utf-8") as f:
        task_context = f.read()

    prompt = f"""You are a Senior System Architect. Read the provided task definition and design a robust, scalable system architecture.

Output Format (Markdown):
# System Architecture
## Overview
## Frontend Components
## Backend Components
## Database Schema (High-level)

Task Context:
{task_context}
"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def tech_agent_node(state: AgentState):
    """3. Agent wyboru technologii."""
    with open(state["task_file"], "r", encoding="utf-8") as f:
        task_context = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f:
        arch_context = f.read()
    
    prompt = f"""You are a Lead Tech Stack Evaluator. Based on the task definition and system architecture, recommend the most suitable technology stack.

Output Format (Markdown):
# Technology Stack
## Frontend (Framework, Styling)
## Backend (Language, Framework)
## Database
## Other Tools

Task Context:
{task_context}

Architecture Context:
{arch_context}
"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def coder_agent_node(state: AgentState):
    """4. Agent programista (zwraca kod jako JSON)."""
    with open(state["task_file"], "r", encoding="utf-8") as f: task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f: arch_ctx = f.read()
    with open(state["tech_file"], "r", encoding="utf-8") as f: tech_ctx = f.read()

    prompt = f"""You are a Senior Software Engineer. Your task is to implement the application based on the provided requirements, architecture, and tech stack.
Break the code into appropriate files for frontend and backend. 

CRITICAL INSTRUCTION: You must return the output EXACTLY as a valid JSON object. Do not include Markdown blocks like ```json. 
The keys must be the file paths (e.g., "frontend/index.html", "backend/main.py") and the values must be the exact source code for that file.

Context for implementation:
Task:
{task_ctx}

Architecture:
{arch_ctx}

Tech Stack:
{tech_ctx}
"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def review_agent_node(state: AgentState):
    """5. Agent Code Review."""
    with open(state["arch_file"], "r", encoding="utf-8") as f: arch_ctx = f.read()
    prompt = f"""You are a Strict Code Auditor. Your task is to analyze the generated code for bugs, security vulnerabilities, and deviations from the architecture.

CRITICAL INSTRUCTION: You are an AUDITOR ONLY, not a developer. 
DO NOT write, rewrite, or provide corrected code snippets. 
DO NOT attempt to fix the code yourself. 

Output Format (Markdown):
# Code Review Report
## Discovered Bugs
## Security Concerns
## Architecture Deviations (vs: {arch_ctx})
## Summary & Recommendations
"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def docker_agent_node(state: AgentState):
    """6. Agent Docker (zwraca pliki konfiguracyjne jako JSON)."""
    prompt = """You are a DevOps Engineer. Your task is to containerize the provided application.
Create the necessary Dockerfiles for the frontend and backend, and a docker-compose.yml file to orchestrate them.

CRITICAL INSTRUCTION: Return the output EXACTLY as a valid JSON object. Do not include Markdown blocks like ```json.
The keys must be the file paths (e.g., "docker-compose.yml", "backend/Dockerfile") and the values must be the file contents.
"""
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}

def save_and_proceed_node(state: AgentState):
    """Zapisuje wyniki pracy agentów, odpala środowisko i czyści pamięć czatu."""
    phase = state["current_phase"]
    content = state["draft_content"]
    next_phase = "done"

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
                clean_content = match.group(0)
                files_dict = json.loads(clean_content)
                for filepath, file_content in files_dict.items():
                    dir_name = os.path.dirname(filepath)
                    if dir_name: os.makedirs(dir_name, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f: f.write(file_content)
        except json.JSONDecodeError:
            with open("code_error.txt", "w", encoding="utf-8") as f: f.write(content)
        next_phase = "review"
        
    elif phase == "review":
        with open(state["review_file"], "w", encoding="utf-8") as f: f.write(content)
        next_phase = "docker"
        
    elif phase == "docker":
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                clean_content = match.group(0)
                files_dict = json.loads(clean_content)
                
                for filepath, file_content in files_dict.items():
                    dir_name = os.path.dirname(filepath)
                    if dir_name: os.makedirs(dir_name, exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f: f.write(file_content)
                
                print("\nRozpoczynam automatyczne budowanie i uruchamianie Docker Compose...")
                if os.path.exists("docker-compose.yml"):
                    subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
                    print("✅ Środowisko uruchomione pomyślnie! Sprawdź http://localhost:3000")
                else:
                    print("⚠️ Brak pliku docker-compose.yml. Agent go nie wygenerował.")
            else:
                print("⚠️ Nie znaleziono żadnego kodu JSON w odpowiedzi agenta.")

        except json.JSONDecodeError:
            with open("docker_error.txt", "w", encoding="utf-8") as f: f.write(content)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Wystąpił błąd podczas próby uruchomienia Dockera: {e}")
            
        next_phase = "done"

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id is not None]

    return {
        "messages": delete_messages + [AIMessage(content=f"Zapisano dane dla fazy '{phase}'. Przechodzimy do fazy: {next_phase}.")],
        "current_phase": next_phase,
        "draft_content": "" 
    }


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
    if phase == "task": return "task_agent"
    elif phase == "arch": return "arch_agent"
    elif phase == "tech": return "tech_agent"
    elif phase == "code": return "coder_agent"
    elif phase == "review": return "review_agent"
    elif phase == "docker": return "docker_agent"
    elif phase == "done": return END
    return END

builder.add_conditional_edges(
    "supervisor", 
    route_from_supervisor,
    {
        "task_agent": "task_agent",
        "arch_agent": "arch_agent",
        "tech_agent": "tech_agent",
        "coder_agent": "coder_agent",
        "review_agent": "review_agent",
        "docker_agent": "docker_agent",
        END: END
    }
)

for agent in ["task_agent", "arch_agent", "tech_agent", "coder_agent", "review_agent", "docker_agent"]:
    builder.add_edge(agent, "human_review")


def route_after_human(state: AgentState):
    last_msg = state["messages"][-1].content.strip().lower()
    if "ok" in last_msg or "akceptuj" in last_msg:
        return "save_and_proceed_node"
    else:
        return "supervisor"
    
builder.add_conditional_edges(
    "human_review", 
    route_after_human,
    {
        "save_and_proceed_node": "save_and_proceed_node",
        "supervisor": "supervisor"
    }
)

builder.add_edge("save_and_proceed_node", "supervisor")

# memory = MemorySaver()

graph = builder.compile(
    # checkpointer=memory,
    interrupt_before=["human_review"] 
)


# if __name__ == "__main__":
#     for file in ["task_definition.md", "architecture.md", "technologies.md", "code_review.md"]:
#         if not os.path.exists(file):
#             with open(file, "w", encoding="utf-8") as f: f.write("")

#     config = {"configurable": {"thread_id": "1"}}
#     initial_state = {
#         "messages": [HumanMessage(content="Chcę stworzyć prosty Landing Page z 2–3 sekcjami.")],
#         "current_phase": "task",
#         "task_file": "task_definition.md",
#         "arch_file": "architecture.md",
#         "tech_file": "technologies.md",
#         "review_file": "code_review.md",
#         "docker_file": "docker-compose.yml"
#     }
    
#     print("Uruchamiam system w terminalu...")
#     for event in graph.stream(initial_state, config, stream_mode="values"):
#         if "draft_content" in event and event["draft_content"]:
#             print("\n--- SZKIC OD AGENTA ---")
#             print(event["draft_content"])
            
#     while True:
#         state = graph.get_state(config)
#         if not state.next:
#             print("\n🎉 Projekt zakończony! Twoja strona powinna być już gotowa.")
#             break
            
#         user_input = input("\n[Akcja] Twoja opinia ('ok' by zapisać plik, lub wpisz uwagi dla agenta): ")
#         graph.update_state(config, {"messages": [HumanMessage(content=user_input)]}, as_node="human_review")
        
#         for event in graph.stream(None, config, stream_mode="values"):
#             if "draft_content" in event and event["draft_content"]:
#                 print("\n--- NOWY SZKIC ---")
#                 print(event["draft_content"])