# 🍳 Recipe Agent (Asystent Kulinarny AI)

Ten projekt to inteligentny asystent kulinarny zbudowany przy pomocy frameworka **LangGraph** oraz modelu **OpenAI (GPT-4o)**. Agent specjalizuje się wyłącznie w tematach związanych z gotowaniem, potrafi rozpoznawać potrawy ze zdjęć i automatycznie generować ustrukturyzowane przepisy.

---

## ✨ Główne funkcjonalności

1. 🛡️ **Restrykcyjny System Prompt (Guardrails):** Agent ma ścisły zakaz rozmawiania na tematy niezwiązane z kuchnią. Jeśli zapytasz go o programowanie czy politykę, grzecznie odmówi i przekieruje rozmowę na tory kulinarne.
2. 👁️ **Rozpoznawanie Obrazu (Vision):** Dzięki wbudowanej funkcji kodowania obrazów do formatu base64 (`encode_image`), użytkownik może dostarczyć agentowi zdjęcie dania, a model zidentyfikuje je i odtworzy przepis.
3. 🛠️ **Wykorzystanie Narzędzi (Tool Calling):** Agent został wyposażony w narzędzie (funkcję Python) `save_recipe_to_json`. Za każdym razem, gdy wygeneruje nowy przepis kulinarny, autonomicznie wywołuje to narzędzie, aby sformatować dane (nazwa, składniki, kroki) i zapisać je fizycznie na dysku jako plik `recipe.json`.

---

## 🏗️ Architektura (LangGraph)

Logika agenta opiera się na prostym, ale potężnym grafie stanu (`StateGraph`):
* **Węzeł `chatbot`**: Główny "mózg" agenta (GPT-4o powiązany z narzędziami).
* **Węzeł `tools` (`ToolNode`)**: Wykonawca akcji, który uruchamia kod w Pythonie (zapisywanie do pliku).
* **Połączenie warunkowe (`tools_condition`)**: Po wygenerowaniu odpowiedzi przez LLM, graf decyduje, czy model chce użyć narzędzia (wtedy przechodzi do węzła `tools`), czy przekazać ostateczną odpowiedź użytkownikowi (koniec działania).

---

## 🚀 Wymagania wstępne

* **Python 3.10+**
* Klucz API od OpenAI

---

## 🛠️ Instalacja i konfiguracja

1. **Przejdź do folderu z projektem:**
   ```bash
   cd Recipe-Agent-Full

2. **Utwórz wirtualne środowisko i aktywuj je:**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate

3. **Zainstaluj wymagane biblioteki:**
    ```bash
    pip install langchain-openai langgraph python-dotenv

4. **Konfiguracja zmiennych środowiskowych:**
    ```bash
    Utwórz plik .env i podaj w nim swój klucz API:
    OPENAI_API_KEY=sk-twoj-sekretny-klucz-api

