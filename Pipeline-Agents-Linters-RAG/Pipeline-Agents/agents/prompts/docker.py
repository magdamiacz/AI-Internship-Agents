def build_docker_prompt(readme_ctx: str) -> str:
    return f"""You are a DevOps Engineer. Containerize the culinary chatbot application.
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
