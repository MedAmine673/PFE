import json
import os

def save_json(path, filename, data):
    os.makedirs(path, exist_ok=True)
    
    full_path = os.path.join(path, f"{filename}.json")
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    return full_path