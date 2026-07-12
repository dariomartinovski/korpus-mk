import json

# ── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_FILE  = 'words_randomized_all.json'   # or 'words_complete.json' if you want to run it after merging
OUTPUT_FILE = 'partial_definition.json'

# Stub phrases that count as "no real definition"
STUB_PHRASES = [
    'зборот е поврзан со:',   # the one you found
    # add more here if you discover other stubs later
]
# ────────────────────────────────────────────────────────────────────────────

def is_stub(definition: str) -> bool:
    d = definition.strip().lower()
    if not d:
        return False
    for stub in STUB_PHRASES:
        if d == stub or d.startswith(stub):
            return True
    return False

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    words = json.load(f)

partial = [word for word in words if is_stub(word.get('definition', ''))]

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(partial, f, ensure_ascii=False, indent=2)

print(f"Found {len(partial)} words with stub/partial definitions.")
print(f"Saved to: {OUTPUT_FILE}")