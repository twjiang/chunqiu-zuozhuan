import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
alias_path = os.path.join(DATA_DIR, 'person_aliases.json')

with open(alias_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_data = {}
for canonical, aliases in data.items():
    if isinstance(aliases, list):
        new_data[canonical] = {
            "aliases": aliases,
            "state": "",
            "desc": ""
        }
    else:
        new_data[canonical] = aliases  # Already in new format

with open(alias_path, 'w', encoding='utf-8') as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print("Migration completed.")
