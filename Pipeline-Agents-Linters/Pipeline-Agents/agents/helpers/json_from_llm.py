import json
import re
from typing import Optional


def parse_json_from_llm(content: str) -> Optional[dict]:
    """
    Próbuje wyodrębnić JSON z odpowiedzi LLM.
    Obsługuje opcjonalne bloki ```json ... ```.
    Zwraca dict lub None przy błędzie parsowania.
    """
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        print(f"⚠️ Błąd parsowania JSON: {e}")
        print(f"Treść odpowiedzi agenta (pierwsze 1000 znaków):\n{content[:1000]}")
        return None
