# 🇩🇪 German Tutor

A focused German learning assistant to help you practice and demonstrate your progress. Built with Python and Streamlit.

## ✨ Features

- **Sentence Assessment**: Get instant feedback on your German sentences with scores, corrections, and explanations
- **Task Generation**: Generate practice exercises (fill-in-the-blank, multiple choice, translation, etc.)
- **Conversational Tutor**: Interactive practice with follow-up prompts based on your mistakes
- **Spaced Repetition (SRS)**: Import your mistakes as flashcards and review them using the SM-2 algorithm
- **Study Streaks & Gamification**: Track your daily practice with streaks and badges
- **Speech Practice**: Transcribe German audio and generate text-to-speech (requires OpenAI API key)
- **Placement Test**: Determine your current German level (A1-C2)
- **Progress Tracking**: Visualize your improvement over time

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment (optional, for speech features):**
   Create a `.env` file:
   ```
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-4o-mini
   ```

3. **Run the app:**
   ```bash
   streamlit run app_streamlit.py
   ```

4. **Start learning!**
   - Open the app in your browser
   - Go to the "Practice" tab to assess sentences
   - Use "Conversation" for interactive practice
   - Check "Progress" to see your improvement

## 📚 Project Structure

```
├── app_streamlit.py          # Main Streamlit UI
├── german_assistant.py       # Core assessment & task generation
├── srs.py                    # Spaced Repetition System (SM-2)
├── streaks.py                # Gamification & streak tracking
├── placement_test.py         # Level placement test
├── speech_utils.py           # Speech transcription & TTS
├── utils.py                  # JSON utilities
├── data/
│   └── german_lessons.json   # Sample lesson data
├── memory.json               # User data (attempts, cards, streaks)
└── german_persona.json       # Tutor preferences
```

## 🎯 Usage

### Practice Tab
Enter a German sentence and get:
- A score (0-100)
- Suggested corrections
- Grammar explanations
- Practice tasks

### Conversation Tab
Have a conversation in German:
- Get feedback on each sentence
- Receive follow-up prompts based on your mistakes
- Track common error patterns

### Progress Tab
View your learning history:
- Recent attempts with scores
- Progress chart over time
- Average score metrics

### Speech Tab (Beta)
- Upload audio files (wav/mp3/m4a/ogg) for transcription
- Record directly from microphone (if `streamlit-audio-recorder` installed)
- Generate text-to-speech for any German text

### Drill (SRS) Tab
- Review flashcards created from your mistakes
- Rate your recall (0-5)
- Cards are scheduled using spaced repetition
- Import recent attempts as new cards

### Preferences Tab
- Set your default level (A1-A2-B1-B2)
- Adjust correction strictness
- Run placement test
- Manage gamification data

## 🧩 Tech Stack

- **Python 3.10+**
- **Streamlit** - Web UI
- **Pandas** - Data visualization
- **OpenAI API** (optional) - Speech features and follow-up generation
- **gTTS** (optional) - Text-to-speech fallback

## 📦 Dependencies

Core:
- `streamlit` - Web framework
- `pandas` - Data analysis

Optional (for enhanced features):
- `openai` - Speech transcription & TTS
- `gTTS` - Text-to-speech fallback
- `streamlit-audio-recorder` - Microphone recording
- `python-dotenv` - Environment variables

## 💡 How It Works

1. **Assessment**: Uses heuristics to check capitalization, verb position, articles, and punctuation
2. **Task Generation**: Creates exercises based on your sentence structure
3. **SRS**: Implements SM-2 algorithm for spaced repetition
4. **Streaks**: Tracks daily visits and assessments to build habits
5. **Follow-ups**: Uses OpenAI (if available) or heuristics to generate practice prompts

## 🔧 Configuration

Edit `german_persona.json` to customize:
- Default level (A1, A2, B1, B2)
- Correction strictness (gentle, balanced, strict)
- Whether to save attempts

## 📊 Data Storage

All data is stored locally in `memory.json`:
- `german_attempts` - Your practice history
- `srs_cards` - Flashcards for spaced repetition
- `study_activity` - Streaks and badges
- `learner_level` - Your current level
- `german_mistakes` - Common error patterns

## 🛠️ Troubleshooting

- **Import errors**: Make sure all files are in the same directory
- **Speech not working**: Set `OPENAI_API_KEY` in `.env` file
- **Audio recorder not working**: Install `streamlit-audio-recorder` or use file upload instead

## 📜 License

MIT License – free to use and modify.
