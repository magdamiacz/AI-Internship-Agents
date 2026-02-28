# main.py
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
import os
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Importy z naszego nowego modułu
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
    if "ok" in last_msg or "akceptuj" in last_msg: return "save_and_proceed_node"
    return "supervisor"
    
builder.add_conditional_edges("human_review", route_after_human, ["save_and_proceed_node", "supervisor"])
builder.add_edge("save_and_proceed_node", "supervisor")

memory = MemorySaver() 

graph = builder.compile(
    checkpointer=memory, 
    interrupt_before=["human_review"] 
)

if __name__ == "__main__":
    # Inicjalizacja pustych plików w folderze docs/, jeśli nie istnieją
    os.makedirs("docs", exist_ok=True)
    
    config = {"configurable": {"thread_id": "1"}}
    initial_state = {
        "messages": [HumanMessage(content="Chcę stworzyć prosty Landing Page z 2–3 sekcjami.")],
        "current_phase": "task",
        "task_file": "docs/task_definition.md",
        "arch_file": "docs/architecture.md",
        "tech_file": "docs/technologies.md",
        "review_file": "docs/code_review.md",
        "readme_file": "README.md"
    }
    
    print("🚀 Uruchamiam system agentowy w terminalu...")
    
    # Pętla obsługująca logikę grafu
    for event in graph.stream(initial_state, config, stream_mode="values"):
        if "draft_content" in event and event["draft_content"]:
            print("\n" + "="*30)
            print(f"📄 SZKIC OD AGENTA ({event.get('active_agent', 'unknown')}):")
            print(event["draft_content"])
            print("="*30)
            
    while True:
        state = graph.get_state(config)
        # Jeśli graf zatrzymał się na punkcie przerwania (human_review)
        if state.next:
            user_input = input("\n[AKCJA] Wpisz 'ok' aby zapisać, lub podaj uwagi dla agenta: ")
            
            # Aktualizacja stanu o wiadomość użytkownika
            graph.update_state(config, {"messages": [HumanMessage(content=user_input)]}, as_node="human_review")
            
            # Kontynuacja strumieniowania po aktualizacji
            for event in graph.stream(None, config, stream_mode="values"):
                if "draft_content" in event and event["draft_content"]:
                    print("\n--- NOWY SZKIC ---")
                    print(event["draft_content"])
        else:
            print("\n🎉 Projekt zakończony pomyślnie!")
            break