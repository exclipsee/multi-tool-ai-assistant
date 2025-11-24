import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import json
from pathlib import Path

# German tutor
try:
    from german_assistant import assess_sentence, generate_tasks
except Exception:
    assess_sentence = None
    generate_tasks = None

# Import your existing tools and config from main.py
from main import (
    OPENAI_MODEL, ASSISTANT_SYSTEM_PROMPT,
    get_weather, calculator, say_hello, system_info, get_time, get_time_in,
    get_news, wiki_search, search_web, fetch_url, fetch_rss,
    translate_text, summarize_text, slugify,
    set_reminder, check_reminders, add_todo, list_todos, complete_todo,
    unit_convert, currency_convert,
    list_files, read_text_file, write_text_file, csv_to_json, json_to_csv,
    zip_paths, unzip_to, sha256_string, sha256_file, b64_encode, b64_decode,
    make_qr, pdf_to_text, md_to_html, take_screenshot,
    regex_replace, password_generate, copy_to_clipboard, paste_from_clipboard,
)

st.set_page_config(page_title="Intelli CLI (UI)", page_icon="🤖", layout="centered")
st.title("🤖 Intelli CLI (UI)")

# Mode selector: keep existing chat but allow German Tutor mode
mode = st.sidebar.selectbox("Mode", ["Chat", "German Tutor"], index=0)

# If German tutor selected, render tutor UI and stop further chat rendering
if mode == "German Tutor":
    st.header("🇩🇪 German Tutor")
    if assess_sentence is None:
        st.error("`german_assistant` not available. Make sure the file exists and is importable.")
        st.stop()

    level = st.selectbox("Target level", ["A1", "A2", "B1", "B2"], index=0)
    focus = st.multiselect("Focus", ["Grammar", "Vocabulary", "Speaking", "Writing"], default=["Grammar"])
    sentence = st.text_area("Enter a German sentence to assess", value="Ich lerne Deutsch")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Assess sentence"):
            res = assess_sentence(sentence, level=level)
            st.subheader("Assessment")
            st.write(f"Score: {res.get('score')}")
            st.write("**Correction:**")
            st.code(res.get('correction'))
            if res.get('explanations'):
                st.markdown("**Explanations:**")
                for e in res.get('explanations'):
                    st.write(f"- {e}")
    with col2:
        if st.button("Generate tasks"):
            tasks = generate_tasks(sentence, level=level, num_tasks=4)
            st.subheader("Tasks")
            for t in tasks:
                st.markdown(f"- **{t.get('type')}**: {t.get('prompt')}")

    # Show sample lessons
    lessons_path = Path(__file__).parent / "data" / "german_lessons.json"
    if lessons_path.exists():
        try:
            data = json.loads(lessons_path.read_text(encoding="utf-8"))
            st.sidebar.subheader("Sample lessons")
            for lvl, lessons in data.get("levels", {}).items():
                if lvl == level:
                    for lesson in lessons:
                        st.sidebar.markdown(f"**{lesson.get('title')}**")
                        for s in lesson.get('sentences', [])[:3]:
                            st.sidebar.write(s)
        except Exception:
            pass

    st.stop()

with st.sidebar:
    st.subheader("Controls")
    if st.button("Check reminders now"):
        try:
            st.info(check_reminders())
        except Exception as e:
            st.error(str(e))
    st.caption("Set OPENAI_API_KEY and OPENAI_MODEL in .env")

# Build agent once and keep in session
if "agent" not in st.session_state:
    model = ChatOpenAI(temperature=0.2, model=OPENAI_MODEL)
    tools = [
        get_weather, calculator, say_hello, system_info, get_time, get_time_in,
        get_news, wiki_search, search_web, fetch_url, fetch_rss,
        translate_text, summarize_text, slugify,
        set_reminder, check_reminders, add_todo, list_todos, complete_todo,
        unit_convert, currency_convert,
        list_files, read_text_file, write_text_file, csv_to_json, json_to_csv,
        zip_paths, unzip_to, sha256_string, sha256_file, b64_encode, b64_decode,
        make_qr, pdf_to_text, md_to_html, take_screenshot,
        regex_replace, password_generate, copy_to_clipboard, paste_from_clipboard,
    ]
    st.session_state.agent = create_react_agent(model, tools)
    st.session_state.history = [SystemMessage(content=ASSISTANT_SYSTEM_PROMPT)]

# Render chat history
for msg in st.session_state.history:
    if isinstance(msg, SystemMessage):
        continue
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.write(msg.content)

# Input box
prompt = st.chat_input("Type a message")
if prompt:
    st.session_state.history.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.write(prompt)

    # Run agent
    try:
        result = st.session_state.agent.invoke({"messages": st.session_state.history})
        ai_text = ""
        msgs = result.get("messages", [])
        for m in reversed(msgs):
            if isinstance(m, AIMessage) or getattr(m, "type", "") == "ai":
                ai_text = m.content
                break
        if not ai_text and msgs:
            ai_text = msgs[-1].content
    except Exception as e:
        ai_text = f"Error: {e}"

    st.session_state.history.append(AIMessage(content=ai_text))
    with st.chat_message("assistant"):
        st.write(ai_text)