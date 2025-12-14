import asyncio
import aiosqlite
import random
import time
import logging
import hashlib
import math
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Dice
from aiogram.enums import ChatType
print("🔥 THIS FILE IS RUNNING")

# ========== НАСТРОЙКИ ==========
TOKEN = "8424494037:AAHrtN5irOGb7SzLQicLHCPQt9p5o8FF_sA"
ADMIN_IDS = {1162907446}  # Твой ID
DB_PATH = "murasaki.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

@router.message(F.text.lower() == "меню")
async def menu_cmd(msg: Message):
    await send_welcome_message(msg)


@router.message(F.text.lower() == "мой бизнес")
async def my_business_cmd(msg: Message):
    await show_my_businesses(msg)


@router.message(F.text.lower() == "майнинг")
async def mining_cmd(msg: Message):
    await show_mining_panel(msg=msg)


@router.message(F.text.lower().in_(["инвестировать", "инвестиции"]))
async def investments_cmd(msg: Message):
    await show_investments_panel(msg=msg)


@router.message(F.text.lower().in_(["мои планеты", "планеты"]))
async def planets_cmd(msg: Message):
    await show_my_planets_panel(msg)


# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
WORK_COOLDOWN = 30  # 30 секунд вместо 60

# ========== МАЙНИНГ БИТКОИНОВ ==========
class BitcoinMining:
    """Класс для майнинга биткоинов"""
    @staticmethod
    def calculate_hashrate(gpu_count: int, gpu_level: int) -> float:
        """Вычисляет хешрейт на основе видеокарт"""
        base_hashrate = 100  # MH/s на одну базовую видеокарту
        return gpu_count * base_hashrate * (1 + gpu_level * 0.8)
    
    @staticmethod
    def calculate_btc_per_hour(hashrate: float) -> float:
        """Вычисляет сколько BTC добывается в час"""
        # Улучшенная формула: 100 MH/s = 0.00001 BTC/час (в 10 раз больше)
        return (hashrate / 100) * 0.00001
    
    @staticmethod
    def get_bitcoin_price() -> float:
        """Текущая цена биткоина в $"""
        base_price = 60000
        fluctuation = random.uniform(-0.05, 0.05)
        return base_price * (1 + fluctuation)
    
    @staticmethod
    def get_gpu_price(gpu_level: int) -> int:
        """Цена видеокарты в зависимости от уровня"""
        base_prices = {
            1: 500_000,      # 500к
            2: 2_500_000,    # 2.5М
            3: 10_000_000,   # 10М
            4: 50_000_000,   # 50М
            5: 200_000_000   # 200М
        }
        return base_prices.get(gpu_level, 500_000)

# ========== БИЗНЕСЫ ==========
BUSINESSES = {
    1: {
        'name': 'Продажа паленого шмота',
        'price': 100_000,  # 100к
        'profit_per_hour': 20_000,  # 20к в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Товары',
        'product_capacity': 100,
        'product_refill_cost': 10_000
    },
    2: {
        'name': 'Забегаловка у метро',
        'price': 1_000_000,  # 1 млн
        'profit_per_hour': 150_000,  # 150к в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Еда',
        'product_capacity': 200,
        'product_refill_cost': 75_000
    },
    3: {
        'name': 'Сервер Minecraft',
        'price': 5_000_000,  # 5 млн
        'profit_per_hour': 600_000,  # 600к в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Слоты',
        'product_capacity': 50,
        'product_refill_cost': 300_000
    },
    4: {
        'name': 'Производство презервативов',
        'price': 25_000_000,  # 25 млн
        'profit_per_hour': 2_500_000,  # 2.5М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Сырье',
        'product_capacity': 500,
        'product_refill_cost': 1_250_000
    },
    5: {
        'name': 'Samsung',
        'price': 100_000_000,  # 100 млн
        'profit_per_hour': 8_000_000,  # 8М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Комплектующие',
        'product_capacity': 1000,
        'product_refill_cost': 4_000_000
    },
    6: {
        'name': 'Аптека',
        'price': 500_000_000,  # 500 млн
        'profit_per_hour': 30_000_000,  # 30М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Лекарства',
        'product_capacity': 800,
        'product_refill_cost': 15_000_000
    },
    7: {
        'name': 'Фабрика мороженого',
        'price': 2_000_000_000,  # 2 млрд
        'profit_per_hour': 100_000_000,  # 100М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Ингредиенты',
        'product_capacity': 1500,
        'product_refill_cost': 50_000_000
    },
    8: {
        'name': 'Парк аттракционов',
        'price': 10_000_000_000,  # 10 млрд
        'profit_per_hour': 400_000_000,  # 400М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Билеты',
        'product_capacity': 5000,
        'product_refill_cost': 200_000_000
    },
    9: {
        'name': 'NASA',
        'price': 50_000_000_000,  # 50 млрд
        'profit_per_hour': 1_500_000_000,  # 1.5Б в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Топливо',
        'product_capacity': 2000,
        'product_refill_cost': 750_000_000
    },
    10: {
        'name': 'ВКонтакте',
        'price': 200_000_000_000,  # 200 млрд
        'profit_per_hour': 6_000_000_000,  # 6Б в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Сервера',
        'product_capacity': 10000,
        'product_refill_cost': 3_000_000_000
    },
    11: {
        'name': 'Владелец бота',
        'price': 1_000_000_000_000,  # 1 трлн
        'profit_per_hour': 30_000_000_000,  # 30Б в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Пользователи',
        'product_capacity': 50000,
        'product_refill_cost': 15_000_000_000
    },
    12: {
        'name': 'Заправка',
        'price': 50_000_000,  # 50 млн
        'profit_per_hour': 2_500_000,  # 2.5М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Топливо',
        'product_capacity': 10000,
        'product_refill_cost': 1_250_000
    },
    13: {
        'name': 'Майнинг ферма',
        'price': 30_000_000,  # 30 млн
        'profit_per_hour': 1_500_000,  # 1.5М в час
        'max_level': 10,
        'upgrade_multiplier': 1.5,
        'product_name': 'Электричество',
        'product_capacity': 5000,
        'product_refill_cost': 750_000
    }
}

# ========== ПЛАНЕТЫ ==========
PLANETS = {
    1: {
        'name': 'Марс с колонией',
        'price_dollars': 1_000_000_000,  # 1 млрд
        'price_plasma': 0,
        'plasma_per_hour': 10,
        'description': 'Первая колония на Марсе'
    },
    2: {
        'name': 'Земля 4040',
        'price_dollars': 0,
        'price_plasma': 500,
        'plasma_per_hour': 25,
        'description': 'Земля будущего'
    },
    3: {
        'name': 'Луна',
        'price_dollars': 0,
        'price_plasma': 2_000,
        'plasma_per_hour': 75,
        'description': 'Лунная база'
    },
    4: {
        'name': 'Ядерное солнце',
        'price_dollars': 0,
        'price_plasma': 7_500,
        'plasma_per_hour': 125,
        'description': 'Искусственная звезда'
    },
    5: {
        'name': 'Звезда Смерти',
        'price_dollars': 0,
        'price_plasma': 50_000,
        'plasma_per_hour': 900,
        'description': 'Легендарное оружие'
    }
}

# ========== ИНВЕСТИЦИИ ==========
INVESTMENTS = {
    1: {
        'name': 'Золотые слитки',
        'duration': 2 * 3600,
        'min_amount': 1_000_000,
        'success_rate': 0.9,
        'profit_multiplier': 1.3
    },
    2: {
        'name': 'IT стартап',
        'duration': 6 * 3600,
        'min_amount': 10_000_000,
        'success_rate': 0.7,
        'profit_multiplier': 2.0
    },
    3: {
        'name': 'Медицина',
        'duration': 12 * 3600,
        'min_amount': 50_000_000,
        'success_rate': 0.8,
        'profit_multiplier': 1.8
    },
    4: {
        'name': 'Акции и облигации',
        'duration': 24 * 3600,
        'min_amount': 200_000_000,
        'success_rate': 0.85,
        'profit_multiplier': 1.5
    },
    5: {
        'name': 'Недвижимость',
        'duration': 72 * 3600,
        'min_amount': 1_000_000_000,
        'success_rate': 0.95,
        'profit_multiplier': 1.2
    }
}

# ========== БЛЭКДЖЕК ==========
bj_games = {}
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
        if time.time() - bj_games[uid]['timestamp'] > 600:
            del bj_games[uid]
            return None
        return bj_games[uid]
    return None

def clear_bj_game(uid: int):
    if uid in bj_games:
        del bj_games[uid]

# ========== ДАРТС: МИШЕНЬ С ЗОНАМИ ==========
DARTS_ZONES = {
    'center': {
        'name': '🎯 Центр',
        'multiplier': 5,
        'probability': 0.1,  # 10% шанс
        'emoji': '🎯'
    },
    'middle': {
        'name': '🟡 Средняя зона',
        'multiplier': 2,
        'probability': 0.3,  # 30% шанс
        'emoji': '🟡'
    },
    'outer': {
        'name': '🔴 Внешняя зона',
        'multiplier': 1,
        'probability': 0.6,  # 60% шанс
        'emoji': '🔴'
    },
    'miss': {
        'name': '❌ Промах',
        'multiplier': 0,
        'probability': 0.0,  # Расчетный
        'emoji': '❌'
    }
}

def get_darts_zone():
    """Определяет в какую зону попал дротик"""
    rand = random.random()
    cumulative = 0
    
    for zone_name, zone_data in DARTS_ZONES.items():
        if zone_name == 'miss':
            continue
        cumulative += zone_data['probability']
        if rand <= cumulative:
            return zone_name
    
    return 'miss'  # Если не попал ни в одну зону (маловероятно)

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

# ========== ФУНКЦИИ ДЛЯ ПАРСИНГА И ФОРМАТИРОВАНИЯ ==========
def parse_amount(amount_str: str) -> int:
    """Парсит строку с числом, поддерживая форматы: 1к, 10кк, 100кк, 1.5к"""
    if not amount_str:
        return 0
    
    amount_str = amount_str.lower().replace(',', '.').replace(' ', '')
    
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
    
    multiplier = 1
    if 'кк' in amount_str:
        multiplier = 1_000_000
    elif 'млн' in amount_str:
        multiplier = 1_000_000
    elif 'м' in amount_str:
        multiplier = 1_000_000
    elif 'к' in amount_str:
        multiplier = 1_000
    elif 'т' in amount_str:
        multiplier = 1_000_000_000_000
    elif 'б' in amount_str:
        multiplier = 1_000_000_000
    
    return int(base_value * multiplier)

def format_money(amount: int) -> str:
    """Форматирует число с разделителями и сокращениями"""
    if amount >= 1_000_000_000_000_000:
        return f"{amount / 1_000_000_000_000_000:.1f}Q"
    elif amount >= 1_000_000_000_000:
        return f"{amount / 1_000_000_000_000:.1f}T"
    elif amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.1f}Б"
    elif amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}М"
    elif amount >= 1_000:
        return f"{amount / 1_000:.1f}к"
    else:
        return str(amount)

def create_progress_bar(percentage: int, length: int = 10):
    """Создает текстовый прогресс-бар"""
    filled = int(length * percentage / 100)
    empty = length - filled
    filled_char = "█"
    empty_char = "░"
    return f"{filled_char * filled}{empty_char * empty}"

# ========== БАЗА ДАННЫХ ==========
async def update_db_structure():
    """Обновить структуру базы данных"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            new_columns = {
                'work_time': 'INTEGER DEFAULT 0',
                'total_work': 'BIGINT DEFAULT 0',
                'total_bonus': 'BIGINT DEFAULT 0',
                'referral_code': 'TEXT',
                'referred_by': 'INTEGER',
                'referral_count': 'INTEGER DEFAULT 0',
                'total_referral_earned': 'BIGINT DEFAULT 0',
                'has_started_bonus': 'BOOLEAN DEFAULT 0',
                'plasma': 'BIGINT DEFAULT 0',
                'bitcoin': 'REAL DEFAULT 0',
                'mining_gpu_count': 'INTEGER DEFAULT 0',
                'mining_gpu_level': 'INTEGER DEFAULT 1',
                'last_mining_claim': 'INTEGER DEFAULT 0',
                'wins': 'INTEGER DEFAULT 0',
                'losses': 'INTEGER DEFAULT 0'
            }
            
            for column, col_type in new_columns.items():
                if column not in column_names:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
            
            await db.commit()
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    user_id INTEGER,
                    business_id INTEGER,
                    level INTEGER DEFAULT 1,
                    product_amount INTEGER DEFAULT 0,
                    last_collected INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, business_id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS planets (
                    user_id INTEGER,
                    planet_id INTEGER,
                    last_collected INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, planet_id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS investments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    investment_id INTEGER,
                    amount BIGINT,
                    end_time INTEGER,
                    successful BOOLEAN DEFAULT NULL
                )
            """)
            
            await db.commit()
            logger.info("✅ Структура БД обновлена")
            
    except Exception as e:
        logger.error(f"Ошибка обновления БД: {e}")

async def init_db():
    """Инициализация базы данных"""
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
                    total_work BIGINT DEFAULT 0,
                    referral_code TEXT,
                    referred_by INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    total_referral_earned BIGINT DEFAULT 0,
                    has_started_bonus BOOLEAN DEFAULT 0,
                    plasma BIGINT DEFAULT 0,
                    bitcoin REAL DEFAULT 0,
                    mining_gpu_count INTEGER DEFAULT 0,
                    mining_gpu_level INTEGER DEFAULT 1,
                    last_mining_claim INTEGER DEFAULT 0
                )
            """)
            await db.commit()
            logger.info("✅ База данных создана")
            
            await update_db_structure()
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")

async def get_user(uid: int):
    """Получить пользователя из БД - ВСЕГДА СВЕЖИЕ ДАННЫЕ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            
            if row:
                user_dict = dict(row)
                # Заполняем недостающие поля
                default_fields = {
                    'work_time': 0,
                    'total_work': 0,
                    'total_bonus': 0,
                    'bonus_time': 0,
                    'referral_code': None,
                    'referred_by': None,
                    'referral_count': 0,
                    'total_referral_earned': 0,
                    'has_started_bonus': False,
                    'plasma': 0,
                    'bitcoin': 0.0,
                    'mining_gpu_count': 0,
                    'mining_gpu_level': 1,
                    'last_mining_claim': 0,
                    'wins': 0,
                    'losses': 0
                }
                
                for field, default in default_fields.items():
                    if field not in user_dict:
                        user_dict[field] = default
                
                # Генерируем реферальный код если нет
                if not user_dict.get('referral_code'):
                    salt = "murasaki_empire_2024"
                    hash_str = hashlib.md5(f"{uid}{salt}".encode()).hexdigest()[:8].upper()
                    referral_code = f"REF{hash_str}"
                    user_dict['referral_code'] = referral_code
                    await db.execute("UPDATE users SET referral_code = ? WHERE id = ?", (referral_code, uid))
                    await db.commit()
                
                return user_dict  # ВОЗВРАЩАЕМ СВЕЖИЕ ДАННЫЕ
            
            # Если пользователя нет, создаем
            salt = "murasaki_empire_2024"
            hash_str = hashlib.md5(f"{uid}{salt}".encode()).hexdigest()[:8].upper()
            referral_code = f"REF{hash_str}"
            
            await db.execute(
                "INSERT INTO users (id, balance, referral_code, has_started_bonus) VALUES (?, ?, ?, ?)",
                (uid, 0, referral_code, 0)
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
                'username': None,
                'referral_code': referral_code,
                'referred_by': None,
                'referral_count': 0,
                'total_referral_earned': 0,
                'has_started_bonus': False,
                'plasma': 0,
                'bitcoin': 0.0,
                'mining_gpu_count': 0,
                'mining_gpu_level': 1,
                'last_mining_claim': 0
            }
    except Exception as e:
        logger.error(f"Ошибка get_user: {e}")
        return None

async def update_username(uid: int, username: str):
    """Обновить имя пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
            await db.commit()
    except:
        pass

async def change_balance(uid: int, delta: int):
    """Изменить баланс пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (uid, 0))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (delta, uid))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка change_balance: {e}")
        return False

async def change_plasma(uid: int, delta: int):
    """Изменить количество плазмы"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET plasma = plasma + ? WHERE id = ?", (delta, uid))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка change_plasma: {e}")
        return False

async def change_bitcoin(uid: int, delta: float):
    """Изменить количество биткоинов"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bitcoin = bitcoin + ? WHERE id = ?", (delta, uid))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Ошибка change_bitcoin: {e}")
        return False

async def update_stats(uid: int, win: bool):
    """Обновить статистику побед/поражений"""
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
    """Получить топ-10 игроков по балансу"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Сначала проверяем, есть ли вообще данные в таблице
            cursor = await db.execute("SELECT COUNT(*) as count FROM users")
            count_row = await cursor.fetchone()
            total_users = count_row['count'] if count_row else 0
            
            if total_users == 0:
                return []
            
            # Получаем топ-10 с балансом больше 0
            cursor = await db.execute("""
                SELECT id, username, balance 
                FROM users 
                WHERE balance > 0 
                ORDER BY balance DESC 
                LIMIT 10
            """)
            rows = await cursor.fetchall()
            
            top_list = []
            for row in rows:
                user_dict = dict(row)
                # Если username пустой, показываем ID
                if not user_dict.get('username'):
                    user_dict['username'] = f"ID {user_dict['id']}"
                top_list.append(user_dict)
            
            return top_list
            
    except Exception as e:
        logger.error(f"Ошибка get_top: {e}")
        return []
async def get_all_users_count():
    """Получить общее количество пользователей - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) as count FROM users")
            row = await cursor.fetchone()
            # row это кортеж, например (5,)
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка get_all_users_count: {e}")
        return 0

async def get_total_money_in_system():
    """Получить общую сумму денег в системе - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT SUM(balance) as total FROM users")
            row = await cursor.fetchone()
            # row это кортеж, например (15000000,)
            return row[0] if row and row[0] else 0
    except Exception as e:
        logger.error(f"Ошибка get_total_money_in_system: {e}")
        return 0

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
def generate_referral_code(user_id: int) -> str:
    """Генерирует реферальный код на основе ID пользователя"""
    salt = "murasaki_empire_2024"
    hash_str = hashlib.md5(f"{user_id}{salt}".encode()).hexdigest()[:8].upper()
    return f"REF{hash_str}"

async def get_user_by_referral_code(code: str):
    """Найти пользователя по реферальному коду"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, username FROM users WHERE referral_code = ?", (code,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Ошибка в get_user_by_referral_code: {e}")
        return None

async def process_referral(new_user_id: int, referral_code: str, bot: Bot = None):
    """Обработка реферального приглашения"""
    try:
        logger.info(f"Начинаем обработку реферала: новый пользователь {new_user_id}, код {referral_code}")
        
        referrer = await get_user_by_referral_code(referral_code)
        if not referrer:
            logger.error(f"Реферер с кодом {referral_code} не найден")
            return False, 0, None
        
        referrer_id = referrer['id']
        referrer_username = referrer.get('username', f"ID {referrer_id}")
        
        if referrer_id == new_user_id:
            logger.error(f"Пользователь пытается пригласить сам себя: {new_user_id}")
            return False, 0, None
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN")
            
            try:
                cursor = await db.execute("SELECT referred_by FROM users WHERE id = ?", (new_user_id,))
                existing_row = await cursor.fetchone()
                
                if existing_row and existing_row[0] is not None:
                    logger.error(f"Пользователь {new_user_id} уже был приглашен ранее")
                    await db.rollback()
                    return False, 0, None
                
                await db.execute("UPDATE users SET referred_by = ? WHERE id = ?", (referrer_id, new_user_id))
                
                cursor = await db.execute(
                    "SELECT referral_count, total_referral_earned FROM users WHERE id = ?", 
                    (referrer_id,)
                )
                referrer_data = await cursor.fetchone()
                
                current_referral_count = referrer_data[0] if referrer_data else 0
                new_referral_count = current_referral_count + 1
                
                reward_amount = random.randint(30_000_000, 100_000_000)
                
                cursor = await db.execute(
                    "SELECT balance, total_referral_earned FROM users WHERE id = ?", 
                    (referrer_id,)
                )
                balance_data = await cursor.fetchone()
                
                current_balance = balance_data[0] if balance_data else 0
                current_total_earned = balance_data[1] if balance_data else 0
                
                new_balance = current_balance + reward_amount
                new_total_earned = current_total_earned + reward_amount
                
                await db.execute("""
                    UPDATE users 
                    SET balance = ?,
                        referral_count = ?,
                        total_referral_earned = ?
                    WHERE id = ?
                """, (new_balance, new_referral_count, new_total_earned, referrer_id))
                
                await db.commit()
                
                logger.info(f"✅ Реферал успешно обработан!")
                logger.info(f"   Новый пользователь: {new_user_id}")
                logger.info(f"   Реферер: {referrer_id} ({referrer_username})")
                logger.info(f"   Награда: {reward_amount:,}")
                logger.info(f"   Новый баланс реферера: {new_balance:,}")
                logger.info(f"   Новое количество рефералов: {new_referral_count}")
                
                async with aiosqlite.connect(DB_PATH) as verify_db:
                    verify_db.row_factory = aiosqlite.Row
                    cursor = await verify_db.execute(
                        "SELECT balance, referral_count, total_referral_earned FROM users WHERE id = ?", 
                        (referrer_id,)
                    )
                    verify_data = await cursor.fetchone()
                    
                    if verify_data:
                        logger.info(f"✅ Проверка данных:")
                        logger.info(f"   Баланс в БД: {verify_data['balance']:,}")
                        logger.info(f"   Рефералов в БД: {verify_data['referral_count']}")
                        logger.info(f"   Заработано в БД: {verify_data['total_referral_earned']:,}")
                
                if bot:
                    try:
                        await bot.send_message(
                            referrer_id,
                            f"🎉 <b>НОВЫЙ РЕФЕРАЛ!</b>\n\n"
                            f"👤 <b>Новый пользователь присоединился по вашей ссылке!</b>\n\n"
                            f"💰 <b>Вы получили:</b> <code>{reward_amount:,}</code>\n"
                            f"📊 <b>Новый баланс:</b> <code>{new_balance:,}</code>\n"
                            f"👥 <b>Всего рефералов:</b> {new_referral_count}\n"
                            f"🏦 <b>Всего заработано на рефералах:</b> <code>{new_total_earned:,}</code>\n\n"
                            f"🎯 <b>Продолжайте приглашать друзей!</b>\n"
                            f"Каждый новый реферал приносит 30-100 миллионов!",
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ Уведомление отправлено рефереру {referrer_id}")
                    except Exception as e:
                        logger.error(f"❌ Не удалось отправить уведомление рефереру {referrer_id}: {e}")
                
                return True, reward_amount, referrer_username
                
            except Exception as e:
                await db.rollback()
                logger.error(f"❌ Ошибка в транзакции при обработке реферала: {e}")
                return False, 0, None
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки реферала: {e}")
        return False, 0, None

# ========== ОБРАБОТКА РЕФЕРАЛЬНОГО СТАРТА ==========
async def handle_referral_start(msg: Message, referral_code: str):
    """Обработка старта с реферальной ссылкой"""
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    
    user = await get_user(uid)
    
    if msg.from_user.username and msg.from_user.username != user.get('username'):
        await update_username(uid, msg.from_user.username)
        user['username'] = msg.from_user.username
    
    if user.get('referred_by') is not None:
        referrer_id = user['referred_by']
        referrer = await get_user(referrer_id)
        referrer_name = referrer.get('username', f"ID {referrer_id}")
        
        bot_username = (await msg.bot.get_me()).username
        user_referral_code = user.get('referral_code', 'НЕТ')
        referral_link = f"https://t.me/{bot_username}?start={user_referral_code}"
        
        text = f"""
🎌 <b>С ВОЗВРАЩЕНИЕМ В MURASAKI EMPIRE, {username}!</b>

👤 <b>Вы уже были приглашены:</b> {referrer_name}

✨ <b>Вы уже в системе!</b>
Продолжайте зарабатывать и приглашать друзей!

🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>

💡 <b>Начните с этих команд:</b>
• <code>меню</code> - показать все возможности
• <code>бонус</code> - получить бонус 5-20М
• <code>работа</code> - заработать 1-5М
• <code>стартбонус</code> - получить стартовый бонус 10М
"""
        
        await msg.answer(text, parse_mode="HTML")
        return
    
    logger.info(f"Новый пользователь {uid} ({username}) присоединяется по коду {referral_code}")
    
    success, reward_amount, referrer_username = await process_referral(uid, referral_code, msg.bot)
    
    user = await get_user(uid)
    
    bot_username = (await msg.bot.get_me()).username
    user_referral_code = user.get('referral_code', 'НЕТ')
    referral_link = f"https://t.me/{bot_username}?start={user_referral_code}"
    
    if success:
        logger.info(f"✅ Реферальная система: начислено {reward_amount:,} пользователю {referrer_username}")
        
        text = f"""
🎌 <b>ДОБРО ПОЖАЛОВАТЬ В MURASAKI EMPIRE, {username}!</b>

🎉 <b>ВЫ ПРИСОЕДИНИЛИСЬ ПО ПРИГЛАШЕНИЮ!</b>

👤 <b>Вас пригласил:</b> {referrer_username}
💰 <b>Он получил:</b> <code>{reward_amount:,}</code>

✨ <b>Что теперь делать?</b>

1. 🎁 <b>Получите стартовый бонус!</b>
   Напишите <code>стартбонус</code> для получения 10М

2. 🎁 <b>Получите ежечасный бонус!</b>
   Напишите <code>бонус</code> для получения 5-20М

3. 💼 <b>Выполните первую работу!</b>
   Напишите <code>работа</code> для заработка 1-5М

4. 👥 <b>Пригласите своих друзей!</b>
   Вы получите 30-100М за каждого друга!

🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>

💡 <b>Главные команды:</b>
• <code>меню</code> — показать все возможности
• <code>профиль</code> — ваша статистика
• <code>рефералы</code> — пригласить друзей

🎯 <b>Удачи в зарабатывании миллионов!</b>
"""
    else:
        logger.warning(f"Реферальный код {referral_code} недействителен или произошла ошибка для пользователя {uid}")
        
        text = f"""
🎌 <b>ДОБРО ПОЖАЛОВАТЬ В MURASAKI EMPIRE, {username}!</b>

⚠️ <b>Реферальная ссылка недействительна или устарела</b>

✨ <b>Но это не проблема! Вы все равно можете:</b>

🎁 <b>Получать бонусы каждый час:</b> 5-20 миллионов!
💼 <b>Работать каждую минуту:</b> 1-5 миллионов!
👥 <b>Приглашать друзей:</b> 30-100М за каждого!

🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>

💡 <b>Начните прямо сейчас:</b>
Напишите <code>стартбонус</code> для получения стартового бонуса 10М!
"""
    
    await msg.answer(text, parse_mode="HTML")

# ========== БИЗНЕС СИСТЕМА ==========
async def get_user_businesses(uid: int):
    """Получить все бизнесы пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM businesses WHERE user_id = ?", (uid,))
            rows = await cursor.fetchall()
            businesses = {}
            for row in rows:
                row_dict = dict(row)
                businesses[row_dict['business_id']] = row_dict
            return businesses
    except Exception as e:
        logger.error(f"Ошибка get_user_businesses: {e}")
        return {}

async def buy_business(uid: int, business_id: int):
    """Купить бизнес"""
    if business_id not in BUSINESSES:
        return False, "Бизнес не найден"
    
    business = BUSINESSES[business_id]
    user = await get_user(uid)
    
    if user['balance'] < business['price']:
        return False, f"Недостаточно средств. Нужно: {format_money(business['price'])}"
    
    user_businesses = await get_user_businesses(uid)
    if business_id in user_businesses:
        return False, "У вас уже есть этот бизнес"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (business['price'], uid))
            
            await db.execute("""
                INSERT INTO businesses (user_id, business_id, level, product_amount, last_collected)
                VALUES (?, ?, ?, ?, ?)
            """, (uid, business_id, 1, business['product_capacity'], int(time.time())))
            
            await db.commit()
            return True, f"Бизнес '{business['name']}' успешно куплен!"
    except Exception as e:
        logger.error(f"Ошибка buy_business: {e}")
        return False, f"Ошибка покупки: {e}"

async def upgrade_business(uid: int, business_id: int):
    """Улучшить бизнес"""
    user_businesses = await get_user_businesses(uid)
    if business_id not in user_businesses:
        return False, "У вас нет этого бизнеса"
    
    business_data = BUSINESSES[business_id]
    user_business = user_businesses[business_id]
    
    if user_business['level'] >= business_data['max_level']:
        return False, "Бизнес достиг максимального уровня"
    
    upgrade_cost = int(business_data['price'] * (business_data['upgrade_multiplier'] ** user_business['level']))
    
    user = await get_user(uid)
    if user['balance'] < upgrade_cost:
        return False, f"Недостаточно средств. Нужно: {format_money(upgrade_cost)}"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (upgrade_cost, uid))
            
            new_level = user_business['level'] + 1
            new_capacity = int(business_data['product_capacity'] * (business_data['upgrade_multiplier'] ** (new_level - 1)))
            
            await db.execute("""
                UPDATE businesses 
                SET level = ?, product_amount = ?
                WHERE user_id = ? AND business_id = ?
            """, (new_level, new_capacity, uid, business_id))
            
            await db.commit()
            return True, f"Бизнес '{business_data['name']}' улучшен до уровня {new_level}!"
    except Exception as e:
        logger.error(f"Ошибка upgrade_business: {e}")
        return False, f"Ошибка улучшения: {e}"

async def refill_products(uid: int, business_id: int):
    """Пополнить продукты бизнеса"""
    user_businesses = await get_user_businesses(uid)
    if business_id not in user_businesses:
        return False, "У вас нет этого бизнеса"
    
    business_data = BUSINESSES[business_id]
    user_business = user_businesses[business_id]
    
    refill_cost = business_data['product_refill_cost']
    refill_amount = business_data['product_capacity'] - user_business['product_amount']
    
    if refill_amount <= 0:
        return False, "Продукты уже заполнены"
    
    user = await get_user(uid)
    if user['balance'] < refill_cost:
        return False, f"Недостаточно средств. Нужно: {format_money(refill_cost)}"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (refill_cost, uid))
            
            await db.execute("""
                UPDATE businesses 
                SET product_amount = ?
                WHERE user_id = ? AND business_id = ?
            """, (business_data['product_capacity'], uid, business_id))
            
            await db.commit()
            return True, f"Продукты бизнеса '{business_data['name']}' пополнены!"
    except Exception as e:
        logger.error(f"Ошибка refill_products: {e}")
        return False, f"Ошибка пополнения: {e}"

async def collect_business_profit(uid: int, business_id: int):
    """Собрать прибыль с бизнеса (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    user_businesses = await get_user_businesses(uid)
    if business_id not in user_businesses:
        return False, "У вас нет этого бизнеса"
    
    business_data = BUSINESSES[business_id]
    user_business = user_businesses[business_id]
    
    # Проверяем наличие продуктов
    if user_business['product_amount'] <= 0:
        return False, "Недостаточно продуктов. Пополните бизнес."
    
    # Полностью используем все продукты
    profit_per_hour = business_data['profit_per_hour'] * (business_data['upgrade_multiplier'] ** (user_business['level'] - 1))
    
    # Прибыль = продукты * (прибыль_в_час / емкость)
    # Это означает, что если продукты заполнены на 100%, то можно собрать прибыль за 1 час
    profit_multiplier = user_business['product_amount'] / business_data['product_capacity']
    profit = int(profit_per_hour * profit_multiplier)
    
    if profit <= 0:
        return False, "Недостаточно продуктов. Пополните бизнес."
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (profit, uid))
            
            # Продукты полностью расходуются
            await db.execute("""
                UPDATE businesses 
                SET product_amount = 0, last_collected = ?
                WHERE user_id = ? AND business_id = ?
            """, (int(time.time()), uid, business_id))
            
            await db.commit()
            return True, profit
    except Exception as e:
        logger.error(f"Ошибка collect_business_profit: {e}")
        return False, 0

async def sell_business(uid: int, business_id: int):
    """Продать бизнес государству"""
    user_businesses = await get_user_businesses(uid)
    if business_id not in user_businesses:
        return False, "У вас нет этого бизнеса"
    
    business_data = BUSINESSES[business_id]
    user_business = user_businesses[business_id]
    
    total_investment = business_data['price']
    for level in range(1, user_business['level']):
        total_investment += int(business_data['price'] * (business_data['upgrade_multiplier'] ** level))
    
    sell_price = int(total_investment * 0.7)
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (sell_price, uid))
            
            await db.execute("DELETE FROM businesses WHERE user_id = ? AND business_id = ?", (uid, business_id))
            
            await db.commit()
            return True, sell_price
    except Exception as e:
        logger.error(f"Ошибка sell_business: {e}")
        return False, 0

# ========== ФУНКЦИЯ ДЛЯ ПОКАЗА СОБСТВЕННЫХ БИЗНЕСОВ (НОВАЯ) ==========
async def show_my_businesses(msg: Message):
    """Показать бизнесы пользователя с inline-кнопками"""
    uid = msg.from_user.id
    user_businesses = await get_user_businesses(uid)
    
    if not user_businesses:
        await msg.reply("У вас пока нет бизнесов. Купите первый бизнес: купить бизнес [id]")
        return
    
    # Получаем все бизнесы пользователя
    keyboard = []
    for biz_id, biz_data in user_businesses.items():
        if biz_id in BUSINESSES:
            business_info = BUSINESSES[biz_id]
            level = biz_data['level']
            product_amount = biz_data['product_amount']
            product_capacity = business_info['product_capacity']
            
            # Статус заполнения
            if product_amount >= product_capacity:
                status = "🟢"
            elif product_amount > product_capacity * 0.5:
                status = "🟡"
            else:
                status = "🔴"
            
            # Кнопка для управления этим бизнесом
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {business_info['name']} (Ур. {level})",
                    callback_data=f"mybiz_{biz_id}"
                )
            ])
    
    # Добавляем кнопку "Назад" если есть бизнесы
    if keyboard:
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    text = "🏢 <b>Ваши бизнесы</b>\n\n"
    text += f"📊 Всего бизнесов: {len(user_businesses)}\n"
    text += "Выберите бизнес для управления:\n\n"
    text += "🟢 - Продукты заполнены\n🟡 - Продукты наполовину\n🔴 - Мало продуктов"
    
    await msg.reply(text, parse_mode="HTML", reply_markup=kb)

# ========== ПЛАНЕТЫ СИСТЕМА ==========
async def get_user_planets(uid: int):
    """Получить все планеты пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM planets WHERE user_id = ?", (uid,))
            rows = await cursor.fetchall()
            planets = {}
            for row in rows:
                row_dict = dict(row)
                planets[row_dict['planet_id']] = row_dict
            return planets
    except Exception as e:
        logger.error(f"Ошибка get_user_planets: {e}")
        return {}

async def buy_planet(uid: int, planet_id: int):
    """Купить планету"""
    if planet_id not in PLANETS:
        return False, "Планета не найдена"
    
    planet = PLANETS[planet_id]
    user = await get_user(uid)
    user_planets = await get_user_planets(uid)
    
    if planet_id in user_planets:
        return False, "У вас уже есть эта планета"
    
    if planet['price_dollars'] > 0:
        if user['balance'] < planet['price_dollars']:
            return False, f"Недостаточно $. Нужно: {format_money(planet['price_dollars'])}"
        currency_type = "$"
        price = planet['price_dollars']
    else:
        if user['plasma'] < planet['price_plasma']:
            return False, f"Недостаточно плазмы. Нужно: {planet['price_plasma']} плазмы"
        currency_type = "плазмы"
        price = planet['price_plasma']
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if planet['price_dollars'] > 0:
                await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, uid))
            else:
                await db.execute("UPDATE users SET plasma = plasma - ? WHERE id = ?", (price, uid))
            
            await db.execute("""
                INSERT INTO planets (user_id, planet_id, last_collected)
                VALUES (?, ?, ?)
            """, (uid, planet_id, int(time.time())))
            
            await db.commit()
            return True, f"Планета '{planet['name']}' куплена за {price}{currency_type}!"
    except Exception as e:
        logger.error(f"Ошибка buy_planet: {e}")
        return False, f"Ошибка покупки: {e}"

async def collect_planet_plasma(uid: int, planet_id: int):
    """Собрать плазму с планеты"""
    user_planets = await get_user_planets(uid)
    if planet_id not in user_planets:
        return False, "У вас нет этой планеты"
    
    planet_data = PLANETS[planet_id]
    user_planet = user_planets[planet_id]
    
    current_time = int(time.time())
    last_collected = user_planet['last_collected'] or current_time
    time_passed = current_time - last_collected
    
    plasma_per_hour = planet_data['plasma_per_hour']
    plasma_collected = int((time_passed / 3600) * plasma_per_hour)
    
    if plasma_collected <= 0:
        return False, "Плазма еще не накопилась"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET plasma = plasma + ? WHERE id = ?", (plasma_collected, uid))
            
            await db.execute("""
                UPDATE planets 
                SET last_collected = ?
                WHERE user_id = ? AND planet_id = ?
            """, (current_time, uid, planet_id))
            
            await db.commit()
            return True, plasma_collected
    except Exception as e:
        logger.error(f"Ошибка collect_planet_plasma: {e}")
        return False, 0

# ========== МАЙНИНГ СИСТЕМА ==========
async def buy_gpu(uid: int):
    """Купить видеокарту для майнинга (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    user = await get_user(uid)
    gpu_level = user['mining_gpu_level']
    
    gpu_price = BitcoinMining.get_gpu_price(gpu_level)
    
    if user['balance'] < gpu_price:
        return False, f"Недостаточно средств. Нужно: {format_money(gpu_price)}"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Снимаем деньги
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (gpu_price, uid))
            
            # Обновляем количество видеокарт
            new_gpu_count = user['mining_gpu_count'] + 1
            await db.execute("UPDATE users SET mining_gpu_count = ? WHERE id = ?", (new_gpu_count, uid))
            
            await db.commit()
            
            # ПОСЛЕ КОММИТА - ОБНОВЛЯЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ
            # Получаем обновленные данные
            cursor = await db.execute("SELECT balance, mining_gpu_count, mining_gpu_level FROM users WHERE id = ?", (uid,))
            updated_user = await cursor.fetchone()
            
            # Рассчитаем новый хешрейт с ОБНОВЛЕННЫМИ данными
            hashrate = BitcoinMining.calculate_hashrate(new_gpu_count, gpu_level)
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            
            return True, f"✅ Видеокарта уровня {gpu_level} куплена за {format_money(gpu_price)}!\n\nТеперь у вас {new_gpu_count} видеокарт.\n⚡ Новый хешрейт: {hashrate:.1f} MH/s\n₿ Майнинг/час: {btc_per_hour:.8f} BTC"
    except Exception as e:
        logger.error(f"Ошибка buy_gpu: {e}")
        return False, f"❌ Ошибка покупки: {e}"

async def upgrade_gpu(uid: int):
    """Улучшить уровень видеокарт (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    user = await get_user(uid)
    
    if user['mining_gpu_level'] >= 5:
        return False, "Достигнут максимальный уровень видеокарт"
    
    if user['mining_gpu_count'] == 0:
        return False, "Сначала купите хотя бы одну видеокарту"
    
    new_level = user['mining_gpu_level'] + 1
    upgrade_cost = BitcoinMining.get_gpu_price(new_level) * user['mining_gpu_count']
    
    if user['balance'] < upgrade_cost:
        return False, f"Недостаточно средств. Нужно: {format_money(upgrade_cost)}"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Снимаем деньги
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (upgrade_cost, uid))
            
            # Обновляем уровень видеокарт
            await db.execute("UPDATE users SET mining_gpu_level = ? WHERE id = ?", (new_level, uid))
            
            await db.commit()
            
            # ПОСЛЕ КОММИТА - ОБНОВЛЯЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ
            # Получаем обновленные данные
            cursor = await db.execute("SELECT balance, mining_gpu_count, mining_gpu_level FROM users WHERE id = ?", (uid,))
            updated_user = await cursor.fetchone()
            
            # Рассчитаем новый хешрейт с ОБНОВЛЕННЫМИ данными
            hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], new_level)
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            
            return True, f"✅ Все видеокарты улучшены до уровня {new_level}!\n\n⚡ Новый хешрейт: {hashrate:.1f} MH/s\n₿ Майнинг/час: {btc_per_hour:.8f} BTC"
    except Exception as e:
        logger.error(f"Ошибка upgrade_gpu: {e}")
        return False, f"❌ Ошибка улучшения: {e}"

async def claim_mining_profit(uid: int):
    """Забрать намайненые биткоины"""
    user = await get_user(uid)
    
    if user['mining_gpu_count'] == 0:
        return False, 0, "У вас нет майнинг фермы. Купите видеокарты!"
    
    current_time = int(time.time())
    last_claim = user['last_mining_claim'] or current_time
    time_passed = current_time - last_claim
    
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    btc_mined = btc_per_hour * (time_passed / 3600)
    
    if btc_mined <= 0:
        return False, 0, "Биткоины еще не намайнились"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bitcoin = bitcoin + ?, last_mining_claim = ? WHERE id = ?", (btc_mined, current_time, uid))
            
            await db.commit()
            
            btc_price = BitcoinMining.get_bitcoin_price()
            usd_value = btc_mined * btc_price
            
            return True, btc_mined, usd_value
    except Exception as e:
        logger.error(f"Ошибка claim_mining_profit: {e}")
        return False, 0, f"Ошибка: {e}"

async def sell_bitcoin(uid: int, amount: float = None):
    """Продать биткоины"""
    user = await get_user(uid)
    
    if user['bitcoin'] <= 0:
        return False, "У вас нет биткоинов"
    
    if amount is None:
        amount = user['bitcoin']
    elif amount > user['bitcoin']:
        return False, "Недостаточно биткоинов"
    
    btc_price = BitcoinMining.get_bitcoin_price()
    usd_amount = amount * btc_price
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bitcoin = bitcoin - ?, balance = balance + ? WHERE id = ?", 
                           (amount, int(usd_amount), uid))
            
            await db.commit()
            return True, amount, int(usd_amount)
    except Exception as e:
        logger.error(f"Ошибка sell_bitcoin: {e}")
        return False, 0, 0

# ========== ИНВЕСТИЦИИ СИСТЕМА ==========
async def get_user_investments(uid: int):
    """Получить активные инвестиции пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM investments 
                WHERE user_id = ? AND successful IS NULL
                ORDER BY end_time ASC
            """, (uid,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Ошибка get_user_investments: {e}")
        return []

async def start_investment(uid: int, investment_id: int, amount: int):
    """Начать инвестицию"""
    if investment_id not in INVESTMENTS:
        return False, "Инвестиция не найдена"
    
    investment = INVESTMENTS[investment_id]
    
    if amount < investment['min_amount']:
        return False, f"Минимальная сумма: {format_money(investment['min_amount'])}"
    
    user = await get_user(uid)
    if user['balance'] < amount:
        return False, f"Недостаточно средств. Нужно: {format_money(amount)}"
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, uid))
            
            end_time = int(time.time()) + investment['duration']
            await db.execute("""
                INSERT INTO investments (user_id, investment_id, amount, end_time)
                VALUES (?, ?, ?, ?)
            """, (uid, investment_id, amount, end_time))
            
            await db.commit()
            
            end_time_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(end_time))
            return True, f"✅ Инвестиция '{investment['name']}' начата!\n\n💰 Сумма: {format_money(amount)}\n⏰ Завершится: {end_time_str}\n📈 Прибыль при успехе: +{int((investment['profit_multiplier'] - 1) * 100)}%"
    except Exception as e:
        logger.error(f"Ошибка start_investment: {e}")
        return False, f"❌ Ошибка: {e}"

async def complete_investment(uid: int, investment_db_id: int):
    """Завершить инвестицию"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM investments WHERE id = ? AND user_id = ?", (investment_db_id, uid))
            investment = await cursor.fetchone()
            
            if not investment:
                return False, "Инвестиция не найдена"
            
            if investment['successful'] is not None:
                return False, "Эта инвестиция уже завершена"
            
            if time.time() < investment['end_time']:
                return False, "Инвестиция еще не завершена"
            
            investment_data = INVESTMENTS[investment['investment_id']]
            
            successful = random.random() < investment_data['success_rate']
            
            if successful:
                profit = int(investment['amount'] * investment_data['profit_multiplier'])
                total = investment['amount'] + profit
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total, uid))
                message = f"✅ Инвестиция успешна!\n💰 Прибыль: +{format_money(profit)}\n💵 Всего получено: {format_money(total)}"
            else:
                message = f"❌ Инвестиция провалилась!\n💸 Потеряно: {format_money(investment['amount'])}"
            
            await db.execute("UPDATE investments SET successful = ? WHERE id = ?", (successful, investment_db_id))
            await db.commit()
            
            return True, message
    except Exception as e:
        logger.error(f"Ошибка complete_investment: {e}")
        return False, f"❌ Ошибка: {e}"

# ========== БОНУСНАЯ СИСТЕМА ==========
async def check_bonus_cooldown(uid: int):
    """Проверка кулдауна на бонус (1 час) - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        user = await get_user(uid)
        last_bonus = user.get('bonus_time', 0) or 0
        total_bonus = user.get('total_bonus', 0) or 0
        
        current_time = time.time()
        
        if last_bonus == 0:
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        
        time_passed = current_time - last_bonus
        
        if time_passed >= 3600:  # 1 час
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        
        remaining = 3600 - time_passed
        return False, remaining, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
    except Exception as e:
        logger.error(f"Ошибка check_bonus_cooldown: {e}")
        return True, 0, {'bonus_time': 0, 'total_bonus': 0}

async def give_bonus(uid: int):
    """Выдать бонус от 5 до 20 миллионов"""
    try:
        amount = random.randint(5_000_000, 20_000_000)
        current_time = int(time.time())
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    bonus_time = ?,
                    total_bonus = COALESCE(total_bonus, 0) + ?
                WHERE id = ?
            """, (amount, current_time, amount, uid))
            
            await db.commit()
            logger.info(f"✅ Бонус выдан пользователю {uid}: {amount}")
            return amount, True
    except Exception as e:
        logger.error(f"Ошибка выдачи бонуса: {e}")
        return 0, False

async def check_work_cooldown(uid: int):
    """Проверка кулдауна на работу (30 секунд)"""
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
        amount = random.randint(1_000_000, 5_000_000)
        current_time = int(time.time())
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    work_time = ?,
                    total_work = COALESCE(total_work, 0) + ?
                WHERE id = ?
            """, (amount, current_time, amount, uid))
            
            await db.commit()
            logger.info(f"✅ Работа выполнена пользователем {uid}: {amount}")
            return amount, True
    except Exception as e:
        logger.error(f"Ошибка выдачи работы: {e}")
        return 0, False

async def give_start_bonus(uid: int):
    """Выдать стартовый бонус 10 миллионов"""
    try:
        user = await get_user(uid)
        
        if user.get('has_started_bonus'):
            return False, "Вы уже получали стартовый бонус!"
        
        start_bonus = 10_000_000
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET balance = balance + ?, 
                    has_started_bonus = 1
                WHERE id = ?
            """, (start_bonus, uid))
            
            await db.commit()
            
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            new_balance = row[0] if row else start_bonus
            
            logger.info(f"✅ Стартовый бонус выдан пользователю {uid}: {start_bonus}")
            
            return True, start_bonus, new_balance
    except Exception as e:
        logger.error(f"Ошибка выдачи стартового бонуса: {e}")
        return False, f"Ошибка: {e}", 0

# ========== ОБРАБОТКА КОМАНД С / И БЕЗ ==========
async def handle_all_commands(msg: Message):
    """Обработчик всех команд - и с / и без /"""
    text = msg.text.strip()
    
    if not text:
        return
    
    parts = text.split()
    cmd = text.lower()
    
    # Обработка /start с реферальным кодом
    if cmd.startswith('/start'):
        if len(parts) > 1:
            referral_code = parts[1]
            await handle_referral_start(msg, referral_code)
        else:
            await send_welcome_message(msg)
        return
    
    # Основные команды без /
    if cmd in ['меню', 'menu', 'старт', 'начать']:
        await send_welcome_message(msg)
        return
    
    if cmd in ['бонус', 'bonus', 'бон', 'bon']:
        await process_bonus(msg)
        return
    
    if cmd in ['работа', 'work', 'раб', 'wrk', 'труд']:
        await process_work(msg)
        return
    
    if cmd in ['баланс', 'balance', 'б', 'баланс']:
        await process_balance(msg)
        return
    
    if cmd in ['профиль', 'profile', 'пр', 'стата', 'stats', 'статистика']:
        await process_profile(msg)
        return
    
    if cmd in ['топ', 'top', 'лидеры', 'лидерборд']:
        await process_top(msg)
        return
    
    if cmd in ['кд', 'cd', 'кулдаун', 'cooldown', 'бонусвремя']:
        await check_bonus_cd(msg)
        return
    
    if cmd in ['кдработы', 'работакд', 'workcd']:
        await check_work_cd(msg)
        return
    
    if cmd in ['стартбонус', 'старт', 'начальныйбонус']:
        await process_start_bonus(msg)
        return
    
    if cmd in ['рефералы', 'рефы', 'реферальная']:
        await process_referrals(msg)
        return
    
    # НОВАЯ КОМАНДА: МОЙ БИЗНЕС
    if cmd in ['мой бизнес', 'мои бизнесы', 'mybusiness', 'mybusinesses']:
        await show_my_businesses(msg)
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
            
        # Дартс
        if cmd in ['дротик', 'дартс', 'дрот', 'darts', 'дарт']:
            await process_darts(msg, parts)
            return
    
    # Бизнес команды
    if cmd in ['бизнесы', 'business', 'бизнес', 'биз']:
        await show_businesses(msg)
        return
    
    if cmd in ['майнинг', 'mining', 'майн']:
        await show_mining_info(msg)
        return
    
    if cmd in ['планеты', 'planets', 'планет']:
        await show_planets(msg)
        return
    
    if cmd in ['инвестиции', 'investments', 'инвест']:
        await show_investments(msg)
        return
    
    if cmd == 'передать' and len(parts) >= 3:
        await process_transfer(msg, parts)
        return
    
    # Новые команды из дополнения
    if cmd in ['майнинг панель', 'miningpanel', 'майн панель']:
        await show_mining_panel(msg)
        return

    if cmd in ['мои планеты', 'myplanets', 'планеты панель']:
        await show_my_planets_panel(msg=msg)
        return

    if cmd in ['инвестировать', 'инвест', 'investment']:
        await show_investments_panel(msg)
        return
    
    # Админ команды
    if msg.from_user.id in ADMIN_IDS:
        if cmd == 'выдать' and len(parts) >= 2:
            if msg.reply_to_message:
                await process_admin_give_reply(msg, parts)
                return
            elif len(parts) >= 3:
                await process_admin_give(msg, parts)
                return
        
        if cmd == 'забрать' and len(parts) >= 2:
            if msg.reply_to_message:
                await process_admin_take_reply(msg, parts)
                return
            elif len(parts) >= 3:
                await process_admin_take(msg, parts)
                return
    
    # Сложные команды с аргументами
    if len(parts) >= 2:
        arg_cmd = ' '.join(parts[:2]).lower()
        if arg_cmd in ['купить бизнес', 'улучшить бизнес', 'пополнить бизнес', 
                      'собрать бизнес', 'продать бизнес', 'купить планету',
                      'собрать плазму', 'начать инвестицию', 'завершить инвестицию',
                      'продать биткоин', 'купить видеокарту', 'улучшить видеокарты',
                      'собрать биткоины']:
            await handle_complex_command(msg, arg_cmd, parts[2:])
            return

async def handle_complex_command(msg: Message, cmd: str, args: list):
    """Обработка сложных команд с аргументами"""
    uid = msg.from_user.id
    
    if cmd == 'купить бизнес' and args:
        business_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= business_id <= len(BUSINESSES):
            success, message = await buy_business(uid, business_id)
            await msg.reply(message, parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID бизнеса")
    
    elif cmd == 'улучшить бизнес' and args:
        business_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= business_id <= len(BUSINESSES):
            success, message = await upgrade_business(uid, business_id)
            await msg.reply(message, parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID бизнеса")
    
    elif cmd == 'пополнить бизнес' and args:
        business_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= business_id <= len(BUSINESSES):
            success, message = await refill_products(uid, business_id)
            await msg.reply(message, parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID бизнеса")
    
    elif cmd == 'собрать бизнес' and args:
        business_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= business_id <= len(BUSINESSES):
            success, result = await collect_business_profit(uid, business_id)
            if success:
                await msg.reply(f"✅ Прибыль собрана: {format_money(result)}", parse_mode="HTML")
            else:
                await msg.reply(f"❌ {result}", parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID бизнеса")
    
    elif cmd == 'продать бизнес' and args:
        business_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= business_id <= len(BUSINESSES):
            success, amount = await sell_business(uid, business_id)
            if success:
                await msg.reply(f"✅ Бизнес продан государству за {format_money(amount)}", parse_mode="HTML")
            else:
                await msg.reply(f"❌ {amount}", parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID бизнеса")
    
    elif cmd == 'купить планету' and args:
        planet_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= planet_id <= len(PLANETS):
            success, message = await buy_planet(uid, planet_id)
            await msg.reply(message, parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID планеты")
    
    elif cmd == 'собрать плазму' and args:
        planet_id = int(args[0]) if args[0].isdigit() else 0
        if 1 <= planet_id <= len(PLANETS):
            success, amount = await collect_planet_plasma(uid, planet_id)
            if success:
                await msg.reply(f"✅ Плазма собрана: {amount} единиц", parse_mode="HTML")
            else:
                await msg.reply(f"❌ {amount}", parse_mode="HTML")
        else:
            await msg.reply("❌ Неверный ID планеты")
    
    elif cmd in ['инвестировать', 'начать инвестицию'] and len(args) >= 1:
        await show_investments_panel(msg)
        return
    
    elif cmd == 'завершить инвестицию' and args:
        try:
            investment_db_id = int(args[0])
            success, message = await complete_investment(uid, investment_db_id)
            await msg.reply(message, parse_mode="HTML")
        except:
            await msg.reply("❌ Неверный формат команды. Используйте: завершить инвестицию [id]")
    
    elif cmd == 'продать биткоин' and args:
        try:
            amount = float(args[0]) if args[0] != 'все' else None
            success, btc_sold, usd_received = await sell_bitcoin(uid, amount)
            if success:
                await msg.reply(f"✅ Продано {btc_sold:.8f} BTC за {format_money(usd_received)}$", parse_mode="HTML")
            else:
                await msg.reply(f"❌ {usd_received}", parse_mode="HTML")
        except:
            await msg.reply("❌ Неверный формат команды. Используйте: продать биткоин [количество] или продать биткоин все")
    
    elif cmd == 'купить видеокарту':
        success, message = await buy_gpu(uid)
        await msg.reply(message, parse_mode="HTML")
    
    elif cmd == 'улучшить видеокарты':
        success, message = await upgrade_gpu(uid)
        await msg.reply(message, parse_mode="HTML")
    
    elif cmd == 'собрать биткоины':
        success, btc_mined, usd_value = await claim_mining_profit(uid)
        if success:
            await msg.reply(f"✅ Получено {btc_mined:.8f} BTC ({format_money(int(usd_value))}$)", parse_mode="HTML")
        else:
            await msg.reply(f"❌ {usd_value}", parse_mode="HTML")

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
async def send_welcome_message(msg: Message):
    """Приветственное сообщение"""
    user = await get_user(msg.from_user.id)
    username = msg.from_user.username or msg.from_user.first_name
    
    welcome_text = f"""
🎌 <b>ДОБРО ПОЖАЛОВАТЬ В MURASAKI EMPIRE, {username}!</b>

💰 <b>Ваш баланс:</b> {format_money(user['balance'])}
⚡ <b>Плазма:</b> {user['plasma']}
₿ <b>Биткоин:</b> {user['bitcoin']:.8f}

✨ <b>Основные системы:</b>

🏢 <b>БИЗНЕСЫ</b> - Покупайте бизнесы и получайте прибыль!
• <code>бизнесы</code> - список бизнесов
• <code>мой бизнес</code> - ваши бизнесы (с кнопками)
• <code>купить бизнес [id]</code> - купить бизнес
• <code>улучшить бизнес [id]</code> - улучшить бизнес
• <code>пополнить бизнес [id]</code> - пополнить продукты
• <code>собрать бизнес [id]</code> - собрать прибыль
• <code>продать бизнес [id]</code> - продать государству

🪐 <b>ПЛАНЕТЫ</b> - Колонизируйте планеты и собирайте плазму!
• <code>планеты</code> - список планет
• <code>купить планету [id]</code> - купить планету
• <code>собрать плазму [id]</code> - собрать плазму

⛏️ <b>МАЙНИНГ</b> - Майните биткоины и продавайте их!
• <code>майнинг</code> - информация о майнинге
• <code>купить видеокарту</code> - купить видеокарту
• <code>улучшить видеокарты</code> - улучшить все видеокарты
• <code>забрать биткоины</code> - забрать намайненые BTC
• <code>продать биткоин [кол-во]</code> - продать BTC

💼 <b>ИНВЕСТИЦИИ</b> - Инвестируйте и получайте прибыль!
• <code>инвестиции</code> - список инвестиций
• <code>начать инвестицию [id]</code> - начать инвестицию (с кнопками)
• <code>начать инвестицию [id] [сумма]</code> - начать инвестицию
• <code>завершить инвестицию [id]</code> - завершить инвестицию

🎰 <b>КАЗИНО И ИГРЫ:</b>
• <code>монетка [ставка]</code> - игра в монетку
• <code>кости [ставка]</code> - игра в кости
• <code>слоты [ставка]</code> - игровые автоматы
• <code>рулетка [ставка] [тип]</code> - рулетка
• <code>блекджек [ставка]</code> - игра в блэкджек

🎮 <b>ОСНОВНЫЕ КОМАНДЫ:</b>
• <code>бонус</code> - получить бонус (5-20М каждый час)
• <code>работа</code> - выполнить работу (1-5М каждые 30 сек)
• <code>стартбонус</code> - получить стартовый бонус 10М
• <code>профиль</code> - ваша статистика
• <code>рефералы</code> - пригласить друзей
• <code>топ</code> - топ игроков

🔗 <b>Ваша реферальная ссылка:</b>
<code>https://t.me/{(await msg.bot.get_me()).username}?start={user['referral_code']}</code>

🎯 <b>Удачи в зарабатывании!</b>
"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Мои бизнесы", callback_data="show_my_businesses"),
         InlineKeyboardButton(text="🪐 Планеты", callback_data="show_planets")],
        [InlineKeyboardButton(text="⛏️ Майнинг", callback_data="show_mining"),
         InlineKeyboardButton(text="💼 Инвестиции", callback_data="show_investments")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="get_bonus"),
         InlineKeyboardButton(text="💼 Работа", callback_data="get_work")],
        [InlineKeyboardButton(text="📊 Профиль", callback_data="show_profile"),
         InlineKeyboardButton(text="🏆 Топ", callback_data="show_top")]
    ])
    
    await msg.answer(welcome_text, parse_mode="HTML", reply_markup=kb)

async def process_bonus(msg: Message):
    """Обработка команды бонус - ВЫДАЕТ бонус"""
    uid = msg.from_user.id
    now = int(time.time())

    # Получаем данные пользователя
    user = await get_user(uid)
    if not user:
        await msg.reply("❌ Пользователь не найден в базе данных!")
        return
    
    # Инициализируем поля, если их нет
    last_bonus = user.get('bonus_time', 0) or 0
    total_bonus = user.get('total_bonus', 0) or 0
    current_balance = user.get('balance', 0)

    # Проверяем, можно ли получить бонус (1 час кулдаун)
    time_passed = now - last_bonus
    remaining = 3600 - time_passed  # 1 час = 3600 секунд
    
    # Если время еще не прошло - показываем ко-даун
    if remaining > 0 and last_bonus != 0:
        minutes = remaining // 60
        seconds = remaining % 60
        progress_percent = int(time_passed / 3600 * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        next_time = now + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        await msg.reply(
            f"⏳ <b>Бонус уже получен!</b>\n\n"
            f"⏰ <b>Следующий бонус через:</b>\n"
            f"{minutes} минут {seconds} секунд\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Доступен с:</b> {next_str}\n"
            f"💰 <b>Всего получено бонусов:</b> {total_bonus:,}",
            parse_mode="HTML"
        )
        return

    # ========== ВЫДАЕМ БОНУС ==========
    bonus_amount = random.randint(5_000_000, 20_000_000)
    
    # 1. Начисляем баланс
    await change_balance(uid, bonus_amount)
    
    # 2. Обновляем информацию о бонусе
    total_bonus += bonus_amount
    
    # Обновляем время бонуса и общую сумму
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bonus_time = ?, total_bonus = ? WHERE id = ?",
            (now, total_bonus, uid)
        )
        await db.commit()
    
    # 3. Получаем обновленный баланс
    updated_user = await get_user(uid)
    new_balance = updated_user.get('balance', current_balance + bonus_amount)

    # 4. Формируем сообщение об успешной выдаче
    progress_bar = create_progress_bar(0)
    next_str = time.strftime('%H:%M:%S', time.localtime(now + 3600))

    await msg.reply(
        f"💎 <b>БОНУС ПОЛУЧЕН!</b> 💎\n\n"
        f"⭐️ <b>БОЛЬШОЙ БОНУС!</b>\n\n"
        f"💰 <b>Сумма:</b> {bonus_amount:,}\n"
        f"📊 <b>Новый баланс:</b> {new_balance:,}\n\n"
        f"⏰ <b>Следующий бонус через 1 час:</b>\n"
        f"🕐 {next_str}\n\n"
        f"{progress_bar} 0%\n\n"
        f"🏦 <b>Всего получено:</b> {total_bonus:,}",
        parse_mode="HTML"
    )

async def check_bonus_cd(msg: Message):
    """Проверить оставшееся время до бонуса"""
    uid = msg.from_user.id
    can_get_bonus, remaining, bonus_data = await check_bonus_cooldown(uid)
    
    if can_get_bonus:
        await msg.reply(
            "🎁 <b>Бонус доступен прямо сейчас!</b>\n\n"
            f"💰 Всего получено: <code>{bonus_data.get('total_bonus', 0):,}</code>\n"
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
            f"💰 Всего получено: <code>{bonus_data.get('total_bonus', 0):,}</code>\n"
            f"🎯 <b>Следующий бонус:</b> 5-20 миллионов",
            parse_mode="HTML"
        )

async def process_work(msg: Message):
    """Обработка команды работа"""
    uid = msg.from_user.id
    
    can_work, remaining, work_data = await check_work_cooldown(uid)
    
    if not can_work:
        seconds = int(remaining)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        progress_percent = int((WORK_COOLDOWN - remaining) / WORK_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        await msg.reply(
            f"⏳ <b>Работа уже выполнена!</b>\n\n"
            f"⏰ Следующая работа через:\n"
            f"<b>{seconds} секунд</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Доступна с:</b> {next_str}\n\n"
            f"💰 Всего заработано: <code>{work_data.get('total_work', 0):,}</code>",
            parse_mode="HTML"
        )
        return
    
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
    
    updated_user = await get_user(uid)
    next_time = time.time() + WORK_COOLDOWN
    next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
    
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
    
    progress_bar = create_progress_bar(0)
    
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
        f"⏰ <b>Следующая работа через 30 секунд:</b>\n"
        f"🕐 {next_str}\n\n"
        f"{progress_bar} 0%\n\n"
        f"🏢 <b>Всего заработано:</b> <code>{updated_user.get('total_work', 0):,}</code>",
        parse_mode="HTML"
    )

async def process_start_bonus(msg: Message):
    """Обработка команды стартовый бонус"""
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    
    success, result, new_balance = await give_start_bonus(uid)
    
    if success:
        await msg.reply(
            f"🎉 <b>СТАРТОВЫЙ БОНУС ПОЛУЧЕН!</b>\n\n"
            f"💰 <b>Сумма:</b> <code>{result:,}</code>\n"
            f"📊 <b>Новый баланс:</b> <code>{new_balance:,}</code>\n\n"
            f"✨ Теперь вы можете:\n"
            f"• Написать <code>бонус</code> для получения 5-20М\n"
            f"• Написать <code>работа</code> для заработка 1-5М\n"
            f"• Написать <code>рефералы</code> для приглашения друзей\n\n"
            f"🎯 <b>Удачи в Murasaki Empire!</b>",
            parse_mode="HTML"
        )
    else:
        await msg.reply(
            f"❌ <b>Не удалось получить стартовый бонус</b>\n\n"
            f"{result}\n\n"
            f"💡 Возможно, вы уже получали стартовый бонус ранее.",
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

async def view_user_profile(msg: Message, user_id: int, is_from_top: bool = False):
    """Показать профиль другого пользователя"""
    user = await get_user(user_id)
    
    if not user:
        await msg.reply("❌ Пользователь не найден")
        return
    
    total = user['wins'] + user['losses']
    win_rate = (user['wins'] / total * 100) if total > 0 else 0
    
    # Получаем текущего пользователя
    current_user = await get_user(msg.from_user.id)
    
    text = f"""
👤 <b>Профиль пользователя</b>

📋 <b>Основная информация:</b>
💰 Баланс: {user['balance']:,}
⚡ Плазма: {user['plasma']}
₿ Биткоин: {user['bitcoin']:.8f}
🏆 Побед: {user['wins']}
💀 Поражений: {user['losses']}
📊 Винрейт: {win_rate:.1f}%

👥 <b>Социальные показатели:</b>
🏢 Бизнесов: {len(await get_user_businesses(user_id))}
🪐 Планет: {len(await get_user_planets(user_id))}
⛏️ Видеокарт: {user['mining_gpu_count']} (ур. {user['mining_gpu_level']})
👥 Рефералов: {user.get('referral_count', 0)}
💰 Заработано на рефералах: {user.get('total_referral_earned', 0):,}

💼 <b>Прогресс:</b>
🎁 Всего получено бонусов: {user.get('total_bonus', 0):,}
💼 Всего заработано работой: {user.get('total_work', 0):,}
"""
    
    # Если это профиль из топа, добавляем кнопку "Назад в топ"
    keyboard = []
    if is_from_top:
        keyboard.append([InlineKeyboardButton(text="🔙 Назад к топу", callback_data="show_top")])
    else:
        keyboard.append([InlineKeyboardButton(text="🏆 Топ игроков", callback_data="show_top")])
    
    # Кнопка для отправки сообщения (если есть username)
    if user.get('username'):
        keyboard.append([InlineKeyboardButton(text="📨 Написать сообщение", url=f"https://t.me/{user['username']}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await msg.reply(text, parse_mode="HTML", reply_markup=kb)
    
    total = user['wins'] + user['losses']
    win_rate = (user['wins'] / total * 100) if total > 0 else 0
    
    can_get_bonus, remaining_bonus, _ = await check_bonus_cooldown(msg.from_user.id)
    can_work, remaining_work, _ = await check_work_cooldown(msg.from_user.id)
    
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
    
    if can_work:
        work_status = "✅ <b>Доступна сейчас!</b>"
        work_time = "Следующая через 30 секунд"
        work_bar = ""
    else:
        seconds = int(remaining_work)
        progress_percent = int((WORK_COOLDOWN - remaining_work) / WORK_COOLDOWN * 100)
        work_bar = create_progress_bar(progress_percent)
        work_status = f"⏳ <b>Через:</b> {seconds}с"
        work_time = f"{work_bar} {progress_percent}%"
    
    referral_info = ""
    if user.get('referred_by'):
        referrer = await get_user(user['referred_by'])
        referrer_name = referrer.get('username', f"ID {user['referred_by']}")
        referral_info = f"👤 <b>Вас пригласил:</b> {referrer_name}\n"
    
    referral_info += f"👥 <b>Ваших рефералов:</b> {user.get('referral_count', 0)}\n"
    referral_info += f"💰 <b>Заработано на рефералах:</b> {user.get('total_referral_earned', 0):,}\n"
    
    start_bonus_info = "✅ <b>Стартовый бонус:</b> получен" if user.get('has_started_bonus') else "❌ <b>Стартовый бонус:</b> не получен"
    
    bot_username = (await msg.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user.get('referral_code', 'НЕТ')}"
    referral_info += f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{referral_link}</code>"
    
    await msg.reply(
        f"👤 <b>Профиль {username}</b>\n\n"
        f"💰 Баланс: {user['balance']:,}\n"
        f"🏆 Побед: {user['wins']}\n"
        f"💀 Поражений: {user['losses']}\n"
        f"📊 Винрейт: {win_rate:.1f}%\n"
        f"{start_bonus_info}\n\n"
        f"🎁 <b>Ежечасный бонус (5-20М):</b>\n"
        f"• Статус: {bonus_status}\n"
        f"• {bonus_time}\n"
        f"• Всего получено: {user.get('total_bonus', 0):,}\n\n"
        f"💼 <b>Ежеминутная работа (1-5М):</b>\n"
        f"• Статус: {work_status}\n"
        f"• {work_time}\n"
        f"• Всего заработано: {user.get('total_work', 0):,}\n\n"
        f"👥 <b>Реферальная система:</b>\n"
        f"{referral_info}",
        parse_mode="HTML"
    )

async def process_referrals(msg: Message):
    """Обработка команды рефералы"""
    user = await get_user(msg.from_user.id)
    username = msg.from_user.username or msg.from_user.first_name
    
    referral_code = user.get('referral_code', 'НЕТ')
    referral_count = user.get('referral_count', 0)
    total_earned = user.get('total_referral_earned', 0)
    
    bot_username = (await msg.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    text = f"""
👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА MURASAKI EMPIRE</b>

👤 <b>Ваш профиль:</b> {username}
🔗 <b>Ваш реферальный код:</b> <code>{referral_code}</code>

💰 <b>Награда за приглашение:</b>
• 30-100 миллионов за каждого друга!

📊 <b>Ваша статистика:</b>
• Приглашено друзей: <b>{referral_count}</b>
• Заработано на рефералах: <code>{total_earned:,}</code>

🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

📝 <b>Как приглашать:</b>
1. Отправьте другу вашу ссылку
2. Друг должен нажать на ссылку и запустить бота
3. Как только он начнет играть, вы получите награду!

🎯 <b>Пример сообщения для друга:</b>
"Привет! Присоединяйся к Murasaki Empire и получай огромные бонусы! 🎌
Твоя ссылка: {referral_link}"
"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_ref_link")],
        [InlineKeyboardButton(text="🏆 Топ рефереров", callback_data="top_refs")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="my_profile_ref")]
    ])
    
    await msg.reply(text, parse_mode="HTML", reply_markup=kb)

async def process_top(msg: Message, user_id: int = None):
    """Обработка команды топ с кликабельными профилями"""
    try:
        current_user_id = msg.from_user.id if msg else user_id
        top_players = await get_top()
        
        if not top_players:
            await msg.reply(
                "🏆 <b>ТОП-10 БОГАЧЕЙ MURASAKI EMPIRE</b>\n\n"
                "📭 В топе пока никого нет!\n\n"
                "💡 Стань первым! Зарабатывайте:\n"
                "• <code>бонус</code> - 5-20М каждый час\n"
                "• <code>работа</code> - 1-5М каждые 30 сек\n"
                "• <code>бизнесы</code> - покупайте и получайте прибыль\n"
                "• <code>инвестиции</code> - вкладывайте и получайте доход",
                parse_mode="HTML"
            )
            return
        
        txt = "🏆 <b>ТОП-10 БОГАЧЕЙ MURASAKI EMPIRE</b>\n\n"
        txt += "<i>Нажми на никнейм, чтобы посмотреть профиль</i>\n\n"
        
        # Эмодзи для мест
        place_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        keyboard_buttons = []
        
        for i, player in enumerate(top_players, 1):
            username = player.get('username', f"ID {player['id']}")
            balance = player.get('balance', 0)
            
            emoji = place_emojis[i-1] if i <= len(place_emojis) else f"{i}."
            
            # Форматируем имя (обрезаем если слишком длинное)
            display_name = username
            if len(username) > 20:
                display_name = username[:17] + "..."
            
            balance_str = format_money(balance)
            
            # ПРОВЕРЯЕМ ЭТО ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ИЛИ НЕТ
            is_current_user = (player['id'] == current_user_id)
            current_marker = " ⭐" if is_current_user else ""
            
            # Формируем текст строки
            if i == 1:
                txt += f"{emoji} <b>👑 {display_name}{current_marker}</b> — <code>{balance_str}</code> 👑\n"
            elif i == 2:
                txt += f"{emoji} <b>⭐ {display_name}{current_marker}</b> — <code>{balance_str}</code>\n"
            elif i == 3:
                txt += f"{emoji} <b>✨ {display_name}{current_marker}</b> — <code>{balance_str}</code>\n"
            else:
                txt += f"{emoji} {display_name}{current_marker} — <code>{balance_str}</code>\n"
            
            # Создаем кнопку для каждого игрока
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {display_name[:15]}{'...' if len(display_name) > 15 else ''}",
                    callback_data=f"view_profile_{player['id']}"
                )
            ])
        
        # Добавляем статистику
        total_players = await get_all_users_count()
        total_money = await get_total_money_in_system()
        
        txt += f"\n📊 <b>Статистика системы:</b>\n"
        txt += f"👥 Всего игроков: <b>{total_players}</b>\n"
        txt += f"💰 Всего денег в системе: <b>{format_money(total_money)}</b>"
        
        # Кнопки для навигации
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔄 Обновить", callback_data="show_top"),
            InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")
        ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await msg.reply(txt, parse_mode="HTML", reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Ошибка process_top: {e}")
        await msg.reply(
            "🏆 <b>ТОП-10 БОГАЧЕЙ MURASAKI EMPIRE</b>\n\n"
            "⚠️ Не удалось загрузить топ. Попробуйте позже.",
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
        seconds = int(remaining)
        progress_percent = int((WORK_COOLDOWN - remaining) / WORK_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        
        await msg.reply(
            f"⏳ <b>До следующей работы:</b>\n"
            f"<b>{seconds} секунд</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Будет доступна в:</b> {next_str}\n\n"
            f"💰 Всего заработано: <code>{work_data.get('total_work', 0):,}</code>\n"
            f"🎯 <b>Следующая работа:</b> 1-5 миллионов",
            parse_mode="HTML"
        )

async def show_businesses(msg: Message):
    """Показать список бизнесов"""
    businesses_list = "<b>🏢 СПИСОК БИЗНЕСОВ</b>\n\n"
    
    for biz_id, biz in BUSINESSES.items():
        businesses_list += f"<b>{biz_id}. {biz['name']}</b>\n"
        businesses_list += f"   💰 Цена: {format_money(biz['price'])}\n"
        businesses_list += f"   💵 Прибыль/час: {format_money(biz['profit_per_hour'])}\n"
        businesses_list += f"   ⚡ Продукты: {biz['product_name']} (емкость: {biz['product_capacity']})\n"
        businesses_list += f"   🔄 Пополнение: {format_money(biz['product_refill_cost'])}\n"
        businesses_list += f"   📈 Уровней: {biz['max_level']}\n\n"
    
    businesses_list += "<b>📋 КОМАНДЫ:</b>\n"
    businesses_list += "• <code>купить бизнес [id]</code> - купить бизнес\n"
    businesses_list += "• <code>улучшить бизнес [id]</code> - улучшить бизнес\n"
    businesses_list += "• <code>пополнить бизнес [id]</code> - пополнить продукты\n"
    businesses_list += "• <code>собрать бизнес [id]</code> - собрать прибыль\n"
    businesses_list += "• <code>продать бизнес [id]</code> - продать государству\n"
    
    await msg.reply(businesses_list, parse_mode="HTML")

async def show_planets(msg: Message):
    """Показать список планет"""
    planets_list = "<b>🪐 СПИСОК ПЛАНЕТ</b>\n\n"
    
    for planet_id, planet in PLANETS.items():
        planets_list += f"<b>{planet_id}. {planet['name']}</b>\n"
        planets_list += f"   📝 {planet['description']}\n"
        if planet['price_dollars'] > 0:
            planets_list += f"   💰 Цена: {format_money(planet['price_dollars'])} $\n"
        else:
            planets_list += f"   ⚡ Цена: {planet['price_plasma']} плазмы\n"
        planets_list += f"   🔋 Генерация: {planet['plasma_per_hour']} плазмы/час\n\n"
    
    planets_list += "<b>📋 КОМАНДЫ:</b>\n"
    planets_list += "• <code>купить планету [id]</code> - купить планету\n"
    planets_list += "• <code>собрать плазму [id]</code> - собрать плазму\n"
    
    await msg.reply(planets_list, parse_mode="HTML")

async def show_mining_info(msg: Message):
    """Показать информацию о майнинге (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    user = await get_user(msg.from_user.id)
    
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    btc_price = BitcoinMining.get_bitcoin_price()
    usd_per_hour = btc_per_hour * btc_price
    
    # Рассчитаем накопленные BTC
    current_time = int(time.time())
    last_claim = user['last_mining_claim'] or current_time
    time_passed = current_time - last_claim
    btc_mined = btc_per_hour * (time_passed / 3600)
    
    mining_info = f"""
<b>⛏️ МАЙНИНГ ФЕРМА</b>

📊 <b>Ваша ферма:</b>
• 🎮 Видеокарт: {user['mining_gpu_count']}
• ⭐ Уровень видеокарт: {user['mining_gpu_level']}
• ⚡ Хешрейт: {hashrate:.1f} MH/s
• ₿ Майнинг/час: {btc_per_hour:.8f} BTC
• 💰 Доход/час: ~{format_money(int(usd_per_hour))}$
• 📈 Курс BTC: {format_money(int(btc_price))}$

💰 <b>Ваши активы:</b>
• 💎 Ваши BTC: {user['bitcoin']:.8f}
• ⏳ Накоплено с последнего сбора: {btc_mined:.8f} BTC (~{format_money(int(btc_mined * btc_price))}$)

💵 <b>Цены видеокарт:</b>
"""
    
    for level in range(1, 6):
        price = BitcoinMining.get_gpu_price(level)
        if level == user['mining_gpu_level']:
            mining_info += f"• 🎯 <b>Уровень {level}: {format_money(price)}</b> (ТЕКУЩИЙ)\n"
        else:
            mining_info += f"• Уровень {level}: {format_money(price)}\n"
    
    mining_info += f"""

📋 <b>КОМАНДЫ:</b>
• <code>купить видеокарту</code> - купить видеокарту ({format_money(BitcoinMining.get_gpu_price(user['mining_gpu_level']))})
• <code>улучшить видеокарты</code> - улучшить все видеокарты
• <code>забрать биткоины</code> - забрать намайненые BTC
• <code>продать биткоин [кол-во]</code> - продать BTC
• <code>продать биткоин все</code> - продать все BTC
"""
    
    await msg.reply(mining_info, parse_mode="HTML")

async def show_investments(msg: Message):
    """Показать список инвестиций"""
    investments_list = "<b>💼 СПИСОК ИНВЕСТИЦИЙ</b>\n\n"
    
    for inv_id, inv in INVESTMENTS.items():
        duration_hours = inv['duration'] // 3600
        investments_list += f"<b>{inv_id}. {inv['name']}</b>\n"
        investments_list += f"   ⏱️ Длительность: {duration_hours} часов\n"
        investments_list += f"   💰 Мин. сумма: {format_money(inv['min_amount'])}\n"
        investments_list += f"   📈 Шанс успеха: {int(inv['success_rate'] * 100)}%\n"
        investments_list += f"   💵 Прибыль: +{int((inv['profit_multiplier'] - 1) * 100)}%\n\n"
    
    investments_list += "<b>📋 КОМАНДЫ:</b>\n"
    investments_list += "• <code>начать инвестицию [id] [сумма]</code> - начать инвестицию\n"
    investments_list += "• <code>завершить инвестицию [id]</code> - завершить инвестицию\n"
    
    await msg.reply(investments_list, parse_mode="HTML")

# ========== ИГРОВЫЕ ФУНКЦИИ ИЗ ТВОЕГО КОДА ==========
async def process_coin(msg: Message, parts: list):
    """Обработка команды монетка"""
    if len(parts) < 2:
        await msg.reply("❌ Укажите ставку!\nПример: <code>монетка 1000</code> или <code>монетка 1к</code> или <code>монетка 1кк</code>", parse_mode="HTML")
        return
    
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
    
    is_number_bet = False
    number_value = None
    
    if bet_type.isdigit():
        num = int(bet_type)
        if 0 <= num <= 36:
            is_number_bet = True
            number_value = str(num)
            bet_type = "число"
    
    valid_types = ['красное', 'черное', 'зеленое', 'четное', 'нечетное',
                  '1-18', '19-36', '1-12', '13-24', '25-36']
    
    if not is_number_bet and bet_type not in valid_types:
        await msg.reply("❌ Неправильный тип ставки. Используй команду рулетка без аргументов для помощи")
        return
    
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    
    loading_msg = await msg.reply("🎰 Крутим рулетку...")
    await asyncio.sleep(1)
    
    final_number = random.choice(ROULETTE_NUMBERS)
    final_color = get_roulette_color(final_number)
    
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

async def process_darts(msg: Message, parts: list):
    """Обработка игры в дротики с мишенью"""
    if len(parts) < 2:
        await msg.reply(
            "🎯 <b>Игра: Дартс</b>\n\n"
            "🏹 <b>Правила:</b>\n"
            "• Попадание в центр (🎯): <b>x5</b>\n"
            "• Попадание в среднюю зону (🟡): <b>x2</b>\n"
            "• Попадание во внешнюю зону (🔴): <b>x1</b> (возврат ставки)\n"
            "• Промах (❌): <b>x0</b> (проигрыш)\n\n"
            "🎯 <b>Использование:</b> <code>дротик [ставка]</code>\n"
            "📊 <b>Примеры:</b>\n"
            "• <code>дротик 1000</code>\n"
            "• <code>дротик 1к</code>\n"
            "• <code>дротик 1кк</code>",
            parse_mode="HTML"
        )
        return
    
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
    
    loading_msg = await msg.reply("🎯 Целюсь в мишень...")
    await asyncio.sleep(1.5)
    
    # Определяем зону попадания для игрока и бота
    player_zone = get_darts_zone()
    bot_zone = get_darts_zone()
    
    player_zone_data = DARTS_ZONES[player_zone]
    bot_zone_data = DARTS_ZONES[bot_zone]
    
    # Визуализация броска кубиком (для эффекта)
    dice_msg = await msg.answer_dice(emoji="🎯")
    await asyncio.sleep(2)
    
    await loading_msg.delete()
    
    # Рассчитываем выигрыш
    player_multiplier = player_zone_data['multiplier']
    bot_multiplier = bot_zone_data['multiplier']
    
    player_win_amount = int(bet * player_multiplier)
    bot_win_amount = int(bet * bot_multiplier)
    
    # Определяем результат
    if player_multiplier > bot_multiplier:
        # Игрок выиграл
        win = player_win_amount
        await change_balance(msg.from_user.id, win)
        await update_stats(msg.from_user.id, True)
        result = f"✅ <b>ВЫИГРЫШ!</b>\n💰 +{win:,} (x{player_multiplier})"
    elif player_multiplier < bot_multiplier:
        # Бот выиграл
        await update_stats(msg.from_user.id, False)
        result = f"❌ <b>ПРОИГРЫШ</b>\n💸 -{bet:,}"
    else:
        # Ничья (одинаковые зоны)
        if player_multiplier > 0:
            # Оба попали, возвращаем ставки
            await change_balance(msg.from_user.id, bet)
            result = f"🤝 <b>НИЧЬЯ!</b>\n🔄 Ставка возвращена"
        else:
            # Оба промахнулись
            await update_stats(msg.from_user.id, False)
            result = f"❌ <b>ОБА ПРОМАХНУЛИСЬ!</b>\n💸 -{bet:,}"
    
    # ASCII-графика мишени
    target_art = """
       🎯 МИШЕНЬ 🎯
    ┌─────────────────┐
    │     🔴 🔴 🔴     │
    │   🔴 🟡 🟡 🟡 🔴   │
    │ 🔴 🟡 🎯 🎯 🎯 🟡 🔴 │
    │   🔴 🟡 🎯 🎯 🎯 🟡 🔴 │
    │     🔴 🟡 🎯 🟡 🔴     │
    │       🔴 🟡 🔴       │
    │         🔴         │
    └─────────────────┘
    """
    
    # Создаем визуализацию попадания
    hit_marker = "⭐"
    
    # Определяем где попадание на мишени
    if player_zone == 'center':
        hit_position = "🎯"
        hit_description = "Прямо в центр!"
    elif player_zone == 'middle':
        hit_position = "🟡"
        hit_description = "В среднюю зону!"
    elif player_zone == 'outer':
        hit_position = "🔴"
        hit_description = "Во внешнюю зону!"
    else:
        hit_position = "❌"
        hit_description = "Промах! Мимо мишени!"
    
    # Результат бота
    if bot_zone == 'center':
        bot_hit = "🎯 Центр"
    elif bot_zone == 'middle':
        bot_hit = "🟡 Средняя зона"
    elif bot_zone == 'outer':
        bot_hit = "🔴 Внешняя зона"
    else:
        bot_hit = "❌ Промах"
    
    text = f"""
🎯 <b>Игра: Дартс</b>

💰 <b>Ставка:</b> {bet:,}

🎯 <b>Твой бросок:</b>
{player_zone_data['emoji']} {player_zone_data['name']}
📊 Множитель: <b>x{player_multiplier}</b>
{hit_description}

🤖 <b>Бросок бота:</b>
{bot_zone_data['emoji']} {bot_hit}
📊 Множитель: <b>x{bot_multiplier}</b>

{target_art}

{result}
"""
    
    await msg.reply(text, parse_mode="HTML")

async def process_bj(msg: Message, parts: list):
    """Обработка команды блэкджек"""
    if len(parts) == 1 and parts[0] in ['бж', 'bj']:
        uid = msg.from_user.id
        game = load_bj_game(uid)
        
        if game:
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
    
    if len(parts) < 2:
        await msg.reply("🃏 Отправь: <code>блекджек [ставка]</code>\nПример: <code>бж 1000</code> или <code>бж 1к</code> или <code>бж 1кк</code>", parse_mode="HTML")
        return
    
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
    
    game = load_bj_game(uid)
    if game:
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

# =======================================
#        ФУНКЦИИ АДМИН-КОМАНД
# =======================================
async def process_admin_give_reply(msg: Message, parts: list):
    """Админ: выдать деньги по ответу"""
    if len(parts) < 2:
        await msg.reply("❌ Используйте: <code>выдать [сумма]</code> в ответ на сообщение")
        return
    
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
    amount_str = parts[2]
    amount = parse_amount(amount_str)
    
    if amount <= 0:
        await msg.reply("❌ Неправильная сумма!")
        return
    
    target_id = None
    if target_arg.isdigit():
        target_id = int(target_arg)
    elif target_arg.startswith('@'):
        username = target_arg[1:]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            if row:
                target_id = row['id']
            else:
                await msg.reply(f"❌ Пользователь @{username} не найден")
                return
    else:
        await msg.reply("❌ Укажите ID или @юзернейм")
        return
    
    await change_balance(target_id, amount)
    new_balance = await get_user(target_id)
    
    await msg.reply(
        f"✅ <b>Деньги выданы!</b>\n\n"
        f"💸 Сумма: <code>{amount:,}</code>\n"
        f"👤 Пользователь: ID {target_id}\n"
        f"💰 Новый баланс: <code>{new_balance['balance']:,}</code>",
        parse_mode="HTML"
    )

async def process_admin_take_reply(msg: Message, parts: list):
    """Админ: забрать деньги по ответу"""
    if len(parts) < 2:
        await msg.reply("❌ Используйте: <code>забрать [сумма]</code> в ответ на сообщение")
        return
    
    amount_str = parts[1]
    amount = parse_amount(amount_str)
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
    amount_str = parts[2]
    amount = parse_amount(amount_str)
    
    target_id = None
    if target_arg.isdigit():
        target_id = int(target_arg)
    elif target_arg.startswith('@'):
        username = target_arg[1:]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            if row:
                target_id = row['id']
            else:
                await msg.reply(f"❌ Пользователь @{username} не найден")
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

# =======================================
#        ХЭНДЛЕРЫ АДМИН-КОМАНД
# =======================================
@router.message(F.text.lower().startswith("выдать"))
async def cmd_give_text(msg: Message):
    parts = msg.text.split()
    if msg.reply_to_message:
        await process_admin_give_reply(msg, parts)
    else:
        await process_admin_give(msg, parts)

@router.message(F.text.lower().startswith("забрать"))
async def cmd_take_text(msg: Message):
    parts = msg.text.split()
    if msg.reply_to_message:
        await process_admin_take_reply(msg, parts)
    else:
        await process_admin_take(msg, parts)

# ========== КОМАНДЫ С / ДЛЯ СОВМЕСТИМОСТИ ==========
@router.message(Command("start", "menu"))
async def cmd_start(msg: Message):
    await send_welcome_message(msg)

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

@router.message(Command("мойбизнес", "моибизнесы", "mybusiness"))
async def cmd_mybusiness_slash(msg: Message):
    """Команда для просмотра собственных бизнесов"""
    await show_my_businesses(msg)

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

@router.message(Command("дротик", "дартс", "дрот", "darts"))
async def cmd_darts_slash(msg: Message, command: CommandObject):
    if not command.args:
        await msg.reply("🎯 Используй: <code>дротик [ставка]</code>\nПример: дротик 1000 или дротик 1к или дротик 1кк", parse_mode="HTML")
        return
    
    parts = ["дротик"] + command.args.split()
    await process_darts(msg, parts)

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
        uid = msg.from_user.id
        game = load_bj_game(uid)
        
        if game:
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
    await handle_all_commands(msg)

@router.message(Command("забрать"))
async def cmd_take_slash(msg: Message):
    await handle_all_commands(msg)

@router.message(Command("бизнесы", "business"))
async def cmd_businesses_slash(msg: Message):
    await show_businesses(msg)

@router.message(Command("майнинг", "mining"))
async def cmd_mining_slash(msg: Message):
    await show_mining_info(msg)

@router.message(Command("планеты", "planets"))
async def cmd_planets_slash(msg: Message):
    await show_planets(msg)

@router.message(Command("инвестиции", "investments"))
async def cmd_investments_slash(msg: Message):
    await show_investments(msg)

# ====== ТЕКСТОВЫЕ КОМАНДЫ (БЕЗ /) ======
@router.message(F.text.lower() == "б")
@router.message(F.text.lower() == "баланс")
@router.message(F.text.lower() == "balance")
async def balance_text_cmd(msg: Message):
    await process_balance(msg)

@router.message(F.text.lower().startswith(("бонус", "bonus")))
async def bonus_text_cmd(msg: Message):
    await process_bonus(msg)

@router.message(F.text.lower().startswith(("работа", "раб", "work")))
async def work_text_cmd(msg: Message):
    await process_work(msg)

@router.message(F.text.lower().startswith(("кд", "cd", "кулдаун")))
async def cd_text_cmd(msg: Message):
    await check_bonus_cd(msg)

@router.message(F.text.lower().startswith(("кдработы", "работакд", "workcd")))
async def work_cd_text_cmd(msg: Message):
    await check_work_cd(msg)

@router.message(F.text.lower().startswith(("профиль", "пр", "стата", "profile")))
async def profile_text_cmd(msg: Message):
    await process_profile(msg)

@router.message(F.text.lower().startswith(("топ", "лидеры", "top")))
async def top_text_cmd(msg: Message):
    await process_top(msg)

@router.message(F.text.lower().startswith(("мойбизнес", "моибизнесы", "mybusiness")))
async def mybusiness_text_cmd(msg: Message):
    await show_my_businesses(msg)

@router.message(F.text.lower().startswith(("монетка", "coin", "мн")))
async def coin_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_coin(msg, parts)

@router.message(F.text.lower().startswith(("дротик", "дартс", "дрот")))
async def darts_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_darts(msg, parts)

@router.message(F.text.lower().startswith(("кости", "dice", "кст")))
async def dice_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_dice(msg, parts)

@router.message(F.text.lower().startswith(("слоты", "slots", "сл")))
async def slots_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_slots(msg, parts)

@router.message(F.text.lower().startswith(("рулетка", "рул")))
async def roulette_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_roulette(msg, parts)

@router.message(F.text.lower().startswith(("блекджек", "блэкджек", "бж", "bj")))
async def bj_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_bj(msg, parts)



@router.message(F.text.lower().startswith(("передать", "transfer")))
async def transfer_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_transfer(msg, parts)

@router.message(F.text.lower().startswith(("выдать",)))
async def give_text_cmd(msg: Message):
    await handle_all_commands(msg)

@router.message(F.text.lower().startswith(("забрать",)))
async def take_text_cmd(msg: Message):
    await handle_all_commands(msg)

@router.message(F.text.lower().startswith(("бизнесы", "business")))
async def businesses_text_cmd(msg: Message):
    await show_businesses(msg)

@router.message(F.text.lower().startswith(("майнинг", "mining")))
async def mining_text_cmd(msg: Message):
    await show_mining_info(msg)

@router.message(F.text.lower().startswith(("планеты", "planets")))
async def planets_text_cmd(msg: Message):
    await show_planets(msg)

@router.message(F.text.lower().startswith(("инвестиции", "investments")))
async def investments_text_cmd(msg: Message):
    await show_investments(msg)

# ========== CALLBACK ОБРАБОТЧИКИ ==========

# ========== ОБРАБОТЧИКИ ДЛЯ "МОЙ БИЗНЕС" (НОВЫЕ) ==========
@router.callback_query(F.data == "show_my_businesses")
async def show_my_businesses_cb(cb: CallbackQuery):
    """Показать бизнесы пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    uid = cb.from_user.id
    user_businesses = await get_user_businesses(uid)
    
    if not user_businesses:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ])
        
        try:
            await cb.message.edit_text(
                "🏢 <b>Ваши бизнесы</b>\n\n"
                "❌ У вас пока нет бизнесов.\n"
                "📋 Чтобы купить бизнес, напишите: <code>купить бизнес [id]</code>\n"
                "📝 Или посмотрите список бизнесов: <code>бизнесы</code>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except:
            await cb.message.answer(
                "🏢 <b>Ваши бизнесы</b>\n\n"
                "❌ У вас пока нет бизнесов.\n"
                "📋 Чтобы купить бизнес, напишите: <code>купить бизнес [id]</code>\n"
                "📝 Или посмотрите список бизнесов: <code>бизнесы</code>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        await cb.answer()
        return
    
    # Если бизнесы есть, показываем их с кнопками
    keyboard = []
    for biz_id, biz_data in user_businesses.items():
        if biz_id in BUSINESSES:
            business_info = BUSINESSES[biz_id]
            level = biz_data['level']
            product_amount = biz_data['product_amount']
            product_capacity = business_info['product_capacity']
            
            # Статус заполнения
            if product_amount >= product_capacity:
                status = "🟢"
            elif product_amount > product_capacity * 0.5:
                status = "🟡"
            else:
                status = "🔴"
            
            # Кнопка для управления этим бизнесом
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {business_info['name']} (Ур. {level})",
                    callback_data=f"mybiz_{biz_id}"
                )
            ])
    
    # Добавляем кнопку "Назад" если есть бизнесы
    if keyboard:
        keyboard.append([InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    text = "🏢 <b>Ваши бизнесы</b>\n\n"
    text += f"📊 Всего бизнесов: {len(user_businesses)}\n"
    text += "Выберите бизнес для управления:\n\n"
    text += "🟢 - Продукты заполнены\n🟡 - Продукты наполовину\n🔴 - Мало продуктов"
    
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("mybiz_"))
async def my_business_callback(cb: CallbackQuery):
    """Обработка выбора бизнеса - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        biz_id = int(cb.data.split("_")[1])
        uid = cb.from_user.id
        
        # Получаем данные бизнеса
        user_businesses = await get_user_businesses(uid)
        if biz_id not in user_businesses:
            await cb.answer("❌ У вас нет этого бизнеса")
            return
        
        biz_data = user_businesses[biz_id]
        business_info = BUSINESSES[biz_id]
        
        # Расчет прибыли
        profit_per_hour = business_info['profit_per_hour'] * (business_info['upgrade_multiplier'] ** (biz_data['level'] - 1))
        
        # Процент заполнения продуктов
        product_percent = int((biz_data['product_amount'] / business_info['product_capacity']) * 100)
        
        # Создаем клавиатуру для управления
        keyboard = [
            [
                InlineKeyboardButton(text="🔄 Пополнить", callback_data=f"biz_refill_{biz_id}"),
                InlineKeyboardButton(text="💰 Собрать", callback_data=f"biz_collect_{biz_id}")
            ],
            [
                InlineKeyboardButton(text="📈 Улучшить", callback_data=f"biz_upgrade_{biz_id}"),
                InlineKeyboardButton(text="💸 Продать", callback_data=f"biz_sell_{biz_id}")
            ],
            [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="show_my_businesses")]
        ]
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Создаем прогресс-бар для продуктов
        progress_bar = create_progress_bar(product_percent)
        
        text = f"""
🏢 <b>{business_info['name']} (Уровень {biz_data['level']})</b>

📊 <b>Информация:</b>
• Уровень: {biz_data['level']}/{business_info['max_level']}
• Продукты: {biz_data['product_amount']}/{business_info['product_capacity']}
{progress_bar} {product_percent}%
• Прибыль в час: {format_money(profit_per_hour)}
• Стоимость пополнения: {format_money(business_info['product_refill_cost'])}
"""
        
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка в my_business_callback: {e}")
        await cb.answer("❌ Ошибка")
        
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка в my_business_callback: {e}")
        await cb.answer("❌ Ошибка")

@router.callback_query(F.data.startswith("biz_refill_"))
async def biz_refill_callback(cb: CallbackQuery):
    """Пополнение продуктов бизнеса"""
    try:
        biz_id = int(cb.data.split("_")[2])
        uid = cb.from_user.id
        
        success, message = await refill_products(uid, biz_id)
        await cb.answer(message)
        
        # Обновляем сообщение
        if success:
            await my_business_callback(cb)
    except Exception as e:
        logger.error(f"Ошибка в biz_refill_callback: {e}")
        await cb.answer("❌ Ошибка пополнения")

@router.callback_query(F.data.startswith("biz_collect_"))
async def biz_collect_callback(cb: CallbackQuery):
    """Сбор прибыли с бизнеса"""
    try:
        biz_id = int(cb.data.split("_")[2])
        uid = cb.from_user.id
        
        success, result = await collect_business_profit(uid, biz_id)
        if success:
            await cb.answer(f"✅ Собрано: {format_money(result)}")
            await my_business_callback(cb)
        else:
            await cb.answer(f"❌ {result}")
    except Exception as e:
        logger.error(f"Ошибка в biz_collect_callback: {e}")
        await cb.answer("❌ Ошибка сбора")

@router.callback_query(F.data.startswith("biz_upgrade_"))
async def biz_upgrade_callback(cb: CallbackQuery):
    """Улучшение бизнеса"""
    try:
        biz_id = int(cb.data.split("_")[2])
        uid = cb.from_user.id
        
        success, message = await upgrade_business(uid, biz_id)
        await cb.answer(message)
        
        if success:
            await my_business_callback(cb)
    except Exception as e:
        logger.error(f"Ошибка в biz_upgrade_callback: {e}")
        await cb.answer("❌ Ошибка улучшения")

@router.callback_query(F.data.startswith("biz_sell_"))
async def biz_sell_callback(cb: CallbackQuery):
    """Продажа бизнеса"""
    try:
        biz_id = int(cb.data.split("_")[2])
        uid = cb.from_user.id
        
        success, amount = await sell_business(uid, biz_id)
        if success:
            await cb.answer(f"✅ Продано за {format_money(amount)}")
            await show_my_businesses(cb.message)
        else:
            await cb.answer(f"❌ {amount}")
    except Exception as e:
        logger.error(f"Ошибка в biz_sell_callback: {e}")
        await cb.answer("❌ Ошибка продажи")

# ========== ОБРАБОТЧИКИ ДЛЯ ИНВЕСТИЦИЙ (НОВЫЕ) ==========
# ========== ИНВЕСТИЦИИ - ЕДИНЫЙ ОБРАБОТЧИК ==========
@router.callback_query(F.data.startswith("invest_"))
async def all_investment_callbacks(cb: CallbackQuery):
    try:
        data = cb.data
        
        if "_select_" in data:
            # invest_select_1
            investment_id = int(data.split("_")[2])
            if 1 <= investment_id <= len(INVESTMENTS):
                inv = INVESTMENTS[investment_id]
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="💰 1M", callback_data=f"invest_start_{investment_id}_1000000"),
                        InlineKeyboardButton(text="💰 10M", callback_data=f"invest_start_{investment_id}_10000000"),
                        InlineKeyboardButton(text="💰 100M", callback_data=f"invest_start_{investment_id}_100000000")
                    ],
                    [
                        InlineKeyboardButton(text="💰 1B", callback_data=f"invest_start_{investment_id}_1000000000"),
                        InlineKeyboardButton(text="💰 5B", callback_data=f"invest_start_{investment_id}_5000000000")
                    ],
                    [InlineKeyboardButton(text="💰 Своя сумма", callback_data=f"invest_custom_{investment_id}")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="show_investments")]
                ])
                
                duration_hours = inv['duration'] // 3600
                duration_minutes = (inv['duration'] % 3600) // 60
                
                text = f"""
💼 <b>Начать инвестицию: {inv['name']}</b>

📊 <b>Параметры:</b>
• Длительность: {duration_hours}ч {duration_minutes}м
• Минимальная сумма: {format_money(inv['min_amount'])}
• Шанс успеха: {int(inv['success_rate'] * 100)}%
• Прибыль при успехе: +{int((inv['profit_multiplier'] - 1) * 100)}%

💰 <b>Выберите сумму:</b>
"""
                await cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
                await cb.answer()
            else:
                await cb.answer("❌ Неверный ID инвестиции")
                
        elif "_start_" in data:
            # invest_start_1_1000000
            parts = data.split("_")
            investment_id = int(parts[2])
            amount = int(parts[3])
            
            success, message = await start_investment(cb.from_user.id, investment_id, amount)
            
            if success:
                await cb.answer("✅ Инвестиция начата!")
                await show_investments_panel(cb=cb)
            else:
                await cb.answer(f"❌ {message}")
                
        elif "_custom_" in data:
            # invest_custom_1
            investment_id = int(data.split("_")[2])
            await cb.answer(f"📝 Введите: начать инвестицию {investment_id} [ваша сумма]")
            
        elif "_complete_" in data:
            # inv_complete_123
            investment_db_id = int(data.split("_")[2])
            success, message = await complete_investment(cb.from_user.id, investment_db_id)
            await cb.answer(message)
            if success:
                await show_investments_panel(cb=cb)
                
        else:
            await cb.answer("❌ Неизвестная команда инвестиции")
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике инвестиций: {e}")
        await cb.answer("❌ Ошибка")

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(cb: CallbackQuery):
    """Вернуться в главное меню"""
    await send_welcome_message(cb.message)
    await cb.answer()

# ========== СУЩЕСТВУЮЩИЕ CALLBACK ОБРАБОТЧИКИ ==========
@router.callback_query(F.data == "copy_ref_link")
async def copy_ref_link_cb(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    referral_code = user.get('referral_code')
    
    if not referral_code:
        await cb.answer("❌ Реферальный код не найден", show_alert=True)
        return
    
    bot_username = (await cb.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    await cb.answer(f"🔗 Ссылка скопирована!\n\n{referral_link}", show_alert=True)

@router.callback_query(F.data == "top_refs")
async def top_refs_cb(cb: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, referral_count, total_referral_earned FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 10"
            )
            rows = await cursor.fetchall()
            
            if not rows:
                await cb.message.answer("🏆 В топе рефереров пока никого нет!")
                await cb.answer()
                return
            
            txt = "🏆 <b>ТОП-10 РЕФЕРЕРОВ MURASAKI EMPIRE</b>\n\n"
            for i, row in enumerate(rows, 1):
                username = row.get('username')
                referral_count = row.get('referral_count', 0)
                total_earned = row.get('total_referral_earned', 0)
                
                if username:
                    username_display = f"@{username}"
                else:
                    username_display = f"ID {row['id']}"
                
                txt += f"{i}. {username_display}\n"
                txt += f"   👥 Рефералов: {referral_count}\n"
                txt += f"   💰 Заработано: {total_earned:,}\n\n"
            
            await cb.message.answer(txt, parse_mode="HTML")
            await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка в top_refs_cb: {e}")
        await cb.answer("❌ Ошибка загрузки топ рефереров")

@router.callback_query(F.data == "my_profile_ref")
async def my_profile_ref_cb(cb: CallbackQuery):
    await process_profile(cb.message)
    await cb.answer()

@router.callback_query(F.data == "get_bonus")
async def get_bonus_cb(cb: CallbackQuery):
    await process_bonus(cb.message)
    await cb.answer()

@router.callback_query(F.data == "get_work")
async def get_work_cb(cb: CallbackQuery):
    await process_work(cb.message)
    await cb.answer()

@router.callback_query(F.data == "show_businesses")
async def show_businesses_cb(cb: CallbackQuery):
    await show_businesses(cb.message)
    await cb.answer()

@router.callback_query(F.data == "show_planets")
async def show_planets_cb(cb: CallbackQuery):
    await show_planets(cb.message)
    await cb.answer()

@router.callback_query(F.data == "show_mining")
async def show_mining_cb(cb: CallbackQuery):
    await show_mining_panel(cb=cb)
    await cb.answer()

@router.callback_query(F.data == "show_investments")
async def show_investments_callback(cb: CallbackQuery):
    await show_investments_panel(cb=cb)
    await cb.answer()

@router.callback_query(F.data == "show_profile")
async def show_profile_cb(cb: CallbackQuery):
    await process_profile(cb.message)
    await cb.answer()

@router.callback_query(F.data == "show_top")
async def show_top_cb(cb: CallbackQuery):
    await process_top(cb.message, cb.from_user.id)
    await cb.answer()

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

# ========== ФУНКЦИИ ИЗ ДОПОЛНЕНИЯ ==========

async def show_mining_panel(msg: Message = None, cb: CallbackQuery = None):
    """Показать красивую inline-панель майнинга - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    # Получаем ID пользователя из сообщения или callback
    if msg:
        uid = msg.from_user.id
        message_obj = msg
    elif cb:
        uid = cb.from_user.id
        message_obj = cb.message
    else:
        return
    
    # ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ДАННЫЕ ИЗ БД
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT mining_gpu_count, mining_gpu_level, bitcoin, last_mining_claim FROM users WHERE id = ?", 
                (uid,)
            )
            row = await cursor.fetchone()
            
            if row:
                user = dict(row)
            else:
                user = {'mining_gpu_count': 0, 'mining_gpu_level': 1, 'bitcoin': 0.0, 'last_mining_claim': 0}
    except Exception as e:
        logger.error(f"Ошибка получения данных для майнинга: {e}")
        user = {'mining_gpu_count': 0, 'mining_gpu_level': 1, 'bitcoin': 0.0, 'last_mining_claim': 0}
    
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    btc_price = BitcoinMining.get_bitcoin_price()
    
    current_time = int(time.time())
    last_claim = user['last_mining_claim'] or current_time
    time_passed = current_time - last_claim
    btc_mined = btc_per_hour * (time_passed / 3600)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить видеокарту", callback_data="mining_buy_gpu"),
            InlineKeyboardButton(text="⚡ Улучшить видеокарты", callback_data="mining_upgrade_gpu")
        ],
        [
            InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim"),
            InlineKeyboardButton(text="💸 Продать BTC", callback_data="mining_sell")
        ],
        [
            InlineKeyboardButton(text="📊 Обновить", callback_data="mining_refresh"),
            InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")
        ]
    ])
    
    text = f"""
⛏️ <b>МАЙНИНГ ФЕРМА</b>

📊 <b>Статистика:</b>
• 🎮 Видеокарт: <b>{user['mining_gpu_count']} шт.</b>
• ⭐ Уровень видеокарт: <b>{user['mining_gpu_level']}/5</b>
• ⚡ Хешрейт: <b>{hashrate:.1f} MH/s</b>
• ₿ BTC/час: <b>{btc_per_hour:.8f}</b>
• 💰 Курс BTC: <b>{format_money(int(btc_price))}$</b>

💰 <b>Балансы:</b>
• 💎 BTC: <b>{user.get('bitcoin', 0.0):.8f}</b>
• ⏳ Накоплено: <b>{btc_mined:.8f} BTC</b>
• 💵 Стоимость: <b>~{format_money(int(btc_mined * btc_price))}$</b>

💡 <b>Доступные действия:</b>
"""
    
    # Если это callback, редактируем существующее сообщение
    if cb:
        try:
            await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
    # Если это сообщение, отправляем новое
    elif msg:
        await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)

async def show_my_planets_panel(msg: Message = None, cb: CallbackQuery = None):
    """Показать панель 'Мои планеты' (исправленная версия)"""
    # Получаем ID пользователя из сообщения или callback
    if msg:
        uid = msg.from_user.id
        message_obj = msg
    elif cb:
        uid = cb.from_user.id
        message_obj = cb.message
    else:
        return
    
    user_planets = await get_user_planets(uid)
    
    if not user_planets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪐 Смотреть все планеты", callback_data="show_planets"),
             InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ])
        
        # Если это callback, редактируем сообщение
        if cb:
            try:
                await message_obj.edit_text("🪐 У вас пока нет планет. Купите первую планету!", parse_mode="HTML", reply_markup=keyboard)
            except:
                await message_obj.answer("🪐 У вас пока нет планет. Купите первую планету!", parse_mode="HTML", reply_markup=keyboard)
        else:
            await message_obj.reply("🪐 У вас пока нет планет. Купите первую планету!", parse_mode="HTML", reply_markup=keyboard)
        return
    
    text = "🪐 <b>МОИ ПЛАНЕТЫ</b>\n\n"
    
    keyboard_buttons = []
    for planet_id, planet_data in user_planets.items():
        if planet_id in PLANETS:
            planet_info = PLANETS[planet_id]
            
            current_time = int(time.time())
            last_collected = planet_data['last_collected'] or current_time
            time_passed = current_time - last_collected
            plasma_accumulated = int((time_passed / 3600) * planet_info['plasma_per_hour'])
            
            text += f"• <b>{planet_info['name']}</b>\n"
            text += f"  ⚡ Генерация: {planet_info['plasma_per_hour']}/час\n"
            text += f"  💎 Накоплено: ~{plasma_accumulated} плазмы\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🪐 {planet_info['name']} - Собрать",
                    callback_data=f"planet_collect_{planet_id}"
                )
            ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="planets_refresh"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    user = await get_user(uid)
    text += f"📊 <b>Общая статистика:</b>\n"
    text += f"• Всего планет: {len(user_planets)}\n"
    text += f"• Ваша плазма: {user['plasma']} единиц"
    
    # Если это callback, редактируем существующее сообщение
    if cb:
        try:
            await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
    # Если это сообщение, отправляем новое
    elif msg:
        await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)

async def show_investments_panel(msg: Message = None, cb: CallbackQuery = None):
    """Показать панель инвестиций с активными инвестициями - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    # Получаем ID пользователя
    if msg:
        uid = msg.from_user.id
        message_obj = msg
    elif cb:
        uid = cb.from_user.id
        message_obj = cb.message
    else:
        return
    
    active_investments = await get_user_investments(uid)
    
    text = "💼 <b>ИНВЕСТИЦИИ</b>\n\n"
    
    if active_investments:
        text += "📈 <b>Активные инвестиции:</b>\n"
        for i, inv in enumerate(active_investments, 1):
            investment_info = INVESTMENTS[inv['investment_id']]
            time_left = inv['end_time'] - int(time.time())
            
            if time_left <= 0:
                status = "✅ ГОТОВО"
                time_text = "Завершено"
            else:
                hours = time_left // 3600
                minutes = (time_left % 3600) // 60
                status = "⏳ АКТИВНО"
                time_text = f"Осталось: {hours}ч {minutes}м"
            
            text += f"{i}. <b>{investment_info['name']}</b>\n"
            text += f"   💰 Сумма: {format_money(inv['amount'])}\n"
            text += f"   🕒 {time_text}\n"
            text += f"   📊 {status}\n\n"
    else:
        text += "📭 <b>У вас нет активных инвестиций</b>\n\n"
    
    text += "💡 <b>Начать новую инвестицию:</b>"
    
    keyboard_buttons = []
    row = []
    for inv_id, inv in INVESTMENTS.items():
        row.append(InlineKeyboardButton(
            text=f"{inv_id}. {inv['name']}",
            callback_data=f"invest_select_{inv_id}"
        ))
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row:
        keyboard_buttons.append(row)
    
    # Добавляем кнопки для завершения активных инвестиций
    if active_investments:
        for inv in active_investments:
            if time.time() >= inv['end_time']:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"✅ Завершить {INVESTMENTS[inv['investment_id']]['name']}",
                        callback_data=f"inv_complete_{inv['id']}"
                    )
                ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="📋 Список инвестиций", callback_data="show_investments_list"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Если это callback, редактируем сообщение
    if cb:
        try:
            await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
    # Если это сообщение, отправляем новое
    elif msg:
        await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)

# ========== CALLBACK ОБРАБОТЧИКИ ИЗ ДОПОЛНЕНИЯ ==========

@router.callback_query(F.data == "mining_buy_gpu")
async def mining_buy_gpu_callback(cb: CallbackQuery):
    success, message = await buy_gpu(cb.from_user.id)
    await cb.answer(message)
    if success:
        # Даем время базе данных обновиться
        await asyncio.sleep(1)
        # ПЕРЕД показом панели обновляем данные
        await refresh_user_data(cb.from_user.id)
        await show_mining_panel(cb=cb)

@router.callback_query(F.data == "mining_upgrade_gpu")
async def mining_upgrade_gpu_callback(cb: CallbackQuery):
    success, message = await upgrade_gpu(cb.from_user.id)
    await cb.answer(message)
    if success:
        # Даем время базе данных обновиться
        await asyncio.sleep(1)
        # ПЕРЕД показом панели обновляем данные
        await refresh_user_data(cb.from_user.id)
        await show_mining_panel(cb=cb)

@router.callback_query(F.data == "mining_claim")
async def mining_claim_callback(cb: CallbackQuery):
    success, btc_mined, usd_value_or_message = await claim_mining_profit(cb.from_user.id)
    if success:
        try:
            await cb.message.edit_text(
                f"✅ <b>Получено {btc_mined:.8f} BTC ({format_money(int(usd_value_or_message))}$)</b>\n\n"
                f"⛏️ <b>МАЙНИНГ ФЕРМА</b>\n\n"
                f"💰 BTC успешно зачислены на ваш счет!\n\n"
                f"🔄 <i>Обновляю панель...</i>",
                parse_mode="HTML"
            )
        except:
            await cb.message.answer(
                f"✅ <b>Получено {btc_mined:.8f} BTC ({format_money(int(usd_value_or_message))}$)</b>\n\n"
                f"⛏️ <b>МАЙНИНГ ФЕРМА</b>\n\n"
                f"💰 BTC успешно зачислены на ваш счет!\n\n"
                f"🔄 <i>Обновляю панель...</i>",
                parse_mode="HTML"
            )
        await asyncio.sleep(2)
        await show_mining_panel(cb=cb)
        await cb.answer()
    else:
        await cb.answer(f"❌ {usd_value_or_message}")

@router.callback_query(F.data == "mining_sell")
async def mining_sell_callback(cb: CallbackQuery):
    await cb.answer("💸 Введите: продать биткоин [количество] или продать биткоин все")

@router.callback_query(F.data == "mining_refresh")
async def mining_refresh_callback(cb: CallbackQuery):
    await show_mining_panel(cb.message)
    await cb.answer("🔄 Обновлено")

@router.callback_query(F.data.startswith("planet_collect_"))
async def planet_collect_callback(cb: CallbackQuery):
    try:
        planet_id = int(cb.data.split("_")[2])
        success, amount = await collect_planet_plasma(cb.from_user.id, planet_id)
        if success:
            await cb.answer(f"✅ Собрано {amount} плазмы")
            await show_my_planets_panel(cb=cb)
        else:
            await cb.answer(f"❌ {amount}")
    except Exception as e:
        logger.error(f"Ошибка в planet_collect_callback: {e}")
        await cb.answer("❌ Ошибка сбора плазмы")

@router.callback_query(F.data.startswith("view_profile_"))
async def view_profile_callback(cb: CallbackQuery):
    """Обработка клика на профиль в топе"""
    try:
        user_id = int(cb.data.split("_")[2])
        await view_user_profile(cb.message, user_id, is_from_top=True)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка view_profile_callback: {e}")
        await cb.answer("❌ Ошибка загрузки профиля")

@router.callback_query(F.data == "planets_refresh")
async def planets_refresh_callback(cb: CallbackQuery):
    await show_my_planets_panel(cb=cb)
    await cb.answer("🔄 Обновлено")

@router.callback_query(F.data.startswith("invest_select_"))
async def invest_select_callback(cb: CallbackQuery):
    try:
        investment_id = int(cb.data.split("_")[2])
        if 1 <= investment_id <= len(INVESTMENTS):
            inv = INVESTMENTS[investment_id]
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💰 1M", callback_data=f"invest_start_{investment_id}_1000000"),
                    InlineKeyboardButton(text="💰 10M", callback_data=f"invest_start_{investment_id}_10000000"),
                    InlineKeyboardButton(text="💰 100M", callback_data=f"invest_start_{investment_id}_100000000")
                ],
                [
                    InlineKeyboardButton(text="💰 1B", callback_data=f"invest_start_{investment_id}_1000000000"),
                    InlineKeyboardButton(text="💰 5B", callback_data=f"invest_start_{investment_id}_5000000000")
                ],
                [InlineKeyboardButton(text="💰 Своя сумма", callback_data=f"invest_custom_{investment_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="show_investments")]
            ])
            
            duration_hours = inv['duration'] // 3600
            duration_minutes = (inv['duration'] % 3600) // 60
            
            text = f"""
💼 <b>Начать инвестицию: {inv['name']}</b>

📊 <b>Параметры:</b>
• Длительность: {duration_hours}ч {duration_minutes}м
• Минимальная сумма: {format_money(inv['min_amount'])}
• Шанс успеха: {int(inv['success_rate'] * 100)}%
• Прибыль при успехе: +{int((inv['profit_multiplier'] - 1) * 100)}%

💰 <b>Выберите сумму:</b>
"""
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await cb.answer()
        else:
            await cb.answer("❌ Неверный ID инвестиции")
    except Exception as e:
        logger.error(f"Ошибка в invest_select_callback: {e}")
        await cb.answer("❌ Ошибка")

@router.callback_query(F.data.startswith("invest_start_") & ~F.data.contains("select"))
async def invest_start_callback(cb: CallbackQuery):
    """Обработка начала инвестиции с конкретной суммой - только для invest_start_"""
    try:
        # callback_data format: "invest_start_1_1000000"
        parts = cb.data.split("_")
        
        logger.info(f"invest_start_callback received: {cb.data}, parts: {parts}")
        
        # Должно быть 4 части: ["invest", "start", "id", "amount"]
        if len(parts) != 4:
            logger.error(f"Неверный формат: {cb.data}, ожидается 'invest_start_id_amount'")
            await cb.answer("❌ Ошибка формата кнопки")
            return
            
        investment_id = int(parts[2])  # parts[0]="invest", parts[1]="start", parts[2]="1", parts[3]="1000000"
        amount = int(parts[3])
        
        logger.info(f"Начинаем инвестицию: user={cb.from_user.id}, inv_id={investment_id}, amount={amount}")
        
        success, message = await start_investment(cb.from_user.id, investment_id, amount)
        
        if success:
            await cb.answer("✅ Инвестиция начата!")
            await show_investments_panel(cb=cb)
        else:
            await cb.answer(f"❌ {message}")
            
    except ValueError as e:
        logger.error(f"Ошибка парсинга чисел в invest_start_callback: {e}, data: {cb.data}")
        await cb.answer("❌ Ошибка: неверный формат суммы")
    except Exception as e:
        logger.error(f"Ошибка в invest_start_callback: {e}")
        await cb.answer("❌ Ошибка начала инвестиции")

@router.callback_query(F.data.startswith("inv_complete_"))
async def invest_complete_callback(cb: CallbackQuery):
    try:
        investment_db_id = int(cb.data.split("_")[2])
        success, message = await complete_investment(cb.from_user.id, investment_db_id)
        await cb.answer(message)
        if success:
            await show_investments_panel(cb.message)
    except Exception as e:
        logger.error(f"Ошибка в invest_complete_callback: {e}")
        await cb.answer("❌ Ошибка завершения")

@router.callback_query(F.data == "show_investments")
async def show_investments_callback(cb: CallbackQuery):
    await show_investments_panel(cb.message)
    await cb.answer()

@router.callback_query(F.data == "show_investments_list")
async def show_investments_list_callback(cb: CallbackQuery):
    await show_investments(cb.message)
    await cb.answer()

# ========== ЗАПУСК ==========
async def main():
    await init_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.include_router(router)  # ← ВАЖНЕЕ ВСЕГО

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info(f"✅ Бот запущен!")
    logger.info("🎯 Теперь команды работают И С / И БЕЗ / !")
    logger.info("🏢 ДОБАВЛЕНЫ БИЗНЕСЫ: 13 бизнесов с системой продуктов!")
    logger.info("🪐 ДОБАВЛЕНЫ ПЛАНЕТЫ: 5 планет с генерацией плазмы!")
    logger.info("⛏️ ДОБАВЛЕН МАЙНИНГ: Майнинг ферма с видеокартами и BTC!")
    logger.info("💼 ДОБАВЛЕНЫ ИНВЕСТИЦИИ: 5 видов инвестиций с риском!")
    logger.info("🎰 ДОБАВЛЕНЫ АЗАРТНЫЕ ИГРЫ: Монетка, Кости, Слоты, Рулетка, Блэкджек!")
    logger.info("💰 Бонус: 5-20М каждый час с прогресс-баром!")
    logger.info("💼 Работа: 1-5М каждые 30 секунд!")
    logger.info("🎁 СТАРТОВЫЙ БОНУС: 10.000.000!")
    logger.info("👥 РЕФЕРАЛЬНАЯ СИСТЕМА: 30-100М за каждого друга!")
    logger.info("📱 Полная поддержка сокращений: 1к, 10кк, 100кк, 1.5к и т.д.")
    logger.info("🎯 ДОБАВЛЕНА КОМАНДА 'МОЙ БИЗНЕС' с inline-кнопками!")
    logger.info("💼 ИНВЕСТИЦИИ: Теперь 'начать инвестицию [id]' показывает панель с выбором суммы!")
    logger.info("⛏️ ДОБАВЛЕНА ПАНЕЛЬ МАЙНИНГА!")
    logger.info("🪐 ДОБАВЛЕНА ПАНЕЛЬ 'МОИ ПЛАНЕТЫ'!")
    logger.info("💼 ДОБАВЛЕНА ПАНЕЛЬ ИНВЕСТИЦИЙ!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
