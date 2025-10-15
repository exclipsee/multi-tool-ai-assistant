# 🤖 Intelli CLI Assistant 3.2 – Many‑Tools Edition

A powerful, local, multi‑tool AI agent for everyday use. Built with Python, LangChain, and LangGraph. It chats, calls tools, and automates tasks from your terminal (CLI) or an optional web UI.

Highlights
- Safe math (AST) calculator
- Timezone‑aware time lookups (e.g., Tokyo)
- Web search and URL fetch/summarize
- News, weather, RSS
- Notes, reminders, todos (persistent)
- Unit and currency conversion
- File ops, CSV/JSON, ZIP, hashes, Base64
- PDF→text, Markdown→HTML, QR codes, screenshots
- Clipboard, regex transforms, password generator
- Caching, atomic saves, Windows‑safe disk info

Note: Jokes tool was removed by request.

---

## 🧩 Tech Stack

- Python 3.10+
- LangChain + LangGraph
- rich, psutil, requests, python‑dotenv, termcolor
- Optional libs for extra tools (see below)

APIs
- OpenAI (chat model via langchain_openai)
- OpenWeatherMap (weather)
- NewsAPI (headlines)
- Wikipedia REST (summaries)
- DuckDuckGo Instant Answer (search)
- exchangerate.host (currency)

---

## 📦 Installation

1) Create a virtual environment (Windows, PowerShell)
```
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

2) Install dependencies
```
pip install -r .\requirements.txt
```

3) Optional features (install as needed)
```
pip install tzdata feedparser markdown pyperclip pdfminer.six "qrcode[pil]" mss beautifulsoup4
```

---

## 🔑 Configuration

Create a .env in the repo root:
```
OPENAI_API_KEY=sk-...
# Use a model your account has access to (example below)
OPENAI_MODEL=gpt-4o-mini

# Optional external APIs
OPENWEATHER_API_KEY=your_openweather_key
NEWS_API_KEY=your_newsapi_key

# HTTP tuning (optional)
HTTP_TIMEOUT=15
HTTP_RETRIES=2
```
Tip: The code defaults OPENAI_MODEL to “gpt-5”. If your key doesn’t have that, set a valid model like gpt-4o or gpt-4o-mini.

---

## ▶️ Run (CLI)

From repo root:
```
python .\project1\main.py
```

Slash commands
- /help – help and tool list
- /clear – clear chat memory
- /notes export – export notes to notes_export.md
- /reminders – check due reminders now
- /tools – show tool names

Examples
- “weather in Berlin”
- “what’s the time in Tokyo” (uses get_time_in)
- “convert 10 km to m”
- “convert 100 USD to EUR”
- “fetch https://example.com”
- “rss https://hnrss.org/frontpage”
- “add todo: ship the project in 2 days”
- “set reminder: stretch in 20 min”
- “csv_to_json data/users.csv”
- “zip_paths [‘project1’, ‘requirements.txt’]”
- “make_qr https://github.com/”

---

## 🧠 Major Capabilities (by category)

- Info & Web: get_weather, get_news, wiki_search, search_web, fetch_url, fetch_rss
- Time: get_time, get_time_in (timezone‑aware for cities/IANA zones)
- Memory & Tasks: save_note, recall_notes, set_reminder, check_reminders, add_todo, list_todos, complete_todo
- Math & Conversion: calculator (safe AST), unit_convert, currency_convert
- Files & Data: list_files, read_text_file, write_text_file, csv_to_json, json_to_csv, zip_paths, unzip_to
- Security & Encoding: sha256_string, sha256_file, b64_encode, b64_decode
- Media & Docs: pdf_to_text, md_to_html, make_qr, take_screenshot
- Text Utils: summarize_text, slugify, regex_replace, password_generate, copy_to_clipboard, paste_from_clipboard
- System: system_info, caching, atomic JSON saves, Windows‑safe disk detection

---

## 🖥️ Optional Web UI

Option A: Streamlit
1) Place app_streamlit.py in the repo root or in project1.
2) If it’s in the repo root, import from the subfolder:
   - from project1.main import OPENAI_MODEL, ASSISTANT_SYSTEM_PROMPT, ...
3) Run:
```
pip install streamlit
streamlit run .\app_streamlit.py
```
Fix “Import 'main' could not be resolved”:
- Ensure the import points to project1.main if your main.py is in project1.
- Or move app_streamlit.py into project1 and use “from main import …”.

Option B: Gradio
```
pip install gradio
python .\app_gradio.py
```
Do the same import adjustment as above based on file location.

---

## 💸 Costs & Privacy

- OpenAI API is paid per token. Use models you have access to.
- NewsAPI/OpenWeatherMap may have free tiers with limits.
- Local tools (files, conversions, QR, PDF, etc.) are free and run locally.
- Prompts sent to OpenAI when the agent calls the model—avoid secrets.

---

## 🛠️ Troubleshooting

- Pylance “Import ‘main’ could not be resolved”: adjust imports to “from project1.main import …” or move UI file into project1.
- Timezone error: install tzdata (pip install tzdata).
- RSS error: install feedparser.
- PDF extraction: install pdfminer.six.
- Markdown conversion: install markdown.
- Clipboard: install pyperclip.
- QR codes: install qrcode[pil].
- Screenshots: install mss.
- Colors on Windows: colorama is included; ensure the venv interpreter is selected in VS Code.

---

## 📜 License

MIT License – free to use and modify.