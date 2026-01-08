import aiosqlite
import os
import logging

# Получаем путь к БД
DB_NAME = os.getenv('DB_PATH', 'murasaki_NEW.db')

async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Включаем поддержку внешних ключей (если нужно)
        await db.execute("PRAGMA foreign_keys = ON")
        
        # --- СЮДА НУЖНО ВСТАВИТЬ СОЗДАНИЕ ТВОИХ ТАБЛИЦ ---
        # Если у тебя есть код CREATE TABLE, вставь его ниже.
        # Для примера я создам тестовую таблицу, чтобы ошибка ушла:
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Если у тебя были другие таблицы (shop, items и т.д.), добавь их здесь:
        # await db.execute("CREATE TABLE IF NOT EXISTS ...")
        
        await db.commit()
        logging.info(f"✅ БД инициализирована: {DB_NAME}")

async def get_db_connection():
    """Вспомогательная функция для получения соединения"""
    return await aiosqlite.connect(DB_NAME)
