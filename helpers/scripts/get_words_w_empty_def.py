import json

with open('words_randomized_all.json', 'r', encoding='utf-8') as f:
    words = json.load(f)

no_definition = [word for word in words if not word.get('definition', '').strip()]

with open('words_no_definition.json', 'w', encoding='utf-8') as f:
    json.dump(no_definition, f, ensure_ascii=False, indent=2)

print(f"Found {len(no_definition)} words without definitions.")