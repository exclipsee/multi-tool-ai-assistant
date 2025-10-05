import os
import platform
import psutil
import requests
import datetime
import json
from dotenv import load_dotenv
from termcolor import colored
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

# --- Load environment variables ---
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# =========================================================
# 🧠 TOOL DEFINITIONS
# =========================================================

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    if not OPENWEATHER_API_KEY:
        return "⚠️ Missing OpenWeatherMap API key."

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            return f"❌ Error: {data.get('message', 'Could not retrieve weather')}"

        weather = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        return (
            f"🌤 Weather in {city}:\n"
            f"- Condition: {weather}\n"
            f"- Temperature: {temp}°C\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind speed: {wind_speed} m/s"
        )

    except Exception as e:
        return f"❌ Error fetching weather: {str(e)}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression (e.g. 5 * (3 + 2)) safely."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"🧮 Result: {result}"
    except Exception as e:
        return f"❌ Error calculating expression: {str(e)}"


@tool
def say_hello(name: str) -> str:
    """Useful for greeting a user."""
    return f"👋 Hello {name}, how are you doing today?"


@tool
def system_info() -> str:
    """Retrieve system information like OS, CPU, and RAM."""
    try:
        os_info = f"{platform.system()} {platform.release()}"
        python_version = platform.python_version()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()

        return (
            f"💻 System Info:\n"
            f"- OS: {os_info}\n"
            f"- Python: {python_version}\n"
            f"- CPU Cores: {cpu_count}\n"
            f"- CPU Usage: {cpu_usage}%\n"
            f"- RAM: {ram.used / (1024**3):.2f} GB used / {ram.total / (1024**3):.2f} GB total"
        )
    except Exception as e:
        return f"❌ Error retrieving system info: {str(e)}"


@tool
def get_time() -> str:
    """Get the current time and date."""
    now = datetime.datetime.now()
    return f"⏰ Current Date & Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def get_news(topic: str = "technology") -> str:
    """Fetch top news headlines for a given topic."""
    if not NEWS_API_KEY:
        return "⚠️ Missing News API key."

    try:
        url = f"https://newsapi.org/v2/top-headlines?q={topic}&language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if data["status"] != "ok":
            return f"❌ Error fetching news: {data.get('message', 'Unknown error')}"

        articles = data["articles"][:5]
        headlines = "\n".join([f"- {a['title']}" for a in articles])
        return f"📰 Top News about '{topic}':\n{headlines}"

    except Exception as e:
        return f"❌ Error fetching news: {str(e)}"


@tool
def tell_joke() -> str:
    """Tell a random joke."""
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "I told my computer I needed a break — it said 'no problem, I’ll go to sleep.'",
        "There are only 10 kinds of people: those who understand binary and those who don’t.",
    ]
    return "😂 " + jokes[datetime.datetime.now().second % len(jokes)]


@tool
def save_note(content: str) -> str:
    """Save a quick note to a local file."""
    try:
        os.makedirs("notes", exist_ok=True)
        filename = f"notes/note_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"📝 Note saved successfully as {filename}"
    except Exception as e:
        return f"❌ Error saving note: {str(e)}"


# =========================================================
# ⚙️ MAIN EXECUTION LOGIC
# =========================================================

def main():
    print(colored("🤖 Welcome to Intelli CLI Assistant!", "cyan", attrs=["bold"]))
    print(colored("Type 'quit' to exit. Try commands like:", "yellow"))
    print(colored(" - What's the weather in Munich?", "yellow"))
    print(colored(" - Calculate 12 * (5 + 3)", "yellow"))
    print(colored(" - Tell me a joke", "yellow"))
    print(colored(" - Save note Buy groceries", "yellow"))
    print()

    model = ChatOpenAI(temperature=0.3)
    tools = [get_weather, calculator, say_hello, system_info, get_time, get_news, tell_joke, save_note]
    agent_executor = create_react_agent(model, tools)

    while True:
        user_input = input(colored("\nYou: ", "green")).strip()
        if user_input.lower() in {"quit", "exit"}:
            print(colored("\n👋 Goodbye, have a great day!", "cyan"))
            break

        try:
            print(colored("Assistant: ", "magenta"), end="")
            for chunk in agent_executor.stream({"messages": [HumanMessage(content=user_input)]}):
                if "agent" in chunk and "messages" in chunk["agent"]:
                    for message in chunk["agent"]["messages"]:
                        print(colored(message.content, "white"))
        except KeyboardInterrupt:
            print(colored("\n🛑 Stopped by user.", "red"))
            break
        except Exception as e:
            print(colored(f"❌ Error: {e}", "red"))


# =========================================================
# 🧩 ENTRY POINT
# =========================================================
if __name__ == "__main__":
    main()
