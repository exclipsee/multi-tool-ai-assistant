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
    # Conversation Tutor tab
    try:
        from german_assistant import generate_followup, track_mistakes
    except Exception:
        generate_followup = None  # type: ignore
        track_mistakes = None  # type: ignore

    tabs = st.tabs(["Practice", "Conversation", "Progress", "Preferences", "Speech (Beta)"])
    # Add Drill (SRS) tab at the end
    try:
        from srs import get_due_cards, import_attempts, schedule_card, add_card
    except Exception:
        get_due_cards = None  # type: ignore
        import_attempts = None  # type: ignore
        schedule_card = None  # type: ignore
        add_card = None  # type: ignore

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

    # --- Conversation Tutor tab ---
    with tabs[1]:
        st.subheader("Conversational Tutor")
        if generate_followup is None or track_mistakes is None:
            st.info("Conversational Tutor unavailable — ensure `german_assistant.generate_followup` is present.")
        else:
            # Initialize session state
            if "tutor_conv" not in st.session_state:
                st.session_state.tutor_conv = [
                    {"role": "assistant", "text": "Hallo! Let's practice German. Say something in German and I'll give feedback."}
                ]

            # Render conversation
            for m in st.session_state.tutor_conv:
                if m["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(m["text"])
                else:
                    with st.chat_message("user"):
                        st.write(m["text"])

            user_input = st.text_input("Your turn (in German)", key="tutor_input")
            if st.button("Send", key="tutor_send") and user_input:
                # Append user message
                st.session_state.tutor_conv.append({"role": "user", "text": user_input})
                # Assess
                try:
                    res = assess_sentence(user_input, persona=persona)
                except Exception:
                    res = None
                if res:
                    # Track mistakes
                    try:
                        track_mistakes(res)
                    except Exception:
                        pass
                    # Show assessment
                    corr = res.get("correction")
                    expl = res.get("explanations", [])
                    assistant_text = f"Score: {res.get('score')}\nCorrection: {corr}\n"
                    if expl:
                        assistant_text += "\nExplanations:\n" + "\n".join([f"- {e}" for e in expl])
                    st.session_state.tutor_conv.append({"role": "assistant", "text": assistant_text})
                    # Follow-up prompt
                    try:
                        fup = generate_followup(res)
                        st.session_state.tutor_conv.append({"role": "assistant", "text": fup.get("prompt")})
                    except Exception:
                        pass

            # Small control to clear conversation
            if st.button("Reset conversation"):
                st.session_state.tutor_conv = [{"role": "assistant", "text": "Hallo! Let's practice German. Say something in German and I'll give feedback."}]

            # Follow-up cache management UI
            with st.expander("Follow-up Cache (manage)"):
                try:
                    mem = __import__("german_assistant")._load_memory()
                    cache = mem.get("followup_cache", {})
                except Exception:
                    cache = {}
                st.write(f"Cached entries: {len(cache)}")
                if st.button("Clear follow-up cache", key="clear_followup_cache"):
                    try:
                        mem = __import__("german_assistant")._load_memory()
                        mem["followup_cache"] = {}
                        __import__("german_assistant")._save_memory(mem)
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to clear cache: {e}")

                shown = 0
                for k, v in list(cache.items()):
                    if shown >= 10:
                        break
                    shown += 1
                    col1, col2, col3 = st.columns([6, 1, 1])
                    prompt_preview = v.get("prompt") or str(v.get("intent"))
                    with col1:
                        st.write(prompt_preview[:300])
                    with col2:
                        if st.button("Refresh", key=f"refresh_{k}"):
                            try:
                                mem = __import__("german_assistant")._load_memory()
                                mem.get("followup_cache", {}).pop(k, None)
                                __import__("german_assistant")._save_memory(mem)
                                assessment = v.get("assessment")
                                if not assessment:
                                    st.warning("No assessment stored for this entry; regenerated entry will be created on next request.")
                                else:
                                    new = __import__("german_assistant").generate_followup(assessment, force_regen=True)
                                    st.success("Refreshed and re-cached entry.")
                                    st.write(new.get("prompt"))
                            except Exception as e:
                                st.error(f"Failed to refresh: {e}")
                    with col3:
                        if st.button("Delete", key=f"del_{k}"):
                            try:
                                mem = __import__("german_assistant")._load_memory()
                                mem.get("followup_cache", {}).pop(k, None)
                                __import__("german_assistant")._save_memory(mem)
                                st.success("Deleted cache entry")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Failed to delete: {e}")

    # --- Progress tab ---
    with tabs[2]:
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

        # --- Drill (SRS) tab ---
        with st.expander("Drill (Spaced Repetition)", expanded=False):
            st.subheader("Drill (SRS)")
            if get_due_cards is None:
                st.info("SRS module not available. Ensure `srs.py` exists.")
            else:
                mem_path = Path(__file__).parent / "memory.json"
                # Show counts
                due = get_due_cards()
                st.markdown(f"**Due cards:** {len(due)}")

                # Import recent attempts button
                if st.button("Import recent attempts as cards"):
                    attempts = []
                    if mem_path.exists():
                        try:
                            j = json.loads(mem_path.read_text(encoding="utf-8"))
                            attempts = j.get("german_attempts", [])
                        except Exception:
                            attempts = []
                    added = import_attempts(attempts) if import_attempts else 0
                    st.success(f"Imported {added} attempts into SRS deck.")

                # Drill loop
                if not hasattr(st.session_state, "srs_queue") or not st.session_state.srs_queue:
                    st.session_state.srs_queue = [c.get("id") for c in due]

                if st.session_state.srs_queue:
                    cid = st.session_state.srs_queue[0]
                    # load card details from memory
                    mem = {}
                    try:
                        mem = json.loads(mem_path.read_text(encoding="utf-8"))
                    except Exception:
                        mem = {}
                    cards = {c.get("id"): c for c in mem.get("srs_cards", [])}
                    card = cards.get(cid)
                    if not card:
                        st.write("Card not found; skipping.")
                        st.session_state.srs_queue.pop(0)
                    else:
                        st.markdown(f"**Front:** {card.get('front')}")
                        if st.button("Reveal answer"):
                            st.markdown(f"**Back (suggested):** {card.get('back')}")
                        rating = st.slider("Rate your recall (0-5)", min_value=0, max_value=5, value=5)
                        if st.button("Submit rating"):
                            schedule_card(card.get("id"), int(rating))
                            st.success("Rating saved — moved to next card.")
                            # pop and reload due list
                            st.session_state.srs_queue.pop(0)
                            # refresh due list in next render
                            st.experimental_rerun()
                else:
                    st.info("No cards due. Import attempts or wait until next review.")

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