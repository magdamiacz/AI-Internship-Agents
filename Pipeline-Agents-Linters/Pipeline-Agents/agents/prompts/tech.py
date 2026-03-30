def build_tech_prompt(task_ctx: str, arch_ctx: str) -> str:
    return f"""You are a Lead Tech Stack Evaluator. Recommend and justify the tech stack.
Stack is fixed: HTML/CSS/JS (frontend), FastAPI + SQLAlchemy + SQLite (backend), OpenAI API.
Task:\n{task_ctx}\nArch:\n{arch_ctx}"""
