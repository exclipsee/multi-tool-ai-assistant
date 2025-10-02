from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import os
import platform
import psutil
import requests



load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")  # fetch the key from .env

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    if not API_KEY:
        return "API key for OpenWeatherMap is missing."

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            return f"Error: {data.get('message', 'Could not retrieve weather')}"

        weather = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        return (
            f"Weather in {city}:\n"
            f"- Condition: {weather}\n"
            f"- Temperature: {temp}°C\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind speed: {wind_speed} m/s"
        )

    except Exception as e:
        return f"Error fetching weather: {str(e)}"

@tool
def calculator(a: float, b: float) -> str:
    """Useful for performing basic arithmetic calculations with numbers"""
    print("Tool has been called.")
    return f"The sum of {a} and {b} is {a + b}"

@tool
def say_hello(name: str) -> str:
    """Useful for greeting a user"""
    print("Tool has been called.")
    return f"Hello {name}, I hope you are well today."

@tool
def system_info() -> str:
    """Useful for retrieving basic system information like OS, Python version, CPU, and RAM."""
    try:
        os_info = platform.system() + " " + platform.release()
        python_version = platform.python_version()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        total_ram = round(psutil.virtual_memory().total / (1024 ** 3), 2)  # in GB
        used_ram = round(psutil.virtual_memory().used / (1024 ** 3), 2)    # in GB

        return (
            f"System Info:\n"
            f"- Operating System: {os_info}\n"
            f"- Python Version: {python_version}\n"
            f"- CPU Cores: {cpu_count}\n"
            f"- CPU Usage: {cpu_usage}%\n"
            f"- RAM: {used_ram} GB used / {total_ram} GB total"
        )
    except Exception as e:
        return f"Error retrieving system info: {str(e)}"


def main():
    model = ChatOpenAI(temperature=0)

    tools = [calculator, say_hello, system_info, get_weather]
    agent_executor = create_react_agent(model, tools)

    print("Welcome! I'm your AI assistant. Type 'quit' to exit.")
    print("You can ask me to perform calculations or chat with me.")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input == "quit":
            break

        print("\nAssistant: ", end="")
        for chunk in agent_executor.stream(
            {"messages": [HumanMessage(content=user_input)]}
        ):
            if "agent" in chunk and "messages" in chunk["agent"]:
                for message in chunk["agent"]["messages"]:
                    print(message.content, end="")
            print()

if __name__ == "__main__":
    main()