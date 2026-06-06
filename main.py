import os
import sys

# Tránh tạo thư mục __pycache__ và file .pyc
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import txa

if __name__ == "__main__":
    txa.main()
