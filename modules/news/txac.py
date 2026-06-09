CONFIG = {
    "emoji": "🗞️",
    "title": "Tin Tức & Tỷ Giá",
    "group_by_parent": False,
    "modules": {
        "func_news/main.py": {"emoji": "🗞️", "title": "Tin tức", "cmds": ["news"]},
        "func_tygia/main.py": {"emoji": "❖", "title": "Tỷ giá", "cmds": ["tygia", "hoan_doi"]},
        "func_giavang/main.py": {"emoji": "❖", "title": "Giavang", "cmds": ["gia_vang"]}
    }
}
