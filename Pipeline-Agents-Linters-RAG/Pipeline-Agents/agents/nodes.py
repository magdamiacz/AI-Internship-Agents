"""
agents/nodes.py — cienki moduł re-eksportujący wszystkie węzły grafu.
Faktyczna logika leży w podmodułach:
  - agents/prompts/   — teksty promptów
  - agents/helpers/   — pipeline_state, project_fs, json_from_llm, file_write, review_context
  - agents/linters/   — ruff_runner, htmlhint_runner, run_all
"""

import os
import subprocess

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, RemoveMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.helpers.file_write import write_files_safely
from agents.helpers.json_from_llm import parse_json_from_llm
from agents.helpers.pipeline_state import ALL_PHASES, update_pipeline_state
from agents.helpers.project_fs import load_existing_project_files
from agents.helpers.review_context import build_review_code_context, load_readme_context
from agents.linters.run_all import run_all_linters
from agents.rag.project_rag import build_rag_context_for_modify
from agents.prompts.arch import build_arch_prompt
from agents.prompts.coder import (
    FEEDBACK_SUFFIX,
    build_coder_prompt_create,
    build_coder_prompt_modify,
)
from agents.prompts.docker import build_docker_prompt
from agents.prompts.review import build_review_prompt
from agents.prompts.supervisor import build_supervisor_prompt
from agents.prompts.task import build_task_prompt
from agents.prompts.tech import build_tech_prompt
from agents.state import AgentState

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0)


# ── Węzły infrastrukturalne ────────────────────────────────────────────────────

def load_project_node(state: AgentState):
    output_dir = state.get("output_dir", "../Culinary-App")
    project_exists = os.path.isdir(output_dir) and any(os.scandir(output_dir))

    if not project_exists:
        print(f"\n[load_project] Projekt nie istnieje w '{output_dir}'. Tryb: CREATE.")
        return {
            "mode": "create",
            "existing_project_files": {},
            "phases_to_run": ALL_PHASES,
        }

    print(f"\n[load_project] Znaleziono istniejący projekt w '{output_dir}'. Tryb: MODIFY.")
    existing_files = load_existing_project_files(output_dir)
    print(f"[load_project] Wczytano {len(existing_files)} plików: {list(existing_files.keys())}")

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


# ── Węzły agentów ──────────────────────────────────────────────────────────────

def supervisor_node(state: AgentState):
    phase = state.get("current_phase", "task")
    prompt = build_supervisor_prompt(phase)
    last_message = state["messages"][-1] if state["messages"] else ""
    response = llm.invoke([SystemMessage(content=prompt), last_message])
    return {"messages": [response], "active_agent": phase}


def task_agent_node(state: AgentState):
    prompt = build_task_prompt()
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def arch_agent_node(state: AgentState):
    with open(state["arch_file"], "r", encoding="utf-8") as f:
        task_ctx = f.read()
    prompt = build_arch_prompt(task_ctx)
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def tech_agent_node(state: AgentState):
    with open(state["task_file"], "r", encoding="utf-8") as f:
        task_ctx = f.read()
    with open(state["arch_file"], "r", encoding="utf-8") as f:
        arch_ctx = f.read()
    prompt = build_tech_prompt(task_ctx, arch_ctx)
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
    user_guidance = (state.get("user_project_guidance") or "").strip()
    output_dir = state.get("output_dir", "../Culinary-App")

    if mode == "modify" and existing_files:
        rag_query_parts = [user_guidance, task_ctx[:4000], arch_ctx[:3000], tech_ctx[:2000]]
        rag_query = "\n\n".join(p for p in rag_query_parts if p)
        print("\n[coder] Budowanie kontekstu RAG (indeks + similarity_search)...")
        rag_block, full_files_block = build_rag_context_for_modify(
            output_dir, rag_query, existing_files
        )
        if rag_block:
            print("[coder] Użyto semantycznego retrievalu (OpenAI embeddings).")
        else:
            print(
                "[coder] RAG niedostępny (brak OPENAI_API_KEY lub indeksu) — pełny kontekst plików jak wcześniej."
            )
        prompt = build_coder_prompt_modify(
            task_ctx,
            arch_ctx,
            tech_ctx,
            rag_block,
            full_files_block,
            user_guidance=user_guidance,
        )
    else:
        prompt = build_coder_prompt_create(
            task_ctx, arch_ctx, tech_ctx, user_guidance=user_guidance
        )

    # Dołącz feedback użytkownika, jeśli nie jest akceptacją
    messages = state["messages"]
    if messages:
        last_msg = messages[-1]
        content = last_msg.content.strip().lower() if hasattr(last_msg, "content") else ""
        is_acceptance = "ok" in content or "akceptuj" in content
        is_start_msg = "kontynuuj" in content or "pracę" in content
        if not is_acceptance and not is_start_msg and len(content) > 5:
            prompt += FEEDBACK_SUFFIX.format(feedback=messages[-1].content)

    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def review_agent_node(state: AgentState):
    readme_path = state.get("readme_file", "docs/README.md")
    output_dir = state.get("output_dir", "../Culinary-App")

    readme_ctx = load_readme_context(readme_path, output_dir)
    project_code_ctx = build_review_code_context(output_dir)
    linter_output = run_all_linters(output_dir)

    prompt = build_review_prompt(readme_ctx, project_code_ctx, linter_output)
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


def docker_agent_node(state: AgentState):
    readme_path = state.get("readme_file", "docs/README.md")
    output_dir = state.get("output_dir", "../Culinary-App")
    readme_ctx = load_readme_context(readme_path, output_dir)
    prompt = build_docker_prompt(readme_ctx)
    response = llm.invoke([SystemMessage(content=prompt)] + state["messages"])
    return {"draft_content": response.content}


# ── Węzeł zapisu ──────────────────────────────────────────────────────────────

def save_and_proceed_node(state: AgentState):
    phase = state["current_phase"]
    content = state["draft_content"]
    next_phase = "done"

    os.makedirs("docs", exist_ok=True)
    output_dir = state.get("output_dir", "../Culinary-App")
    mode = state.get("mode", "create")

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
        files_dict = parse_json_from_llm(content)
        if files_dict:
            write_files_safely(files_dict, base_path=output_dir, mode=mode)
            print(f"\n✅ Kod zapisany do: {output_dir}")
            # Kopiuj README do docs/ dla review_agent
            readme_src = os.path.join(output_dir, "README.md")
            if os.path.exists(readme_src):
                with open(readme_src, "r", encoding="utf-8") as f:
                    readme_content = f.read()
                with open(state["readme_file"], "w", encoding="utf-8") as f:
                    f.write(readme_content)
        else:
            print("⚠️ Nie znaleziono JSON w odpowiedzi agenta. Treść (pierwsze 1000 znaków):")
            print(content[:1000])
        next_phase = "review"

    elif phase == "review":
        with open(state["review_file"], "w", encoding="utf-8") as f:
            f.write(content)
        next_phase = "docker"

    elif phase == "docker":
        os.makedirs(output_dir, exist_ok=True)
        files_dict = parse_json_from_llm(content)
        if files_dict:
            write_files_safely(files_dict, base_path=output_dir, mode=mode)
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
        else:
            print("⚠️ Nie znaleziono JSON w odpowiedzi agenta.")
        next_phase = "done"

    if phase in ALL_PHASES:
        update_pipeline_state(output_dir, phase)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"] if m.id is not None]

    return {
        "messages": delete_messages + [AIMessage(content=f"Zapisano fazę '{phase}'. Następna faza: {next_phase}.")],
        "current_phase": next_phase,
        "draft_content": "",
    }
