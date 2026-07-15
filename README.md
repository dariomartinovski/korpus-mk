# KorpusMK 🇲🇰

Learn a new Macedonian word every day, straight to your Telegram.

KorpusMK sends you a daily word from the official Macedonian dictionary — with its definition and word type — every morning. Great for language learners, diaspora Macedonians, or anyone who just loves their language.

---

## Get Started

1. Open Telegram and search for **[@korpus_mk_bot](https://t.me/korpus_mk_bot)**
2. Press **Start** or type `/start`
3. You'll receive today's word instantly, and every morning from then on

By default you'll receive your daily word at **11:00** Skopje time. You can set a custom time at signup or change it later.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Subscribe and get today's word right away (default time: 11:00) |
| `/start HH:MM` | Subscribe with a custom daily notification time |
| `/set_time HH:MM` | Change your daily notification time |
| `/zbor` | Get today's word at any time |
| `/nov_zbor` | Get a random word from the list |
| `/define <word>` | Look up any word in the full dictionary |
| `/stop` | Unsubscribe from daily messages |

---

## Admin Commands

These commands are only available to admins, set directly in the database.

| Command | What it does |
|---------|-------------|
| `/broadcast <text>` | Send a message to all subscribers |
| `/notify <name1,name2> <text>` | Send a message to specific subscribers by first name |
| `/stats` | Show total number of subscribers |

---

## Examples

**Subscribe with default time (11:00):**
```
/start
```

**Subscribe with a custom time:**
```
/start 17:00
```

**Change your notification time:**
```
/set_time 08:30
```

**Get today's word:**
```
/zbor

📖 Збор на денот
━━━━━━━━━━━━━━━
🔤 благодарност

📝 именка

📌 Значење:
Чувство на признателност кон некого за направено добро.
```

**Get a random word:**
```
/nov_zbor

🎲 Случаен збор
━━━━━━━━━━━━━━━
🔤 суверен

📝 именка

📌 Значење:
Врховен носител на државната власт.
```

**Look up a word:**
```
/define корумпиран

📖 корумпиран
━━━━━━━━━━━━━━━
📝 придавка

📌 Значење:
Оној што е поткупен, продаден.
```

**Look up a word with a typo:**
```
/define корумпирн

❌ Зборот корумпирн не е пронајден.

Дали мислевте на: корумпиран?
```

**Admin — broadcast to all subscribers:**
```
/broadcast Одржување утре од 10-12ч. Ботот нема да биде достапен.
```

**Admin — notify specific subscribers by name:**
```
/notify Марко Здраво, ова е само за тебе!
/notify Марко,Ана Одржување утре!
```

---

## About

Words are sourced from [makedonski.gov.mk](https://makedonski.gov.mk) — the official Macedonian language dictionary. The bot sends a new word every day at your chosen time (default **11:00**), Skopje time.