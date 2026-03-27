# agents/state.py
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_phase: str
    active_agent: str
    draft_content: str

    # Ścieżki do plików w folderze docs/
    task_file: str
    arch_file: str
    tech_file: str
    review_file: str
    
    # Ścieżka do wygenerowanego README.md
    readme_file: str

    # Katalog wyjściowy dla wygenerowanego projektu
    output_dir: str

    # Tryb działania: "create" (nowy projekt) lub "modify" (istniejący projekt)
    mode: str

    # Istniejące pliki projektu {rel_path: content} — wypełniane przez load_project_node
    existing_project_files: dict

    # Lista faz do uruchomienia, np. ["code", "review", "docker"]
    phases_to_run: list