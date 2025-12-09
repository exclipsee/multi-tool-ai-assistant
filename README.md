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

## 🇩🇪 German Tutor (new)

This repository now includes a lightweight German learning assistant to help you practice and demonstrate your progress to potential employers.

- Module: `german_assistant.py` — provides `assess_sentence(sentence, level)` and `generate_tasks(sentence, level, ...)`.
- Sample lessons: `data/german_lessons.json` (A1/A2 examples) used by the Streamlit UI sidebar.
- Streamlit UI: `app_streamlit.py` has a "German Tutor" mode in the sidebar for quick assessments and task generation.
- CLI: use the `/german <sentence>` slash command inside the interactive CLI (`python main.py`) to get a score, suggested correction, explanations, and example exercises.

Usage examples
- Streamlit (choose "German Tutor" in sidebar):

```powershell
pip install streamlit
streamlit run .\app_streamlit.py
```

### 🗣 Speech Integration (Beta)

New: `speech_utils.py` + Speech tab in the German Tutor UI.

Provided features:
- Upload German audio (wav/mp3/m4a/ogg) and transcribe (OpenAI Whisper if `OPENAI_API_KEY` set; stub otherwise).
- Text-to-Speech generation of any German sentence (OpenAI TTS preferred; falls back to `gTTS`).
- Quick transfer: After transcription you can reuse the text for assessment/tasks.

Requirements:
- Set `OPENAI_API_KEY` for high quality transcription + neural TTS.
- Installs `gTTS` as fallback.

Roadmap ideas:
- Live microphone capture (streamlit-webrtc).
- Offline local whisper (`faster-whisper`).
- Pronunciation / phoneme scoring.
- Batch drilling from lesson sentences.

Live microphone capture (Quick setup)
- The Speech tab now supports live microphone recording using an optional component. Install the recorder and run Streamlit:

```powershell
pip install -r requirements.txt
streamlit run .\app_streamlit.py
```

### 📈 Study Streaks & Gamification

We've added a lightweight gamification system to help you build a habit:

- What it records: daily "visits" to the `German Tutor` mode and completed assessments. Data is stored in `memory.json` under the `study_activity` key.
- What you see: the Streamlit sidebar displays your current streak (consecutive active days), total assessments, and earned badges (e.g. "First Activity", "3-Day Streak", "7-Day Streak", "10 Assessments").
- Automatic tracking: visits are recorded when you open the `German Tutor` mode; assessments recorded via the UI call are counted automatically.
- SRS suggestion: the sidebar also shows a quick suggestion if you have SRS cards due to review today.

How to use
- Run the app and open `German Tutor` — your visit will be recorded automatically.
- Do assessments (Practice tab or Conversation mode) to earn badges and grow your streak.
- To inspect stored data manually, open `memory.json` and look for the `study_activity` object.

Why: small rewards and visible progress help with retention — this provides a friendly nudge to practice daily.

- If you prefer the component approach, install: `pip install streamlit-audio-recorder` (optional). If it's not installed the UI falls back to file upload.

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