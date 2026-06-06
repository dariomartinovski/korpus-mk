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
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WORDS_FILE = "words_randomized_all.json"
SEND_HOUR = 11
SEND_MINUTE = 0
TIMEZONE = "Europe/Skopje"

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
    next_send = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=0, microsecond=0)
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
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_subscriber(chat_id, first_name, username=None):
    conn = get_conn()
    conn.cursor().execute(
        """INSERT INTO subscribers (chat_id, first_name, username)
           VALUES (%s, %s, %s)
           ON CONFLICT (chat_id) DO UPDATE SET
               first_name = EXCLUDED.first_name,
               username = EXCLUDED.username""",
        (chat_id, first_name, username)
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
    username = update.effective_user.username

    if is_subscribed(chat_id):
        await update.message.reply_text(
            f"👋 Веќе си претплатен, {first_name}! Ќе добиваш збор на денот секој ден во {SEND_HOUR:02d}:{SEND_MINUTE:02d}ч.\n\n"
            f"Напиши /zbor за да го добиеш денешниот збор."
        )
        return

    add_subscriber(chat_id, first_name, username)

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
    logging.info(f"New subscriber: {first_name} (@{username}) ({chat_id}). Total: {len(subscribers)}")

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

# --- Scheduled daily send ---
async def send_daily_word(context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    entry = pick_word(words)
    message = build_message(entry)
    subscribers = get_all_subscribers()

    logging.info(f"Sending daily word to {len(subscribers)} subscribers...")

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

    logging.info(f"Daily word sent. Failed/removed: {failed}")

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
    bot_app.add_handler(CommandHandler("zbor", zbor))
    bot_app.add_handler(CommandHandler("nov_zbor", nov_zbor))
    bot_app.add_handler(CommandHandler("stats", stats))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))
    bot_app.add_handler(CommandHandler("notify", notify))

    bot_app.job_queue.run_daily(
        send_daily_word,
        time=time(hour=SEND_HOUR, minute=SEND_MINUTE, tzinfo=tz)
    )

    print(f"🤖 Bot is running... Daily word at {SEND_HOUR:02d}:{SEND_MINUTE:02d} {TIMEZONE}")
    bot_app.run_polling()