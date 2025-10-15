import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

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