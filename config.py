# -*- coding: UTF-8 -*-
import json
import os

try:
    # Resolve path to txa.json in the same directory as config.py
    config_path = os.path.join(os.path.dirname(__file__), "txa.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot_data = data.get("data", [{}])[0]
        prefix = bot_data.get("prefix", ".")
    else:
        prefix = "."
except Exception:
    prefix = "."
