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
    docker_agent_node, save_and_proceed_node,
    load_project_node, phase_selector_node
)

load_dotenv()

builder = StateGraph(AgentState)

builder.add_node("load_project", load_project_node)
builder.add_node("phase_selector", phase_selector_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("task_agent", task_agent_node)
builder.add_node("arch_agent", arch_agent_node)
builder.add_node("tech_agent", tech_agent_node)
builder.add_node("coder_agent", coder_agent_node)
builder.add_node("review_agent", review_agent_node)
builder.add_node("docker_agent", docker_agent_node)
builder.add_node("save_and_proceed_node", save_and_proceed_node)
builder.add_node("human_review", lambda x: x)

builder.add_edge(START, "load_project")
builder.add_edge("load_project", "phase_selector")
builder.add_edge("phase_selector", "supervisor")

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
builder.add_edge("save_and_proceed_node", "ask_continue")

builder.add_node("ask_continue", lambda x: x)


def route_exit_or_continue(state: AgentState):
    last_msg = state["messages"][-1].content.strip().lower()
    if last_msg in ("e", "w", "q", "exit", "wyjść", "wyjsc", "quit", "koniec"):
        return END
    return "supervisor"


builder.add_conditional_edges("ask_continue", route_exit_or_continue, [END, "supervisor"])

memory = MemorySaver()

graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["human_review", "ask_continue"],
)

if __name__ == "__main__":
    import json

    os.makedirs("docs", exist_ok=True)

    print("\n=== AI Pipeline Agentów ===")
    output_dir_default = "../Culinary-App"
    output_dir_input = input(f"Katalog projektu [{output_dir_default}]: ").strip() or output_dir_default
    output_dir = os.path.normpath(output_dir_input)

    project_name = os.path.basename(os.path.abspath(output_dir))
    state_file = os.path.join(output_dir, "pipeline_state.json")
    all_phases = ["task", "arch", "tech", "code", "review", "docker"]
    phases_done = []
    last_phase = None

    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            phases_done = saved.get("phases_done", [])
            last_phase = saved.get("last_completed_phase")
            print(f"\n✅ Znaleziono projekt: {project_name}")
            print(f"   Ukończone fazy: {', '.join(phases_done) if phases_done else 'brak'}")
            print(f"   Ostatnia faza: {last_phase or '-'}")
        except Exception:
            pass

    if not phases_done and os.path.isdir(output_dir) and any(os.scandir(output_dir)):
        print(f"\n✅ Znaleziono projekt: {project_name}")
        print("   Brak pipeline_state.json — brak zapisanej historii faz (dostępne wszystkie fazy)")

    print("\nWybierz agenta:")
    print("  1. task_agent   - Specyfikacja wymagań")
    print("  2. arch_agent   - Architektura systemu")
    print("  3. tech_agent   - Stack technologiczny")
    print("  4. coder_agent  - Generowanie kodu")
    print("  5. review_agent - Code Review (z linterami)")
    print("  6. docker_agent - Konteneryzacja")
    print("  7. Uruchom wszystkie brakujące fazy")
    print("  0. Wyjście")

    choice = input("\nWybór [7]: ").strip() or "7"

    phase_map = {"1": "task", "2": "arch", "3": "tech", "4": "code", "5": "review", "6": "docker"}

    if choice == "0":
        print("Do widzenia.")
        exit(0)

    if choice == "7":
        phases_to_run = [p for p in all_phases if p not in phases_done]
        if not phases_to_run:
            print("Wszystkie fazy ukończone.")
            exit(0)
    elif choice in phase_map:
        phases_to_run = [phase_map[choice]]
    else:
        print("Nieprawidłowy wybór.")
        exit(1)

    print(
        "\nOpcjonalnie — wskazówki do tego uruchomienia (np. co zmienić w istniejącym kodzie, "
        "czego pilnować). Używane w zapytaniu RAG i w prompcie coder_agent. Enter = pomiń."
    )
    user_project_guidance = input("> ").strip()

    current_phase = phases_to_run[0]
    initial_state = {
        "messages": [HumanMessage(content="Kontynuuj pracę nad projektem.")],
        "current_phase": current_phase,
        "mode": "create",
        "existing_project_files": {},
        "phases_to_run": phases_to_run,
        "task_file": "docs/task_definition.md",
        "arch_file": "docs/architecture.md",
        "tech_file": "docs/technologies.md",
        "review_file": "docs/code_review.md",
        "readme_file": "docs/README.md",
        "output_dir": output_dir,
        "user_project_guidance": user_project_guidance,
    }

    config = {"configurable": {"thread_id": "pipeline-session"}}

    print(f"\n🚀 Uruchamiam pipeline — fazy: {phases_to_run}")

    for event in graph.stream(initial_state, config, stream_mode="values"):
        if "draft_content" in event and event["draft_content"]:
            print("\n" + "=" * 50)
            print(f"📄 SZKIC OD AGENTA ({event.get('active_agent', 'unknown')}):")
            print(event["draft_content"])
            print("=" * 50)

    while True:
        state = graph.get_state(config)
        if state.next:
            next_nodes = [n[0] if isinstance(n, tuple) else n for n in state.next]
            if "ask_continue" in next_nodes:
                user_input = input(
                    "\n✅ Faza zapisana. Wyjść (e) czy kontynuować z kolejnymi agentami (c)? [c]: "
                ).strip().lower() or "c"
                graph.update_state(config, {"messages": [HumanMessage(content=user_input)]}, as_node="ask_continue")
            else:
                user_input = input(
                    "\n[AKCJA] 'ok' / 'akceptuj' aby zapisać i przejść dalej, "
                    "lub wpisz konkretne uwagi (co poprawić w szkicu / kodzie): "
                )
                graph.update_state(config, {"messages": [HumanMessage(content=user_input)]}, as_node="human_review")

            for event in graph.stream(None, config, stream_mode="values"):
                if "draft_content" in event and event["draft_content"]:
                    print("\n--- NOWY SZKIC ---")
                    print(event["draft_content"])
        else:
            print("\n🎉 Pipeline zakończony!")
            print(f"📁 Kod zapisany w: {output_dir}")
            break