import json
import logging
import psycopg2
import os
import random
from datetime import date, time, datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
import asyncio
from difflib import get_close_matches
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WORDS_FILE = "words_randomized_all.json"
TIMEZONE = "Europe/Skopje"
DEFAULT_SEND_TIME = "11:00"

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Flask ---
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    words = load_words()
    entry = pick_word(words)

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    default_hour, default_minute = map(int, DEFAULT_SEND_TIME.split(":"))
    next_send = now.replace(hour=default_hour, minute=default_minute, second=0, microsecond=0)
    if now >= next_send:
        next_send += timedelta(days=1)
    diff = int((next_send - now).total_seconds()) * 1000

    return f"""<!DOCTYPE html>
<html lang="mk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>КорпусМК — Збор на денот</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #20232e; color: #e8e8e8; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem 1rem; }}
    .page {{ max-width: 480px; width: 100%; text-align: center; }}
    .label {{ font-size: 12px; color: #666; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.75rem; }}
    hr {{ border: none; border-top: 1px solid #2e3140; margin: 1.25rem 0; }}
    .word {{ font-size: 44px; font-weight: 500; margin: 0.5rem 0; }}
    .badge {{ display: inline-block; font-size: 12px; padding: 3px 12px; border-radius: 20px; background: #2a2d3a; color: #888; margin-bottom: 1.75rem; border: 1px solid #333645; }}
    .card {{ background: #272a35; border: 1px solid #2e3140; border-radius: 12px; padding: 1.25rem 1.5rem; text-align: left; margin-bottom: 1rem; }}
    .card-label {{ font-size: 11px; color: #555; margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .card-text {{ font-size: 15px; line-height: 1.65; color: #ccc; }}
    .timer-wrap {{ margin-top: 2.5rem; padding-top: 1.5rem; border-top: 1px solid #2e3140; }}
    .timer-label {{ font-size: 12px; color: #555; margin-bottom: 0.5rem; }}
    .timer {{ font-size: 32px; font-weight: 500; font-variant-numeric: tabular-nums; letter-spacing: 0.04em; color: #e8e8e8; }}
  </style>
</head>
<body>
  <div class="page">
    <p class="label">🇲🇰 збор на денот</p>
    <hr>
    <p class="word">{entry['word']}</p>
    <span class="badge">{entry['type']}</span>
    <div class="card">
      <p class="card-label">Значење</p>
      <p class="card-text">{entry['definition']}</p>
    </div>
    <div class="timer-wrap">
      <p class="timer-label">нов збор за</p>
      <p class="timer" id="countdown">--:--:--</p>
    </div>
  </div>
  <script>
    var ms = {diff};
    function tick() {{
      ms -= 1000;
      if (ms < 0) {{ location.reload(); return; }}
      var h = Math.floor(ms / 3600000);
      var m = Math.floor((ms % 3600000) / 60000);
      var s = Math.floor((ms % 60000) / 1000);
      document.getElementById('countdown').textContent =
        String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    }}
    tick();
    setInterval(tick, 1000);
  </script>
</body>
</html>"""

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# --- Database ---
def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            send_time TIME DEFAULT '11:00:00',
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS username TEXT")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS send_time TIME DEFAULT '11:00:00'")
    conn.commit()
    conn.close()

def add_subscriber(chat_id, first_name, username=None, send_time=DEFAULT_SEND_TIME):
    conn = get_conn()
    conn.cursor().execute(
        """INSERT INTO subscribers (chat_id, first_name, username, send_time)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (chat_id) DO UPDATE SET
               first_name = EXCLUDED.first_name,
               username = EXCLUDED.username""",
        (chat_id, first_name, username, send_time)
    )
    conn.commit()
    conn.close()

def remove_subscriber(chat_id):
    conn = get_conn()
    conn.cursor().execute(
        "DELETE FROM subscribers WHERE chat_id = %s", (chat_id,)
    )
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chat_id, first_name, username FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_subscribers_for_time(send_time: str):
    """Get all subscribers whose send_time matches the given HH:MM."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT chat_id, first_name, username FROM subscribers WHERE to_char(send_time, 'HH24:MI') = %s",
        (send_time,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def update_send_time(chat_id, send_time: str):
    conn = get_conn()
    conn.cursor().execute(
        "UPDATE subscribers SET send_time = %s WHERE chat_id = %s",
        (send_time, chat_id)
    )
    conn.commit()
    conn.close()

def is_subscribed(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM subscribers WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def is_admin(chat_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM subscribers WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0])

# --- Words ---
def load_words():
    with open(WORDS_FILE, encoding="utf-8") as f:
        words = json.load(f)
    return [w for w in words if w.get("difficulty", 0) >= 5]

def load_all_words():
    with open(WORDS_FILE, encoding="utf-8") as f:
        return json.load(f)

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

# --- Helpers ---
def parse_time_arg(arg: str):
    """Parse HH:MM string, return (hour, minute) or None if invalid."""
    try:
        parts = arg.strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
        return None
    except ValueError:
        return None

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Parse optional time argument
    send_time = DEFAULT_SEND_TIME
    if context.args:
        parsed = parse_time_arg(context.args[0])
        if parsed is None:
            await update.message.reply_text(
                "❌ Невалидно време. Користи формат HH:MM (24 часовен), пр. /start 17:00"
            )
            return
        send_time = f"{parsed[0]:02d}:{parsed[1]:02d}"

    if is_subscribed(chat_id):
        await update.message.reply_text(
            f"👋 Веќе си претплатен, {first_name}!\n"
            f"За промена на времето напиши /set_time HH:MM"
        )
        return

    add_subscriber(chat_id, first_name, username, send_time)

    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)

    subscribers = get_all_subscribers()
    await update.message.reply_text(
        f"👋 Добредојде, {first_name}! Претплатен си на *Збор на денот*.\n"
        f"Ќе добиваш порака секој ден во *{send_time}ч*.\n\n"
        f"Еве го денешниот збор:\n\n{message}",
        parse_mode="Markdown"
    )
    logging.info(f"New subscriber: {first_name} (@{username}) ({chat_id}) at {send_time}. Total: {len(subscribers)}")

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

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name

    if not is_subscribed(chat_id):
        await update.message.reply_text("Не си претплатен. Напиши /start за да се претплатиш.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Употреба: /set_time HH:MM\n"
            "Пример: /set_time 17:00"
        )
        return

    parsed = parse_time_arg(context.args[0])
    if parsed is None:
        await update.message.reply_text(
            "❌ Невалидно време. Користи формат HH:MM, пр. /set_time 17:00"
        )
        return

    send_time = f"{parsed[0]:02d}:{parsed[1]:02d}"
    update_send_time(chat_id, send_time)

    await update.message.reply_text(
        f"✅ Времето е променето! Ќе добиваш збор на денот секој ден во *{send_time}ч*.",
        parse_mode="Markdown"
    )
    logging.info(f"Updated send time for {first_name} ({chat_id}) to {send_time}")

async def zbor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)
    await update.message.reply_text(message, parse_mode="Markdown")

async def nov_zbor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    entry = random.choice(words)
    message = (
        f"🎲 *Случаен збор*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔤 *{entry['word']}*\n\n"
        f"📝 _{entry['type']}_\n\n"
        f"📌 *Значење:*\n{entry['definition']}"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_all_subscribers()
    await update.message.reply_text(f"📊 Вкупно претплатници: {len(subscribers)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Немаш дозвола за оваа команда.")
        return

    if not context.args:
        await update.message.reply_text("❌ Употреба: /broadcast <текст>")
        return

    text = " ".join(context.args)
    subscribers = get_all_subscribers()
    await update.message.reply_text(f"📤 Испраќам до {len(subscribers)} претплатници...")

    sent, failed = 0, 0
    for chat_id, first_name, username in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 *Известување*\n━━━━━━━━━━━━━━━\n{text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception as e:
            logging.warning(f"Failed to send to {first_name} ({chat_id}): {e}")
            failed += 1

    await update.message.reply_text(f"✅ Пратено: {sent} | ❌ Неуспешно: {failed}")

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Немаш дозвола за оваа команда.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Употреба: /notify ime1,ime2 <текст>\n"
            "Пример: /notify Марко,Ана Здраво!"
        )
        return

    target_names = [n.strip().lower() for n in context.args[0].split(",")]
    text = " ".join(context.args[1:])

    all_subscribers = get_all_subscribers()

    targets = [
        (chat_id, first_name, username)
        for chat_id, first_name, username in all_subscribers
        if (username and username.lower() in target_names)
        or (first_name and first_name.lower() in target_names)
    ]

    if not targets:
        names = [f"@{un}" if un else fn for _, fn, un in all_subscribers]
        await update.message.reply_text(
            f"⚠️ Не се пронајдени: {context.args[0]}\n"
            f"Достапни: {', '.join(names) if names else '(none)'}"
        )
        return

    await update.message.reply_text(f"📤 Испраќам до {len(targets)} корисник(ци)...")

    sent, failed = 0, 0
    for chat_id, first_name, username in targets:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 *Известување*\n━━━━━━━━━━━━━━━\n{text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception as e:
            logging.warning(f"Failed to send to {first_name} ({chat_id}): {e}")
            failed += 1

    await update.message.reply_text(f"✅ Пратено: {sent} | ❌ Неуспешно: {failed}")

async def define(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Употреба: /define <збор>\n"
            "Пример: /define корумпиран"
        )
        return

    query = " ".join(context.args).strip().lower()
    words = load_all_words()

    # Try exact match first (case-insensitive)
    match = next((w for w in words if w["word"].lower() == query), None)

    if match:
        message = (
            f"📖 *{match['word']}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 _{match['type']}_\n\n"
            f"📌 *Значење:*\n{match['definition']}"
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        return

    # No exact match - look for similar words
    all_word_strings = [w["word"] for w in words]
    similar = get_close_matches(query, [w.lower() for w in all_word_strings], n=3, cutoff=0.7)

    if similar:
        similar_display = [w for w in all_word_strings if w.lower() in similar]
        await update.message.reply_text(
            f"❌ Зборот *{query}* не е пронајден.\n\n"
            f"Дали мислевте на: {', '.join(similar_display)}?",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Зборот *{query}* не е пронајден во речникот.",
            parse_mode="Markdown"
        )

# --- Scheduled daily send ---
async def send_daily_word(context: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M")

    subscribers = get_subscribers_for_time(current_time)
    if not subscribers:
        return

    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)

    logging.info(f"Sending daily word at {current_time} to {len(subscribers)} subscribers...")

    failed = 0
    for chat_id, first_name, username in subscribers:
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

    logging.info(f"Done. Failed/removed: {failed}")

async def clear_updates():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)

asyncio.run(clear_updates())

# --- Main ---
if __name__ == "__main__":
    init_db()

    Thread(target=run_flask, daemon=True).start()

    tz = pytz.timezone(TIMEZONE)
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("stop", stop))
    bot_app.add_handler(CommandHandler("set_time", settime))
    bot_app.add_handler(CommandHandler("zbor", zbor))
    bot_app.add_handler(CommandHandler("nov_zbor", nov_zbor))
    bot_app.add_handler(CommandHandler("stats", stats))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))
    bot_app.add_handler(CommandHandler("notify", notify))
    bot_app.add_handler(CommandHandler("define", define))

    seconds_until_next_minute = 60 - datetime.now().second
    bot_app.job_queue.run_repeating(send_daily_word, interval=60, first=seconds_until_next_minute)

    print(f"🤖 Bot is running... Daily word scheduler active ({TIMEZONE})")
    bot_app.run_polling()