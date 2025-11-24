import os
import platform
import psutil
import requests
import datetime
import json
import time
import math
import ast
import re
import secrets
import string
import hashlib
import base64
import csv
import zipfile
import io
import textwrap
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Iterable
from dotenv import load_dotenv
from termcolor import colored
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from deep_translator import DeeplTranslator
from rich.live import Live
from rich.table import Table
# German assistant integration
try:
    from german_assistant import assess_sentence, generate_tasks
except Exception:
    assess_sentence = None
    generate_tasks = None

# Optional: better colors on Windows terminals
try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

# Optional HTML parser
try:
    from bs4 import BeautifulSoup  # pip install beautifulsoup4
except Exception:
    BeautifulSoup = None

# Optional timezone support
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:
    ZoneInfo = None
    class ZoneInfoNotFoundError(Exception):
        pass

# Optional RSS
try:
    import feedparser  # pip install feedparser
except Exception:
    feedparser = None

# Optional Markdown to HTML
try:
    import markdown  # pip install markdown
except Exception:
    markdown = None

# Optional clipboard
try:
    import pyperclip  # pip install pyperclip
except Exception:
    pyperclip = None

# Optional PDF to text
try:
    from pdfminer.high_level import extract_text as pdf_extract_text  # pip install pdfminer.six
except Exception:
    pdf_extract_text = None

# Optional QR code
try:
    import qrcode  # pip install qrcode[pil]
except Exception:
    qrcode = None

# Optional screenshot
try:
    import mss  # pip install mss
except Exception:
    mss = None

# =========================================================
# 🌟 CONFIGURATION
# =========================================================
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_FILE = PROJECT_ROOT / "memory.json"
LOG_FILE = PROJECT_ROOT / "assistant_log.json"

# HTTP defaults
DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "15"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "IntelliCLI/3.2 (+https://example.local) Python/requests",
)

# Caches (TTL seconds)
CACHE_TTL_WEATHER = 600
CACHE_TTL_NEWS = 300
CACHE_TTL_CURRENCY = 3600
_cache: Dict[str, Dict[str, Tuple[float, Any]]] = {"weather": {}, "news": {}, "currency": {}}

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

def _http_get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """GET JSON with retries and default timeout."""
    last_exc = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            resp = _session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_exc = e
            time.sleep(min(2 ** attempt, 5))
    raise last_exc  # type: ignore

def _http_get_text(url: str) -> str:
    """GET text with retries and default timeout."""
    last_exc = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            resp = _session.get(url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_exc = e
            time.sleep(min(2 ** attempt, 5))
    raise last_exc  # type: ignore

# =========================================================
# 🧩 MEMORY & LOGGING
# =========================================================
def load_json(file: Path, default):
    """Load JSON safely. If empty/corrupt, back it up and return default."""
    if file.exists():
        try:
            if file.stat().st_size == 0:
                return default
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            try:
                backup = file.with_suffix(file.suffix + f".corrupt.{int(time.time())}")
                file.replace(backup)
            except Exception:
                pass
            return default
    return default

def save_json(file: Path, data):
    """Atomically write JSON to avoid partial writes that corrupt the file."""
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(file.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(file)

memory = load_json(MEMORY_FILE, {"notes": [], "knowledge": [], "reminders": [], "todos": []})
log = load_json(LOG_FILE, [])

def add_note(content: str):
    memory["notes"].append({
        "timestamp": datetime.datetime.now().isoformat(),
        "note": content
    })
    save_json(MEMORY_FILE, memory)
    return "📝 Note saved!"

def add_reminder(text: str, due_iso: str):
    memory["reminders"].append({
        "id": f"r-{int(time.time()*1000)}",
        "text": text,
        "due": due_iso,
        "done": False,
        "created": datetime.datetime.now().isoformat()
    })
    save_json(MEMORY_FILE, memory)

def add_todo_item(text: str, due_iso: Optional[str] = None):
    item = {
        "id": f"t-{int(time.time()*1000)}",
        "text": text,
        "due": due_iso,
        "done": False,
        "created": datetime.datetime.now().isoformat(),
        "done_at": None
    }
    memory["todos"].append(item)
    save_json(MEMORY_FILE, memory)
    return item

def log_interaction(user_input, assistant_response):
    log.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user_input,
        "assistant": assistant_response
    })
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1_500_000:
            LOG_FILE.rename(LOG_FILE.with_suffix(".old.json"))
    except Exception:
        pass
    save_json(LOG_FILE, log)

# =========================================================
# 🔒 SAFE CALCULATOR (AST)
# =========================================================
_ALLOWED_FUNCS = {k: getattr(math, k) for k in (
    "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10",
    "exp", "pow", "fabs", "floor", "ceil", "factorial", "degrees", "radians"
)}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

class _SafeEval(ast.NodeVisitor):
    def visit(self, node):
        return super().visit(node)

    def visit_Expression(self, node):  # type: ignore
        return self.visit(node.body)

    def visit_BinOp(self, node):  # type: ignore
        left, right = self.visit(node.left), self.visit(node.right)
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div): return left / right
        if isinstance(node.op, ast.Pow): return left ** right
        if isinstance(node.op, ast.Mod): return left % right
        if isinstance(node.op, ast.FloorDiv): return left // right
        raise ValueError("Operator not allowed")

    def visit_UnaryOp(self, node):  # type: ignore
        val = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd): return +val
        if isinstance(node.op, ast.USub): return -val
        raise ValueError("Unary operator not allowed")

    def visit_Num(self, node):  # py<3.8
        return node.n

    def visit_Constant(self, node):  # py>=3.8
        if isinstance(node.value, (int, float)): return node.value
        raise ValueError("Only int/float constants allowed")

    def visit_Name(self, node):
        if node.id in _ALLOWED_CONSTS: return _ALLOWED_CONSTS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCS:
            args = [self.visit(a) for a in node.args]
            return _ALLOWED_FUNCS[node.func.id](*args)
        raise ValueError("Only math functions allowed")

def safe_eval(expr: str):
    """Safely evaluate a math expression using limited AST and math module."""
    tree = ast.parse(expr, mode="eval")
    return _SafeEval().visit(tree)

# =========================================================
# 🧠 TOOLS (core)
# =========================================================
@tool
def get_weather(city: str) -> str:
    """Get current weather for a city using OpenWeatherMap and return a readable summary."""
    if not OPENWEATHER_API_KEY:
        return "⚠️ Missing OpenWeatherMap API key."
    key = city.lower().strip()
    now = time.time()
    cached = _cache["weather"].get(key)
    if cached and (now - cached[0] < CACHE_TTL_WEATHER):
        return cached[1]
    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        data = _http_get_json(url, params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"})
        if data.get("cod") != 200:
            return f"❌ Error: {data.get('message', 'Could not retrieve weather')}"
        weather = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        out = (
            f"🌤 Weather in {city}:\n"
            f"- Condition: {weather}\n"
            f"- Temperature: {temp}°C\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind Speed: {wind_speed} m/s"
        )
        _cache["weather"][key] = (now, out)
        return out
    except Exception as e:
        return f"❌ Error fetching weather: {str(e)}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression using a safe AST-based parser with common math functions."""
    try:
        result = safe_eval(expression)
        return f"🧮 Result: {result}"
    except Exception as e:
        return f"❌ Error calculating expression: {str(e)}"

@tool
def say_hello(name: str) -> str:
    """Return a friendly greeting for the provided name."""
    return f"👋 Hello {name}! Nice to see you."

@tool
def system_info() -> str:
    """Show OS, Python version, CPU cores/usage, RAM, and system disk usage."""
    try:
        os_info = f"{platform.system()} {platform.release()}"
        python_version = platform.python_version()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk_root = os.path.abspath(os.sep)
        disk = psutil.disk_usage(disk_root)
        return (
            f"💻 System Info:\n"
            f"- OS: {os_info}\n"
            f"- Python: {python_version}\n"
            f"- CPU Cores: {cpu_count}\n"
            f"- CPU Usage: {cpu_usage}%\n"
            f"- RAM: {ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB\n"
            f"- Disk: {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB ({disk.percent}%)"
        )
    except Exception as e:
        return f"❌ Error retrieving system info: {str(e)}"

@tool
def get_time() -> str:
    """Return the current local date and time as a formatted string."""
    now = datetime.datetime.now()
    return f"⏰ Current Date & Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

# =========================================================
# 🌍 Timezones and locales
# =========================================================
CITY_TO_TZ = {
    "tokyo": "Asia/Tokyo", "berlin": "Europe/Berlin", "munich": "Europe/Berlin",
    "paris": "Europe/Paris", "london": "Europe/London", "new york": "America/New_York",
    "nyc": "America/New_York", "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles", "chicago": "America/Chicago", "toronto": "America/Toronto",
    "vancouver": "America/Vancouver", "mexico city": "America/Mexico_City", "sao paulo": "America/Sao_Paulo",
    "madrid": "Europe/Madrid", "rome": "Europe/Rome", "istanbul": "Europe/Istanbul", "moscow": "Europe/Moscow",
    "cairo": "Africa/Cairo", "johannesburg": "Africa/Johannesburg", "dubai": "Asia/Dubai",
    "delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata", "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong", "seoul": "Asia/Seoul", "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai", "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne"
}

def _resolve_tz(place: str) -> Optional[str]:
    s = place.strip()
    if "/" in s:
        return s
    return CITY_TO_TZ.get(s.lower())

@tool
def get_time_in(place: str) -> str:
    """Get current date & time for a city or IANA timezone (e.g., 'Tokyo' or 'Asia/Tokyo')."""
    if ZoneInfo is None:
        return "⚠️ Timezone support missing. Use Python 3.9+ or `pip install tzdata`."
    tzid = _resolve_tz(place)
    if not tzid:
        return "❌ Unknown city/timezone. Try an IANA timezone like 'Asia/Tokyo'."
    try:
        tz = ZoneInfo(tzid)
    except ZoneInfoNotFoundError:
        return "⚠️ Timezone database not found. Run: pip install tzdata"
    now = datetime.datetime.now(tz)
    offset = now.utcoffset() or datetime.timedelta(0)
    sign = "+" if offset >= datetime.timedelta(0) else "-"
    total = int(abs(offset).total_seconds())
    hh, mm = divmod(total // 60, 60)
    label = tzid if "/" in place else place.title()
    return f"⏰ {label}: {now.strftime('%Y-%m-%d %H:%M:%S')} ({tz.key}, UTC{sign}{hh:02d}:{mm:02d})"

# =========================================================
# 📰 News, web, content
# =========================================================
@tool
def get_news(topic: str = "technology") -> str:
    """Fetch top news headlines for a topic via NewsAPI and format the first few results."""
    if not NEWS_API_KEY:
        return "⚠️ Missing News API key."
    key = topic.lower().strip()
    now = time.time()
    cached = _cache["news"].get(key)
    if cached and (now - cached[0] < CACHE_TTL_NEWS):
        return cached[1]
    try:
        url = "https://newsapi.org/v2/top-headlines"
        data = _http_get_json(url, params={"q": topic, "language": "en", "apiKey": NEWS_API_KEY})
        if data.get("status") != "ok":
            return f"❌ Error fetching news: {data.get('message', 'Unknown error')}"
        articles = data.get("articles", [])[:5]
        headlines = "\n".join([f"- {a.get('title')}" for a in articles if a.get('title')])
        out = f"📰 Top News '{topic}':\n{headlines or 'No results.'}"
        _cache["news"][key] = (now, out)
        return out
    except Exception as e:
        return f"❌ Error fetching news: {str(e)}"

@tool
def wiki_search(query: str) -> str:
    """Search Wikipedia for a summary."""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        data = _http_get_json(url)
        if "title" not in data:
            return "❌ No results found."
        return f"📘 {data.get('title')}: {data.get('extract', 'No summary found.')}"
    except Exception as e:
        return f"❌ Error fetching Wikipedia info: {str(e)}"

@tool
def search_web(query: str) -> str:
    """DuckDuckGo Instant Answer search (top results)."""
    try:
        data = _http_get_json("https://api.duckduckgo.com/",
                              params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1})
        lines = []
        if data.get("AbstractText"):
            lines.append(data["AbstractText"])
        for rt in data.get("RelatedTopics", [])[:5]:
            if isinstance(rt, dict) and rt.get("Text"):
                lines.append(f"- {rt['Text']}")
        return f"🔎 Results for '{query}':\n" + ("\n".join(lines) or "No results.")
    except Exception as e:
        return f"❌ Web search error: {e}"

@tool
def fetch_url(url: str, max_chars: int = 1200) -> str:
    """Fetch URL and return a summarized plain-text snippet."""
    try:
        html = _http_get_text(url)
        if not BeautifulSoup:
            txt = re.sub(r"<[^>]+>", " ", html)
            txt = re.sub(r"\s+", " ", txt).strip()
            return f"🌐 Content (truncated): {txt[:max_chars]}"
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = " ".join(soup.get_text(separator=" ").split())
        return f"🌐 Content (truncated): {text[:max_chars]}"
    except Exception as e:
        return f"❌ Fetch error: {e}"

@tool
def fetch_rss(url: str, limit: int = 5) -> str:
    """Fetch RSS/Atom feed titles. Requires feedparser."""
    if not feedparser:
        return "⚠️ Install feedparser to use RSS: pip install feedparser"
    try:
        feed = feedparser.parse(url)
        items = feed.get("entries", [])[:max(1, min(limit, 20))]
        if not items:
            return "No items."
        lines = [f"- {e.get('title', 'Untitled')}" for e in items]
        return "📰 Feed:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ RSS error: {e}"

# =========================================================
# 🌐 Translation & text utilities
# =========================================================
@tool
def translate_text(text: str, target_lang: str = "EN") -> str:
    """Translate text using DeepL (via deep_translator)."""
    try:
        translated = DeeplTranslator(target=target_lang).translate(text)
        return f"🌍 Translation ({target_lang}): {translated}"
    except Exception as e:
        return f"❌ Translation error: {e}"

@tool
def summarize_text(text: str, max_chars: int = 500) -> str:
    """Very simple length-limited summarizer (non-ML): squeezes whitespace and truncates smartly."""
    txt = " ".join(text.split())
    if len(txt) <= max_chars:
        return txt
    # Try to cut at sentence boundary near limit
    cut = txt[:max_chars]
    last_dot = cut.rfind(". ")
    if last_dot > max_chars * 0.6:
        return cut[:last_dot+1] + " …"
    return cut + " …"

@tool
def slugify(text: str) -> str:
    """Create a filesystem-friendly slug from text."""
    s = re.sub(r"[^a-zA-Z0-9\-_\s]", "", text).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s or "item"

# =========================================================
# 📅 Reminders & Todos
# =========================================================
def _parse_when(when: str) -> Optional[datetime.datetime]:
    when = when.strip().lower()
    now = datetime.datetime.now()
    m = re.match(r"in\s+(\d+)\s*(s|sec|secs|second|seconds)$", when)
    if m:
        return now + datetime.timedelta(seconds=int(m.group(1)))
    m = re.match(r"in\s+(\d+)\s*(m|min|mins|minute|minutes)$", when)
    if m:
        return now + datetime.timedelta(minutes=int(m.group(1)))
    m = re.match(r"in\s+(\d+)\s*(h|hr|hrs|hour|hours)$", when)
    if m:
        return now + datetime.timedelta(hours=int(m.group(1)))
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(when, fmt)
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=9, minute=0, second=0)
            return dt
        except Exception:
            pass
    return None

def _check_reminders_now() -> str:
    now = datetime.datetime.now()
    due = []
    for r in memory.get("reminders", []):
        if not r.get("done") and datetime.datetime.fromisoformat(r["due"]) <= now:
            due.append(r)
            r["done"] = True
    if due:
        save_json(MEMORY_FILE, memory)
        lines = [f"🔔 {d['text']} (due {d['due']})" for d in due]
        return "\n".join(lines)
    return "No reminders due."

@tool
def set_reminder(text: str, when: str) -> str:
    """Set a reminder. Examples: 'in 20 min', 'in 2 hours', '2025-12-31 18:00'."""
    dt = _parse_when(when)
    if not dt:
        return "❌ Unable to parse time. Try 'in 10 min' or 'YYYY-MM-DD HH:MM'."
    add_reminder(text, dt.isoformat())
    return f"⏳ Reminder set for {dt.strftime('%Y-%m-%d %H:%M')}"

@tool
def check_reminders() -> str:
    """Check for due reminders and mark them delivered."""
    return _check_reminders_now()

@tool
def add_todo(text: str, due: Optional[str] = None) -> str:
    """Add a todo item, optionally with due (like 'in 2h' or 'YYYY-MM-DD')."""
    due_iso = None
    if due:
        dt = _parse_when(due)
        if dt:
            due_iso = dt.isoformat()
    item = add_todo_item(text, due_iso)
    return f"✅ Todo added [{item['id']}]{' due ' + due if due else ''}: {item['text']}"

@tool
def list_todos(show_done: bool = True) -> str:
    """List todos."""
    items = memory.get("todos", [])
    if not items:
        return "No todos."
    lines = []
    for i, t in enumerate(items, 1):
        if (not show_done) and t.get("done"):
            continue
        status = "✅" if t.get("done") else "⬜"
        due = f" (due {t['due']})" if t.get("due") else ""
        lines.append(f"{i}. {status} {t['text']}{due} [{t['id']}]")
    return "\n".join(lines) if lines else "No todos."

@tool
def complete_todo(id_or_index: str) -> str:
    """Mark a todo done by id or list index (1-based)."""
    items = memory.get("todos", [])
    if not items:
        return "No todos."
    target = None
    if id_or_index.isdigit():
        idx = int(id_or_index) - 1
        if 0 <= idx < len(items):
            target = items[idx]
    else:
        for t in items:
            if t.get("id") == id_or_index:
                target = t
                break
    if not target:
        return "❌ Not found."
    if target.get("done"):
        return "Already completed."
    target["done"] = True
    target["done_at"] = datetime.datetime.now().isoformat()
    save_json(MEMORY_FILE, memory)
    return f"✅ Completed: {target['text']}"

# =========================================================
# 💱 Converters
# =========================================================
@tool
def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """Convert common units (length, mass, temperature, volume). Examples: 10, 'km', 'm'; 72, 'F', 'C'."""
    f = from_unit.strip().lower()
    t = to_unit.strip().lower()
    # Temperature
    if f in {"c", "celsius"} and t in {"f", "fahrenheit"}:
        return f"{value} C = {value * 9/5 + 32:.2f} F"
    if f in {"f", "fahrenheit"} and t in {"c", "celsius"}:
        return f"{value} F = {(value - 32) * 5/9:.2f} C"
    if f in {"c", "celsius"} and t in {"k", "kelvin"}:
        return f"{value} C = {value + 273.15:.2f} K"
    if f in {"k", "kelvin"} and t in {"c", "celsius"}:
        return f"{value} K = {value - 273.15:.2f} C"
    if f in {"f", "fahrenheit"} and t in {"k", "kelvin"}:
        return f"{value} F = {((value - 32) * 5/9) + 273.15:.2f} K"
    if f in {"k", "kelvin"} and t in {"f", "fahrenheit"}:
        return f"{value} K = {(value - 273.15) * 9/5 + 32:.2f} F"
    # Length (m-based)
    length = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
    if f in length and t in length:
        meters = value * length[f]
        return f"{value} {from_unit} = {meters/length[t]:.6g} {to_unit}"
    # Mass (kg-based)
    mass = {"mg": 1e-6, "g": 1e-3, "kg": 1.0, "lb": 0.45359237, "oz": 0.0283495231}
    if f in mass and t in mass:
        kg = value * mass[f]
        return f"{value} {from_unit} = {kg/mass[t]:.6g} {to_unit}"
    # Volume (L-based)
    vol = {"ml": 0.001, "l": 1.0, "gal": 3.785411784}
    if f in vol and t in vol:
        liters = value * vol[f]
        return f"{value} {from_unit} = {liters/vol[t]:.6g} {to_unit}"
    return "❌ Unsupported units."

@tool
def currency_convert(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert currency using exchangerate.host (no API key)."""
    frm = from_currency.strip().upper()
    to = to_currency.strip().upper()
    key = f"{frm}->{to}"
    now = time.time()
    cached = _cache["currency"].get(key)
    if cached and (now - cached[0] < CACHE_TTL_CURRENCY):
        rate = cached[1]
        return f"{amount:.2f} {frm} = {amount * rate:.2f} {to} (rate {rate:.4f}, cached)"
    try:
        data = _http_get_json("https://api.exchangerate.host/convert", params={"from": frm, "to": to, "amount": 1})
        if not data.get("success"):
            return f"❌ Currency API error."
        rate = float(data["result"])
        _cache["currency"][key] = (now, rate)
        return f"{amount:.2f} {frm} = {amount * rate:.2f} {to} (rate {rate:.4f})"
    except Exception as e:
        return f"❌ Currency error: {e}"

# =========================================================
# 🗂️ Files & data helpers
# =========================================================
def _ensure_in_project(p: Path) -> bool:
    try:
        rp = p.resolve()
        return (PROJECT_ROOT in rp.parents) or (rp == PROJECT_ROOT)
    except Exception:
        return False

@tool
def list_files(path: str = ".") -> str:
    """List files and folders (scoped to project root)."""
    try:
        base = (PROJECT_ROOT / path).resolve()
        if not _ensure_in_project(base):
            return "❌ Path outside project root."
        items = []
        for p in base.iterdir():
            kind = "DIR " if p.is_dir() else "FILE"
            size = f"{p.stat().st_size}B" if p.is_file() else ""
            items.append(f"{kind}\t{p.relative_to(PROJECT_ROOT)}\t{size}")
        return "\n".join(sorted(items)) or "(empty)"
    except Exception as e:
        return f"❌ list_files error: {e}"

@tool
def read_text_file(rel_path: str, max_chars: int = 8000) -> str:
    """Read a text file from project root."""
    try:
        p = (PROJECT_ROOT / rel_path)
        if not _ensure_in_project(p):
            return "❌ Path outside project root."
        if not p.exists() or not p.is_file():
            return "❌ File not found."
        data = p.read_text(encoding="utf-8", errors="replace")
        return data if len(data) <= max_chars else data[:max_chars] + "\n…(truncated)"
    except Exception as e:
        return f"❌ read_text_file error: {e}"

@tool
def write_text_file(rel_path: str, content: str, mode: str = "w") -> str:
    """Write text to a file in project root (mode: w/a)."""
    try:
        if mode not in {"w", "a"}:
            return "❌ Invalid mode. Use 'w' or 'a'."
        p = (PROJECT_ROOT / rel_path)
        if not _ensure_in_project(p):
            return "❌ Path outside project root."
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        return f"✅ Wrote {len(content)} chars to {p.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ write_text_file error: {e}"

@tool
def csv_to_json(rel_path: str, delimiter: str = ",") -> str:
    """Convert a CSV file in project root to JSON (string)."""
    try:
        p = (PROJECT_ROOT / rel_path)
        if not (_ensure_in_project(p) and p.exists()):
            return "❌ CSV not found."
        with open(p, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f, delimiter=delimiter)
            rows = list(rdr)
        return json.dumps(rows, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"❌ csv_to_json error: {e}"

@tool
def json_to_csv(rel_path_in: str, rel_path_out: str, delimiter: str = ",") -> str:
    """Convert a JSON array of objects in project root to CSV and save to rel_path_out."""
    try:
        pi = (PROJECT_ROOT / rel_path_in)
        po = (PROJECT_ROOT / rel_path_out)
        if not (_ensure_in_project(pi) and _ensure_in_project(po) and pi.exists()):
            return "❌ Path error."
        data = json.loads(pi.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            return "❌ JSON must be a non-empty list of objects."
        headers = sorted({k for row in data for k in row.keys()})
        with open(po, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
            wr.writeheader()
            for row in data:
                wr.writerow({k: row.get(k, "") for k in headers})
        return f"✅ Wrote CSV: {po.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ json_to_csv error: {e}"

@tool
def zip_paths(paths: List[str], out_zip: str = "archive.zip") -> str:
    """Zip multiple project-root paths into one ZIP."""
    try:
        out = (PROJECT_ROOT / out_zip)
        if not _ensure_in_project(out):
            return "❌ Output path outside project root."
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rp in paths:
                p = (PROJECT_ROOT / rp)
                if not _ensure_in_project(p) or not p.exists():
                    return f"❌ Invalid path: {rp}"
                if p.is_dir():
                    for sub in p.rglob("*"):
                        if sub.is_file():
                            zf.write(sub, sub.relative_to(PROJECT_ROOT))
                else:
                    zf.write(p, p.relative_to(PROJECT_ROOT))
        return f"✅ Created {out.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ zip_paths error: {e}"

@tool
def unzip_to(rel_zip: str, dest_dir: str = ".") -> str:
    """Extract a ZIP within project root to dest_dir."""
    try:
        z = (PROJECT_ROOT / rel_zip)
        dest = (PROJECT_ROOT / dest_dir)
        if not (z.exists() and _ensure_in_project(z) and _ensure_in_project(dest)):
            return "❌ Path error."
        with zipfile.ZipFile(z, "r") as zf:
            for member in zf.namelist():
                target = (dest / member).resolve()
                if not _ensure_in_project(target):
                    return "❌ Unsafe ZIP entry."
            zf.extractall(dest)
        return f"✅ Extracted to {dest.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ unzip_to error: {e}"

@tool
def sha256_string(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

@tool
def sha256_file(rel_path: str) -> str:
    """Compute SHA-256 hash of a file in project root."""
    try:
        p = (PROJECT_ROOT / rel_path)
        if not (_ensure_in_project(p) and p.exists() and p.is_file()):
            return "❌ File not found."
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"❌ sha256_file error: {e}"

@tool
def b64_encode(text: str) -> str:
    """Base64-encode a string."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")

@tool
def b64_decode(b64_text: str) -> str:
    """Base64-decode a string."""
    try:
        return base64.b64decode(b64_text.encode("ascii")).decode("utf-8", errors="replace")
    except Exception as e:
        return f"❌ b64_decode error: {e}"

# =========================================================
# 🖼️ Media helpers
# =========================================================
@tool
def make_qr(text: str, out_path: str = "qr.png") -> str:
    """Create a QR code PNG in the project root. Requires qrcode."""
    if not qrcode:
        return "⚠️ Install qrcode: pip install qrcode[pil]"
    try:
        p = (PROJECT_ROOT / out_path)
        if not _ensure_in_project(p):
            return "❌ Path outside project root."
        img = qrcode.make(text)
        img.save(p)
        return f"✅ Saved QR: {p.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ make_qr error: {e}"

@tool
def pdf_to_text(rel_path: str, max_chars: int = 5000) -> str:
    """Extract text from a PDF in project root. Requires pdfminer.six."""
    if not pdf_extract_text:
        return "⚠️ Install pdfminer.six to extract PDF text."
    try:
        p = (PROJECT_ROOT / rel_path)
        if not (_ensure_in_project(p) and p.exists()):
            return "❌ PDF not found."
        text = pdf_extract_text(str(p))
        text = " ".join(text.split())
        return text if len(text) <= max_chars else text[:max_chars] + " …"
    except Exception as e:
        return f"❌ pdf_to_text error: {e}"

@tool
def md_to_html(rel_md_in: str, rel_html_out: str) -> str:
    """Convert Markdown file to HTML file in project root. Requires markdown."""
    if not markdown:
        return "⚠️ Install markdown: pip install markdown"
    try:
        inp = (PROJECT_ROOT / rel_md_in)
        out = (PROJECT_ROOT / rel_html_out)
        if not (_ensure_in_project(inp) and _ensure_in_project(out) and inp.exists()):
            return "❌ Path error."
        html = markdown.markdown(inp.read_text(encoding="utf-8"))
        out.write_text(html, encoding="utf-8")
        return f"✅ Wrote HTML: {out.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ md_to_html error: {e}"

@tool
def take_screenshot(out_path: str = "screenshot.png") -> str:
    """Take a screenshot and save PNG to project root. Requires mss."""
    if not mss:
        return "⚠️ Install mss: pip install mss"
    try:
        p = (PROJECT_ROOT / out_path)
        if not _ensure_in_project(p):
            return "❌ Path outside project root."
        with mss.mss() as sct:
            sct.shot(output=str(p))
        return f"✅ Saved screenshot: {p.relative_to(PROJECT_ROOT)}"
    except Exception as e:
        return f"❌ screenshot error: {e}"

# =========================================================
# 🧰 Utilities
# =========================================================
@tool
def regex_replace(text: str, pattern: str, repl: str, flags: str = "") -> str:
    """Regex replace with optional flags: i,m,s."""
    fl = 0
    if "i" in flags: fl |= re.IGNORECASE
    if "m" in flags: fl |= re.MULTILINE
    if "s" in flags: fl |= re.DOTALL
    return re.sub(pattern, repl, text, flags=fl)

@tool
def password_generate(length: int = 16, digits: bool = True, symbols: bool = True) -> str:
    """Generate a random password."""
    chars = string.ascii_letters
    if digits: chars += string.digits
    if symbols: chars += "!@#$%^&*()-_=+[]{};:,.?/\\"
    return "".join(secrets.choice(chars) for _ in range(max(4, min(length, 128))))

@tool
def copy_to_clipboard(text: str) -> str:
    """Copy text to clipboard. Requires pyperclip."""
    if not pyperclip:
        return "⚠️ Install pyperclip to use clipboard."
    try:
        pyperclip.copy(text)
        return "✅ Copied to clipboard."
    except Exception as e:
        return f"❌ Clipboard error: {e}"

@tool
def paste_from_clipboard() -> str:
    """Paste text from clipboard. Requires pyperclip."""
    if not pyperclip:
        return "⚠️ Install pyperclip to use clipboard."
    try:
        return pyperclip.paste() or ""
    except Exception as e:
        return f"❌ Clipboard error: {e}"

# =========================================================
# 📝 Notes
# =========================================================
@tool
def save_note(content: str) -> str:
    """Save a note to persistent memory.json and confirm."""
    return add_note(content)

@tool
def recall_notes() -> str:
    """List all saved notes with timestamps, or indicate if none exist."""
    if not memory["notes"]:
        return "🗒 No notes found."
    return "\n".join([f"- {n['note']} (saved {n['timestamp']})" for n in memory["notes"]])

# =========================================================
# 🧭 SYSTEM PROMPT
# =========================================================
ASSISTANT_SYSTEM_PROMPT = (
    "You are Intelli CLI, a helpful, concise assistant. "
    "Use tools when they clearly help. "
    "For time-in-city requests, always call get_time_in and never guess. "
    "Prefer safe calculations and avoid making up URLs. "
    "Keep responses short and actionable."
)

# =========================================================
# ⚙️ MAIN EXECUTION
# =========================================================
def print_due_reminders_once():
    try:
        msg = _check_reminders_now()
        if msg and not msg.startswith("No reminders"):
            print(colored(msg, "magenta"))
    except Exception:
        pass

def export_notes_markdown() -> str:
    if not memory["notes"]:
        return "No notes to export."
    out = ["# Notes Export"]
    for n in memory["notes"]:
        out.append(f"- {n['timestamp']}: {n['note']}")
    path = PROJECT_ROOT / "notes_export.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return f"Exported to {path.name}"

def main():
    print(colored("🤖 Welcome to Intelli CLI 3.2 (Many-Tools Edition)!", "cyan", attrs=["bold"]))
    print(colored("Type 'quit' to exit. Use /help for local commands.", "yellow"))

    model = ChatOpenAI(temperature=0.2, model=OPENAI_MODEL)
    tools = [
        # core
        get_weather, calculator, say_hello, system_info, get_time, get_time_in,
        get_news, wiki_search, search_web, fetch_url, fetch_rss,
        translate_text, summarize_text, slugify,
        # reminders & todos
        set_reminder, check_reminders, add_todo, list_todos, complete_todo,
        # converters
        unit_convert, currency_convert,
        # files & data
        list_files, read_text_file, write_text_file, csv_to_json, json_to_csv,
        zip_paths, unzip_to, sha256_string, sha256_file, b64_encode, b64_decode,
        # media and misc
        make_qr, pdf_to_text, md_to_html, take_screenshot,
        regex_replace, password_generate, copy_to_clipboard, paste_from_clipboard,
        save_note, recall_notes,
    ]

    agent_executor = create_react_agent(model, tools)

    conversation: List[Any] = [SystemMessage(content=ASSISTANT_SYSTEM_PROMPT)]

    def handle_slash_commands(cmd: str) -> Optional[bool]:
        if cmd == "/help":
            print(colored("Local commands:", "yellow"))
            print("- /help               Show this help")
            print("- /clear              Clear chat memory")
            print("- /notes export       Export notes to notes_export.md")
            print("- /reminders          Check due reminders now")
            print("- /tools              List tool names")
            return True
        if cmd == "/clear":
            del conversation[1:]
            print(colored("Memory cleared.", "yellow"))
            return True
        if cmd == "/notes export":
            print(colored(export_notes_markdown(), "yellow"))
            return True
        if cmd == "/reminders":
            print_due_reminders_once()
            return True
        if cmd == "/tools":
            print(", ".join(sorted([t.name for t in tools])))
            return True
        if cmd.startswith("/german"):
            # Usage: /german <sentence>
            parts = cmd.split(" ", 1)
            if len(parts) == 1 or not parts[1].strip():
                print(colored("Usage: /german <German sentence to assess>", "yellow"))
                return True
            if assess_sentence is None:
                print(colored("german_assistant not available. Please add german_assistant.py.", "red"))
                return True
            sentence = parts[1].strip()
            res = assess_sentence(sentence)
            print(colored(f"Score: {res.get('score')}", "cyan"))
            print(colored("Correction:", "yellow"))
            print(res.get('correction'))
            if res.get('explanations'):
                print(colored("Explanations:", "yellow"))
                for e in res.get('explanations'):
                    print(f"- {e}")
            # generate a couple of tasks
            tasks = generate_tasks(sentence, num_tasks=2) if generate_tasks else []
            if tasks:
                print(colored("Suggested tasks:", "yellow"))
                for t in tasks:
                    print(f"- {t.get('type')}: {t.get('prompt')}")
            return True
        return None

    while True:
        print_due_reminders_once()
        user_input = input(colored("\nYou: ", "green")).strip()
        if user_input.lower() in {"quit", "exit"}:
            print(colored("👋 Goodbye!", "cyan"))
            break

        if user_input.startswith("/"):
            handled = handle_slash_commands(user_input)
            if handled:
                continue

        try:
            conversation.append(HumanMessage(content=user_input))
            result = agent_executor.invoke({"messages": conversation})
            ai_text = ""
            try:
                msgs = result.get("messages", [])
                for m in reversed(msgs):
                    if isinstance(m, AIMessage) or getattr(m, "type", "") == "ai":
                        ai_text = m.content
                        break
                if not ai_text and msgs:
                    ai_text = msgs[-1].content
            except Exception:
                ai_text = str(result)
            print(colored(ai_text, "white"))
            conversation.append(AIMessage(content=ai_text))
            log_interaction(user_input, ai_text)
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