import json
import os

with open('../wip-results/partial_definition.json', 'r', encoding='utf-8') as f:
    words = json.load(f)

# Filter only words without definitions
no_definition = [word for word in words if not word.get('definition', '').strip()]

# Split into batches of 50
batch_size = 50
os.makedirs('../wip-results/batches-partial-def', exist_ok=True)

for i in range(0, len(no_definition), batch_size):
    batch = no_definition[i:i + batch_size]
    batch_num = (i // batch_size) + 1
    filename = f'../wip-results/batches-partial-def/batch_{batch_num:03d}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

total_batches = (len(no_definition) + batch_size - 1) // batch_size
print(f"Found {len(no_definition)} words without definitions.")
print(f"Saved {total_batches} batch files in the '../wip-results/batches-partial-def/' folder.")