
# Culinary Chatbot

This project is a culinary chatbot web application that generates recipes and corresponding dish images based on user queries. It uses AI technologies to provide an engaging and interactive experience for users seeking culinary inspiration and guidance.

## Features

- **Chat Interface**: A user-friendly chat interface to interact with the bot.
- **Recipe Generation**: AI-generated recipes with ingredients and steps.
- **Image Generation**: AI-generated images of the dishes.

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

4. **Run the FastAPI server**:
   ```bash
   uvicorn backend.main:app --reload
   ```

5. **Open the frontend**:
   Open `frontend/index.html` in your web browser.

## Usage

- Type a message in the chat interface and click 'Send'.
- The bot will respond with a recipe and an image of the dish.

## Notes

- Ensure that the OpenAI API keys and other necessary configurations are set up correctly for the AI tools to function.
- The image generation is simulated and does not produce real images in this setup.
