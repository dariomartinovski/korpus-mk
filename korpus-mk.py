import json
import logging
import sqlite3
import os
from datetime import date, time
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
import pytz
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WORDS_FILE = "words_randomized_all.json"
DB_FILE = "subscribers.db"
SEND_HOUR = 18
SEND_MINUTE = 15
TIMEZONE = "Europe/Skopje"

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Flask (for Render to keep the service alive) ---
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# --- Database ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            first_name TEXT,
            subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_subscriber(chat_id, first_name):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR IGNORE INTO subscribers (chat_id, first_name) VALUES (?, ?)",
        (chat_id, first_name)
    )
    conn.commit()
    conn.close()

def remove_subscriber(chat_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT chat_id, first_name FROM subscribers").fetchall()
    conn.close()
    return rows

def is_subscribed(chat_id):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT 1 FROM subscribers WHERE chat_id = ?", (chat_id,)).fetchone()
    conn.close()
    return row is not None

# --- Words ---
def load_words():
    with open(WORDS_FILE, encoding="utf-8") as f:
        words = json.load(f)
    return [w for w in words if w.get("difficulty", 0) >= 5]

def pick_word(words):
    day_index = date.today().timetuple().tm_yday
    return words[day_index % len(words)]

def build_message(entry):
    return (
        f"📖 *Збор на денот*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔤 *{entry['word']}*\n\n"
        f"📝 _{entry['type']}_\n\n"
        f"📌 *Значење:*\n{entry['definition']}"
    )

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name

    if is_subscribed(chat_id):
        await update.message.reply_text(
            f"👋 Веќе си претплатен, {first_name}! Ќе добиваш збор на денот секој ден во {SEND_HOUR:02d}:{SEND_MINUTE:02d}ч.\n\n"
            f"Напиши /zbor за да го добиеш денешниот збор."
        )
        return

    add_subscriber(chat_id, first_name)

    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)

    subscribers = get_all_subscribers()
    await update.message.reply_text(
        f"👋 Добредојде, {first_name}! Претплатен си на *Збор на денот*.\n"
        f"Ќе добиваш порака секој ден во {SEND_HOUR:02d}:{SEND_MINUTE:02d}ч.\n\n"
        f"Еве го денешниот збор:\n\n{message}",
        parse_mode="Markdown"
    )
    logging.info(f"New subscriber: {first_name} ({chat_id}). Total: {len(subscribers)}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name

    if not is_subscribed(chat_id):
        await update.message.reply_text("Не си претплатен. Напиши /start за да се претплатиш.")
        return

    remove_subscriber(chat_id)
    await update.message.reply_text(
        f"👋 Се одјавивте, {first_name}. Нема да добивате повеќе пораки.\n"
        f"Напиши /start ако сакаш да се претплатиш повторно."
    )
    logging.info(f"Unsubscribed: {first_name} ({chat_id})")

async def zbor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)
    await update.message.reply_text(message, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_all_subscribers()
    await update.message.reply_text(f"📊 Вкупно претплатници: {len(subscribers)}")

# --- Scheduled daily send ---
async def send_daily_word(context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)
    subscribers = get_all_subscribers()

    logging.info(f"Sending daily word to {len(subscribers)} subscribers...")

    failed = 0
    for chat_id, first_name in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Failed to send to {first_name} ({chat_id}): {e}")
            remove_subscriber(chat_id)
            failed += 1

    logging.info(f"Daily word sent. Failed/removed: {failed}")

# --- Main ---
if __name__ == "__main__":
    init_db()

    # Start Flask in background thread
    Thread(target=run_flask, daemon=True).start()

    tz = pytz.timezone(TIMEZONE)
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("stop", stop))
    bot_app.add_handler(CommandHandler("zbor", zbor))
    bot_app.add_handler(CommandHandler("stats", stats))

    bot_app.job_queue.run_daily(
        send_daily_word,
        time=time(hour=SEND_HOUR, minute=SEND_MINUTE, tzinfo=tz)
    )

    print(f"🤖 Bot is running... Daily word at {SEND_HOUR:02d}:{SEND_MINUTE:02d} {TIMEZONE}")
    bot_app.run_polling()