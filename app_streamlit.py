import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import json
from pathlib import Path
import pandas as pd
try:
    from speech_utils import transcribe_audio, synthesize_speech
except Exception:
    transcribe_audio = None  # type: ignore
    synthesize_speech = None  # type: ignore
try:
    # Optional lightweight recorder component (returns WAV bytes or base64 data)
    from streamlit_audio_recorder import audio_recorder  # type: ignore
except Exception:
    audio_recorder = None  # type: ignore

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

    # Paths for persona and memory
    PROJECT_ROOT = Path(__file__).parent
    PERSONA_PATH = PROJECT_ROOT / "german_persona.json"
    MEMORY_PATH = PROJECT_ROOT / "memory.json"

    # Load persona defaults
    persona = {
        "default_level": "A1",
        "strictness": "balanced",
        "save_attempts": True,
    }
    if PERSONA_PATH.exists():
        try:
            persona.update(json.loads(PERSONA_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass

    tabs = st.tabs(["Practice", "Progress", "Preferences", "Speech (Beta)"])

    # --- Practice tab ---
    with tabs[0]:
        level = st.selectbox("Target level", ["A1", "A2", "B1", "B2"], index=["A1","A2","B1","B2"].index(persona.get("default_level","A1")))
        focus = st.multiselect("Focus", ["Grammar", "Vocabulary", "Speaking", "Writing"], default=["Grammar"])
        initial_sentence = st.session_state.get("transcribed_sentence", "Ich lerne Deutsch")
        sentence = st.text_area("Enter a German sentence to assess", value=initial_sentence)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Assess sentence"):
                res = assess_sentence(sentence, level=level, persona=persona, save_attempt=persona.get("save_attempts", True))
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

    # --- Progress tab ---
    with tabs[1]:
        st.subheader("Your recent attempts")
        attempts = []
        if MEMORY_PATH.exists():
            try:
                mem = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
                attempts = mem.get("german_attempts", [])
            except Exception:
                attempts = []
        if not attempts:
            st.info("No attempts recorded yet. Assess sentences to build history.")
        else:
            recent = list(reversed(attempts))[:50]
            # Build DataFrame with timestamps and scores for plotting
            try:
                df = pd.DataFrame(recent)
                if "timestamp" in df.columns and "score" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
                    if not df.empty:
                        st.metric("Average score (recent)", f"{df['score'].mean():.1f}")
                        st.line_chart(df["score"])
                    else:
                        scores = [a.get("score", 0) for a in recent]
                        avg = sum(scores) / len(scores) if scores else 0
                        st.metric("Average score (recent)", f"{avg:.1f}")
                        st.line_chart(scores)
                else:
                    scores = [a.get("score", 0) for a in recent]
                    avg = sum(scores) / len(scores) if scores else 0
                    st.metric("Average score (recent)", f"{avg:.1f}")
                    st.line_chart(scores)
            except Exception:
                # fallback to simple list chart if pandas is missing or fails
                scores = [a.get("score", 0) for a in recent]
                avg = sum(scores) / len(scores) if scores else 0
                st.metric("Average score (recent)", f"{avg:.1f}")
                try:
                    st.line_chart(scores)
                except Exception:
                    pass

            # List the recent entries
            for a in recent:
                ts = a.get("timestamp", "")
                st.markdown(f"- **{a.get('original')}** → {a.get('correction')} ({a.get('score')}) — {ts}")

    # --- Preferences tab ---
    with tabs[2]:
        st.subheader("German Tutor Preferences")
        new_level = st.selectbox("Default level", ["A1", "A2", "B1", "B2"], index=["A1","A2","B1","B2"].index(persona.get("default_level","A1")))
        strict = st.radio("Correction strictness", ["gentle", "balanced", "strict"], index=["gentle","balanced","strict"].index(persona.get("strictness","balanced")))
        save_attempts = st.checkbox("Save attempts to memory.json", value=bool(persona.get("save_attempts", True)))
        if st.button("Save preferences"):
            persona_update = {"default_level": new_level, "strictness": strict, "save_attempts": save_attempts}
            try:
                PERSONA_PATH.write_text(json.dumps(persona_update, indent=2, ensure_ascii=False), encoding="utf-8")
                st.success("Preferences saved to german_persona.json")
            except Exception as e:
                st.error(f"Failed to save preferences: {e}")

    # --- Speech (Beta) tab ---
    with tabs[3]:
        st.subheader("Speech Practice (Beta)")
        st.caption("Upload a short German audio clip (wav/mp3/m4a/ogg) to transcribe. Requires OPENAI_API_KEY for best results.")
        # Live recorder (optional component)
        recorded = None
        if audio_recorder:
            st.caption("Or record directly from your microphone (click to start/stop).")
            try:
                recorded = audio_recorder()
            except Exception:
                recorded = None

        # If recorder produced data, show a small player and allow transcription
        if recorded:
            # Recorded might be bytes or a data-url string
            import base64
            if isinstance(recorded, str) and recorded.startswith("data:"):
                audio_bytes = base64.b64decode(recorded.split(",", 1)[1])
            elif isinstance(recorded, (bytes, bytearray)):
                audio_bytes = bytes(recorded)
            else:
                audio_bytes = None

            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if transcribe_audio and st.button("Transcribe recording"):
                    text, source = transcribe_audio(audio_bytes, filename="recording.wav")
                    st.write(f"**Source:** {source}")
                    st.write(f"**Transcription:** {text}")
                    if st.button("Use transcription for assessment"):
                        st.session_state["transcribed_sentence"] = text
                        st.info("Transcription stored — go to Practice tab.")
            else:
                st.warning("Could not decode recorded audio. You can upload a file instead.")

        # Fallback: file upload
        audio_file = st.file_uploader("Or upload recorded speech", type=["wav", "mp3", "m4a", "ogg"])
        if audio_file and transcribe_audio:
            if st.button("Transcribe audio"):
                data = audio_file.read()
                text, source = transcribe_audio(data, filename=audio_file.name)
                st.write(f"**Source:** {source}")
                st.write(f"**Transcription:** {text}")
                if st.button("Use transcription for assessment"):
                    st.session_state["transcribed_sentence"] = text
                    st.info("Go to Practice tab and paste the transcription if not auto-filled.")
        elif not transcribe_audio:
            st.warning("Speech utilities not available. Check `speech_utils.py`.")

        st.divider()
        st.caption("Text-to-Speech any German text")
        tts_text = st.text_area("Text to speak", value="Guten Tag! Willkommen zum Sprachtraining.")
        voice = st.selectbox("Voice (OpenAI)", ["alloy", "verse", "aria", "nova"], index=0)
        if st.button("Generate Audio"):
            if synthesize_speech:
                audio_bytes, mime, source = synthesize_speech(tts_text, voice=voice)
                st.write(f"**Source:** {source}")
                if audio_bytes:
                    st.audio(audio_bytes, format=mime)
                else:
                    st.error("Failed to generate audio.")
            else:
                st.error("TTS unavailable (missing dependency or API key).")

    # Show sample lessons in sidebar
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