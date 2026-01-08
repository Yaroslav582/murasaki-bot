import os

# Используем путь из переменной окружения или main.py
DB_NAME = os.getenv('DB_PATH', 'murasaki_NEW.db')
