import json
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
alias_path = os.path.join(DATA_DIR, 'person_aliases.json')

with open(alias_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Add some sample data for demonstration
updates = {
    "季孙行父": {
        "state": "鲁国",
        "desc": "即季文子。春秋时期鲁国正卿，季孙氏的代表人物之一。历事鲁文公、鲁宣公、鲁成公、鲁襄公四代国君，执掌鲁国朝政长达三十余年。"
    },
    "士匄": {
        "state": "晋国",
        "desc": "即范宣子。春秋时期晋国正卿，范氏家族领袖。曾主导修筑诸侯之城，并在平阴之会中代表晋国与诸侯结盟。"
    },
    "公子遂": {
        "state": "鲁国",
        "desc": "即东门襄仲。春秋时期鲁国大夫，鲁庄公之子。曾赴齐国、晋国等多次进行外交活动，在鲁国政坛有较大影响力。"
    }
}

for name, info in updates.items():
    if name in data:
        data[name]["state"] = info["state"]
        data[name]["desc"] = info["desc"]

with open(alias_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Sample bios added.")
