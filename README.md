
# Basic AI Assistant

An interactive AI assistant built with **Python**, **LangChain**, and **LangGraph** that can perform calculations, fetch live weather, provide system information, and chat with the user. This project demonstrates working with AI tools, APIs, and environment variables in a modular Python application — perfect for a portfolio or learning project.

---

## Features

* **Calculator** – perform basic arithmetic operations.
* **Greeting Tool** – personalized greeting messages.
* **System Info** – retrieve OS, Python version, CPU, and RAM usage.
* **Weather Tool** – fetch live weather information for any city using OpenWeatherMap API.
* **Interactive Chat** – chat with the AI assistant in the terminal.

---

## Demo

```
Welcome! I'm your AI assistant. Type 'quit' to exit.
You can ask me to perform calculations or chat with me.

You: what’s the weather in Tokyo?

Assistant: Weather in Tokyo:
- Condition: Clear sky
- Temperature: 28°C
- Humidity: 60%
- Wind speed: 3.5 m/s
```

---

## Setup Instructions

1. **Clone the repository**

```
git clone <your_repo_url>
cd Basic AI Agent/project1
```

2. **Create and activate a virtual environment**

```
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. **Install dependencies**

```
pip install -r requirements.txt
```

4. **Configure API keys**

* Create a `.env` file in the project root:

```
OPENWEATHER_API_KEY=your_openweathermap_api_key
OPENAI_API_KEY=your_openai_api_key
```

5. **Run the AI assistant**

```
python main.py
```

Type `quit` to exit.

---

## Project Structure

```
Basic AI Agent/
├─ .venv/               # Virtual environment
├─ main.py              # Main application script
├─ requirements.txt     # Python dependencies
├─ .env.example         # Example environment variables
├─ README.md            # This file
```

---

## Dependencies

* Python 3.13+
* [LangChain](https://www.langchain.com/)
* [LangGraph](https://github.com/langgraph/langgraph)
* [python-dotenv](https://pypi.org/project/python-dotenv/)
* [psutil](https://pypi.org/project/psutil/)
* [requests](https://pypi.org/project/requests/)

---

## License

This project is open source and available under the MIT License.