# 🤖 Intelli CLI Assistant 3.0 – Your Personal AI Companion

**Intelli CLI Assistant 3.0** is a **feature-rich, terminal-based AI assistant** built with **Python**, **LangChain**, and **LangGraph**.
It’s your personal command-line companion that can **fetch information, perform tasks, translate text, and monitor your system** — all while engaging in natural conversation.

This project demonstrates **modular AI architecture**, **real API integrations**, and **CLI-based interaction design**, making it ideal for learning, showcasing AI programming skills, or daily personal use.

---

## 🚀 What’s New in Version 3.0

✨ **New Features:**

* 🧠 **Wikipedia Search** – instantly retrieve summaries from Wikipedia.
* 🌍 **DeepL Translator** – translate text between languages using DeepL (via `deep_translator`).
* 🖥️ **Live System Monitor** – visualize real-time CPU, RAM, and disk usage with dynamic updates using `rich`.

---

## ⚙️ Core Capabilities

| Category                | Description                                                   |
| ----------------------- | ------------------------------------------------------------- |
| 🧮 **Calculator**       | Evaluate arithmetic expressions safely and quickly.           |
| 🌤 **Weather Info**     | Get live weather updates via the OpenWeatherMap API.          |
| 📰 **News Fetcher**     | Retrieve top headlines for any topic using NewsAPI.           |
| 💻 **System Info**      | Display OS, CPU, RAM, and Python version details.             |
| 🗒️ **Notes & Memory**  | Save and recall personal notes (persistent local memory).     |
| 😂 **Jokes & Fun**      | Get a random joke or a cheerful message.                      |
| 🕒 **Time & Date**      | Check the current date and time.                              |
| 🧾 **Persistent Logs**  | Keep a record of your chat history and actions.               |
| 🌍 **Translator**       | Translate any text using DeepL’s translation engine.          |
| 📘 **Wikipedia Search** | Retrieve short and accurate encyclopedia-style summaries.     |
| 📊 **System Monitor**   | Live dashboard showing CPU, RAM, and disk usage (via `rich`). |

---

## 🧩 Tech Stack

**Languages & Frameworks:**

* 🐍 Python 3.10+
* 🧩 LangChain + LangGraph (for AI reasoning and tool use)
* 🪄 `deep_translator` (DeepL translation)
* 📦 `requests`, `psutil`, `dotenv`, `termcolor`, `rich`

**APIs:**

* OpenWeatherMap API 🌦️
* NewsAPI 📰
* Wikipedia REST API 📘
* DeepL Translator 🌍

---

## 🧰 Example Commands

| Type               | Example Input                             |
| ------------------ | ----------------------------------------- |
| 🌤 Weather         | `What's the weather in Munich?`           |
| 📰 News            | `Show me news about AI`                   |
| 📘 Wikipedia       | `Search Wikipedia for Python programming` |
| 🌍 Translation     | `Translate "Bonjour" to English`          |
| 🖥️ System Monitor | `Monitor system for 15 seconds`           |
| 🧮 Calculator      | `Calculate (15 + 10) * 2`                 |
| 🗒️ Notes          | `Save note: Finish project report`        |
| 😂 Fun             | `Tell me a joke`                          |

---

## 💡 Future Plans

* 🧩 Add semantic memory (using embeddings) for smarter recall.
* 🔔 Implement reminders and notifications.
* 🎙️ Add voice input/output support.
* 📂 File summarization and document Q&A features.

---

## 🔥 License

**MIT License** – free, open source, and available for learning or customization.