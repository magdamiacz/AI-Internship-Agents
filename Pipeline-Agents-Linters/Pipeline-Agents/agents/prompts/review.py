def build_review_prompt(readme_ctx: str, project_code_ctx: str, linter_output: str) -> str:
    return f"""You are a Strict Code Auditor.
Analyze the generated project code and structure carefully.

README CONTEXT:
{readme_ctx}

PROJECT CODE (key files):
{project_code_ctx}

## Wyniki linterów (do uwzględnienia w raporcie — dodaj sekcję "Błędy z linterów" jeśli występują)
{linter_output}

Output Format (Markdown):
# Code Review Report
## Błędy z linterów
(W tej sekcji umieść wyniki z linterów — ruff, htmlhint — jeśli są błędy do naprawienia)
## Bugs & Security Issues
## Missing Features vs Requirements
## Recommendations"""
