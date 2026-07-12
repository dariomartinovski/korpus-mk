import json
import re

# ── CONFIG ──────────────────────────────────────────────────────────────────
ORIGINAL_FILE    = '../wip-results/words_complete.json'
DEFINITIONS_FILE = '../wip-results/combined_definitions_pd.json'
OUTPUT_FILE      = '../wip-results/words_with_definitions.json'

STUB_PHRASES = [
    'зборот е поврзан со:',
    'со значење',
]
# ────────────────────────────────────────────────────────────────────────────

def normalize(word: str) -> str:
    """Lowercase and strip surrounding punctuation/whitespace for matching."""
    return re.sub(r'[^\w\s]', '', word.strip().lower())

def is_stub(definition: str) -> bool:
    d = definition.strip().lower()
    if not d:
        return True
    for stub in STUB_PHRASES:
        if d == stub or d.startswith(stub):
            return True
    return False

with open(ORIGINAL_FILE, 'r', encoding='utf-8') as f:
    original = json.load(f)

with open(DEFINITIONS_FILE, 'r', encoding='utf-8') as f:
    definitions = json.load(f)

# Build lookup keyed by normalized word → {definition, type}
def_lookup = {}
for entry in definitions:
    word = entry.get('word', '').strip()
    defn = entry.get('definition', '').strip()
    type_ = entry.get('type', '').strip()
    if word and defn and not is_stub(defn):
        def_lookup[normalize(word)] = {'definition': defn, 'type': type_}

filled  = 0
missing = []

result = []
for entry in original:
    new_entry = dict(entry)
    word = new_entry.get('word', '').strip()
    has_definition = not is_stub(new_entry.get('definition', ''))

    if not has_definition:
        key = normalize(word)
        if key in def_lookup:
            new_entry['definition'] = def_lookup[key]['definition']
            if def_lookup[key]['type']:          # only overwrite type if generated one is non-empty
                new_entry['type'] = def_lookup[key]['type']
            filled += 1
        else:
            missing.append(word)

    result.append(new_entry)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Total words       : {len(result)}")
print(f"Definitions filled: {filled}")
print(f"Still missing     : {len(missing)}")
print(f"Saved to          : {OUTPUT_FILE}")

if missing:
    print(f"\nWords still without a definition ({len(missing)}):")
    for w in missing:
        print(f"  {w}")