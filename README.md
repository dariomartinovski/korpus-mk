# KorpusMK Bot 🇲🇰

A Telegram bot that sends a **Macedonian word of the day** to subscribers, sourced from the official Macedonian dictionary at [makedonski.gov.mk](https://makedonski.gov.mk).

## Features

- 📖 Daily word with definition and word type
- 🔔 Subscribers receive the word automatically every morning
- 🗃️ SQLite database to store subscribers
- 🧹 Auto-removes users who block the bot
- ⚙️ Difficulty-based filtering (only sends words with difficulty ≥ 5)

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe and receive today's word immediately |
| `/stop` | Unsubscribe from daily messages |
| `/zbor` | Get today's word on demand |
| `/stats` | Show total subscriber count |

## Project Structure

```
├── bot.py                  # Main bot — handles commands + daily schedule
├── scrape_words.py         # Scraper for makedonski.gov.mk (one-time run)
├── classify_words.py       # Rule-based difficulty classifier (one-time run)
├── words_classified.json   # Full word list with difficulty scores
├── subscribers.db          # SQLite database (auto-created on first run)
├── requirements.txt        # Python dependencies
└── render.yaml             # Render.com deployment config
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/korpus-mk-bot
cd korpus-mk-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the steps
3. Copy the token you receive

### 4. Configure the token

Either set it as an environment variable:

```bash
export TELEGRAM_TOKEN="your-token-here"
```

Or paste it directly into `bot.py` at the top:

```python
TELEGRAM_TOKEN = "your-token-here"
```

### 5. Run the bot

```bash
python bot.py
```

## Word List

The word list is scraped from [makedonski.gov.mk](https://makedonski.gov.mk/corpus) which contains ~51,000 words from the official Macedonian dictionary. To regenerate it:

```bash
# Scrape all words (takes ~2 hours, resumable)
python scrape_words.py

# Classify by difficulty (1-10 scale, runs in seconds)
python classify_words.py
```

The difficulty classifier uses a rule-based scoring system based on word length, grammatical type, foreign suffixes (`-ција`, `-ален`, etc.), and definition complexity.

## Deployment (Render.com)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) and create a new **Worker** service
3. Connect your GitHub repo
4. Add `TELEGRAM_TOKEN` as an environment variable in Render's dashboard
5. Deploy — the bot runs 24/7 for free

## Adjusting the daily send time

In `bot.py`, change these two lines:

```python
SEND_HOUR = 9    # Hour in 24h format
SEND_MINUTE = 0
TIMEZONE = "Europe/Skopje"
```

## License

MIT