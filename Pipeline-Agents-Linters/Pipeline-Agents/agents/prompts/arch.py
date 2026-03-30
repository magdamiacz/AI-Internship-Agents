def build_arch_prompt(task_ctx: str) -> str:
    return f"""You are a Senior System Architect. Design architecture based on requirements.
The system is: HTML/JS frontend + FastAPI backend + SQLite database + OpenAI (GPT-4o + DALL-E 3).
Task Context:\n{task_ctx}"""
