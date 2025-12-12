# Murasaki Empire Bot - ПОЛНАЯ ВЕРСИЯ С БЛЭКДЖЕКОМ
# КОМАНДЫ РАБОТАЮТ И С / И БЕЗ /

import asyncio
import aiosqlite
import random
import time
import logging
import os
import shutil
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Dice
from aiogram.enums import ChatType

# ========== НАСТРОЙКИ ==========
TOKEN = "8424494037:AAHrtN5irOGb7SzLQicLHCPQt9p5o8FF_sA"
ADMIN_IDS = {1162907446}  # Твой ID
DB_PATH = "murasaki.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ РАБОТЫ ==========
WORK_COOLDOWN = 60  # 1 минута в секундах

# ========== ФУНКЦИИ ДЛЯ ПАРСИНГА ЧИСЕЛ ==========
def parse_amount(amount_str: str) -> int:
    """
    Парсит строку с числом, поддерживая форматы:
    - "1000" -> 1000
    - "1к" -> 1000
    - "1.5к" -> 1500
    - "1кк" -> 1000000
    - "1.5кк" -> 1500000
    - "1м" -> 1000000
    - "1.5м" -> 1500000
    - "1млн" -> 1000000
    - "10кк" -> 10000000
    - "100кк" -> 100000000
    """
    if not amount_str:
        return 0
    
    amount_str = amount_str.lower().replace(',', '.').replace(' ', '')
    
    # Удаляем нечисловые символы кроме точки
    clean_str = ''
    for char in amount_str:
        if char.isdigit() or char == '.':
            clean_str += char
        else:
            break
    
    if not clean_str:
        return 0
    
    try:
        base_value = float(clean_str)
    except:
        return 0
    
    # Определяем множитель
    multiplier = 1
    
    if 'кк' in amount_str:
        multiplier = 1_000_000
    elif 'млн' in amount_str:
        multiplier = 1_000_000
    elif 'м' in amount_str:
        multiplier = 1_000_000
    elif 'к' in amount_str:
        multiplier = 1_000
    
    return int(base_value * multiplier)

# ========== БАЗА ДАННЫХ ==========
async def update_db_structure():
    """Обновить структуру базы данных"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем наличие полей
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем недостающие поля
            if 'work_time' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN work_time INTEGER DEFAULT 0")
                logger.info("✅ Добавлено поле work_time")
            
            if 'total_work' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN total_work BIGINT DEFAULT 0")
                logger.info("✅ Добавлено поле total_work")
            
            if 'total_bonus' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN total_bonus BIGINT DEFAULT 0")
                logger.info("✅ Добавлено поле total_bonus")
            
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления БД: {e}")

async def init_db():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance BIGINT DEFAULT 0,
                bonus_time INTEGER DEFAULT 0,
                work_time INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_bonus BIGINT DEFAULT 0,
                total_work BIGINT DEFAULT 0
            )
            """)
            await db.commit()
            logger.info("✅ База данных создана")
            
            # Обновляем структуру для существующих баз
            await update_db_structure()
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")

async def get_user(uid: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if row:
                user_dict = dict(row)
                # Убедимся, что все поля есть
                if 'work_time' not in user_dict:
                    user_dict['work_time'] = 0
                if 'total_work' not in user_dict:
                    user_dict['total_work'] = 0
                if 'total_bonus' not in user_dict:
                    user_dict['total_bonus'] = 0
                if 'bonus_time' not in user_dict:
                    user_dict['bonus_time'] = 0
                return user_dict
            
            # Создаем нового пользователя
            await db.execute(
                "INSERT INTO users (id, balance, bonus_time, work_time, total_bonus, total_work, wins, losses) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, 0, 0, 0, 0, 0, 0, 0)
            )
            await db.commit()
            return {
                'id': uid, 
                'balance': 0, 
                'bonus_time': 0, 
                'work_time': 0,
                'wins': 0, 
                'losses': 0, 
                'total_bonus': 0, 
                'total_work': 0, 
                'username': None
            }
    except Exception as e:
        logger.error(f"Ошибка get_user: {e}")
        return {
            'id': uid, 
            'balance': 0, 
            'bonus_time': 0, 
            'work_time': 0,
            'wins': 0, 
            'losses': 0, 
            'total_bonus': 0, 
            'total_work': 0, 
            'username': None
        }

async def change_balance(uid: int, delta: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (uid, 0))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (delta, uid))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка change_balance: {e}")
        return False

async def update_username(uid: int, username: str):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
            await db.commit()
    except:
        pass

async def update_stats(uid: int, win: bool):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if win:
                await db.execute("UPDATE users SET wins = wins + 1 WHERE id = ?", (uid,))
            else:
                await db.execute("UPDATE users SET losses = losses + 1 WHERE id = ?", (uid,))
            await db.commit()
    except:
        pass

async def get_top():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, balance FROM users ORDER BY balance DESC LIMIT 10"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except:
        return []

# ========== ФУНКЦИЯ ДЛЯ ПРОГРЕСС-БАРА ==========
def create_progress_bar(percentage: int, length: int = 10):
    """Создает текстовый прогресс-бар"""
    filled = int(length * percentage / 100)
    empty = length - filled
    
    filled_char = "█"
    empty_char = "░"
    
    progress_bar = f"{filled_char * filled}{empty_char * empty}"
    
    return progress_bar

# ========== МОДУЛЬ БОНУСА ==========
async def check_bonus_cooldown(uid: int):
    """Проверка кулдауна на бонус (1 час)"""
    try:
        user = await get_user(uid)
        last_bonus = user.get('bonus_time', 0)
        total_bonus = user.get('total_bonus', 0)
        
        current_time = time.time()
        
        if last_bonus == 0:
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        
        time_passed = current_time - last_bonus
        
        if time_passed >= 3600:
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        
        remaining = 3600 - time_passed
        return False, remaining, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
    except Exception as e:
        logger.error(f"Ошибка check_bonus_cooldown: {e}")
        return True, 0, {'bonus_time': 0, 'total_bonus': 0}

async def give_bonus(uid: int):
    """Выдать бонус от 5 до 20 миллионов"""
    try:
        # Генерируем бонус от 5,000,000 до 20,000,000
        amount = random.randint(5_000_000, 20_000_000)
        current_time = int(time.time())
        
        # Сначала получаем пользователя, чтобы убедиться что он существует
        user = await get_user(uid)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Обновляем баланс, время бонуса и сумму бонусов
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    bonus_time = ?,
                    total_bonus = COALESCE(total_bonus, 0) + ?
                WHERE id = ?
            """, (amount, current_time, amount, uid))
            
            await db.commit()
            return amount, True  # Возвращаем сумму и статус
    except Exception as e:
        logger.error(f"Ошибка выдачи бонуса: {e}")
        return 0, False

# ========== МОДУЛЬ РАБОТЫ ==========
async def check_work_cooldown(uid: int):
    """Проверка кулдауна на работу (1 минута)"""
    try:
        user = await get_user(uid)
        last_work = user.get('work_time', 0)
        total_work = user.get('total_work', 0)
        
        current_time = time.time()
        
        if last_work == 0:
            return True, 0, {'work_time': last_work, 'total_work': total_work}
        
        time_passed = current_time - last_work
        
        if time_passed >= WORK_COOLDOWN:
            return True, 0, {'work_time': last_work, 'total_work': total_work}
        
        remaining = WORK_COOLDOWN - time_passed
        return False, remaining, {'work_time': last_work, 'total_work': total_work}
    except Exception as e:
        logger.error(f"Ошибка check_work_cooldown: {e}")
        return True, 0, {'work_time': 0, 'total_work': 0}

async def give_work_reward(uid: int):
    """Выдать награду за работу (1-5 миллионов)"""
    try:
        # Генерируем награду от 1,000,000 до 5,000,000
        amount = random.randint(1_000_000, 5_000_000)
        current_time = int(time.time())
        
        # Сначала получаем пользователя, чтобы убедиться что он существует
        user = await get_user(uid)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Обновляем баланс, время работы и сумму заработанного
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    work_time = ?,
                    total_work = COALESCE(total_work, 0) + ?
                WHERE id = ?
            """, (amount, current_time, amount, uid))
            
            await db.commit()
            return amount, True  # Возвращаем сумму и статус
    except Exception as e:
        logger.error(f"Ошибка выдачи работы: {e}")
        return 0, False

# ========== БЛЭКДЖЕК ==========
bj_games = {}

# Карты для блэкджека
CARD_VALUES = {"2":2, "3":3, "4":4, "5":5, "6":6, "7":7, "8":8, "9":9, 
               "10":10, "J":10, "Q":10, "K":10, "A":11}
CARDS = list(CARD_VALUES.keys())

def hand_value(hand):
    total = sum(CARD_VALUES.get(c, 0) for c in hand)
    aces = hand.count("A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def format_cards(hand, hide_first=False):
    if not hand:
        return "пусто"
    if hide_first:
        return f"🂠, {', '.join(hand[1:])}"
    return ', '.join(hand)

def save_bj_game(uid: int, bet: int, hand: list, dealer_hand: list):
    bj_games[uid] = {
        'bet': bet,
        'hand': hand,
        'dealer_hand': dealer_hand,
        'timestamp': time.time()
    }

def load_bj_game(uid: int):
    if uid in bj_games:
        # Проверяем, не устарела ли игра (10 минут)
        if time.time() - bj_games[uid]['timestamp'] > 600:
            del bj_games[uid]
            return None
        return bj_games[uid]
    return None

def clear_bj_game(uid: int):
    if uid in bj_games:
        del bj_games[uid]

# ========== РУЛЕТКА ==========
ROULETTE_NUMBERS = list(range(0, 37))
ROULETTE_RED = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
ROULETTE_BLACK = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
ROULETTE_EVEN = list(range(2, 37, 2))
ROULETTE_ODD = list(range(1, 37, 2))
ROULETTE_1_18 = list(range(1, 19))
ROULETTE_19_36 = list(range(19, 37))
ROULETTE_1_12 = list(range(1, 13))
ROULETTE_13_24 = list(range(13, 25))
ROULETTE_25_36 = list(range(25, 37))

def get_roulette_color(number):
    if number == 0:
        return "зеленое"
    elif number in ROULETTE_RED:
        return "красное"
    else:
        return "черное"

def get_roulette_result(number: int, bet_type: str, bet_value: str = None):
    if bet_type == "число":
        return int(bet_value) == number
    elif bet_type == "красное":
        return number in ROULETTE_RED
    elif bet_type == "черное":
        return number in ROULETTE_BLACK
    elif bet_type == "зеленое":
        return number == 0
    elif bet_type == "четное":
        return number in ROULETTE_EVEN and number != 0
    elif bet_type == "нечетное":
        return number in ROULETTE_ODD
    elif bet_type == "1-18":
        return number in ROULETTE_1_18
    elif bet_type == "19-36":
        return number in ROULETTE_19_36
    elif bet_type == "1-12":
        return number in ROULETTE_1_12
    elif bet_type == "13-24":
        return number in ROULETTE_13_24
    elif bet_type == "25-36":
        return number in ROULETTE_25_36
    return False

def get_roulette_multiplier(bet_type: str):
    multipliers = {
        "число": 36,
        "зеленое": 36,
        "красное": 2,
        "черное": 2,
        "четное": 2,
        "нечетное": 2,
        "1-18": 2,
        "19-36": 2,
        "1-12": 3,
        "13-24": 3,
        "25-36": 3
    }
    return multipliers.get(bet_type, 1)

# ========== ОБРАБОТКА КОМАНД С / И БЕЗ ==========
@router.message(F.text)
async def handle_all_commands(msg: Message):
    """Обработчик всех команд - и с / и без /"""
    text = msg.text.strip()
    
    # Пропускаем пустые сообщения
    if not text:
        return
    
    # Разделяем команду и аргументы
    parts = text.split()
    cmd = parts[0].lower()
    
    # ОБРАБОТКА КОМАНД БЕЗ /
    
    # Бонус
    if cmd in ['бонус', 'bonus', 'бон', 'bon']:
        await process_bonus(msg)
        return
    
    # Работа
    if cmd in ['работа', 'work', 'раб', 'wrk', 'труд']:
        await process_work(msg)
        return
    
    # Баланс
    if cmd in ['баланс', 'balance', 'б', 'баланс']:
        await process_balance(msg)
        return
    
    # Профиль
    if cmd in ['профиль', 'profile', 'пр', 'стата', 'stats', 'статистика']:
        await process_profile(msg)
        return
    
    # Топ
    if cmd in ['топ', 'top', 'лидеры', 'лидерборд']:
        await process_top(msg)
        return
    
    # КД бонуса
    if cmd in ['кд', 'cd', 'кулдаун', 'cooldown', 'бонусвремя']:
        await check_bonus_cd(msg)
        return
    
    # КД работы
    if cmd in ['кдработы', 'работакд', 'workcd']:
        await check_work_cd(msg)
        return
    
    # Передать
    if cmd == 'передать' and len(parts) >= 3:
        await process_transfer(msg, parts)
        return
    
    # Игры с аргументами
    if len(parts) >= 2:
        # Монетка
        if cmd in ['монетка', 'coin', 'мн', 'coinflip', 'монета']:
            await process_coin(msg, parts)
            return
        
        # Кости
        if cmd in ['кости', 'dice', 'кст', 'дайс']:
            await process_dice(msg, parts)
            return
        
        # Слоты
        if cmd in ['слоты', 'slots', 'сл', 'слот']:
            await process_slots(msg, parts)
            return
        
        # Рулетка
        if cmd in ['рулетка', 'roulette', 'рул', 'rul', 'rule']:
            await process_roulette(msg, parts)
            return
        
        # Блэкджек
        if cmd in ['блекджек', 'блэкджек', 'bj', 'бж', 'blackjack']:
            await process_bj(msg, parts)
            return
    
    # Админ команды без /
    if msg.from_user.id in ADMIN_IDS:
        # Выдать (ответ на сообщение)
        if cmd == 'выдать' and len(parts) >= 2:
            if msg.reply_to_message:
                await process_admin_give_reply(msg, parts)
                return
        
        # Выдать по ID/юзернейму
        if cmd == 'выдать' and len(parts) >= 3:
            await process_admin_give(msg, parts)
            return
        
        # Забрать (ответ на сообщение)
        if cmd == 'забрать' and len(parts) >= 2:
            if msg.reply_to_message:
                await process_admin_take_reply(msg, parts)
                return
        
        # Забрать по ID/юзернейму
        if cmd == 'забрать' and len(parts) >= 3:
            await process_admin_take(msg, parts)
            return

# ========== ФУНКЦИИ ОБРАБОТКИ КОМАНД ==========
async def process_bonus(msg: Message):
    """Обработка команды бонус (каждый час, 5-20М)"""
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    
    can_get_bonus, remaining, bonus_data = await check_bonus_cooldown(uid)
    
    if not can_get_bonus:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        # Показываем прогресс-бар
        progress_percent = int((3600 - remaining) / 3600 * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        await msg.reply(
            f"⏳ <b>Бонус уже получен!</b>\n\n"
            f"⏰ Следующий бонус через:\n"
            f"<b>{minutes}м {seconds}с</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Доступен с:</b> {next_str}\n\n"
            f"💰 Всего получено бонусов: <code>{bonus_data.get('total_bonus', 0):,}</code>",
            parse_mode="HTML"
        )
        return
    
    # Выдаем бонус
    amount, success = await give_bonus(uid)
    
    if not success:
        user_data = await get_user(uid)
        await msg.reply(
            f"⚠️ <b>Не удалось выдать бонус</b>\n\n"
            f"💰 <b>Текущий баланс:</b> <code>{user_data.get('balance', 0):,}</code>\n"
            f"🎁 <b>Всего получено бонусов:</b> <code>{user_data.get('total_bonus', 0):,}</code>",
            parse_mode="HTML"
        )
        return
    
    # Получаем обновленные данные
    updated_user = await get_user(uid)
    next_time = time.time() + 3600
    next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
    
    # Выбираем случайный эмодзи
    emojis = ["🎁", "💰", "💎", "💵", "🪙", "💸", "🎰", "🏆", "🤑", "💯"]
    emoji = random.choice(emojis)
    
    # Создаем красивый прогресс-бар
    progress_bar = create_progress_bar(0)  # 0% после получения
    
    # Определяем уровень бонуса (визуальный индикатор)
    bonus_level = ""
    if amount >= 15_000_000:
        bonus_level = "🔥 МЕГА БОНУС!"
    elif amount >= 10_000_000:
        bonus_level = "⭐ БОЛЬШОЙ БОНУС!"
    else:
        bonus_level = "✨ ХОРОШИЙ БОНУС!"
    
    await msg.reply(
        f"{emoji} <b>БОНУС ПОЛУЧЕН!</b> {emoji}\n\n"
        f"{bonus_level}\n\n"
        f"💰 <b>Сумма:</b> <code>{amount:,}</code>\n"
        f"📊 <b>Новый баланс:</b> <code>{updated_user.get('balance', 0):,}</code>\n\n"
        f"⏰ <b>Следующий бонус через 1 час:</b>\n"
        f"🕐 {next_str}\n\n"
        f"{progress_bar} 0%\n\n"
        f"🏦 <b>Всего получено:</b> <code>{updated_user.get('total_bonus', 0):,}</code>",
        parse_mode="HTML"
    )

async def process_work(msg: Message):
    """Обработка команды работа (каждую минуту, 1-5М)"""
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    
    can_work, remaining, work_data = await check_work_cooldown(uid)
    
    if not can_work:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        # Показываем прогресс-бар
        progress_percent = int((WORK_COOLDOWN - remaining) / WORK_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        await msg.reply(
            f"⏳ <b>Работа уже выполнена!</b>\n\n"
            f"⏰ Следующая работа через:\n"
            f"<b>{minutes}м {seconds}с</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Доступна с:</b> {next_str}\n\n"
            f"💰 Всего заработано: <code>{work_data.get('total_work', 0):,}</code>",
            parse_mode="HTML"
        )
        return
    
    # Выдаем награду за работу
    amount, success = await give_work_reward(uid)
    
    if not success:
        user_data = await get_user(uid)
        await msg.reply(
            f"⚠️ <b>Не удалось выполнить работу</b>\n\n"
            f"💰 <b>Текущий баланс:</b> <code>{user_data.get('balance', 0):,}</code>\n"
            f"💼 <b>Всего заработано:</b> <code>{user_data.get('total_work', 0):,}</code>",
            parse_mode="HTML"
        )
        return
    
    # Получаем обновленные данные
    updated_user = await get_user(uid)
    next_time = time.time() + WORK_COOLDOWN
    next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
    
    # Список работ
    jobs = [
        "💼 Офисный работник",
        "🚚 Водитель доставки",
        "👨‍💻 Программист",
        "👨‍🍳 Шеф-повар",
        "🏗️ Строитель",
        "👨‍⚕️ Врач",
        "👮‍♂️ Полицейский",
        "🔥 Пожарный",
        "✈️ Пилот",
        "🎬 Актер"
    ]
    
    job = random.choice(jobs)
    
    # Создаем красивый прогресс-бар
    progress_bar = create_progress_bar(0)  # 0% после получения
    
    # Определяем уровень оплаты
    salary_level = ""
    if amount >= 4_000_000:
        salary_level = "🔥 ВЫСОКАЯ ЗАРПЛАТА!"
    elif amount >= 2_500_000:
        salary_level = "⭐ ХОРОШАЯ ЗАРПЛАТА!"
    else:
        salary_level = "✨ СТАНДАРТНАЯ ЗАРПЛАТА!"
    
    await msg.reply(
        f"💼 <b>РАБОТА ВЫПОЛНЕНА!</b> 💼\n\n"
        f"👨‍💻 <b>Должность:</b> {job}\n"
        f"{salary_level}\n\n"
        f"💰 <b>Зарплата:</b> <code>{amount:,}</code>\n"
        f"📊 <b>Новый баланс:</b> <code>{updated_user.get('balance', 0):,}</code>\n\n"
        f"⏰ <b>Следующая работа через 1 минуту:</b>\n"
        f"🕐 {next_str}\n\n"
        f"{progress_bar} 0%\n\n"
        f"🏢 <b>Всего заработано:</b> <code>{updated_user.get('total_work', 0):,}</code>",
        parse_mode="HTML"
    )

async def check_bonus_cd(msg: Message):
    """Проверить оставшееся время до бонуса"""
    uid = msg.from_user.id
    can_get_bonus, remaining, bonus_data = await check_bonus_cooldown(uid)
    
    if can_get_bonus:
        await msg.reply(
            "🎁 <b>Бонус доступен прямо сейчас!</b>\n\n"
            f"💰 Всего получено бонусов: <code>{bonus_data.get('total_bonus', 0):,}</code>\n"
            f"✨ <b>Следующий бонус:</b> 5-20 миллионов",
            parse_mode="HTML"
        )
    else:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        progress_percent = int((3600 - remaining) / 3600 * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        await msg.reply(
            f"⏳ <b>До следующего бонуса:</b>\n"
            f"<b>{minutes} минут {seconds} секунд</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Будет доступен в:</b> {next_str}\n\n"
            f"💰 Всего получено бонусов: <code>{bonus_data.get('total_bonus', 0):,}</code>\n"
            f"🎯 <b>Следующий бонус:</b> 5-20 миллионов",
            parse_mode="HTML"
        )

async def check_work_cd(msg: Message):
    """Проверить оставшееся время до работы"""
    uid = msg.from_user.id
    can_work, remaining, work_data = await check_work_cooldown(uid)
    
    if can_work:
        await msg.reply(
            "💼 <b>Работа доступна прямо сейчас!</b>\n\n"
            f"💰 Всего заработано: <code>{work_data.get('total_work', 0):,}</code>\n"
            f"✨ <b>Следующая работа:</b> 1-5 миллионов",
            parse_mode="HTML"
        )
    else:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        progress_percent = int((WORK_COOLDOWN - remaining) / WORK_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        await msg.reply(
            f"⏳ <b>До следующей работы:</b>\n"
            f"<b>{minutes} минут {seconds} секунд</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Будет доступна в:</b> {next_str}\n\n"
            f"💰 Всего заработано: <code>{work_data.get('total_work', 0):,}</code>\n"
            f"🎯 <b>Следующая работа:</b> 1-5 миллионов",
            parse_mode="HTML"
        )

async def process_balance(msg: Message):
    """Обработка команды баланс"""
    user = await get_user(msg.from_user.id)
    await msg.reply(f"💰 Баланс: <code>{user['balance']:,}</code>", parse_mode="HTML")

async def process_profile(msg: Message):
    """Обработка команды профиль"""
    user = await get_user(msg.from_user.id)
    username = msg.from_user.username or msg.from_user.first_name
    
    total = user['wins'] + user['losses']
    win_rate = (user['wins'] / total * 100) if total > 0 else 0
    
    can_get_bonus, remaining_bonus, _ = await check_bonus_cooldown(msg.from_user.id)
    can_work, remaining_work, _ = await check_work_cooldown(msg.from_user.id)
    
    # Статус бонуса
    if can_get_bonus:
        bonus_status = "✅ <b>Доступен сейчас!</b>"
        bonus_time = "Следующий через 1 час"
        bonus_bar = ""
    else:
        minutes = int(remaining_bonus // 60)
        seconds = int(remaining_bonus % 60)
        progress_percent = int((3600 - remaining_bonus) / 3600 * 100)
        bonus_bar = create_progress_bar(progress_percent)
        bonus_status = f"⏳ <b>Через:</b> {minutes}м {seconds}с"
        bonus_time = f"{bonus_bar} {progress_percent}%"
    
    # Статус работы
    if can_work:
        work_status = "✅ <b>Доступна сейчас!</b>"
        work_time = "Следующая через 1 минуту"
        work_bar = ""
    else:
        minutes = int(remaining_work // 60)
        seconds = int(remaining_work % 60)
        progress_percent = int((WORK_COOLDOWN - remaining_work) / WORK_COOLDOWN * 100)
        work_bar = create_progress_bar(progress_percent)
        work_status = f"⏳ <b>Через:</b> {minutes}м {seconds}с"
        work_time = f"{work_bar} {progress_percent}%"
    
    await msg.reply(
        f"👤 <b>Профиль {username}</b>\n\n"
        f"💰 Баланс: {user['balance']:,}\n"
        f"🏆 Побед: {user['wins']}\n"
        f"💀 Поражений: {user['losses']}\n"
        f"📊 Винрейт: {win_rate:.1f}%\n\n"
        f"🎁 <b>Ежечасный бонус (5-20М):</b>\n"
        f"• Статус: {bonus_status}\n"
        f"• {bonus_time}\n"
        f"• Всего получено: {user.get('total_bonus', 0):,}\n\n"
        f"💼 <b>Ежеминутная работа (1-5М):</b>\n"
        f"• Статус: {work_status}\n"
        f"• {work_time}\n"
        f"• Всего заработано: {user.get('total_work', 0):,}",
        parse_mode="HTML"
    )

async def process_top(msg: Message):
    """Обработка команды топ - ИСПРАВЛЕННЫЙ"""
    top = await get_top()
    if not top:
        await msg.reply("🏆 В топе пока никого нет!")
        return
    
    txt = "🏆 <b>ТОП-10 Богачей</b>\n\n"
    for i, row in enumerate(top, 1):
        username = row.get('username')
        balance = row.get('balance', 0)
        
        if username:
            username_display = f"{username}"
        else:
            username_display = f"ID {row['id']}"
        
        # Форматируем баланс
        balance_str = f"{balance:,}"
        txt += f"{i}. {username_display} — {balance_str}💰\n"
    
    await msg.reply(txt, parse_mode="HTML")

async def process_coin(msg: Message, parts: list):
    """Обработка команды монетка"""
    if len(parts) < 2:
        await msg.reply("❌ Укажите ставку!\nПример: <code>монетка 1000</code> или <code>монетка 1к</code> или <code>монетка 1кк</code>", parse_mode="HTML")
        return
    
    # Парсим ставку с поддержкой "к", "кк", "м"
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    user = await get_user(msg.from_user.id)
    
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {user['balance']:,}", parse_mode="HTML")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Орел", callback_data=f"coin_{bet}_orel"),
         InlineKeyboardButton(text="🪙 Решка", callback_data=f"coin_{bet}_reshka")]
    ])
    
    await msg.reply(
        f"🎲 <b>Монетка</b>\n\n"
        f"💰 Ставка: <code>{bet:,}</code>\n"
        f"💸 Твой баланс: <code>{user['balance']:,}</code>\n\n"
        f"Выбери сторону:",
        parse_mode="HTML",
        reply_markup=kb
    )

async def process_dice(msg: Message, parts: list):
    """Обработка команды кости"""
    if len(parts) < 2:
        await msg.reply("❌ Укажите ставку!\nПример: <code>кости 1000</code> или <code>кости 1к</code> или <code>кости 1кк</code>", parse_mode="HTML")
        return
    
    # Парсим ставку с поддержкой "к", "кк", "м"
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    user = await get_user(msg.from_user.id)
    
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {user['balance']:,}", parse_mode="HTML")
        return
    
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    
    loading_msg = await msg.reply("🎲 Бросаем кости...")
    await asyncio.sleep(1.5)
    
    dice_msg = await msg.answer_dice(emoji="🎲")
    player_roll = dice_msg.dice.value
    
    await asyncio.sleep(2)
    
    dice_msg2 = await msg.answer_dice(emoji="🎲")
    bot_roll = dice_msg2.dice.value
    
    await asyncio.sleep(1)
    
    if player_roll > bot_roll:
        win = bet * 2
        await change_balance(msg.from_user.id, win)
        await update_stats(msg.from_user.id, True)
        result = f"✅ ВЫИГРЫШ! +{bet:,}"
    elif player_roll < bot_roll:
        await update_stats(msg.from_user.id, False)
        result = f"❌ ПРОИГРЫШ -{bet:,}"
    else:
        await change_balance(msg.from_user.id, bet)
        result = "🤝 НИЧЬЯ! Ставка возвращена"
    
    await loading_msg.delete()
    
    await msg.reply(
        f"🎲 <b>Игра в кости</b>\n\n"
        f"💰 Ставка: {bet:,}\n\n"
        f"🎯 Твой бросок: {player_roll}\n"
        f"🤖 Бросок бота: {bot_roll}\n\n"
        f"{result}",
        parse_mode="HTML"
    )

async def process_slots(msg: Message, parts: list):
    """Обработка команды слоты"""
    if len(parts) < 2:
        await msg.reply("❌ Укажите ставку!\nПример: <code>слоты 500</code> или <code>слоты 0.5к</code> или <code>слоты 1кк</code>", parse_mode="HTML")
        return
    
    # Парсим ставку с поддержкой "к", "кк", "м"
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте:\n• 500 или 0.5к = 500\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    user = await get_user(msg.from_user.id)
    
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {user['balance']:,}", parse_mode="HTML")
        return
    
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    
    symbols = ["🍒", "🔔", "💎", "7️⃣", "🍋", "⭐"]
    loading_msg = await msg.reply("🎰 <b>Крутим слоты...</b>\n┃ 🎰 ┃ 🎰 ┃ 🎰 ┃", parse_mode="HTML")
    
    for i in range(12):
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)
        await loading_msg.edit_text(f"🎰 <b>Крутим слоты...</b>\n┃ {slot1} ┃ {slot2} ┃ {slot3} ┃", parse_mode="HTML")
        await asyncio.sleep(0.1)
    
    for i in range(6):
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)
        await loading_msg.edit_text(f"🎰 <b>Крутим слоты...</b>\n┃ {slot1} ┃ {slot2} ┃ {slot3} ┃", parse_mode="HTML")
        await asyncio.sleep(0.2)
    
    result = [random.choice(symbols) for _ in range(3)]
    
    if result[0] == result[1] == result[2]:
        win = bet * 10
        await change_balance(msg.from_user.id, win)
        await update_stats(msg.from_user.id, True)
        result_text = f"🎰 <b>ДЖЕКПОТ!</b> 🎰\n💰 Выигрыш: <code>{win:,}</code>"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win = bet * 3
        await change_balance(msg.from_user.id, win)
        await update_stats(msg.from_user.id, True)
        result_text = f"✅ <b>ВЫИГРЫШ!</b>\n💰 +{win:,}"
    else:
        await update_stats(msg.from_user.id, False)
        result_text = f"❌ <b>ПРОИГРЫШ</b>\n💸 -{bet:,}"
    
    text = f"""
🎰 <b>Игра: Слоты</b>

💰 Ставка: {bet:,}

🎯 Результат: ┃ {result[0]} ┃ {result[1]} ┃ {result[2]} ┃

{result_text}
"""
    
    await loading_msg.edit_text(text, parse_mode="HTML")

async def process_roulette(msg: Message, parts: list):
    """Обработка команды рулетка"""
    if len(parts) < 3:
        await msg.reply(
            "🎰 <b>Рулетка - Помощь</b>\n\n"
            "🎯 <b>Формат:</b> <code>рулетка [ставка] [тип]</code>\n"
            "🎯 <b>Коротко:</b> <code>рул [ставка] [тип]</code>\n\n"
            "🎯 <b>Типы ставок:</b>\n"
            "• <code>красное</code> / <code>крас</code> (x2)\n"
            "• <code>черное</code> / <code>черн</code> (x2)\n"
            "• <code>зеленое</code> / <code>зел</code> (x36)\n"
            "• <code>четное</code> / <code>чет</code> (x2)\n"
            "• <code>нечетное</code> / <code>нечет</code> (x2)\n"
            "• <code>1-18</code> / <code>19-36</code> (x2)\n"
            "• <code>1-12</code> / <code>13-24</code> / <code>25-36</code> (x3)\n"
            "• <code>[число от 0 до 36]</code> (x36)\n\n"
            "🎯 <b>Примеры:</b>\n"
            "<code>рулетка 1000 красное</code>\n"
            "<code>рул 5к 17</code>\n"
            "<code>рулетка 2к четное</code>\n"
            "<code>рул 1кк 1-12</code>\n"
            "<code>рул 10кк красное</code>",
            parse_mode="HTML"
        )
        return
    
    # Парсим ставку с поддержкой "к", "кк", "м"
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    user = await get_user(msg.from_user.id)
    
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {user['balance']:,}", parse_mode="HTML")
        return
    
    bet_type = parts[2].lower()
    
    # Нормализуем тип ставки
    if bet_type in ['крас', 'red', 'кр']:
        bet_type = 'красное'
    elif bet_type in ['черн', 'чер', 'black', 'чр']:
        bet_type = 'черное'
    elif bet_type in ['зел', 'green', '0', 'зл']:
        bet_type = 'зеленое'
    elif bet_type in ['чет', 'even', 'четн', 'ч']:
        bet_type = 'четное'
    elif bet_type in ['нечет', 'odd', 'неч', 'н']:
        bet_type = 'нечетное'
    elif bet_type == '0':
        bet_type = 'зеленое'
    
    # Проверяем, является ли ставка на число
    is_number_bet = False
    number_value = None
    
    if bet_type.isdigit():
        num = int(bet_type)
        if 0 <= num <= 36:
            is_number_bet = True
            number_value = str(num)
            bet_type = "число"
    
    # Допустимые типы
    valid_types = ['красное', 'черное', 'зеленое', 'четное', 'нечетное',
                  '1-18', '19-36', '1-12', '13-24', '25-36']
    
    if not is_number_bet and bet_type not in valid_types:
        await msg.reply("❌ Неправильный тип ставки. Используй команду рулетка без аргументов для помощи")
        return
    
    # Снимаем ставку
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    
    # Крутим рулетку (без анимации)
    loading_msg = await msg.reply("🎰 Крутим рулетку...")
    await asyncio.sleep(1)
    
    # Финальный результат
    final_number = random.choice(ROULETTE_NUMBERS)
    final_color = get_roulette_color(final_number)
    
    # Проверяем выигрыш
    is_win = get_roulette_result(final_number, bet_type, number_value)
    multiplier = get_roulette_multiplier(bet_type)
    
    if is_win:
        win = bet * multiplier
        await change_balance(msg.from_user.id, win)
        await update_stats(msg.from_user.id, True)
        result_text = f"✅ <b>ВЫИГРЫШ!</b>\n💰 +{win:,} (x{multiplier})"
    else:
        await update_stats(msg.from_user.id, False)
        result_text = f"❌ <b>ПРОИГРЫШ</b>\n💸 -{bet:,}"
    
    display_value = number_value if number_value else bet_type
    
    # Удаляем сообщение "Крутим рулетку..."
    await loading_msg.delete()
    
    text = f"""
🎰 <b>Рулетка - Результат</b>

💰 Ставка: {bet:,}
🎯 Тип ставки: {display_value}
📈 Множитель: x{multiplier}

🎯 Выпало число: <b>{final_number}</b>
🎨 Цвет: {final_color}

{result_text}
"""
    
    await msg.reply(text, parse_mode="HTML")

async def process_bj(msg: Message, parts: list):
    """Обработка команды блэкджек"""
    # Обработка команды без аргументов (просто "бж" или "bj")
    if len(parts) == 1 and parts[0] in ['бж', 'bj']:
        # Проверяем активную игру
        uid = msg.from_user.id
        game = load_bj_game(uid)
        
        if game:
            # Показываем текущую игру
            hand = game['hand']
            dealer_hand = game['dealer_hand']
            bet = game['bet']
            player_value = hand_value(hand)
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
                 InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")],
                [InlineKeyboardButton(text="🎴 Показать текущую игру", callback_data="bj_show")]
            ])
            
            text = f"""
🃏 <b>Блэкджек - Активная игра</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}

Игра активна! Выбери действие или нажми "Показать текущую игру"
"""
            await msg.reply(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.reply("🃏 Отправь: <code>блекджек [ставка]</code>\nПример: <code>бж 1000</code> или <code>бж 1к</code> или <code>бж 1кк</code>", parse_mode="HTML")
        return
    
    # Обычная команда с ставкой
    if len(parts) < 2:
        await msg.reply("🃏 Отправь: <code>блекджек [ставка]</code>\nПример: <code>бж 1000</code> или <code>бж 1к</code> или <code>бж 1кк</code>", parse_mode="HTML")
        return
    
    # Парсим ставку с поддержкой "к", "кк", "м"
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    user = await get_user(msg.from_user.id)
    
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {user['balance']:,}", parse_mode="HTML")
        return
    
    uid = msg.from_user.id
    
    # Проверяем активную игру
    game = load_bj_game(uid)
    if game:
        # Показываем текущее состояние игры с кнопками действий
        hand = game['hand']
        dealer_hand = game['dealer_hand']
        bet = game['bet']
        player_value = hand_value(hand)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
             InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")],
            [InlineKeyboardButton(text="🎴 Показать текущую игру", callback_data="bj_show")]
        ])
        
        text = f"""
🃏 <b>Блэкджек - Активная игра</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}

Игра активна! Выбери действие или нажми "Показать текущую игру"
"""
        await msg.reply(text, parse_mode="HTML", reply_markup=kb)
        return
    
    # Новая игра
    success = await change_balance(uid, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    
    hand = [random.choice(CARDS), random.choice(CARDS)]
    dealer_hand = [random.choice(CARDS), random.choice(CARDS)]
    
    save_bj_game(uid, bet, hand, dealer_hand)
    player_value = hand_value(hand)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
         InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")]
    ])
    
    text = f"""
🃏 <b>Блэкджек - Новая игра</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}
📊 <b>Видимая сумма дилера:</b> {CARD_VALUES.get(dealer_hand[1], 0)}

Выбери действие:
"""
    await msg.reply(text, parse_mode="HTML", reply_markup=kb)

async def process_transfer(msg: Message, parts: list):
    """Обработка команды передачи денег"""
    if len(parts) < 3:
        await msg.reply("❌ Используйте: <code>передать [сумма] @юзернейм</code>\nПример: передать 1000 @username", parse_mode="HTML")
        return
    
    # Парсим сумму с поддержкой "к", "кк", "м"
    amount_str = parts[1]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    sender_id = msg.from_user.id
    sender = await get_user(sender_id)
    
    if sender['balance'] < amount:
        await msg.reply(f"❌ Недостаточно средств! Баланс: {sender['balance']:,}", parse_mode="HTML")
        return
    
    recipient_username = parts[2].lower().replace('@', '')
    
    if recipient_username.isdigit():
        await msg.reply("❌ Укажите @юзернейм, а не ID")
        return
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, username FROM users WHERE username = ?", (recipient_username,))
            row = await cursor.fetchone()
            
            if not row:
                await msg.reply(f"❌ Пользователь @{recipient_username} не найден в системе")
                return
            
            recipient_id = row['id']
            
            if recipient_id == sender_id:
                await msg.reply("❌ Нельзя переводить деньги самому себе!")
                return
            
            success = await change_balance(sender_id, -amount)
            if not success:
                await msg.reply("❌ Ошибка при списании средств")
                return
            
            success = await change_balance(recipient_id, amount)
            if not success:
                await change_balance(sender_id, amount)
                await msg.reply("❌ Ошибка при переводе. Деньги возвращены.")
                return
            
            updated_sender = await get_user(sender_id)
            updated_recipient = await get_user(recipient_id)
            
            sender_name = msg.from_user.username or msg.from_user.first_name
            
            await msg.reply(
                f"✅ <b>Перевод выполнен успешно!</b>\n\n"
                f"💰 Сумма: <code>{amount:,}</code>\n"
                f"👤 От: {sender_name} (ID: {sender_id})\n"
                f"👥 Кому: @{recipient_username} (ID: {recipient_id})\n\n"
                f"📊 <b>Новые балансы:</b>\n"
                f"• Ваш баланс: <code>{updated_sender['balance']:,}</code>\n"
                f"• Баланс получателя: <code>{updated_recipient['balance']:,}</code>",
                parse_mode="HTML"
            )
            
            try:
                await msg.bot.send_message(
                    recipient_id,
                    f"💰 <b>Вы получили перевод!</b>\n\n"
                    f"💸 Сумма: <code>{amount:,}</code>\n"
                    f"👤 От: {sender_name} (ID: {sender_id})\n"
                    f"📊 Ваш новый баланс: <code>{updated_recipient['balance']:,}</code>",
                    parse_mode="HTML"
                )
            except:
                pass
    
    except Exception as e:
        logger.error(f"Ошибка при переводе: {e}")
        await msg.reply("❌ Ошибка при выполнении перевода")

# ========== АДМИН КОМАНДЫ ==========
async def process_admin_give_reply(msg: Message, parts: list):
    """Админ: выдать деньги по ответу"""
    if len(parts) < 2:
        await msg.reply("❌ Используйте: <code>выдать [сумма]</code> в ответ на сообщение")
        return
    
    # Парсим сумму с поддержкой "к", "кк", "м"
    amount_str = parts[1]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    target_id = msg.reply_to_message.from_user.id
    target_username = msg.reply_to_message.from_user.username or msg.reply_to_message.from_user.first_name
    
    await change_balance(target_id, amount)
    new_balance = await get_user(target_id)
    
    await msg.reply(
        f"✅ <b>Деньги выданы!</b>\n\n"
        f"💸 Сумма: <code>{amount:,}</code>\n"
        f"👤 Получатель: {target_username} (ID: {target_id})\n"
        f"💰 Новый баланс: <code>{new_balance['balance']:,}</code>",
        parse_mode="HTML"
    )

async def process_admin_give(msg: Message, parts: list):
    """Админ: выдать деньги по ID/юзернейму"""
    if len(parts) < 3:
        await msg.reply("❌ Используйте: <code>выдать @юзернейм [сумма]</code> или <code>выдать ID [сумма]</code>")
        return
    
    target_arg = parts[1]
    
    # Парсим сумму с поддержкой "к", "кк", "м"
    amount_str = parts[2]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    # Ищем пользователя
    target_id = None
    
    if target_arg.isdigit():
        # По ID
        target_id = int(target_arg)
    elif target_arg.startswith('@'):
        # По юзернейму
        username = target_arg[1:]
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
                row = await cursor.fetchone()
                if row:
                    target_id = row['id']
                else:
                    await msg.reply(f"❌ Пользователь @{username} не найден")
                    return
        except:
            await msg.reply("❌ Ошибка поиска")
            return
    else:
        await msg.reply("❌ Укажите ID или @юзернейм")
        return
    
    # Выдаем
    await change_balance(target_id, amount)
    new_balance = await get_user(target_id)
    
    await msg.reply(
        f"✅ <b>Деньги выданы!</b>\n\n"
        f"💸 Сумма: <code>{amount:,}</code>\n"
        f"👤 Получатель: ID {target_id}\n"
        f"💰 Новый баланс: <code>{new_balance['balance']:,}</code>",
        parse_mode="HTML"
    )

async def process_admin_take_reply(msg: Message, parts: list):
    """Админ: забрать деньги по ответу"""
    if len(parts) < 2:
        await msg.reply("❌ Используйте: <code>забрать [сумма]</code> в ответ на сообщение")
        return
    
    # Парсим сумму с поддержкой "к", "кк", "м"
    amount_str = parts[1]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    target_id = msg.reply_to_message.from_user.id
    target_username = msg.reply_to_message.from_user.username or msg.reply_to_message.from_user.first_name
    
    target_user = await get_user(target_id)
    if target_user['balance'] < amount:
        await msg.reply(f"❌ У пользователя только {target_user['balance']:,}")
        return
    
    await change_balance(target_id, -amount)
    new_balance = await get_user(target_id)
    
    await msg.reply(
        f"✅ <b>Деньги забраны!</b>\n\n"
        f"💸 Сумма: <code>{amount:,}</code>\n"
        f"👤 Пользователь: {target_username} (ID: {target_id})\n"
        f"💰 Новый баланс: <code>{new_balance['balance']:,}</code>",
        parse_mode="HTML"
    )

async def process_admin_take(msg: Message, parts: list):
    """Админ: забрать деньги по ID/юзернейму"""
    if len(parts) < 3:
        await msg.reply("❌ Используйте: <code>забрать @юзернейм [сумма]</code> или <code>забрать ID [сумма]</code>")
        return
    
    target_arg = parts[1]
    
    # Парсим сумму с поддержкой "к", "кк", "м"
    amount_str = parts[2]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма! Используйте:\n• 1000 или 1к = 1,000\n• 1кк или 1м = 1,000,000\n• 10кк = 10,000,000\n• 1.5к = 1,500")
        return
    
    # Ищем пользователя
    target_id = None
    
    if target_arg.isdigit():
        target_id = int(target_arg)
    elif target_arg.startswith('@'):
        username = target_arg[1:]
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
                row = await cursor.fetchone()
                if row:
                    target_id = row['id']
                else:
                    await msg.reply(f"❌ Пользователь @{username} не найден")
                    return
        except:
            await msg.reply("❌ Ошибка поиска")
            return
    else:
        await msg.reply("❌ Укажите ID или @юзернейм")
        return
    
    target_user = await get_user(target_id)
    if target_user['balance'] < amount:
        await msg.reply(f"❌ У пользователя только {target_user['balance']:,}")
        return
    
    await change_balance(target_id, -amount)
    new_balance = await get_user(target_id)
    
    await msg.reply(
        f"✅ <b>Деньги забраны!</b>\n\n"
        f"💸 Сумма: <code>{amount:,}</code>\n"
        f"👤 Пользователь: ID {target_id}\n"
        f"💰 Новый баланс: <code>{new_balance['balance']:,}</code>",
        parse_mode="HTML"
    )

# ========== КОМАНДЫ С / ДЛЯ СОВМЕСТИМОСТИ ==========
@router.message(Command("start", "menu"))
async def cmd_start(msg: Message):
    user = await get_user(msg.from_user.id)
    username = msg.from_user.username or msg.from_user.first_name
    
    can_get_bonus, remaining_bonus, _ = await check_bonus_cooldown(msg.from_user.id)
    can_work, remaining_work, _ = await check_work_cooldown(msg.from_user.id)
    
    bonus_info = ""
    work_info = ""
    
    if can_get_bonus:
        bonus_info = "🎁 <b>Бонус доступен прямо сейчас!</b>"
    else:
        minutes = int(remaining_bonus // 60)
        seconds = int(remaining_bonus % 60)
        progress_percent = int((3600 - remaining_bonus) / 3600 * 100)
        progress_bar = create_progress_bar(progress_percent)
        bonus_info = f"⏳ <b>Бонус через:</b> {minutes}м {seconds}с\n{progress_bar} {progress_percent}%"
    
    if can_work:
        work_info = "💼 <b>Работа доступна прямо сейчас!</b>"
    else:
        minutes = int(remaining_work // 60)
        seconds = int(remaining_work % 60)
        progress_percent = int((WORK_COOLDOWN - remaining_work) / WORK_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        work_info = f"⏳ <b>Работа через:</b> {minutes}м {seconds}с\n{progress_bar} {progress_percent}%"
    
    text = f"""
🎌 <b>Привет, {username}!</b>

💰 <b>Твой баланс:</b> <code>{user['balance']:,}</code>

🎁 <b>Ежечасный бонус:</b> 5-20М 💰
{bonus_info}

💼 <b>Ежеминутная работа:</b> 1-5М 💰
{work_info}

<b>📱 Поддержка сокращений:</b>
• 1к = 1,000 | 1кк = 1,000,000
• 10кк = 10,000,000 | 100кк = 100,000,000
• 1.5к = 1,500 | 2.5кк = 2,500,000
• 1м = 1,000,000 | 1.5м = 1,500,000

<b>Примеры ставок:</b>
• монетка 1к
• кости 500к
• слоты 1кк
• рулетка 10кк красное
• блекджек 5кк
• передать 100кк @username

<b>Команды работают и с / и без:</b>
• баланс / б - показать баланс
• бонус - получить бонус (каждый час!)
• работа - выполнить работу (каждую минуту!)
• кд - проверить время до бонуса
• кдработы - проверить время до работы
• профиль / пр - статистика
• топ - топ игроков

<b>Игры:</b>
• монетка [ставка] - игра в монетку
• кости [ставка] - игра в кости
• слоты [ставка] - игровые автоматы
• рулетка [ставка] [тип] - рулетка
• блекджек [ставка] - игра в блэкджек

<b>Деньги:</b>
• передать [сумма] @юзернейм - передать деньги
"""
    await msg.answer(text, parse_mode="HTML")

# Также оставляем команды с / для удобства
@router.message(Command("баланс", "б", "balance"))
async def cmd_balance_slash(msg: Message):
    await process_balance(msg)

@router.message(Command("бонус", "bonus"))
async def cmd_bonus_slash(msg: Message):
    await process_bonus(msg)

@router.message(Command("работа", "work", "раб"))
async def cmd_work_slash(msg: Message):
    await process_work(msg)

@router.message(Command("кд", "cd", "кулдаун"))
async def cmd_cd_slash(msg: Message):
    await check_bonus_cd(msg)

@router.message(Command("кдработы", "работакд", "workcd"))
async def cmd_work_cd_slash(msg: Message):
    await check_work_cd(msg)

@router.message(Command("профиль", "пр", "стата", "profile"))
async def cmd_profile_slash(msg: Message):
    await process_profile(msg)

@router.message(Command("топ", "лидеры", "top"))
async def cmd_top_slash(msg: Message):
    await process_top(msg)

@router.message(Command("монетка", "coin", "мн"))
async def cmd_coin_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply("🎲 Используй: <code>монетка [ставка]</code>\nПример: монетка 1000 или монетка 1к или монетка 1кк", parse_mode="HTML")
        return
    
    parts = ["монетка"] + command.args.split()
    await process_coin(msg, parts)

@router.message(Command("кости", "dice", "кст"))
async def cmd_dice_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply("🎲 Используй: <code>кости [ставка]</code>\nПример: кости 1000 или кости 1к или кости 1кк", parse_mode="HTML")
        return
    
    parts = ["кости"] + command.args.split()
    await process_dice(msg, parts)

@router.message(Command("слоты", "slots", "сл"))
async def cmd_slots_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply("🎰 Используй: <code>слоты [ставка]</code>\nПример: слоты 500 или слоты 0.5к или слоты 1кк", parse_mode="HTML")
        return
    
    parts = ["слоты"] + command.args.split()
    await process_slots(msg, parts)

@router.message(Command("рулетка", "roulette", "рул"))
async def cmd_roulette_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply(
            "🎰 <b>Рулетка - Помощь</b>\n\n"
            "🎯 <b>Формат:</b> <code>рулетка [ставка] [тип]</code>\n\n"
            "🎯 <b>Типы ставок:</b>\n"
            "• <code>красное</code> (x2)\n"
            "• <code>черное</code> (x2)\n"
            "• <code>зеленое</code> (x36)\n"
            "• <code>четное</code> / <code>нечетное</code> (x2)\n"
            "• <code>1-18</code> / <code>19-36</code> (x2)\n"
            "• <code>1-12</code> / <code>13-24</code> / <code>25-36</code> (x3)\n"
            "• <code>[число от 0 до 36]</code> (x36)\n\n"
            "<b>📱 Поддержка сокращений:</b>\n"
            "• 1к = 1,000 | 1кк = 1,000,000\n"
            "• 10кк = 10,000,000 | 100кк = 100,000,000\n"
            "• Пример: <code>рул 10кк красное</code>",
            parse_mode="HTML"
        )
        return
    
    parts = ["рулетка"] + command.args.split()
    await process_roulette(msg, parts)

@router.message(Command("блекджек", "блэкджек", "bj", "бж", "blackjack"))
async def cmd_bj_slash(msg: Message, command: CommandObject):
    if not command.args:
        # Проверяем активную игру
        uid = msg.from_user.id
        game = load_bj_game(uid)
        
        if game:
            # Показываем текущую игру
            hand = game['hand']
            dealer_hand = game['dealer_hand']
            bet = game['bet']
            player_value = hand_value(hand)
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
                 InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")],
                [InlineKeyboardButton(text="🎴 Показать текущую игру", callback_data="bj_show")]
            ])
            
            text = f"""
🃏 <b>Блэкджек - Активная игра</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}

Игра активна! Выбери действие или нажми "Показать текущую игру"
"""
            await msg.reply(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.reply("🃏 Используй: <code>блекджек [ставка]</code>\nПример: блекджек 1000 или блекджек 1к или блекджек 1кк", parse_mode="HTML")
        return
    
    parts = ["блекджек"] + command.args.split()
    await process_bj(msg, parts)

@router.message(Command("передать", "transfer"))
async def cmd_transfer_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply("💸 Используй: <code>передать [сумма] @юзернейм</code>\nПример: передать 1000 @username или передать 1к @username или передать 1кк @username", parse_mode="HTML")
        return
    
    parts = ["передать"] + command.args.split()
    await process_transfer(msg, parts)

@router.message(Command("выдать"))
async def cmd_give_slash(msg: Message):
    # Передаем обработку в общую функцию
    await handle_all_commands(msg)

@router.message(Command("забрать"))
async def cmd_take_slash(msg: Message):
    # Передаем обработку в общую функцию
    await handle_all_commands(msg)

# ========== CALLBACK ОБРАБОТЧИКИ ДЛЯ БЛЭКДЖЕКА ==========
@router.callback_query(F.data == "bj_show")
async def bj_show_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    game = load_bj_game(uid)
    
    if not game:
        await cb.answer("❌ Нет активной игры", show_alert=True)
        return
    
    hand = game['hand']
    dealer_hand = game['dealer_hand']
    bet = game['bet']
    player_value = hand_value(hand)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
         InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")]
    ])
    
    text = f"""
🃏 <b>Блэкджек - Текущая игра</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}

Выбери действие:
"""
    
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer("Текущая игра загружена")

@router.callback_query(F.data == "bj_hit")
async def bj_hit_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    game = load_bj_game(uid)
    
    if not game:
        await cb.answer("❌ Нет активной игры. Начни новую: блекджек [ставка]", show_alert=True)
        return
    
    bet = game['bet']
    hand = game['hand']
    dealer_hand = game['dealer_hand']
    
    hand.append(random.choice(CARDS))
    player_value = hand_value(hand)
    
    await cb.answer("🎴 Вы взяли карту...")
    
    if player_value > 21:
        clear_bj_game(uid)
        await update_stats(uid, False)
        
        text = f"""
🃏 <b>Блэкджек - Перебор!</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value} (>21)

❌ <b>ПЕРЕБОР! Вы проиграли {bet:,}</b>
"""
        await cb.message.edit_text(text, parse_mode="HTML")
    else:
        save_bj_game(uid, bet, hand, dealer_hand)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Взять карту", callback_data="bj_hit"),
             InlineKeyboardButton(text="🛑 Остановиться", callback_data="bj_stand")]
        ])
        
        text = f"""
🃏 <b>Блэкджек - Продолжаем игру</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Сумма очков:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand, hide_first=True)}
📊 <b>Видимая сумма дилера:</b> {CARD_VALUES.get(dealer_hand[1], 0)}

Выбери действие:
"""
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "bj_stand")
async def bj_stand_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    game = load_bj_game(uid)
    
    if not game:
        await cb.answer("❌ Нет активной игры", show_alert=True)
        return
    
    bet = game['bet']
    hand = game['hand']
    dealer_hand = game['dealer_hand']
    
    player_value = hand_value(hand)
    
    await cb.answer("🛑 Останавливаемся...")
    
    while hand_value(dealer_hand) < 17:
        dealer_hand.append(random.choice(CARDS))
    
    dealer_value = hand_value(dealer_hand)
    
    clear_bj_game(uid)
    
    if player_value > 21:
        result = f"❌ <b>ПРОИГРЫШ</b>\n💸 Вы проиграли {bet:,}"
        await update_stats(uid, False)
    elif dealer_value > 21:
        win = bet * 2
        await change_balance(uid, win)
        result = f"✅ <b>ВЫИГРЫШ!</b>\n💰 Вы выиграли {bet:,}"
        await update_stats(uid, True)
    elif player_value > dealer_value:
        win = bet * 2
        await change_balance(uid, win)
        result = f"✅ <b>ВЫИГРЫШ!</b>\n💰 Вы выиграли {bet:,}"
        await update_stats(uid, True)
    elif player_value < dealer_value:
        result = f"❌ <b>ПРОИГРЫШ</b>\n💸 Вы проиграли {bet:,}"
        await update_stats(uid, False)
    else:
        await change_balance(uid, bet)
        result = "🤝 <b>НИЧЬЯ!</b>\n🔄 Ставка возвращена"
    
    text = f"""
🃏 <b>Блэкджек - Результат игры</b>

💰 Ставка: <code>{bet:,}</code>

🃁 <b>Твои карты:</b> {format_cards(hand)}
📊 <b>Твоя сумма:</b> {player_value}

🤖 <b>Карты дилера:</b> {format_cards(dealer_hand)}
📊 <b>Сумма дилера:</b> {dealer_value}

{result}
"""
    await cb.message.edit_text(text, parse_mode="HTML")

# ========== CALLBACK ОБРАБОТЧИКИ ДЛЯ МОНЕТКИ ==========
@router.callback_query(F.data.startswith("coin_"))
async def coin_flip_cb(cb: CallbackQuery):
    try:
        _, bet_str, choice = cb.data.split("_")
        bet = int(bet_str)
    except:
        await cb.answer("❌ Ошибка")
        return
    
    uid = cb.from_user.id
    await change_balance(uid, -bet)
    
    await cb.message.edit_text("🎲 Подбрасываем монетку...")
    await asyncio.sleep(1.5)
    
    result = random.choice(["orel", "reshka"])
    
    if result == choice:
        win = bet * 2
        await change_balance(uid, win)
        await update_stats(uid, True)
        result_text = f"✅ <b>ВЫИГРЫШ!</b>\n💰 +{bet:,}"
    else:
        await update_stats(uid, False)
        result_text = f"❌ <b>ПРОИГРЫШ</b>\n💸 -{bet:,}"
    
    ru_result = "🦅 Орел" if result == "orel" else "🪙 Решка"
    ru_choice = "🦅 Орел" if choice == "orel" else "🪙 Решка"
    
    text = f"""
🎲 <b>Монетка - Результат</b>

💰 Ставка: {bet:,}

🎯 Выпало: {ru_result}
🎯 Твой выбор: {ru_choice}

{result_text}
"""
    
    await cb.message.edit_text(text, parse_mode="HTML")
    await cb.answer()

# ========== ОБНОВЛЕНИЕ ЮЗЕРНЕЙМА ==========
@router.message()
async def update_username_handler(msg: Message):
    uid = msg.from_user.id
    username = msg.from_user.username
    if username:
        await update_username(uid, username)

# ========== ЗАПУСК ==========
async def main():
    await init_db()
    
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    me = await bot.get_me()
    logger.info(f"✅ Бот запущен: @{me.username}")
    logger.info("🎯 Теперь команды работают И С / И БЕЗ / !")
    logger.info("🎰 Добавлен БЛЭКДЖЕК с полной игровой механикой")
    logger.info("💰 Бонус: 5-20М каждый час с прогресс-баром!")
    logger.info("💼 Работа: 1-5М каждую минуту!")
    logger.info("📱 Полная поддержка сокращений: 1к, 10кк, 100кк, 1.5к и т.д.")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
