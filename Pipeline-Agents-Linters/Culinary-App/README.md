# Culinary Chatbot

This project is a culinary chatbot web application that generates recipes and corresponding dish images based on user queries. It uses AI technologies to provide an engaging and interactive experience for users seeking culinary inspiration and guidance.

## Features

- **Chat Interface**: A user-friendly chat interface to interact with the bot.
- **Recipe Generation**: AI-generated recipes with ingredients and steps.
- **Image Generation**: AI-generated images of the dishes.
- **User Authentication**: Register and login to save and view personal recipes.

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: FastAPI
- **Database**: SQLite with SQLAlchemy
- **AI Tools**: LangChain, OpenAI GPT-4o, DALL-E 3

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd culinary-chatbot
   ```

2. **Set up the virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Set environment variables**:
   Copy `backend/.env.example` to `backend/.env` and fill in at least:
   - `OPENAI_API_KEY` — required for the AI features.
   - `JWT_SECRET` — long random string for signing JWTs (e.g. `openssl rand -hex 32`). Do not use the default value in production.
   - `PASSWORD_PEPPER` (recommended) — application secret used with HMAC-SHA256 before bcrypt. **Salt** for each password is still generated automatically inside bcrypt; **pepper** is one shared server secret, not stored in the database. If unset, the app uses legacy `bcrypt(plain password)` for compatibility; after you set `PASSWORD_PEPPER`, new signups use the stronger scheme and existing users get upgraded on next successful login.

   Optional: `ENV=production` — the app will refuse to start if `JWT_SECRET` is still the default or too short.

5. **Run the FastAPI server** (from the repository root, or `cd backend` and adjust the module path):
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Or from project root: `uvicorn backend.main:app --reload`

6. **Open the frontend**:
   Open `frontend/index.html` in your web browser.

## Usage

- Register or login to start using the chatbot.
- Type a message in the chat interface and click 'Send'.
- The bot will respond with a recipe and an image of the dish.

## Notes

- Ensure that the OpenAI API keys and other necessary configurations are set up correctly for the AI tools to function.
- The image generation is simulated and does not produce real images in this setup.
