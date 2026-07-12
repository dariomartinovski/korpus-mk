import json
import os
import glob

# ── CONFIG ──────────────────────────────────────────────────────────────────
BATCHES_FOLDER = '../wip-results/batches-partial-def-processed'          # folder containing batch001.json … batch110.json
OUTPUT_FILE    = '../wip-results/combined_definitions_pd.json'
# ────────────────────────────────────────────────────────────────────────────

batch_files = sorted(glob.glob(os.path.join(BATCHES_FOLDER, 'batch*.json')))

if not batch_files:
    print(f"No batch files found in '{BATCHES_FOLDER}/'")
    exit(1)

all_words = []
skipped   = []

for path in batch_files:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            all_words.extend(data)
        else:
            print(f"  Warning: {path} is not a JSON array — skipped.")
            skipped.append(path)
    except json.JSONDecodeError as e:
        print(f"  Error parsing {path}: {e} — skipped.")
        skipped.append(path)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(all_words, f, ensure_ascii=False, indent=2)

print(f"Combined {len(batch_files) - len(skipped)} files → {len(all_words)} words")
print(f"Saved to: {OUTPUT_FILE}")
if skipped:
    print(f"Skipped {len(skipped)} files: {skipped}")