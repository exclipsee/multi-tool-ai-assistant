import os
import platform
import psutil
import requests
import datetime
import json
from pathlib import Path
from dotenv import load_dotenv
from termcolor import colored
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from deep_translator import DeeplTranslator
from rich.live import Live
from rich.table import Table
import time

# =========================================================
# 🌟 CONFIGURATION
# =========================================================
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MEMORY_FILE = Path("memory.json")
LOG_FILE = Path("assistant_log.json")

# =========================================================
# 🧩 MEMORY & LOGGING
# =========================================================
def load_json(file, default):
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

memory = load_json(MEMORY_FILE, {"notes": [], "knowledge": [], "reminders": []})
log = load_json(LOG_FILE, [])

def add_note(content):
    memory["notes"].append({
        "timestamp": datetime.datetime.now().isoformat(),
        "note": content
    })
    save_json(MEMORY_FILE, memory)
    return "📝 Note saved!"

def log_interaction(user_input, assistant_response):
    log.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user_input,
        "assistant": assistant_response
    })
    save_json(LOG_FILE, log)

# =========================================================
# 🧠 TOOLS
# =========================================================

@tool
def get_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "⚠️ Missing OpenWeatherMap API key."
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        data = requests.get(url).json()
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
            f"- Wind Speed: {wind_speed} m/s"
        )
    except Exception as e:
        return f"❌ Error fetching weather: {str(e)}"

@tool
def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"🧮 Result: {result}"
    except Exception as e:
        return f"❌ Error calculating expression: {str(e)}"

@tool
def say_hello(name: str) -> str:
    return f"👋 Hello {name}! Nice to see you."

@tool
def system_info() -> str:
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
    now = datetime.datetime.now()
    return f"⏰ Current Date & Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

@tool
def get_news(topic: str = "technology") -> str:
    if not NEWS_API_KEY:
        return "⚠️ Missing News API key."
    try:
        url = f"https://newsapi.org/v2/top-headlines?q={topic}&language=en&apiKey={NEWS_API_KEY}"
        data = requests.get(url).json()
        if data["status"] != "ok":
            return f"❌ Error fetching news: {data.get('message', 'Unknown error')}"
        articles = data["articles"][:5]
        headlines = "\n".join([f"- {a['title']}" for a in articles])
        return f"📰 Top News '{topic}':\n{headlines}"
    except Exception as e:
        return f"❌ Error fetching news: {str(e)}"

@tool
def tell_joke() -> str:
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "I told my computer I needed a break — it said 'no problem, I’ll go to sleep.'",
        "There are only 10 kinds of people: those who understand binary and those who don’t.",
    ]
    return "😂 " + jokes[datetime.datetime.now().second % len(jokes)]

@tool
def save_note(content: str) -> str:
    return add_note(content)

@tool
def recall_notes() -> str:
    if not memory["notes"]:
        return "🗒 No notes found."
    return "\n".join([f"- {n['note']} (saved {n['timestamp']})" for n in memory["notes"]])

# =========================================================
# 🆕 NEW TOOLS
# =========================================================

@tool
def wiki_search(query: str) -> str:
    """Search Wikipedia for a summary."""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        data = requests.get(url).json()
        if "title" not in data:
            return "❌ No results found."
        return f"📘 {data.get('title')}: {data.get('extract', 'No summary found.')}"
    except Exception as e:
        return f"❌ Error fetching Wikipedia info: {str(e)}"

@tool
def translate_text(text: str, target_lang: str = "EN") -> str:
    """Translate text using DeepL (via deep_translator)."""
    try:
        translated = DeeplTranslator(target=target_lang).translate(text)
        return f"🌍 Translation ({target_lang}): {translated}"
    except Exception as e:
        return f"❌ Translation error: {e}"

@tool
def system_monitor(duration: int = 10) -> str:
    """Live system monitor showing CPU, RAM, and Disk usage."""
    try:
        with Live(refresh_per_second=1) as live:
            for _ in range(duration):
                table = Table(title="🖥️ System Monitor", style="bold cyan")
                table.add_column("Metric", justify="left", style="yellow")
                table.add_column("Value", justify="right", style="white")

                cpu = psutil.cpu_percent(interval=0.5)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                table.add_row("CPU Usage", f"{cpu}%")
                table.add_row("RAM Usage", f"{ram.percent}% ({ram.used / (1024**3):.1f} GB / {ram.total / (1024**3):.1f} GB)")
                table.add_row("Disk Usage", f"{disk.percent}% ({disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB)")

                live.update(table)
                time.sleep(1)
        return "✅ Monitoring complete."
    except KeyboardInterrupt:
        return "🛑 Monitoring stopped by user."
    except Exception as e:
        return f"❌ Error in system monitor: {e}"

# =========================================================
# ⚙️ MAIN EXECUTION
# =========================================================
def main():
    print(colored("🤖 Welcome to Intelli CLI 3.0 (Enhanced Edition)!", "cyan", attrs=["bold"]))
    print(colored("Type 'quit' to exit.", "yellow"))
    print(colored("Try commands: Weather, News, Wiki, Translate, Monitor, Note, SystemInfo, Joke", "yellow"))

    model = ChatOpenAI(temperature=0.3)
    tools = [
        get_weather, calculator, say_hello, system_info, get_time,
        get_news, tell_joke, save_note, recall_notes,
        wiki_search, translate_text, system_monitor
    ]

    agent_executor = create_react_agent(model, tools)

    while True:
        user_input = input(colored("\nYou: ", "green")).strip()
        if user_input.lower() in {"quit", "exit"}:
            print(colored("👋 Goodbye!", "cyan"))
            break

        try:
            response_text = ""
            for chunk in agent_executor.stream({"messages": [HumanMessage(content=user_input)]}):
                if "agent" in chunk and "messages" in chunk["agent"]:
                    for message in chunk["agent"]["messages"]:
                        text = message.content
                        print(colored(text, "white"))
                        response_text += text
            log_interaction(user_input, response_text)
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
