import json
import os
from datetime import date

ALL_PHASES = ["task", "arch", "tech", "code", "review", "docker"]


def update_pipeline_state(output_dir: str, phase: str) -> None:
    """Zapisuje lub aktualizuje pipeline_state.json w katalogu projektu."""
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
    saved["phases_done"] = sorted(
        phases_done,
        key=lambda p: ALL_PHASES.index(p) if p in ALL_PHASES else 999,
    )

    os.makedirs(output_dir, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
