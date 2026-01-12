import asyncio
import aiosqlite
import random
import time
import logging
import hashlib
import html
import math
import re
import secrets
import shutil
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Dice
from aiogram.exceptions import TelegramBadRequest
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ChatType
import sys
import os
import db
import warnings
# Suppress aiohttp warnings
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")
# Suppress asyncio unclosed resource warnings
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
LOCK_FILE = "murasaki_bot.lock"
def check_single_instance():
    """Проверяет, что бот запущен только один раз"""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            if os.name == 'nt':
                import psutil
                if psutil.pid_exists(pid):
                    print(f"❌ Бот уже запущен (PID: {pid})!")
                    print("Закройте предыдущий экземпляр и удалите файл murasaki_bot.lock")
                    sys.exit(1)
            else:
                import signal
                try:
                    os.kill(pid, 0)
                    print(f"❌ Бот уже запущен (PID: {pid})!")
                    print("Закройте предыдущий экземпляр и удалите файл murasaki_bot.lock")
                    sys.exit(1)
                except OSError:
                    pass
        except:
            pass
        finally:
            # Создаем lock-файл с PID текущего процесса
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
    # Удаляем lock-файл при выходе
    import atexit
    atexit.register(cleanup_lock_file)
def cleanup_lock_file():
    """Удаляет lock-файл при завершении"""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except:
            pass
# Вызываем проверку в самом начале
check_single_instance()
print("🔥 ФАЙЛ ЗАПУЩЕН")
# ========== НАСТРОЙКИ ==========
TOKEN = "8424494037:AAHrtN5irOGb7SzLQicLHCPQt9p5o8FF_sA"
ADMIN_IDS = {1162907446}
CREATOR_ID = 1162907446
# ========== НАСТРОЙКА ПУТИ К БД (RAILWAY VOLUMES) ==========
def get_db_path():
    """Определяет путь к БД в зависимости от окружения"""
    # Если запущено на Railway (проверяем переменную окружения)
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Путь к volume на Railway
        data_dir = '/data'
        # Создаем директорию если её нет
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
                print(f"✅ Создана директория: {data_dir}")
            except Exception as e:
                print(f"⚠️ Не удалось создать {data_dir}: {e}")
                # Используем текущую директорию как fallback
                return "murasaki_NEW.db"
        db_path = os.path.join(data_dir, 'murasaki_NEW.db')
        print(f"🗄️ Railway БД: {db_path}")
        return db_path
    else:
        # Локальная разработка
        print("💻 Локальная БД: murasaki_NEW.db")
        return "murasaki_NEW.db"
DB_PATH = get_db_path()
HELP_COMMANDS = {
    "Профиль и старт": [
        ("профиль", "ваш профиль"),
        ("страна", "информация о стране"),
        ("выбор страны", "выбрать стартовую страну"),
    ],
    "Заработок": [
        ("бонус", "бонус по кд"),
        ("работа", "активный заработок"),
        ("собрать доход", "доход со страны"),
    ],
    "Экономика": [
        ("улучшения", "улучшения страны"),
        ("бизнесы", "бизнесы внутри страны"),
        ("налоги", "управление налогами"),
        ("экономика", "статус экономики"),
    ],
    "Армия и войны": [
        ("армия", "управление армией"),
        ("оружие", "магазин оружия"),
        ("техника", "магазин техники"),
        ("войны", "список войн"),
        ("война", "текущая война"),
    ],
    "Кланы": [
        ("клан", "информация о клане"),
        ("создать клан", ""),
        ("клан склад", ""),
        ("клан выйти", ""),
    ],
    "Боссы": [
        ("боссы", "список боссов"),
        ("босс", "текущий босс"),
        ("атака босса", ""),
    ],
    "Космос": [
        ("космос", "меню космоса"),
        ("экспедиции", ""),
        ("колонии", ""),
        ("технологии", ""),
    ],
    "Кредиты": [
        ("кредиты", ""),
        ("кредит запросить", ""),
        ("кредит платить", ""),
        ("кредит сигма", ""),
    ],
    "Развлечения": [
        ("казино", ""),
        ("рулетка", ""),
    ],
    "Прочее": [
        ("хелп", "список команд"),
    ],
    "???????": [
        ("??????? ?????? [???-??|???]", "??????? ?????? ?? ??????"),
        ("??????? ???????? [???-??|???]", "??????? ???????? ?? ??????"),
        ("??????? ????????? [???-??|???]", "??????? ????????? ?? ??????"),
    ],
}
def build_help_text(is_admin: bool) -> str:
    lines = []
    for section, items in HELP_COMMANDS.items():
        lines.append(f"📌 {section}:")
        for command, description in items:
            if description:
                lines.append(f"- {command} — {description}")
            else:
                lines.append(f"- {command}")
        lines.append("")
    if is_admin:
        lines.append("Для админ-команд используйте: админ")
    return "\n".join(lines).strip()
# ========== КОНФИГ СТАРТОВЫХ СТРАН ==========
START_COUNTRIES = [
    {'code': 'arcadia', 'name': 'Аркадия', 'description': '+5% налоги', 'bonus_type': 'tax_rate', 'bonus_value': 0.05},
    {'code': 'aurelion', 'name': 'Аурелион', 'description': '+5% доход бизнесов', 'bonus_type': 'business_income', 'bonus_value': 0.05},
    {'code': 'zlatoria', 'name': 'Златория', 'description': '+10% стартовая казна', 'bonus_type': 'start_treasury', 'bonus_value': 0.10},
    {'code': 'valoria', 'name': 'Валория', 'description': '-5% стоимость апгрейдов', 'bonus_type': 'upgrade_cost', 'bonus_value': -0.05},
    {'code': 'merkatia', 'name': 'Меркатия', 'description': '+5% торговля', 'bonus_type': 'trade_bonus', 'bonus_value': 0.05},
    {'code': 'lumenсия', 'name': 'Люменсия', 'description': '+10% прирост населения', 'bonus_type': 'population_growth', 'bonus_value': 0.10},
    {'code': 'sancteria', 'name': 'Санктерия', 'description': '+10 счастье', 'bonus_type': 'happiness', 'bonus_value': 10},
    {'code': 'eventia', 'name': 'Эвентия', 'description': '-10% негативные ивенты', 'bonus_type': 'event_resistance', 'bonus_value': -0.10},
    {'code': 'novalis', 'name': 'Новалис', 'description': '+10 грамотность', 'bonus_type': 'literacy', 'bonus_value': 10},
    {'code': 'harmonia', 'name': 'Гармония', 'description': '-10% преступность', 'bonus_type': 'crime', 'bonus_value': -10},
    {'code': 'noxara', 'name': 'Ноксара', 'description': '+5% боевая сила', 'bonus_type': 'military_power', 'bonus_value': 0.05},
    {'code': 'kratosia', 'name': 'Кратосия', 'description': '+10% лимит людей', 'bonus_type': 'population_cap', 'bonus_value': 0.10},
    {'code': 'fortex', 'name': 'Фортекс', 'description': '-10% потери армии', 'bonus_type': 'army_losses', 'bonus_value': -0.10},
    {'code': 'bastion', 'name': 'Бастион', 'description': '+5% защита', 'bonus_type': 'defense', 'bonus_value': 0.05},
    {'code': 'dominia', 'name': 'Доминия', 'description': '+5% урон по боссам', 'bonus_type': 'boss_damage', 'bonus_value': 0.05},
    {'code': 'technolis', 'name': 'Технолис', 'description': '+10% эффективность зданий', 'bonus_type': 'building_efficiency', 'bonus_value': 0.10},
    {'code': 'industria', 'name': 'Индустрия', 'description': '+5% рабочие места', 'bonus_type': 'jobs', 'bonus_value': 0.05},
    {'code': 'logistar', 'name': 'Логистар', 'description': '-10% upkeep армии', 'bonus_type': 'army_upkeep', 'bonus_value': -0.10},
    {'code': 'energolia', 'name': 'Энерголия', 'description': '+10% энергетические бонусы', 'bonus_type': 'energy_bonus', 'bonus_value': 0.10},
    {'code': 'megapolis', 'name': 'Мегаполис', 'description': '+10% population_cap', 'bonus_type': 'population_cap', 'bonus_value': 0.10},
    {'code': 'astrea', 'name': 'Астрея', 'description': '+10% плазма', 'bonus_type': 'plasma_bonus', 'bonus_value': 0.10},
    {'code': 'orbiton', 'name': 'Орбитон', 'description': '+5% урон по боссам', 'bonus_type': 'boss_damage', 'bonus_value': 0.05},
    {'code': 'singula', 'name': 'Сингуля', 'description': '+5% шанс уникалок', 'bonus_type': 'unique_chance', 'bonus_value': 0.05},
    {'code': 'kosmarium', 'name': 'Космариум', 'description': '-10% космо-апгрейды', 'bonus_type': 'cosmo_upgrades', 'bonus_value': -0.10},
    {'code': 'nova-prime', 'name': 'Нова-Прайм', 'description': '+5% космо-бонусы', 'bonus_type': 'cosmo_bonus', 'bonus_value': 0.05},
    {'code': 'equilibrium', 'name': 'Эквилибриум', 'description': '+3% ко всем доходам', 'bonus_type': 'all_income', 'bonus_value': 0.03},
    {'code': 'valdheim', 'name': 'Вальдхейм', 'description': '+5 стабильность', 'bonus_type': 'stability', 'bonus_value': 5},
    {'code': 'civilis', 'name': 'Цивилис', 'description': '+5 счастье и грамотность', 'bonus_type': 'happiness_literacy', 'bonus_value': 5},
    {'code': 'progressa', 'name': 'Прогресса', 'description': '+5% апгрейды и доход', 'bonus_type': 'upgrades_income', 'bonus_value': 0.05},
    {'code': 'alliance', 'name': 'Альянсия', 'description': '+3% доход и сила', 'bonus_type': 'income_power', 'bonus_value': 0.03},
]
# Особая страна для создателя
CREATOR_COUNTRY = {
    'code': 'sigma_empire',
    'name': 'Империя Великого Сигмы Ярика',
    'description': '+15% доход, +15% боевая сила, +20% урон по боссам, +20 стабильность, +20 счастье',
    'bonus_type': 'creator_bonuses',
    'bonus_value': {'income': 0.15, 'military_power': 0.15, 'boss_damage': 0.20, 'stability': 20, 'happiness': 20}
}
# ========== КОНФИГ ТИТУЛОВ ==========
TITLES_CONFIG = [
    {'code': 'iron_ruler', 'name': 'Железный Правитель', 'description': '30 дней без бунтов', 'bonus_type': 'income', 'bonus_value': 0.02, 'permanent': 1},
    {'code': 'military_maniac', 'name': 'Военный Маньяк', 'description': '50 побед в войнах', 'bonus_type': 'combat', 'bonus_value': 0.02, 'permanent': 1},
    {'code': 'casino_magnate', 'name': 'Казино-Магнат', 'description': 'оборот ставок > 10B', 'bonus_type': 'casino', 'bonus_value': 0.01, 'permanent': 1},
    {'code': 'sigma_killer', 'name': 'Убийца Сигмы', 'description': 'победа над Жирным Сигмой Яриком', 'bonus_type': 'boss', 'bonus_value': 0.03, 'permanent': 1},
    {'code': 'wealthy_trader', 'name': 'Богатый Торговец', 'description': 'баланс > 100B', 'bonus_type': 'income', 'bonus_value': 0.01, 'permanent': 0},
    {'code': 'plasma_master', 'name': 'Мастер Плазмы', 'description': 'плазма > 1M', 'bonus_type': 'income', 'bonus_value': 0.015, 'permanent': 1},
    {'code': 'wealthy_trader', 'name': 'Богатый Торговец', 'description': 'баланс > 100B', 'bonus_type': 'income', 'bonus_value': 0.01, 'permanent': 0},
    {'code': 'space_pioneer', 'name': '\u041f\u0435\u0440\u0432\u043e\u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0442\u0435\u043b\u044c', 'description': '\u043f\u0435\u0440\u0432\u043e\u0435 \u043a\u043e\u0441\u043c\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u0435', 'bonus_type': 'prestige', 'bonus_value': 1, 'permanent': 1},
    {'code': 'void_conqueror', 'name': '\u041f\u043e\u043a\u043e\u0440\u0438\u0442\u0435\u043b\u044c \u0411\u0435\u0437\u0434\u043d\u044b', 'description': '\u043c\u043d\u043e\u0433\u043e \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u0439 \u0432 \u043a\u043e\u0441\u043c\u043e\u0441\u0435', 'bonus_type': 'prestige', 'bonus_value': 2, 'permanent': 1},
    {'code': 'sigma_witness', 'name': '\u0412\u0438\u0434\u0435\u0432\u0448\u0438\u0439 \u0421\u0438\u0433\u043c\u0443', 'description': '\u043e\u0442\u043a\u0440\u044b\u0442\u0438\u0435 \u0441\u0438\u0433\u043c\u0430-\u0430\u043d\u043e\u043c\u0430\u043b\u0438\u0438', 'bonus_type': 'prestige', 'bonus_value': 3, 'permanent': 1},
    {'code': 'referral_guru', 'name': 'Реферальный Гуру', 'description': '100+ рефералов', 'bonus_type': 'income', 'bonus_value': 0.02, 'permanent': 1},
    {'code': 'mining_tycoon', 'name': 'Майнинг-Магнат', 'description': '100+ видеокарт', 'bonus_type': 'income', 'bonus_value': 0.01, 'permanent': 1},
    {'code': 'business_empire', 'name': 'Империя Бизнеса', 'description': 'Все бизнесы страны макс уровня', 'bonus_type': 'income', 'bonus_value': 0.025, 'permanent': 1},
    {'code': 'war_hero', 'name': 'Герой Войны', 'description': '100+ побед в войнах', 'bonus_type': 'combat', 'bonus_value': 0.03, 'permanent': 1},
    {'code': 'debtor', 'name': '\u0414\u043e\u043b\u0436\u043d\u0438\u043a', 'description': '\u0434\u0435\u0444\u043e\u043b\u0442 \u043f\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0443', 'bonus_type': 'income', 'bonus_value': -0.03, 'permanent': 1},
]
# ========== КОНФИГ МИРОВЫХ СОБЫТИЙ ==========
WORLD_EVENTS_CONFIG = [
    {'code': 'economic_crisis', 'name': 'Экономический кризис', 'description': 'Все доходы снижены на 20%', 'effect_type': 'income', 'effect_value': -0.20, 'duration_hours': 48},
    {'code': 'war_era', 'name': 'Эра войн', 'description': 'Урон в войнах увеличен на 10%', 'effect_type': 'war_damage', 'effect_value': 0.10, 'duration_hours': 72},
    {'code': 'scientific_breakthrough', 'name': 'Научный прорыв', 'description': 'Производство плазмы увеличено на 20%', 'effect_type': 'plasma', 'effect_value': 0.20, 'duration_hours': 96},
    {'code': 'sigma_week', 'name': 'Неделя Сигмы', 'description': 'Боссы сильнее, но дают больше лута', 'effect_type': 'boss_buff', 'effect_value': 0.15, 'duration_hours': 168},
    {'code': 'golden_age', 'name': 'Золотой век', 'description': 'Все доходы увеличены на 15%', 'effect_type': 'income', 'effect_value': 0.15, 'duration_hours': 120},
    {'code': 'dark_times', 'name': 'Темные времена', 'description': 'Шанс негативных событий увеличен', 'effect_type': 'event_chance', 'effect_value': 0.20, 'duration_hours': 60},
    {'code': 'peace_era', 'name': 'Эра мира', 'description': 'Стабильность стран выше', 'effect_type': 'stability', 'effect_value': 0.10, 'duration_hours': 84},
    {'code': 'mining_boom', 'name': 'Бум майнинга', 'description': 'Эффективность майнинга +25%', 'effect_type': 'mining', 'effect_value': 0.25, 'duration_hours': 72},
]
# ========== БИЗНЕСЫ СТРАНЫ ==========
BUSINESS_DEFS = {
    "giga_latte": {
        "name": "Сеть кофеен «Гига Латте»",
        "base_cost": 40_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 37_500_000,
        "income_max_day": 52_500_000,
        "jobs": 120,
        "upkeep_day": 0
    },
    "nextgen_arena": {
        "name": "Киберспорт-арена «Некстген»",
        "base_cost": 60_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 52_500_000,
        "income_max_day": 75_000_000,
        "jobs": 160,
        "upkeep_day": 0
    },
    "hype_media": {
        "name": "Студия контента «Хайп Медиа»",
        "base_cost": 75_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 67_500_000,
        "income_max_day": 97_500_000,
        "jobs": 180,
        "upkeep_day": 0
    },
    "sprint_hub": {
        "name": "Логистический хаб «Спринт»",
        "base_cost": 90_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 82_500_000,
        "income_max_day": 112_500_000,
        "jobs": 220,
        "upkeep_day": 0
    },
    "cashflow_fintech": {
        "name": "Финтех-сервис «КэшФлоу»",
        "base_cost": 125_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 105_000_000,
        "income_max_day": 142_500_000,
        "jobs": 260,
        "upkeep_day": 0
    },
    "aero_pro": {
        "name": "Фабрика дронов «Аэро-Про»",
        "base_cost": 175_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 135_000_000,
        "income_max_day": 180_000_000,
        "jobs": 320,
        "upkeep_day": 0
    },
    "lifelab_bio": {
        "name": "Биотех-центр «ЛайфЛаб»",
        "base_cost": 250_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 180_000_000,
        "income_max_day": 240_000_000,
        "jobs": 380,
        "upkeep_day": 0
    },
    "skymarsh_spaceport": {
        "name": "Космопорт «СкайМарш»",
        "base_cost": 400_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 270_000_000,
        "income_max_day": 360_000_000,
        "jobs": 480,
        "upkeep_day": 0
    },
    "synthesis_ai": {
        "name": "ИИ-холдинг «Синтез»",
        "base_cost": 600_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 360_000_000,
        "income_max_day": 480_000_000,
        "jobs": 600,
        "upkeep_day": 0
    },
    "nox_datacenters": {
        "name": "Сеть дата-центров «Нокс»",
        "base_cost": 900_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 480_000_000,
        "income_max_day": 675_000_000,
        "jobs": 720,
        "upkeep_day": 0
    },
    "bot_owner": {
        "name": "Статус «Хозяин бота»",
        "base_cost": 1_500_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 750_000_000,
        "income_max_day": 1_050_000_000,
        "jobs": 900,
        "upkeep_day": 0
    },
    "fat_sigma_owner": {
        "name": "Статус «Хозяин Жирного Сигмы Ярика»",
        "base_cost": 3_000_000_000,
        "max_level": 1,
        "income_bonus": 0.0,
        "income_min_day": 1_350_000_000,
        "income_max_day": 1_950_000_000,
        "jobs": 1200,
        "upkeep_day": 0
    }
}
LEGACY_BUSINESS_DEFS = {
    1: {"price": 100_000, "upgrade_multiplier": 1.5},
    2: {"price": 1_000_000, "upgrade_multiplier": 1.5},
    3: {"price": 5_000_000, "upgrade_multiplier": 1.5},
    4: {"price": 25_000_000, "upgrade_multiplier": 1.5},
    5: {"price": 100_000_000, "upgrade_multiplier": 1.5},
    6: {"price": 500_000_000, "upgrade_multiplier": 1.5},
    7: {"price": 2_000_000_000, "upgrade_multiplier": 1.5},
    8: {"price": 10_000_000_000, "upgrade_multiplier": 1.5},
    9: {"price": 50_000_000_000, "upgrade_multiplier": 1.5},
    10: {"price": 200_000_000_000, "upgrade_multiplier": 1.5},
    11: {"price": 1_000_000_000_000, "upgrade_multiplier": 1.5},
    12: {"price": 50_000_000, "upgrade_multiplier": 1.5},
    13: {"price": 30_000_000, "upgrade_multiplier": 1.5}
}
# ========== КОНФИГ СПЕЦИАЛИЗАЦИЙ СТРАНЫ ==========
COUNTRY_SPECIALIZATIONS = {
    'military': {
        'name': 'Военная',
        'description': 'Фокус на военной мощи',
        'bonuses': [
            {'type': 'combat_power', 'value': 0.10, 'description': '+10% боевой силы'},
        ],
        'penalties': [
            {'type': 'income', 'value': -0.05, 'description': '-5% дохода'},
        ]
    },
    'economic': {
        'name': 'Экономическая',
        'description': 'Фокус на экономическом развитии',
        'bonuses': [
            {'type': 'income', 'value': 0.10, 'description': '+10% дохода'},
            {'type': 'jobs', 'value': 0.05, 'description': '+5% рабочих мест'},
        ],
        'penalties': [
            {'type': 'happiness', 'value': -5, 'description': '-5 счастья'},
        ]
    },
    'science': {
        'name': 'Научная',
        'description': 'Фокус на исследованиях и технологиях',
        'bonuses': [
            {'type': 'literacy', 'value': 10, 'description': '+10 грамотности'},
            {'type': 'research_speed', 'value': 0.15, 'description': '+15% скорость исследований'},
        ],
        'penalties': [
            {'type': 'stability', 'value': -5, 'description': '-5 стабильности'},
        ]
    },
    'social': {
        'name': 'Социальная',
        'description': 'Фокус на благополучии населения',
        'bonuses': [
            {'type': 'happiness', 'value': 10, 'description': '+10 счастья'},
            {'type': 'population_growth', 'value': 0.10, 'description': '+10% прирост населения'},
        ],
        'penalties': [
            {'type': 'crime', 'value': 5, 'description': '+5 преступности'},
        ]
    }
}
SPECIALIZATION_CHANGE_COOLDOWN = 7 * 24 * 3600  # 7 дней в секундах
crash_games = {}  # {user_id: {"active": bool, "message_id": int, "bet": int, "multiplier": float, "crashed": bool}}
# in-memory throttle for auto-plasma accrual: {user_id: last_tick_timestamp}
last_plasma_tick = {}
# ========== ВОЙНЫ ==========
WAR_MIN_PEOPLE_START = 1000
WAR_MIN_PEOPLE_ACTIVE = 300
WAR_ROUND_INTERVAL = 5 * 60
WAR_MAX_ROUNDS = 10
WAR_COOLDOWN = 6 * 60 * 60
WAR_MAX_LAZY_ROUNDS = 3
WAR_TRIBUTE_CAP = 30_000_000
WAR_TRIBUTE_PCT_RANGE = (0.05, 0.10)
CREDIT_MIN_AMOUNT = 100_000
CREDIT_MAX_AMOUNT = 1_000_000_000
CREDIT_MIN_INTEREST_PCT = 1
CREDIT_MAX_INTEREST_PCT = 30
CREDIT_MIN_DAYS = 1
CREDIT_MAX_DAYS = 14
CREDIT_MIN_STABILITY = 40
CREDIT_SIGMA_MAX_AMOUNT = 250_000_000
# ========== SPACE CONFIG ==========
SPACE_MAX_ACTIVE_EXPEDITIONS_BASE = 1
SPACE_MAX_COLONIES = 3
SPACE_EXPEDITION_TYPES = {
    'cheap': {
        'name': 'дешёвая',
        'min_hours': 1,
        'max_hours': 1,
        'base_fail': 0.15,
        'discovery_chance': 0.15,
        'loot': {'plasma': (1, 3), 'plutonium': (0, 1), 'artifacts': (0, 1), 'tech_data': (0, 1)}
    },
    'medium': {
        'name': 'средняя',
        'min_hours': 1,
        'max_hours': 1,
        'base_fail': 0.30,
        'discovery_chance': 0.30,
        'loot': {'plasma': (3, 7), 'plutonium': (1, 3), 'artifacts': (0, 2), 'tech_data': (1, 2)}
    },
    'elite': {
        'name': 'элитная',
        'min_hours': 1,
        'max_hours': 1,
        'base_fail': 0.45,
        'discovery_chance': 0.50,
        'loot': {'plasma': (8, 15), 'plutonium': (3, 6), 'artifacts': (1, 4), 'tech_data': (2, 4)}
    }
}
SPACE_DISCOVERY_TYPES = [
    {'type': 'planet', 'rarity': 'rare', 'weight': 35, 'description': 'Обнаружена новая планета с потенциалом колонизации.'},
    {'type': 'anomaly', 'rarity': 'rare', 'weight': 25, 'description': 'Зафиксирована аномалия с неизученным полем.'},
    {'type': 'derelict_station', 'rarity': 'epic', 'weight': 18, 'description': 'Найдена заброшенная станция с фрагментами данных.'},
    {'type': 'ancient_ruins', 'rarity': 'epic', 'weight': 15, 'description': 'Следы древней цивилизации. Опасно, но очень интересно.'},
    {'type': 'sigma_anomaly', 'rarity': 'legendary', 'weight': 7, 'description': 'Сигма-аномалия. Что-то непонятное наблюдает вас.'}
]
SPACE_COLONY_TYPES = {
    'ice': {'name': 'ледяная', 'bonus_type': 'plasma', 'yield_plasma': 4, 'yield_plutonium': 0, 'yield_artifacts': 0, 'yield_tech': 0},
    'volcanic': {'name': 'вулканическая', 'bonus_type': 'plutonium', 'yield_plasma': 0, 'yield_plutonium': 3, 'yield_artifacts': 0, 'yield_tech': 0},
    'anomalous': {'name': 'аномальная', 'bonus_type': 'boss_damage', 'yield_plasma': 1, 'yield_plutonium': 1, 'yield_artifacts': 1, 'yield_tech': 0},
    'ancient': {'name': 'древняя', 'bonus_type': 'unique_chance', 'yield_plasma': 0, 'yield_plutonium': 1, 'yield_artifacts': 2, 'yield_tech': 1}
}
SPACE_TECH_CONFIG = [
    {'tech_code': 'nav_array', 'name': 'Навигационный маяк', 'description': 'Снижает риск экспедиций', 'cost_plasma': 60, 'cost_plutonium': 5},
    {'tech_code': 'defense_matrix', 'name': 'Защитный матричный блок', 'description': 'Снижает потери в экспедициях', 'cost_plasma': 90, 'cost_plutonium': 10},
    {'tech_code': 'ai_core', 'name': 'Ядро ИИ', 'description': 'Улучшает лут', 'cost_plasma': 120, 'cost_plutonium': 15},
    {'tech_code': 'anomaly_scanner', 'name': 'Сканер аномалий', 'description': 'Больше открытий', 'cost_plasma': 140, 'cost_plutonium': 20}
]
CREDIT_SIGMA_INTEREST_PCT = 15
CREDIT_SIGMA_DAYS = 7
CREDIT_DEFAULT_STABILITY_PENALTY = 10
CREDIT_DEFAULT_TAX_PENALTY = 0.02
CREDIT_DEFAULT_TREASURY_PENALTY_PCT = 0.05
SIGMA_DEFAULT_STABILITY_PENALTY = 20
SIGMA_DEFAULT_TAX_PENALTY = 0.04
SIGMA_DEFAULT_TREASURY_PENALTY_PCT = 0.10
WAR_LOSS_RANGES = {
    "winner": {"people": (0.04, 0.08), "weapons": (0.02, 0.05), "tech": (0.01, 0.02)},
    "loser": {"people": (0.08, 0.14), "weapons": (0.05, 0.09), "tech": (0.02, 0.04)},
    "draw": {"people": (0.06, 0.11), "weapons": (0.035, 0.07), "tech": (0.015, 0.03)},
}
# pending war confirmations: {user_id: {"token": str, "attacker_country_id": int, "defender_country_id": int, "expires_at": int}}
war_challenges = {}
# ========== КОНФИГ ЗДАНИЙ СТРАНЫ ==========
BUILDING_CONFIG = {
    'parks': {
        'name': 'Парки',
        'max_level': 10,
        'base_cost': 1000000,
        'jobs_provided': 200,
        'effects': {'income_bonus': 5, 'stability_bonus': 2, 'happiness_bonus': 5, 'literacy_bonus': 1}
    },
    'police': {
        'name': 'Полиция',
        'max_level': 10,
        'base_cost': 1500000,
        'jobs_provided': 300,
        'effects': {'stability_bonus': 3, 'raid_protection': 10, 'crime_reduction': 10}
    },
    'court': {
        'name': 'Суд',
        'max_level': 10,
        'base_cost': 2000000,
        'jobs_provided': 100,
        'effects': {'stability_bonus': 4, 'income_bonus': 3, 'crime_reduction': 5}
    },
    'education': {
        'name': 'Образование',
        'max_level': 10,
        'base_cost': 2500000,
        'jobs_provided': 400,
        'effects': {'income_bonus': 8, 'people_limit_add': 50, 'literacy_bonus': 10}
    },
    'hospital': {
        'name': 'Больница',
        'max_level': 10,
        'base_cost': 3000000,
        'jobs_provided': 250,
        'effects': {'stability_bonus': 5, 'people_limit_add': 30, 'happiness_bonus': 3, 'hospital_bonus': 0.1}
    },
    'school': {
        'name': 'Школа',
        'max_level': 10,
        'base_cost': 2200000,
        'jobs_provided': 350,
        'effects': {'literacy_bonus': 8, 'happiness_bonus': 2, 'people_limit_add': 40}
    },
    'fire_department': {
        'name': 'Пожарная',
        'max_level': 10,
        'base_cost': 1800000,
        'jobs_provided': 150,
        'effects': {'stability_bonus': 2, 'fire_damage_reduction': 20, 'happiness_bonus': 1}
    },
    'tax_office': {
        'name': 'Налоговая',
        'max_level': 10,
        'base_cost': 1800000,
        'jobs_provided': 120,
        'effects': {'income_bonus': 12}
    },
    'logistics_hub': {
        'name': 'Логистический хаб',
        'max_level': 10,
        'base_cost': 4000000,
        'jobs_provided': 500,
        'effects': {'income_bonus': 10, 'upkeep_reduction': 5}
    },
    'industrial_complex': {
        'name': 'Промышленный комплекс',
        'max_level': 10,
        'base_cost': 5000000,
        'jobs_provided': 800,
        'effects': {'income_bonus': 15, 'tech_limit_add': 5}
    },
    'development_bank': {
        'name': 'Банк развития',
        'max_level': 10,
        'base_cost': 3500000,
        'jobs_provided': 200,
        'effects': {'income_bonus': 7, 'stability_bonus': 3}
    },
    'trade_port': {
        'name': 'Торговый порт',
        'max_level': 10,
        'base_cost': 4500000,
        'jobs_provided': 600,
        'effects': {'income_bonus': 13}
    },
    'power_grid': {
        'name': 'Энергосеть',
        'max_level': 10,
        'base_cost': 2800000,
        'jobs_provided': 180,
        'effects': {'income_bonus': 6, 'stability_bonus': 2}
    },
    'nuclear_plant': {
        'name': 'АЭС',
        'max_level': 10,
        'base_cost': 6000000,
        'jobs_provided': 150,
        'effects': {'income_bonus': 20, 'stability_bonus': -5}
    },
    'roads': {
        'name': 'Дороги',
        'max_level': 10,
        'base_cost': 3200000,
        'jobs_provided': 100,
        'effects': {'income_bonus': 4, 'stability_bonus': 3, 'vehicle_limit_add': 10}
    },
    'airport': {
        'name': 'Аэропорт',
        'max_level': 10,
        'base_cost': 5500000,
        'jobs_provided': 400,
        'effects': {'income_bonus': 9, 'vehicle_limit_add': 5}
    },
    'internet': {
        'name': 'Интернет',
        'max_level': 10,
        'base_cost': 3800000,
        'jobs_provided': 80,
        'effects': {'income_bonus': 11, 'literacy_bonus': 3, 'happiness_bonus': 2}
    },
    'barracks': {
        'name': 'Казармы',
        'max_level': 10,
        'base_cost': 2200000,
        'jobs_provided': 250,
        'effects': {'combat_bonus': 5, 'people_limit_add': 20}
    },
    'miltech_center': {
        'name': 'Воентех центр',
        'max_level': 10,
        'base_cost': 5500000,
        'jobs_provided': 300,
        'effects': {'combat_bonus': 8, 'tech_limit_add': 3}
    },
    'weapons_factory': {
        'name': 'Оружейный завод',
        'max_level': 10,
        'base_cost': 7000000,
        'jobs_provided': 450,
        'effects': {'combat_bonus': 10}
    },
    'tank_factory': {
        'name': 'Танковый завод',
        'max_level': 10,
        'base_cost': 8000000,
        'jobs_provided': 350,
        'effects': {'combat_bonus': 12}
    },
    'air_defense': {
        'name': 'ПВО',
        'max_level': 10,
        'base_cost': 6500000,
        'jobs_provided': 200,
        'effects': {'raid_protection': 15, 'combat_bonus': 6}
    },
    'intelligence': {
        'name': 'Разведка',
        'max_level': 10,
        'base_cost': 5000000,
        'jobs_provided': 180,
        'effects': {'raid_protection': 20, 'combat_bonus': 4}
    },
    'military_academy': {
        'name': 'Военная академия',
        'max_level': 10,
        'base_cost': 4200000,
        'jobs_provided': 220,
        'effects': {'combat_bonus': 7, 'literacy_bonus': 5}
    },
    'space_station': {
        'name': 'Космостанция',
        'max_level': 10,
        'base_cost': 10000000,
        'jobs_provided': 100,
        'effects': {'income_bonus': 25, 'stability_bonus': 10}
    },
    'research_institute': {
        'name': 'НИИ',
        'max_level': 10,
        'base_cost': 7500000,
        'jobs_provided': 280,
        'effects': {'income_bonus': 18, 'tech_limit_add': 8, 'literacy_bonus': 6}
    }
}
# ========== КОНФИГ ПРЕДМЕТОВ ==========
ITEM_CONFIG = {
    # Оружие
    'pistol': {'category': 'weapon', 'name': 'Пистолет', 'tier': 1, 'power': 10, 'upkeep_day': 100, 'price_money': 50000},
    'smg': {'category': 'weapon', 'name': 'ПП', 'tier': 2, 'power': 25, 'upkeep_day': 300, 'price_money': 150000},
    'rifle': {'category': 'weapon', 'name': 'Винтовка', 'tier': 2, 'power': 40, 'upkeep_day': 500, 'price_money': 250000},
    'mg': {'category': 'weapon', 'name': 'Пулемёт', 'tier': 3, 'power': 80, 'upkeep_day': 1000, 'price_money': 500000},
    'sniper': {'category': 'weapon', 'name': 'Снайперка', 'tier': 3, 'power': 120, 'upkeep_day': 1500, 'price_money': 750000},
    'grenade_launcher': {'category': 'weapon', 'name': 'Гранатомёт', 'tier': 4, 'power': 200, 'upkeep_day': 2500, 'price_money': 1500000},
    'armor_kit': {'category': 'armor', 'name': 'Бронекомплект', 'tier': 2, 'power': 30, 'upkeep_day': 400, 'price_money': 200000},
    'assault_kit': {'category': 'armor', 'name': 'Штурмовой комплект', 'tier': 3, 'power': 60, 'upkeep_day': 800, 'price_money': 400000},
    'atgm_kit': {'category': 'weapon', 'name': 'ПТРК', 'tier': 4, 'power': 150, 'upkeep_day': 2000, 'price_money': 1200000},
    'aa_kit': {'category': 'weapon', 'name': 'ПЗРК', 'tier': 4, 'power': 100, 'upkeep_day': 1800, 'price_money': 1000000},
    # Техника
    'apc_s': {'category': 'vehicle', 'name': 'БТР-С', 'tier': 2, 'power': 100, 'upkeep_day': 2000, 'price_money': 2000000},
    'ifv_lynx': {'category': 'vehicle', 'name': 'БМП Lynx', 'tier': 3, 'power': 250, 'upkeep_day': 4000, 'price_money': 5000000},
    'spg_thunder': {'category': 'vehicle', 'name': 'САУ Thunder', 'tier': 4, 'power': 500, 'upkeep_day': 8000, 'price_money': 10000000},
    'tank_t34': {'category': 'vehicle', 'name': 'Т-34', 'tier': 2, 'power': 150, 'upkeep_day': 3000, 'price_money': 3000000},
    'tank_bulat': {'category': 'vehicle', 'name': 'Танк Булат', 'tier': 3, 'power': 350, 'upkeep_day': 6000, 'price_money': 7000000},
    'tank_armada': {'category': 'vehicle', 'name': 'Танк Armada', 'tier': 4, 'power': 700, 'upkeep_day': 12000, 'price_money': 15000000, 'req_building': 'tank_factory', 'req_building_level': 3},
    'heavy_colossus': {'category': 'vehicle', 'name': 'Тяжёлый Colossus', 'tier': 5, 'power': 1000, 'upkeep_day': 20000, 'price_money': 25000000, 'price_plutonium': 10},
    'mlrs_storm': {'category': 'vehicle', 'name': 'РСЗО Storm', 'tier': 4, 'power': 600, 'upkeep_day': 10000, 'price_money': 12000000},
    'spg_volcano': {'category': 'vehicle', 'name': 'САУ Volcano', 'tier': 5, 'power': 1200, 'upkeep_day': 25000, 'price_money': 30000000, 'price_plutonium': 15},
    'armored_train': {'category': 'vehicle', 'name': 'Бронепоезд', 'tier': 4, 'power': 800, 'upkeep_day': 15000, 'price_money': 20000000},
    'orbital_drone': {'category': 'vehicle', 'name': 'Орбитальный дрон', 'tier': 5, 'power': 1500, 'upkeep_day': 30000, 'price_money': 50000000, 'price_plasma': 5},
    'titan_mech': {'category': 'vehicle', 'name': 'Титан-мех', 'tier': 5, 'power': 2000, 'upkeep_day': 50000, 'price_money': 100000000, 'price_plutonium': 50, 'price_plasma': 20}
}
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Включить подробные логи
logging.getLogger('aiogram').setLevel(logging.DEBUG)
router = Router()

@router.message(Command("боссы", "bosses", "страны", "countries", "шахта", "mine"))
@router.message(F.text.lower().in_([
    "боссы", "/боссы", "bosses", "/bosses",
    "страны", "/страны", "countries", "/countries",
    "шахта", "/шахта", "mine", "/mine"
]))
async def quick_command_router(msg: Message):
    text = (msg.text or "").strip().lower()
    if text in {"боссы", "/боссы", "bosses", "/bosses"}:
        text, reply_markup = await build_bosses_panel(msg.from_user.id)
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
        return
    if text in {"страны", "/страны", "countries", "/countries"}:
        await show_country_selection(msg)
        return
    if text in {"шахта", "/шахта", "mine", "/mine"}:
        text, reply_markup = await build_mine_panel(msg.from_user.id)
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
        return

@router.message(lambda msg: bool(msg.text) and (
    globals().get("creating_transport_company", {}).get(msg.from_user.id)
    or globals().get("creating_construction_company", {}).get(msg.from_user.id)
))
async def handle_company_name_prompt_early(msg: Message):
    uid = msg.from_user.id
    name = msg.text.strip()
    if globals().get("creating_transport_company", {}).get(uid):
        await _create_transport_company_from_name(uid, name, msg)
        return
    if globals().get("creating_construction_company", {}).get(uid):
        await _create_construction_company_from_name(uid, name, msg)
        return
@router.message(F.text.lower().startswith("купить планету"))
async def buy_planet_cmd(msg: Message):
    try:
        parts = msg.text.split()
        if len(parts) < 3:
            await msg.reply(
                "❌ Использование:\n<code>купить планету [id]</code>",
                parse_mode="HTML"
            )
            return
        planet_id = int(parts[2])
        success, result = await buy_planet(msg.from_user.id, planet_id)
        await msg.reply(result if success else f"❌ {result}")
    except ValueError:
        await msg.reply("❌ ID планеты должен быть числом")
    except Exception as e:
        await msg.reply(
            f"❌ <b>Ошибка</b>\n<code>{e}</code>",
            parse_mode="HTML"
        )
        raise
@router.message(F.text.lower().in_(["рефералы", "мои рефералы", "пригласить"]))
async def referrals_cmd(msg: Message):
    uid = msg.from_user.id
    user = await get_user(uid)
    bot_username = (await msg.bot.get_me()).username
    referral_code = user['referral_code']
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    text = (
        "👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"📨 <b>Ваш код:</b> <code>{referral_code}</code>\n\n"
        f"👤 <b>Приглашено:</b> {user.get('referral_count', 0)}\n"
        f"💰 <b>Заработано:</b> {format_money(user.get('total_referral_earned', 0))}\n\n"
        "🎁 <b>Награда за друга:</b> 30–100М\n"
        "⚠️ Засчитывается только первый /start"
    )
    # ДОБАВЛЯЕМ ОТПРАВКУ СООБЩЕНИЯ:
    await msg.reply(text, parse_mode="HTML")
# ========== КОМАНДЫ ДЛЯ ЛОТЕРЕИ ==========
@router.message(F.text.lower().in_(["лотерея", "lottery", "лот", "лотерейка"]))
async def lottery_cmd(msg: Message):
    """Команда для показа лотереи"""
    await show_lottery_info(msg=msg)
@router.message(F.text.lower().startswith("купить лотерейный"))
async def buy_lottery_cmd(msg: Message):
    """Команда для покупки лотерейных билетов"""
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "🎫 <b>Покупка лотерейных билетов</b>\n\n"
            "📝 <b>Использование:</b>\n"
            "- <code>купить лотерейный 1</code> - 1 бронзовый билет (50М)\n"
            "- <code>купить лотерейный 2</code> - 1 золотой билет (100М)\n"
            "- <code>купить лотерейный 1 5</code> - 5 бронзовых билетов (250М)\n"
            "- <code>купить лотерейный 2 3</code> - 3 золотых билета (300М)",
            parse_mode="HTML"
        )
        return
    try:
        ticket_type = int(parts[2])
        count = int(parts[3]) if len(parts) > 3 else 1
        success, message = await buy_lottery_ticket(msg.from_user.id, ticket_type, count)
        await msg.reply(message, parse_mode="HTML")
    except ValueError:
        await msg.reply("❌ Неверный формат. Используйте числа для типа билета и количества.")
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
async def profile_cmd(msg: Message):
    uid = msg.from_user.id
    user = await get_user(uid)
    country_name = "нет"
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT name FROM countries WHERE owner_user_id = ? LIMIT 1", (uid,))
            row = await cursor.fetchone()
            if row:
                country_name = row[0]
    except Exception as e:
        logger.error(f"Ошибка загрузки страны в профиле: {e}")
    # Получить титулы пользователя
    titles = await get_user_titles(uid)
    titles_text = ""
    if titles:
        titles_list = [f"🏅 {t['name']}" for t in titles[:3]]  # Показать первые 3
        titles_text = f"\n\n🎖️ <b>Титулы:</b>\n" + "\n".join(titles_list)
        if len(titles) > 3:
            titles_text += f"\n... и ещё {len(titles) - 3} титулов"
    else:
        titles_text = "\n\n🎖️ <b>Титулы:</b> Нет титулов"
    # Получить текущее мировое событие
    current_event = await get_current_world_event()
    event_text = ""
    if current_event:
        event_text = f"\n\n🌍 <b>Мировое событие:</b> {current_event['name']}\n{current_event['description']}"
    else:
        event_text = "\n\n🌍 <b>Мировое событие:</b> Спокойные времена"
    text = (
        "👤 <b>ПРОФИЛЬ</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Баланс: {format_money(user['balance'])}\n"
        f"🏳️ Страна: {country_name}\n"
        f"💎 Плазма: {user.get('plasma', 0)}\n"
        f"₿ Биткоины: {user.get('bitcoin', 0):.6f}\n\n"
        f"👥 Рефералы: {user.get('referral_count', 0)}\n"
        f"💸 Заработано на рефералах: {format_money(user.get('total_referral_earned', 0))}\n\n"
        f"🏆 Победы: {user.get('wins', 0)}\n"
        f"💀 Поражения: {user.get('losses', 0)}"
        f"{titles_text}"
        f"{event_text}"
    )
    await msg.reply(text, parse_mode="HTML")
@router.message(F.text.lower() == "тестреф")
async def test_ref_cmd(msg: Message):
    """Тест реферальной системы"""
    uid = msg.from_user.id
    user = await get_user(uid)
    bot_username = (await msg.bot.get_me()).username
    referral_code = user['referral_code']
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    text = (
        f"\U0001F3F0 ????? ????????? ??????\n\n"
        f"??????, {username}!\n\n"
        f"\U0001F30D ?????? ?????? ????? ????? ?? ???, ??????? ???????? ?? ???? ????????!\n\n"
        "???????? ??????, ??????? ?????? ????? ????? ? ?????????? ????:\n"
    )
    await msg.reply(text, parse_mode="HTML")
@router.message(F.text.lower() == "меню")
async def menu_cmd(msg: Message):
    await send_welcome_message(msg)
@router.message(Command("fishing", "рыбалка"))
async def fishing_cmd(msg: Message):
    text, reply_markup = await build_fishing_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().startswith(("рыбалка", "fishing")))
async def fishing_text_cmd(msg: Message):
    text, reply_markup = await build_fishing_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().startswith(("рыбачить", "ловить рыбу")))
async def fishing_catch_cmd(msg: Message):
    uid = msg.from_user.id
    user = await get_user(uid)
    boat_level = int(user.get("fishing_boat_level", 0) or 0)
    rod_level = int(user.get("fishing_rod_level", 0) or 0)
    tackle_level = int(user.get("fishing_tackle_level", 0) or 0)
    if boat_level <= 0 or rod_level <= 0:
        await msg.reply("Нужны лодка и удочка.")
        return
    now = int(time.time())
    last_ts = int(user.get("fishing_last_ts", 0) or 0)
    if last_ts and now - last_ts < FISHING_COOLDOWN:
        remaining = FISHING_COOLDOWN - (now - last_ts)
        await msg.reply(f"Подожди {format_short_seconds(remaining)}.")
        return
    boat = get_fishing_boat_config(boat_level)
    rod = get_fishing_rod_config(rod_level)
    tackle = get_fishing_tackle_config(tackle_level)
    location_index = int(user.get("fishing_location", 1) or 1)
    max_location = get_max_fishing_location(boat_level)
    if location_index > max_location:
        location_index = max_location
    location = get_fishing_location(location_index) or FISHING_LOCATIONS[0]
    rarity_bonus = 0.0
    exp_bonus = 0.0
    if boat:
        rarity_bonus += boat["rarity_bonus"]
        exp_bonus += boat["exp_bonus"]
    if rod:
        exp_bonus += rod["exp_bonus"]
    if tackle:
        rarity_bonus += tackle["rarity_bonus"]
        exp_bonus += tackle["exp_bonus"]
    rarity_weights = location["rarity_weights"]
    weights = []
    for rarity in FISHING_RARITY_ORDER:
        weight = rarity_weights.get(rarity, 0)
        if rarity in {"rare", "epic", "legendary", "mythic"}:
            weight = int(round(weight * (1 + rarity_bonus)))
        weights.append(weight)
    if sum(weights) <= 0:
        weights = [1 if r == "common" else 0 for r in FISHING_RARITY_ORDER]
    rarity = random.choices(FISHING_RARITY_ORDER, weights=weights, k=1)[0]
    pool = [f for f in FISH_CONFIG if location_index in f["locations"]]
    candidates = [f for f in pool if f["rarity"] == rarity]
    if not candidates:
        candidates = pool if pool else FISH_CONFIG
    fish = random.choice(candidates)
    count = get_fishing_catch_count(rod_level)
    exp_gain = max(1, int(round(FISHING_EXP_BASE * (1 + exp_bonus)))) * count
    new_exp = int(user.get("fishing_exp", 0) or 0) + exp_gain
    old_level = int(user.get("fishing_level", 1) or 1)
    new_level = get_fishing_level(new_exp)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT count FROM user_fish WHERE user_id = ? AND fish_code = ?",
            (uid, fish["code"])
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE user_fish SET count = count + ? WHERE user_id = ? AND fish_code = ?",
                (count, uid, fish["code"])
            )
        else:
            await db.execute(
                "INSERT INTO user_fish (user_id, fish_code, count) VALUES (?, ?, ?)",
                (uid, fish["code"], count)
            )
        await db.execute(
            "UPDATE users SET fishing_last_ts = ?, fishing_exp = ?, fishing_level = ?, fish_caught_total = fish_caught_total + ?, fishing_location = ? WHERE id = ?",
            (now, new_exp, new_level, count, location_index, uid)
        )
        await db.commit()
    total_value = fish["price"] * count
    message = f"Поймано: {fish['name']} x{count} (+{format_money(total_value)})"
    if new_level > old_level:
        message += f"\nУровень рыбака повышен до {new_level}!"
    await msg.reply(message)
    text, reply_markup = await build_fishing_panel(uid)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower() == "майнинг")
async def mining_cmd(msg: Message):
    await show_mining_panel(msg=msg)
@router.message(F.text.lower().startswith(("копать", "копать руду")))
async def mining_dig_cmd(msg: Message):
    uid = msg.from_user.id
    user = await get_user(uid)
    pickaxe_level = int(user.get("pickaxe_level", 0) or 0)
    if pickaxe_level <= 0:
        await msg.reply("Нужна кирка. Купи ее в магазине шахты.")
        return
    now = int(time.time())
    last_ts = int(user.get("mine_last_ts", 0) or 0)
    if last_ts and now - last_ts < ORE_MINE_COOLDOWN:
        remaining = ORE_MINE_COOLDOWN - (now - last_ts)
        await msg.reply(f"Подожди {format_duration(remaining)}.")
        return
    pickaxe = get_pickaxe_config(pickaxe_level)
    ore_key = random.choices(ORE_KEYS, weights=pickaxe["weights"], k=1)[0]
    ore = ORE_CONFIG[ore_key]
    ore_field = f"ore_{ore_key}"
    max_qty = min(15, 3 + pickaxe_level * 3)
    qty = scale_mining_qty(random.randint(1, max_qty))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            f"UPDATE users SET {ore_field} = {ore_field} + ?, mine_last_ts = ? WHERE id = ?",
            (qty, now, uid)
        )
        await db.commit()
    await msg.reply(f"Добыто: {ore['name']} (+{qty})")
    text, reply_markup = await build_mine_panel(uid)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().in_(["инвестировать", "инвестиции"]))
async def investments_cmd(msg: Message):
    await show_investments_panel(msg=msg)
@router.message(F.text.lower().in_(["мои планеты", "планеты"]))
async def planets_cmd(msg: Message):
    await show_my_planets_panel(msg)
# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
WORK_COOLDOWN = 300  # 5 минут
BONUS_COOLDOWN = 3600  # 1 час
REFERRAL_ACTIONS_REQUIRED = 20
DAILY_REWARDS_M = [
    10, 15, 20, 25, 30, 35, 50, 80, 100, 120, 150
]
while len(DAILY_REWARDS_M) < 30:
    DAILY_REWARDS_M.append(DAILY_REWARDS_M[-1] + 30)
# ⬇ ДОБАВИТЬ НОВЫЕ КОНСТАНТЫ:
GAMES_COOLDOWN = 5  # 5 секунд для всех азартных игр
BOSS_COOLDOWN = 300  # 5 минут для атаки босса
BOSS_LIFETIME = 24 * 60 * 60  # 24 часа жизни босса
ORE_MINE_COOLDOWN = 120  # 2 минуты между копанием
FISHING_COOLDOWN = 5  # 5 секунд между попытками рыбалки
TAXI_COOLDOWN = 300  # 5 ????? ????? ?????????
INCOME_MULTIPLIER = 1.0
PRICE_MULTIPLIER = 0.8
COUNTRY_INCOME_MULTIPLIER = 2 * INCOME_MULTIPLIER

def scale_income(value: int) -> int:
    if not value or value <= 0:
        return 0
    return max(1, int(round(value * INCOME_MULTIPLIER)))

def get_daily_reward_amount(streak: int) -> int:
    if streak <= 0:
        streak = 1
    idx = min(30, streak) - 1
    base = DAILY_REWARDS_M[idx] * 1_000_000
    return scale_income(base)

def scale_price(value: int) -> int:
    if not value or value <= 0:
        return 0
    return max(1, int(round(value * PRICE_MULTIPLIER)))

def scale_mining_qty(qty: int) -> int:
    if qty <= 0:
        return 0
    return max(1, int(round(qty * INCOME_MULTIPLIER)))
TAXI_PARK_MAX_LEVEL = 10
TAXI_PARK_UPGRADE_COSTS = [
    50_000_000, 120_000_000, 250_000_000, 500_000_000, 1_000_000_000,
    2_000_000_000, 4_000_000_000, 7_000_000_000, 11_000_000_000
]
TAXI_CAR_CONFIG = [
    {"code": "vaz_2107", "name": "VAZ 2107", "price": 5_000_000, "work_min": 300_000, "work_max": 500_000, "park_min": 4_000_000, "park_max": 6_800_000},
    {"code": "kia_rio", "name": "Kia Rio", "price": 10_000_000, "work_min": 600_000, "work_max": 1_000_000, "park_min": 8_000_000, "park_max": 13_600_000},
    {"code": "hyundai_solaris", "name": "Hyundai Solaris", "price": 18_000_000, "work_min": 1_080_000, "work_max": 1_800_000, "park_min": 14_400_000, "park_max": 24_000_000},
    {"code": "skoda_octavia", "name": "Skoda Octavia", "price": 30_000_000, "work_min": 1_800_000, "work_max": 3_000_000, "park_min": 24_000_000, "park_max": 40_000_000},
    {"code": "toyota_camry", "name": "Toyota Camry", "price": 50_000_000, "work_min": 3_000_000, "work_max": 5_000_000, "park_min": 40_000_000, "park_max": 66_800_000},
    {"code": "bmw_5", "name": "BMW 5", "price": 80_000_000, "work_min": 4_800_000, "work_max": 8_000_000, "park_min": 64_000_000, "park_max": 106_800_000},
    {"code": "mercedes_e", "name": "Mercedes E", "price": 120_000_000, "work_min": 7_200_000, "work_max": 12_000_000, "park_min": 96_000_000, "park_max": 160_000_000},
    {"code": "audi_a6", "name": "Audi A6", "price": 170_000_000, "work_min": 10_200_000, "work_max": 17_000_000, "park_min": 136_000_000, "park_max": 226_800_000},
    {"code": "lexus_ls", "name": "Lexus LS", "price": 230_000_000, "work_min": 13_800_000, "work_max": 23_000_000, "park_min": 184_000_000, "park_max": 306_800_000},
    {"code": "tesla_model_s", "name": "Tesla Model S", "price": 320_000_000, "work_min": 19_200_000, "work_max": 32_000_000, "park_min": 256_000_000, "park_max": 426_800_000},
    {"code": "porsche_panamera", "name": "Porsche Panamera", "price": 450_000_000, "work_min": 27_000_000, "work_max": 45_000_000, "park_min": 360_000_000, "park_max": 600_000_000},
    {"code": "range_rover", "name": "Range Rover", "price": 650_000_000, "work_min": 39_000_000, "work_max": 65_000_000, "park_min": 520_000_000, "park_max": 866_800_000},
    {"code": "mercedes_s", "name": "Mercedes S", "price": 900_000_000, "work_min": 54_000_000, "work_max": 90_000_000, "park_min": 720_000_000, "park_max": 1_200_000_000},
    {"code": "bentley_flying_spur", "name": "Bentley Flying Spur", "price": 1_300_000_000, "work_min": 78_000_000, "work_max": 130_000_000, "park_min": 1_040_000_000, "park_max": 1_733_200_000},
    {"code": "rolls_royce_phantom", "name": "Rolls-Royce Phantom", "price": 2_000_000_000, "work_min": 120_000_000, "work_max": 200_000_000, "park_min": 1_600_000_000, "park_max": 2_666_800_000},
]
TRANSPORT_CREATE_COST = 25_000_000_000
TRANSPORT_ORDER_DURATION = 3 * 3600
TRANSPORT_OFFICES = [
    {"code": "roadside", "name": "Склад у трассы", "price": 5_000_000_000, "income_mult": 1.00, "risk_add": 0},
    {"code": "city", "name": "Городской офис", "price": 10_000_000_000, "income_mult": 1.15, "risk_add": 3},
    {"code": "regional", "name": "Региональный офис", "price": 20_000_000_000, "income_mult": 1.30, "risk_add": 6},
    {"code": "national", "name": "Национальный офис", "price": 40_000_000_000, "income_mult": 1.50, "risk_add": 10},
    {"code": "global", "name": "Международный штаб", "price": 80_000_000_000, "income_mult": 1.70, "risk_add": 15},
]
TRANSPORT_TRUCKS = [
    {"code": "gazelle", "name": "Газель NEXT", "price": 2_500_000_000, "income_mult": 0.60},
    {"code": "iveco", "name": "Iveco Stralis", "price": 5_000_000_000, "income_mult": 0.75},
    {"code": "scania_p", "name": "Scania P-series", "price": 8_000_000_000, "income_mult": 0.90},
    {"code": "volvo_fh", "name": "Volvo FH", "price": 12_000_000_000, "income_mult": 1.05},
    {"code": "man_tgx", "name": "MAN TGX", "price": 18_000_000_000, "income_mult": 1.15},
    {"code": "daf_xf", "name": "DAF XF", "price": 26_000_000_000, "income_mult": 1.25},
    {"code": "mercedes_actros", "name": "Mercedes Actros", "price": 36_000_000_000, "income_mult": 1.35},
    {"code": "scania_s", "name": "Scania S-series", "price": 50_000_000_000, "income_mult": 1.50},
    {"code": "volvo_fh16", "name": "Volvo FH16", "price": 70_000_000_000, "income_mult": 1.65},
    {"code": "kenworth_w900", "name": "Kenworth W900", "price": 100_000_000_000, "income_mult": 1.80},
]
TRANSPORT_CARGO = [
    {"code": "vegetables", "name": "Овощи", "base_income": 600_000_000, "base_risk": 2},
    {"code": "metal", "name": "Металл", "base_income": 900_000_000, "base_risk": 4},
    {"code": "weapons", "name": "Оружие", "base_income": 1_200_000_000, "base_risk": 9},
    {"code": "food", "name": "Продукты", "base_income": 700_000_000, "base_risk": 3},
    {"code": "diamonds", "name": "Алмазы", "base_income": 1_400_000_000, "base_risk": 7},
    {"code": "contraband", "name": "Контрабанда", "base_income": 1_600_000_000, "base_risk": 12},
    {"code": "construction", "name": "Стройматериалы", "base_income": 850_000_000, "base_risk": 4},
]
CONSTRUCTION_CREATE_COST = 50_000_000_000
CONSTRUCTION_RESOURCE_PRICES = {
    "workers": 50_000_000,
    "materials": 20_000_000,
    "land": 2_000_000_000
}
CONSTRUCTION_OFFICES = [
    {"level": 1, "name": "Проектный участок", "price": 10_000_000_000, "income_mult": 1.00, "risk_add": 0},
    {"level": 2, "name": "Городской отдел", "price": 20_000_000_000, "income_mult": 1.10, "risk_add": 2},
    {"level": 3, "name": "Региональный штаб", "price": 35_000_000_000, "income_mult": 1.20, "risk_add": 4},
    {"level": 4, "name": "Проектный центр", "price": 55_000_000_000, "income_mult": 1.30, "risk_add": 6},
    {"level": 5, "name": "Национальный офис", "price": 80_000_000_000, "income_mult": 1.40, "risk_add": 8},
    {"level": 6, "name": "Инфраструктурный блок", "price": 110_000_000_000, "income_mult": 1.55, "risk_add": 10},
    {"level": 7, "name": "Девелоперский узел", "price": 150_000_000_000, "income_mult": 1.70, "risk_add": 12},
    {"level": 8, "name": "Инвестиционный офис", "price": 200_000_000_000, "income_mult": 1.85, "risk_add": 14},
    {"level": 9, "name": "Международная дирекция", "price": 260_000_000_000, "income_mult": 2.00, "risk_add": 16},
    {"level": 10, "name": "Глобальный холдинг", "price": 330_000_000_000, "income_mult": 2.20, "risk_add": 18},
]
CONSTRUCTION_PROJECTS = [
    {"code": "garage", "name": "Гаражный комплекс", "min_level": 1, "workers": 40, "materials": 120, "land": 1, "base_income": 2_000_000_000, "duration": 2 * 3600, "base_risk": 3},
    {"code": "warehouse", "name": "Складской ангар", "min_level": 1, "workers": 55, "materials": 160, "land": 1, "base_income": 2_600_000_000, "duration": 3 * 3600, "base_risk": 4},
    {"code": "small_shop", "name": "Торговый павильон", "min_level": 1, "workers": 60, "materials": 180, "land": 1, "base_income": 3_000_000_000, "duration": 3 * 3600, "base_risk": 4},
    {"code": "gas_station", "name": "АЗС у трассы", "min_level": 1, "workers": 70, "materials": 210, "land": 1, "base_income": 3_400_000_000, "duration": 4 * 3600, "base_risk": 5},
    {"code": "cafe", "name": "Кафе у дороги", "min_level": 1, "workers": 75, "materials": 230, "land": 1, "base_income": 3_800_000_000, "duration": 4 * 3600, "base_risk": 5},
    {"code": "auto_service", "name": "Автосервис", "min_level": 2, "workers": 90, "materials": 260, "land": 1, "base_income": 4_500_000_000, "duration": 5 * 3600, "base_risk": 6},
    {"code": "mini_hotel", "name": "Мини-отель", "min_level": 2, "workers": 100, "materials": 300, "land": 1, "base_income": 5_200_000_000, "duration": 5 * 3600, "base_risk": 6},
    {"code": "small_office", "name": "Небольшой офис", "min_level": 2, "workers": 110, "materials": 320, "land": 1, "base_income": 5_800_000_000, "duration": 6 * 3600, "base_risk": 7},
    {"code": "apartment_3f", "name": "Жилой дом (3 этажа)", "min_level": 2, "workers": 120, "materials": 350, "land": 1, "base_income": 6_400_000_000, "duration": 6 * 3600, "base_risk": 7},
    {"code": "fitness", "name": "Фитнес-центр", "min_level": 2, "workers": 130, "materials": 380, "land": 1, "base_income": 7_200_000_000, "duration": 6 * 3600, "base_risk": 8},
    {"code": "mall_small", "name": "ТЦ (малый)", "min_level": 3, "workers": 150, "materials": 450, "land": 2, "base_income": 8_000_000_000, "duration": 7 * 3600, "base_risk": 8},
    {"code": "office_center", "name": "Офисный центр", "min_level": 3, "workers": 170, "materials": 500, "land": 2, "base_income": 9_200_000_000, "duration": 7 * 3600, "base_risk": 9},
    {"code": "hospital_small", "name": "Частная клиника", "min_level": 3, "workers": 190, "materials": 560, "land": 2, "base_income": 10_500_000_000, "duration": 8 * 3600, "base_risk": 9},
    {"code": "business_center", "name": "Бизнес-центр", "min_level": 3, "workers": 210, "materials": 620, "land": 2, "base_income": 12_000_000_000, "duration": 8 * 3600, "base_risk": 10},
    {"code": "bridge_small", "name": "Малый мост", "min_level": 3, "workers": 220, "materials": 700, "land": 2, "base_income": 13_200_000_000, "duration": 9 * 3600, "base_risk": 11},
    {"code": "residential_8f", "name": "ЖК (8 этажей)", "min_level": 4, "workers": 240, "materials": 780, "land": 2, "base_income": 14_800_000_000, "duration": 9 * 3600, "base_risk": 11},
    {"code": "logistics_center", "name": "Логистический центр", "min_level": 4, "workers": 260, "materials": 820, "land": 2, "base_income": 16_000_000_000, "duration": 10 * 3600, "base_risk": 12},
    {"code": "water_treatment", "name": "Очистные сооружения", "min_level": 4, "workers": 280, "materials": 900, "land": 2, "base_income": 17_500_000_000, "duration": 10 * 3600, "base_risk": 12},
    {"code": "school", "name": "Школа", "min_level": 4, "workers": 300, "materials": 950, "land": 2, "base_income": 18_500_000_000, "duration": 11 * 3600, "base_risk": 13},
    {"code": "stadium_small", "name": "Стадион (малый)", "min_level": 5, "workers": 330, "materials": 1_050, "land": 3, "base_income": 20_000_000_000, "duration": 12 * 3600, "base_risk": 14},
    {"code": "hospital_large", "name": "Городская больница", "min_level": 5, "workers": 360, "materials": 1_150, "land": 3, "base_income": 22_000_000_000, "duration": 12 * 3600, "base_risk": 14},
    {"code": "residential_16f", "name": "ЖК (16 этажей)", "min_level": 5, "workers": 380, "materials": 1_250, "land": 3, "base_income": 24_000_000_000, "duration": 13 * 3600, "base_risk": 15},
    {"code": "airport_terminal", "name": "Терминал аэропорта", "min_level": 6, "workers": 420, "materials": 1_400, "land": 4, "base_income": 27_000_000_000, "duration": 14 * 3600, "base_risk": 16},
    {"code": "power_plant", "name": "ТЭС/ГЭС", "min_level": 6, "workers": 450, "materials": 1_550, "land": 4, "base_income": 30_000_000_000, "duration": 14 * 3600, "base_risk": 17},
    {"code": "metro_station", "name": "Станция метро", "min_level": 7, "workers": 480, "materials": 1_700, "land": 4, "base_income": 33_000_000_000, "duration": 15 * 3600, "base_risk": 18},
    {"code": "bridge_large", "name": "Крупный мост", "min_level": 7, "workers": 520, "materials": 1_850, "land": 4, "base_income": 36_000_000_000, "duration": 16 * 3600, "base_risk": 19},
    {"code": "stadium_large", "name": "Стадион (большой)", "min_level": 8, "workers": 560, "materials": 2_100, "land": 5, "base_income": 40_000_000_000, "duration": 18 * 3600, "base_risk": 20},
    {"code": "skyscraper", "name": "Небоскреб", "min_level": 9, "workers": 620, "materials": 2_400, "land": 5, "base_income": 45_000_000_000, "duration": 20 * 3600, "base_risk": 22},
    {"code": "spaceport", "name": "Космопорт", "min_level": 10, "workers": 700, "materials": 2_800, "land": 6, "base_income": 52_000_000_000, "duration": 24 * 3600, "base_risk": 25},
]
FISHING_EXP_PER_LEVEL = 100
FISHING_EXP_BASE = 5
FISHING_RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]
FISHING_LOCATIONS = [
    {
        "index": 1,
        "name": "Тихая заводь",
        "required_boat_level": 1,
        "rarity_weights": {"common": 70, "uncommon": 22, "rare": 7, "epic": 1, "legendary": 0, "mythic": 0}
    },
    {
        "index": 2,
        "name": "Речные перекаты",
        "required_boat_level": 3,
        "rarity_weights": {"common": 55, "uncommon": 25, "rare": 15, "epic": 4, "legendary": 1, "mythic": 0}
    },
    {
        "index": 3,
        "name": "Озеро туманов",
        "required_boat_level": 5,
        "rarity_weights": {"common": 40, "uncommon": 25, "rare": 20, "epic": 10, "legendary": 0, "mythic": 0}
    },
    {
        "index": 4,
        "name": "Северный пролив",
        "required_boat_level": 7,
        "rarity_weights": {"common": 30, "uncommon": 24, "rare": 22, "epic": 15, "legendary": 0, "mythic": 0}
    },
    {
        "index": 5,
        "name": "Бездна Империи",
        "required_boat_level": 9,
        "rarity_weights": {"common": 20, "uncommon": 20, "rare": 22, "epic": 20, "legendary": 13, "mythic": 5}
    },
]
FISHING_BOATS = [
    {"level": 1, "name": "Надувная лодка", "price": 2_000_000, "rarity_bonus": 0.00, "exp_bonus": 0.00},
    {"level": 2, "name": "Деревянный баркас", "price": 5_000_000, "rarity_bonus": 0.03, "exp_bonus": 0.02},
    {"level": 3, "name": "Речная шхуна", "price": 12_000_000, "rarity_bonus": 0.05, "exp_bonus": 0.03},
    {"level": 4, "name": "Морской катер", "price": 30_000_000, "rarity_bonus": 0.07, "exp_bonus": 0.05},
    {"level": 5, "name": "Скоростной катамаран", "price": 70_000_000, "rarity_bonus": 0.10, "exp_bonus": 0.07},
    {"level": 6, "name": "Рыболовный траулер", "price": 150_000_000, "rarity_bonus": 0.13, "exp_bonus": 0.10},
    {"level": 7, "name": "Экспедиционная яхта", "price": 280_000_000, "rarity_bonus": 0.16, "exp_bonus": 0.12},
    {"level": 8, "name": "Океанский крейсер", "price": 450_000_000, "rarity_bonus": 0.20, "exp_bonus": 0.15},
    {"level": 9, "name": "Полярный ледокол", "price": 750_000_000, "rarity_bonus": 0.25, "exp_bonus": 0.18},
    {"level": 10, "name": "Легендарный «Левиафан»", "price": 1_200_000_000, "rarity_bonus": 0.32, "exp_bonus": 0.22},
]
FISHING_RODS = [
    {"level": 1, "name": "Бамбуковая удочка", "price": 1_000_000, "exp_bonus": 0.00},
    {"level": 2, "name": "Сосновая удочка", "price": 2_500_000, "exp_bonus": 0.08},
    {"level": 3, "name": "Стеклопластиковая удочка", "price": 6_000_000, "exp_bonus": 0.12},
    {"level": 4, "name": "Карбоновая удочка", "price": 15_000_000, "exp_bonus": 0.18},
    {"level": 5, "name": "Композитная удочка", "price": 35_000_000, "exp_bonus": 0.25},
    {"level": 6, "name": "Титановая удочка", "price": 80_000_000, "exp_bonus": 0.32},
    {"level": 7, "name": "Плазменная удочка", "price": 180_000_000, "exp_bonus": 0.40},
    {"level": 8, "name": "Имперская удочка", "price": 350_000_000, "exp_bonus": 0.50},
]
FISHING_TACKLE = [
    {"level": 1, "name": "Простые снасти", "price": 500_000, "rarity_bonus": 0.00, "exp_bonus": 0.00},
    {"level": 2, "name": "Усиленные снасти", "price": 2_000_000, "rarity_bonus": 0.04, "exp_bonus": 0.02},
    {"level": 3, "name": "Точные снасти", "price": 6_000_000, "rarity_bonus": 0.08, "exp_bonus": 0.03},
    {"level": 4, "name": "Премиум снасти", "price": 20_000_000, "rarity_bonus": 0.12, "exp_bonus": 0.05},
    {"level": 5, "name": "Легендарные снасти", "price": 60_000_000, "rarity_bonus": 0.18, "exp_bonus": 0.07},
    {"level": 6, "name": "Сигма-снасти", "price": 150_000_000, "rarity_bonus": 0.25, "exp_bonus": 0.10},
]
FISH_CONFIG = [
    {"code": "carass", "name": "Карась", "rarity": "common", "price": 120_000, "locations": [1, 2, 3]},
    {"code": "roach", "name": "Плотва", "rarity": "common", "price": 105_000, "locations": [1, 2, 3]},
    {"code": "perch", "name": "Окунь", "rarity": "common", "price": 180_000, "locations": [1, 2, 3, 4]},
    {"code": "ruff", "name": "Ерш", "rarity": "common", "price": 90_000, "locations": [1, 2, 3]},
    {"code": "bream", "name": "Лещ", "rarity": "common", "price": 240_000, "locations": [1, 2, 3, 4]},
    {"code": "gudgeon", "name": "Пескарь", "rarity": "common", "price": 75_000, "locations": [1, 2]},
    {"code": "bleak", "name": "Уклейка", "rarity": "common", "price": 84_000, "locations": [1, 2]},
    {"code": "dace", "name": "Елец", "rarity": "common", "price": 135_000, "locations": [1, 2, 3]},
    {"code": "chub", "name": "Голавль", "rarity": "uncommon", "price": 360_000, "locations": [2, 3, 4]},
    {"code": "ide", "name": "Язь", "rarity": "uncommon", "price": 420_000, "locations": [2, 3, 4]},
    {"code": "tench", "name": "Линь", "rarity": "uncommon", "price": 480_000, "locations": [2, 3, 4]},
    {"code": "zander", "name": "Судак", "rarity": "uncommon", "price": 660_000, "locations": [2, 3, 4, 5]},
    {"code": "trout", "name": "Форель", "rarity": "uncommon", "price": 600_000, "locations": [3, 4, 5]},
    {"code": "whitefish", "name": "Сиг", "rarity": "uncommon", "price": 540_000, "locations": [3, 4]},
    {"code": "pike", "name": "Щука", "rarity": "rare", "price": 1_050_000, "locations": [3, 4, 5]},
    {"code": "catfish", "name": "Сом", "rarity": "rare", "price": 1_350_000, "locations": [3, 4, 5]},
    {"code": "sturgeon", "name": "Осетр", "rarity": "rare", "price": 1_800_000, "locations": [4, 5]},
    {"code": "eel", "name": "Угорь", "rarity": "rare", "price": 1_500_000, "locations": [4, 5]},
    {"code": "halibut", "name": "Палтус", "rarity": "rare", "price": 2_100_000, "locations": [4, 5]},
    {"code": "salmon", "name": "Лосось", "rarity": "epic", "price": 3_600_000, "locations": [4, 5]},
    {"code": "tuna", "name": "Тунец", "rarity": "epic", "price": 4_500_000, "locations": [4, 5]},
    {"code": "swordfish", "name": "Рыба-меч", "rarity": "epic", "price": 6_000_000, "locations": [5]},
    {"code": "golden_sturgeon", "name": "Золотой осетр", "rarity": "legendary", "price": 15_000_000, "locations": [5]},
    {"code": "leviathan_carp", "name": "Карп-левиафан", "rarity": "legendary", "price": 22_500_000, "locations": [5]},
    {"code": "abyssal_dragonfish", "name": "Бездонный драконий сом", "rarity": "mythic", "price": 45_000_000, "locations": [5]},
]
FISH_BY_CODE = {f["code"]: f for f in FISH_CONFIG}
def get_taxi_car_config(code: str):
    for car in TAXI_CAR_CONFIG:
        if car["code"] == code:
            return car
    return None
async def _get_user_taxi_cars(db: aiosqlite.Connection, uid: int) -> dict:
    cursor = await db.execute(
        "SELECT car_code, count FROM user_taxi_cars WHERE user_id = ?",
        (uid,)
    )
    rows = await cursor.fetchall()
    return {row[0]: int(row[1] or 0) for row in rows}
async def _get_user_taxi_park_cars(db: aiosqlite.Connection, uid: int) -> dict:
    cursor = await db.execute(
        "SELECT car_code, count FROM user_taxi_park_cars WHERE user_id = ?",
        (uid,)
    )
    rows = await cursor.fetchall()
    return {row[0]: int(row[1] or 0) for row in rows}
async def _get_user_taxi_park(db: aiosqlite.Connection, uid: int):
    cursor = await db.execute(
        "SELECT level, last_collect_ts FROM user_taxi_park WHERE user_id = ?",
        (uid,)
    )
    row = await cursor.fetchone()
    if not row:
        await db.execute(
            "INSERT INTO user_taxi_park (user_id, level, last_collect_ts) VALUES (?, 1, 0)",
            (uid,)
        )
        await db.commit()
        return {"level": 1, "last_collect_ts": 0}
    return {"level": int(row[0] or 1), "last_collect_ts": int(row[1] or 0)}
def _taxi_park_multiplier(level: int) -> float:
    return 1 + max(0, level - 1) * 0.05
async def build_taxi_panel(uid: int):
    user = await get_user(uid)
    active_code = user.get("taxi_active_car")
    active_car = get_taxi_car_config(active_code) if active_code else None
    active_name = active_car["name"] if active_car else "Нет машины"
    now = int(time.time())
    last_ts = int(user.get("taxi_last_ts", 0) or 0)
    cooldown_left = max(0, TAXI_COOLDOWN - (now - last_ts)) if last_ts else 0
    text = "🚖 <b>Такси</b>\n\n"
    text += f"Активная машина: <b>{active_name}</b>\n"
    if cooldown_left > 0:
        text += f"Перерыв: {format_duration(cooldown_left)}\n"
    else:
        text += "Можно работать.\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Работать", callback_data="taxi_work"),
            InlineKeyboardButton(text="Гараж", callback_data="taxi_garage")
        ],
        [InlineKeyboardButton(text="Таксопарк", callback_data="taxi_park")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    return text, keyboard
async def build_taxi_garage(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        owned = await _get_user_taxi_cars(db, uid)
    text = "🚗 <b>Гараж такси</b>\n\n"
    for car in TAXI_CAR_CONFIG:
        count = owned.get(car["code"], 0)
        suffix = f" (в наличии: {count})" if count > 0 else ""
        text += f"{car['name']} - {format_money(car['price'])}{suffix}\n"
    keyboard = []
    for car in TAXI_CAR_CONFIG:
        count = owned.get(car["code"], 0)
        if count > 0:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"Выбрать {car['name']}",
                    callback_data=f"taxi_set_{car['code']}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {car['name']} за {format_money(car['price'])}",
                callback_data=f"taxi_buy_{car['code']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="taxi_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_taxi_park_view(uid: int):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        park = await _get_user_taxi_park(db, uid)
        park_cars = await _get_user_taxi_park_cars(db, uid)
    level = park["level"]
    mult = _taxi_park_multiplier(level)
    bonus_pct = int((mult - 1) * 100)
    min_hour = 0
    max_hour = 0
    total_cars = 0
    lines = []
    for code, count in park_cars.items():
        car = get_taxi_car_config(code)
        if not car or count <= 0:
            continue
        total_cars += count
        min_hour += car["park_min"] * count
        max_hour += car["park_max"] * count
        lines.append(f"• {car['name']} x{count}")
    min_hour = int(min_hour * mult)
    max_hour = int(max_hour * mult)
    text = "🏢 <b>Таксопарк</b>\n\n"
    text += f"Уровень: <b>{level}</b> (+{bonus_pct}% к доходу)\n"
    text += f"Машин в парке: <b>{total_cars}</b>\n"
    if total_cars > 0:
        text += f"Доход в час: {format_money(min_hour)} - {format_money(max_hour)}\n"
    if lines:
        text += "\n".join(lines) + "\n"
    else:
        text += "В парке нет машин.\n"
    last_ts = park["last_collect_ts"]
    if last_ts:
        remaining = max(0, 3600 - (now - last_ts))
        if remaining > 0:
            text += f"Сбор через: {format_duration(remaining)}\n"
    keyboard = [
        [InlineKeyboardButton(text="Собрать доход", callback_data="taxi_park_collect")],
        [InlineKeyboardButton(text="Добавить машину", callback_data="taxi_park_add_menu")],
        [InlineKeyboardButton(text="Улучшить парк", callback_data="taxi_park_upgrade")],
        [InlineKeyboardButton(text="Назад", callback_data="taxi_menu")]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_taxi_park_add_menu(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        owned = await _get_user_taxi_cars(db, uid)
    text = "➕ <b>Добавить машину в таксопарк</b>\n\n"
    keyboard = []
    for car in TAXI_CAR_CONFIG:
        count = owned.get(car["code"], 0)
        if count <= 0:
            continue
        text += f"{car['name']} - доступно: {count}\n"
        keyboard.append([
            InlineKeyboardButton(
                text=f"Добавить 1 {car['name']}",
                callback_data=f"taxi_park_add_{car['code']}"
            )
        ])
    if not keyboard:
        text += "Нет доступных машин.\n"
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="taxi_park")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.message(Command("такси", "taxi"))
async def taxi_cmd(msg: Message):
    text, reply_markup = await build_taxi_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().in_(["такси", "taxi"]))
async def taxi_text_cmd(msg: Message):
    text, reply_markup = await build_taxi_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().strip() == "\u0442\u0430\u043a\u0441\u043e\u0432\u0430\u0442\u044c")
async def taxi_work_text_cmd(msg: Message):
    uid = msg.from_user.id
    user = await get_user(uid)
    active_code = user.get("taxi_active_car")
    car = get_taxi_car_config(active_code) if active_code else None
    if not car:
        await msg.reply("\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043c\u0430\u0448\u0438\u043d\u0443 \u0432 \u0433\u0430\u0440\u0430\u0436\u0435 \u0442\u0430\u043a\u0441\u0438.", parse_mode="HTML")
        return
    now = int(time.time())
    last_ts = int(user.get("taxi_last_ts", 0) or 0)
    if last_ts and now - last_ts < TAXI_COOLDOWN:
        remaining = TAXI_COOLDOWN - (now - last_ts)
        await msg.reply(f"\u0414\u043e \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0439 \u0440\u0430\u0431\u043e\u0442\u044b: {format_duration(remaining)}", parse_mode="HTML")
        return
    reward = random.randint(car["work_min"], car["work_max"])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, taxi_last_ts = ? WHERE id = ?",
            (reward, now, uid)
        )
        await db.commit()
    await msg.reply(f"\u0417\u0430\u0440\u0430\u0431\u043e\u0442\u043e\u043a: +{format_money(reward)}", parse_mode="HTML")
    text, reply_markup = await build_taxi_panel(uid)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "taxi_menu")
async def taxi_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_taxi_panel(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "taxi_garage")
async def taxi_garage_cb(cb: CallbackQuery):
    text, reply_markup = await build_taxi_garage(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "taxi_park")
async def taxi_park_cb(cb: CallbackQuery):
    text, reply_markup = await build_taxi_park_view(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "taxi_park_add_menu")
async def taxi_park_add_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_taxi_park_add_menu(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "taxi_work")
async def taxi_work_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    user = await get_user(uid)
    active_code = user.get("taxi_active_car")
    car = get_taxi_car_config(active_code) if active_code else None
    if not car:
        await cb.answer("Сначала выберите машину.", show_alert=True)
        return
    now = int(time.time())
    last_ts = int(user.get("taxi_last_ts", 0) or 0)
    if last_ts and now - last_ts < TAXI_COOLDOWN:
        remaining = TAXI_COOLDOWN - (now - last_ts)
        await cb.answer(f"Перерыв: {format_duration(remaining)}", show_alert=True)
        return
    reward = random.randint(car["work_min"], car["work_max"])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, taxi_last_ts = ? WHERE id = ?",
            (reward, now, uid)
        )
        await db.commit()
    await cb.answer(f"Заработано: +{format_money(reward)}", show_alert=True)
    text, reply_markup = await build_taxi_panel(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("taxi_buy_"))
async def taxi_buy_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("taxi_buy_", "")
    car = get_taxi_car_config(code)
    if not car:
        await cb.answer("Неизвестная машина.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < car["price"]:
        await cb.answer("Недостаточно денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (car["price"], uid)
        )
        await db.execute(
            "INSERT INTO user_taxi_cars (user_id, car_code, count) "
            "VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, car_code) DO UPDATE SET count = count + 1",
            (uid, code)
        )
        if not user.get("taxi_active_car"):
            await db.execute(
                "UPDATE users SET taxi_active_car = ? WHERE id = ?",
                (code, uid)
            )
        await db.commit()
    await cb.answer(f"Куплено: {car['name']}", show_alert=True)
    text, reply_markup = await build_taxi_garage(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("taxi_set_"))
async def taxi_set_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("taxi_set_", "")
    car = get_taxi_car_config(code)
    if not car:
        await cb.answer("Неизвестная машина.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM user_taxi_cars WHERE user_id = ? AND car_code = ?",
            (uid, code)
        )
        row = await cursor.fetchone()
        if not row or int(row[0] or 0) <= 0:
            await cb.answer("У вас нет этой машины.", show_alert=True)
            return
        await db.execute(
            "UPDATE users SET taxi_active_car = ? WHERE id = ?",
            (code, uid)
        )
        await db.commit()
    await cb.answer(f"Активная машина: {car['name']}", show_alert=True)
    text, reply_markup = await build_taxi_garage(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("taxi_park_add_"))
async def taxi_park_add_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("taxi_park_add_", "")
    car = get_taxi_car_config(code)
    if not car:
        await cb.answer("Неизвестная машина.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT count FROM user_taxi_cars WHERE user_id = ? AND car_code = ?",
            (uid, code)
        )
        row = await cursor.fetchone()
        if not row or int(row[0] or 0) <= 0:
            await db.rollback()
            await cb.answer("Нет машин в гараже.", show_alert=True)
            return
        await db.execute(
            "UPDATE user_taxi_cars SET count = count - 1 WHERE user_id = ? AND car_code = ?",
            (uid, code)
        )
        await db.execute(
            "INSERT INTO user_taxi_park_cars (user_id, car_code, count) "
            "VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, car_code) DO UPDATE SET count = count + 1",
            (uid, code)
        )
        await db.commit()
    await cb.answer(f"Добавлено в парк: {car['name']}", show_alert=True)
    text, reply_markup = await build_taxi_park_add_menu(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
async def _collect_taxi_park_income(uid: int):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        park = await _get_user_taxi_park(db, uid)
        park_cars = await _get_user_taxi_park_cars(db, uid)
        last_ts = park["last_collect_ts"]
        if last_ts == 0:
            await db.execute(
                "UPDATE user_taxi_park SET last_collect_ts = ? WHERE user_id = ?",
                (now, uid)
            )
            await db.commit()
            return False, "Первый сбор доступен через 1 час.", 0
        hours = int((now - last_ts) // 3600)
        if hours <= 0:
            remaining = 3600 - (now - last_ts)
            return False, f"Сбор через {format_duration(remaining)}", 0
        level = park["level"]
        mult = _taxi_park_multiplier(level)
        min_hour = 0
        max_hour = 0
        if not park_cars:
            return False, "В парке нет машин.", 0
        for code, count in park_cars.items():
            car = get_taxi_car_config(code)
            if not car or count <= 0:
                continue
            min_hour += car["park_min"] * count
            max_hour += car["park_max"] * count
        min_hour = int(min_hour * mult)
        max_hour = int(max_hour * mult)
        total_income = 0
        if hours > 48:
            avg = (min_hour + max_hour) / 2
            total_income = int(avg * hours)
        else:
            for _ in range(hours):
                total_income += random.randint(min_hour, max_hour) if max_hour > 0 else 0
        if total_income <= 0:
            return False, "Дохода нет.", 0
        new_ts = last_ts + hours * 3600
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (total_income, uid)
        )
        await db.execute(
            "UPDATE user_taxi_park SET last_collect_ts = ? WHERE user_id = ?",
            (new_ts, uid)
        )
        await db.commit()
    return True, "OK", total_income
@router.message(F.text.lower().in_(["таксопарк", "taxi park"]))
async def taxi_park_text_cmd(msg: Message):
    text, reply_markup = await build_taxi_park_view(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().startswith("собрать доход таксопарка"))
async def taxi_park_collect_msg(msg: Message):
    success, message, total_income = await _collect_taxi_park_income(msg.from_user.id)
    if success:
        await msg.reply(f"Собрано: {format_money(total_income)}", parse_mode="HTML")
    else:
        await msg.reply(f"{message}", parse_mode="HTML")
@router.callback_query(F.data == "taxi_park_collect")
async def taxi_park_collect_cb(cb: CallbackQuery):
    success, message, total_income = await _collect_taxi_park_income(cb.from_user.id)
    if success:
        await cb.answer(f"Собрано: {format_money(total_income)}", show_alert=True)
    else:
        await cb.answer(message, show_alert=True)
    text, reply_markup = await build_taxi_park_view(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "taxi_park_upgrade")
async def taxi_park_upgrade_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    user = await get_user(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        park = await _get_user_taxi_park(db, uid)
        level = park["level"]
        if level >= TAXI_PARK_MAX_LEVEL:
            await cb.answer("Таксопарк уже максимального уровня.", show_alert=True)
            return
        cost_idx = level - 1
        if cost_idx >= len(TAXI_PARK_UPGRADE_COSTS):
            await cb.answer("Upgrade cost not found.", show_alert=True)
            return
        cost = TAXI_PARK_UPGRADE_COSTS[cost_idx]
        if user["balance"] < cost:
            await cb.answer("Недостаточно денег.", show_alert=True)
            return
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (cost, uid)
        )
        await db.execute(
            "UPDATE user_taxi_park SET level = level + 1 WHERE user_id = ?",
            (uid,)
        )
        await db.commit()
    await cb.answer(f"Таксопарк улучшен до уровня {level + 1}.", show_alert=True)
    text, reply_markup = await build_taxi_park_view(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
def get_transport_office_config(code: str):
    for office in TRANSPORT_OFFICES:
        if office["code"] == code:
            return office
    return None
def get_transport_truck_config(code: str):
    for truck in TRANSPORT_TRUCKS:
        if truck["code"] == code:
            return truck
    return None
def get_transport_cargo_config(code: str):
    for cargo in TRANSPORT_CARGO:
        if cargo["code"] == code:
            return cargo
    return None
async def _get_transport_company(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, office_code, active_truck_code FROM transport_companies WHERE owner_user_id = ?",
            (uid,)
        )
        row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "office_code": row["office_code"],
        "active_truck_code": row["active_truck_code"],
    }
async def _get_transport_trucks(db: aiosqlite.Connection, company_id: int) -> dict:
    cursor = await db.execute(
        "SELECT truck_code, count FROM transport_trucks WHERE company_id = ?",
        (company_id,)
    )
    rows = await cursor.fetchall()
    return {row[0]: int(row[1] or 0) for row in rows}
async def _get_transport_order(db: aiosqlite.Connection, company_id: int):
    cursor = await db.execute(
        "SELECT cargo_code, income, risk, started_at, ends_at FROM transport_orders WHERE company_id = ?",
        (company_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "cargo_code": row[0],
        "income": int(row[1] or 0),
        "risk": int(row[2] or 0),
        "started_at": int(row[3] or 0),
        "ends_at": int(row[4] or 0),
    }
def _calc_transport_order(cargo: dict, office: dict, truck: dict):
    office_mult = office["income_mult"] if office else 1.0
    truck_mult = truck["income_mult"] if truck else 1.0
    income = int(cargo["base_income"] * office_mult * truck_mult)
    risk = int(cargo["base_risk"] + (office["risk_add"] if office else 0))
    return max(1, income), min(95, max(0, risk))
async def build_transport_menu(uid: int):
    company = await _get_transport_company(uid)
    if not company:
        text = "🚛 <b>Транспортная компания</b>\n\n"
        text += "У вас нет транспортной компании.\n"
        text += f"Стоимость создания: <b>{format_money(TRANSPORT_CREATE_COST)}</b>\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Создать ТК", callback_data="tc_create")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
        ])
        return text, keyboard
    async with aiosqlite.connect(DB_PATH) as db:
        trucks = await _get_transport_trucks(db, company["id"])
        order = await _get_transport_order(db, company["id"])
    total_trucks = sum(trucks.values())
    office = get_transport_office_config(company["office_code"])
    office_name = office["name"] if office else "Не выбран"
    active_truck = get_transport_truck_config(company["active_truck_code"])
    active_truck_name = active_truck["name"] if active_truck else "Не выбрана"
    text = "🚛 <b>Транспортная компания</b>\n\n"
    text += f"Название: <b>{html.escape(company['name'])}</b>\n"
    text += f"Офис: <b>{office_name}</b>\n"
    text += f"Активная фура: <b>{active_truck_name}</b>\n"
    text += f"Фур в гараже: <b>{total_trucks}</b>\n"
    if order:
        cargo = get_transport_cargo_config(order["cargo_code"])
        cargo_name = cargo["name"] if cargo else order["cargo_code"]
        remaining = max(0, order["ends_at"] - int(time.time()))
        text += "\nАктивный заказ:\n"
        text += f"• Груз: <b>{cargo_name}</b>\n"
        text += f"• Доход: <b>{format_money(order['income'])}</b>\n"
        text += f"• Риск: <b>{order['risk']}%</b>\n"
        if remaining > 0:
            text += f"• До завершения: {format_duration(remaining)}\n"
        else:
            text += "• Готов к завершению\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Офисы", callback_data="tc_offices"),
            InlineKeyboardButton(text="Фуры", callback_data="tc_trucks")
        ],
        [InlineKeyboardButton(text="Заказы", callback_data="tc_orders")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    return text, keyboard
async def build_transport_offices(uid: int):
    company = await _get_transport_company(uid)
    if not company:
        return await build_transport_menu(uid)
    office_code = company["office_code"]
    text = "🏢 <b>Офисы транспортной компании</b>\n\n"
    offices = sorted(TRANSPORT_OFFICES, key=lambda o: o["price"], reverse=True)
    for office in offices:
        bonus = int(round((office["income_mult"] - 1) * 100))
        current = " (выбран)" if office["code"] == office_code else ""
        text += (
            f"{office['name']} - {format_money(office['price'])} "
            f"(+{bonus}% доход, +{office['risk_add']}% риск){current}\n"
        )
    keyboard = []
    for office in offices:
        if office["code"] == office_code:
            continue
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {office['name']} за {format_money(office['price'])}",
                callback_data=f"tc_buy_office_{office['code']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="tc_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_transport_trucks(uid: int):
    company = await _get_transport_company(uid)
    if not company:
        return await build_transport_menu(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        trucks_owned = await _get_transport_trucks(db, company["id"])
    text = "🚛 <b>Фуры транспортной компании</b>\n\n"
    for truck in TRANSPORT_TRUCKS:
        count = trucks_owned.get(truck["code"], 0)
        suffix = f" (в гараже: {count})" if count > 0 else ""
        text += f"{truck['name']} - {format_money(truck['price'])}{suffix}\n"
    keyboard = []
    for truck in TRANSPORT_TRUCKS:
        count = trucks_owned.get(truck["code"], 0)
        if count > 0:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"Выбрать {truck['name']}",
                    callback_data=f"tc_set_truck_{truck['code']}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {truck['name']} за {format_money(truck['price'])}",
                callback_data=f"tc_buy_truck_{truck['code']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="tc_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_transport_orders(uid: int):
    company = await _get_transport_company(uid)
    if not company:
        return await build_transport_menu(uid)
    office = get_transport_office_config(company["office_code"])
    if not office:
        text = "🚛 <b>Заказы</b>\n\nСначала купите офис, чтобы брать заказы."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Офисы", callback_data="tc_offices")],
            [InlineKeyboardButton(text="Назад", callback_data="tc_menu")]
        ])
        return text, keyboard
    async with aiosqlite.connect(DB_PATH) as db:
        trucks_owned = await _get_transport_trucks(db, company["id"])
        order = await _get_transport_order(db, company["id"])
    if not trucks_owned:
        text = "🚛 <b>Заказы</b>\n\nСначала купите фуру."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Фуры", callback_data="tc_trucks")],
            [InlineKeyboardButton(text="Назад", callback_data="tc_menu")]
        ])
        return text, keyboard
    active_truck = get_transport_truck_config(company["active_truck_code"])
    if not active_truck:
        text = "🚛 <b>Заказы</b>\n\nВыберите активную фуру в меню фур."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Фуры", callback_data="tc_trucks")],
            [InlineKeyboardButton(text="Назад", callback_data="tc_menu")]
        ])
        return text, keyboard
    if order:
        cargo = get_transport_cargo_config(order["cargo_code"])
        cargo_name = cargo["name"] if cargo else order["cargo_code"]
        remaining = max(0, order["ends_at"] - int(time.time()))
        text = "🚛 <b>Активный заказ</b>\n\n"
        text += f"Груз: <b>{cargo_name}</b>\n"
        text += f"Доход: <b>{format_money(order['income'])}</b>\n"
        text += f"Риск: <b>{order['risk']}%</b>\n"
        if remaining > 0:
            text += f"До завершения: {format_duration(remaining)}\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Обновить", callback_data="tc_orders")],
                [InlineKeyboardButton(text="Назад", callback_data="tc_menu")]
            ])
        else:
            text += "Заказ готов к завершению.\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Завершить заказ", callback_data="tc_finish")],
                [InlineKeyboardButton(text="Назад", callback_data="tc_menu")]
            ])
        return text, keyboard
    text = "🚛 <b>Взять заказ</b>\n\n"
    text += f"Офис: <b>{office['name']}</b>\n"
    text += f"Фура: <b>{active_truck['name']}</b>\n\n"
    text += f"Время выполнения: {format_duration(TRANSPORT_ORDER_DURATION)}\n\n"
    keyboard = []
    for cargo in TRANSPORT_CARGO:
        income, risk = _calc_transport_order(cargo, office, active_truck)
        text += f"{cargo['name']} - доход {format_money(income)}, риск {risk}%\n"
        keyboard.append([
            InlineKeyboardButton(
                text=f"Взять: {cargo['name']}",
                callback_data=f"tc_take_{cargo['code']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="tc_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.message(F.text.lower().in_(["тк", "транспортная компания", "транс комп", "транс-комп", "транспортнаякомпания"]))
async def transport_company_cmd(msg: Message):
    text, reply_markup = await build_transport_menu(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower() == "моя тк")
async def transport_company_my_cmd(msg: Message):
    text, reply_markup = await build_transport_menu(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "tc_menu")
async def transport_company_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_transport_menu(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "tc_create")
async def transport_company_create_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    company = await _get_transport_company(uid)
    if company:
        await cb.answer("У вас уже есть ТК.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < TRANSPORT_CREATE_COST:
        await cb.answer("Недостаточно денег для создания ТК.", show_alert=True)
        return
    creating_transport_company[uid] = True
    logger.info(f"TC create prompt set uid={uid}")
    await cb.answer()
    await cb.message.answer("Введите название ТК или напишите 'отмена'.")
@router.callback_query(F.data == "tc_offices")
async def transport_company_offices_cb(cb: CallbackQuery):
    text, reply_markup = await build_transport_offices(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("tc_buy_office_"))
async def transport_company_buy_office_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("tc_buy_office_", "")
    office = get_transport_office_config(code)
    if not office:
        await cb.answer("Офис не найден.", show_alert=True)
        return
    company = await _get_transport_company(uid)
    if not company:
        await cb.answer("Сначала создайте ТК.", show_alert=True)
        return
    if company["office_code"] == code:
        await cb.answer("Офис уже выбран.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < office["price"]:
        await cb.answer("Недостаточно денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (office["price"], uid)
        )
        await db.execute(
            "UPDATE transport_companies SET office_code = ? WHERE owner_user_id = ?",
            (code, uid)
        )
        await db.commit()
    await cb.answer(f"Офис куплен: {office['name']}", show_alert=True)
    text, reply_markup = await build_transport_offices(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "tc_trucks")
async def transport_company_trucks_cb(cb: CallbackQuery):
    text, reply_markup = await build_transport_trucks(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("tc_buy_truck_"))
async def transport_company_buy_truck_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("tc_buy_truck_", "")
    truck = get_transport_truck_config(code)
    if not truck:
        await cb.answer("Фура не найдена.", show_alert=True)
        return
    company = await _get_transport_company(uid)
    if not company:
        await cb.answer("Сначала создайте ТК.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < truck["price"]:
        await cb.answer("Недостаточно денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (truck["price"], uid)
        )
        await db.execute(
            "INSERT INTO transport_trucks (company_id, truck_code, count) "
            "VALUES (?, ?, 1) "
            "ON CONFLICT(company_id, truck_code) DO UPDATE SET count = count + 1",
            (company["id"], code)
        )
        if not company["active_truck_code"]:
            await db.execute(
                "UPDATE transport_companies SET active_truck_code = ? WHERE owner_user_id = ?",
                (code, uid)
            )
        await db.commit()
    await cb.answer(f"Фура куплена: {truck['name']}", show_alert=True)
    text, reply_markup = await build_transport_trucks(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("tc_set_truck_"))
async def transport_company_set_truck_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("tc_set_truck_", "")
    truck = get_transport_truck_config(code)
    if not truck:
        await cb.answer("Фура не найдена.", show_alert=True)
        return
    company = await _get_transport_company(uid)
    if not company:
        await cb.answer("Сначала создайте ТК.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM transport_trucks WHERE company_id = ? AND truck_code = ?",
            (company["id"], code)
        )
        row = await cursor.fetchone()
        if not row or int(row[0] or 0) <= 0:
            await cb.answer("У вас нет этой фуры.", show_alert=True)
            return
        await db.execute(
            "UPDATE transport_companies SET active_truck_code = ? WHERE owner_user_id = ?",
            (code, uid)
        )
        await db.commit()
    await cb.answer(f"Активная фура: {truck['name']}", show_alert=True)
    text, reply_markup = await build_transport_trucks(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "tc_orders")
async def transport_company_orders_cb(cb: CallbackQuery):
    text, reply_markup = await build_transport_orders(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("tc_take_"))
async def transport_company_take_order_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("tc_take_", "")
    cargo = get_transport_cargo_config(code)
    if not cargo:
        await cb.answer("Заказ не найден.", show_alert=True)
        return
    company = await _get_transport_company(uid)
    if not company:
        await cb.answer("Сначала создайте ТК.", show_alert=True)
        return
    office = get_transport_office_config(company["office_code"])
    if not office:
        await cb.answer("Сначала купите офис.", show_alert=True)
        return
    active_truck = get_transport_truck_config(company["active_truck_code"])
    if not active_truck:
        await cb.answer("Выберите активную фуру.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        order = await _get_transport_order(db, company["id"])
        if order:
            await cb.answer("У вас уже есть активный заказ.", show_alert=True)
            return
        trucks_owned = await _get_transport_trucks(db, company["id"])
        if trucks_owned.get(active_truck["code"], 0) <= 0:
            await cb.answer("У вас нет выбранной фуры.", show_alert=True)
            return
        income, risk = _calc_transport_order(cargo, office, active_truck)
        now = int(time.time())
        await db.execute(
            "INSERT INTO transport_orders (company_id, cargo_code, income, risk, started_at, ends_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (company["id"], code, income, risk, now, now + TRANSPORT_ORDER_DURATION)
        )
        await db.commit()
    await cb.answer("Заказ принят.", show_alert=True)
    text, reply_markup = await build_transport_orders(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "tc_finish")
async def transport_company_finish_order_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    company = await _get_transport_company(uid)
    if not company:
        await cb.answer("Сначала создайте ТК.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        order = await _get_transport_order(db, company["id"])
        if not order:
            await cb.answer("Активного заказа нет.", show_alert=True)
            return
        now = int(time.time())
        if order["ends_at"] > now:
            remaining = order["ends_at"] - now
            await cb.answer(f"До завершения: {format_duration(remaining)}", show_alert=True)
            return
        success = random.random() >= (order["risk"] / 100)
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "DELETE FROM transport_orders WHERE company_id = ?",
            (company["id"],)
        )
        if success:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (order["income"], uid)
            )
        await db.commit()
    if success:
        await cb.answer(f"Заказ выполнен! Доход: {format_money(order['income'])}", show_alert=True)
    else:
        await cb.answer("Заказ провален из-за риска. Доход не получен.", show_alert=True)
    text, reply_markup = await build_transport_menu(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
def get_construction_office(level: int):
    for office in CONSTRUCTION_OFFICES:
        if office["level"] == level:
            return office
    return None
def get_construction_project(code: str):
    for project in CONSTRUCTION_PROJECTS:
        if project["code"] == code:
            return project
    return None
async def _get_construction_company(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, office_level FROM construction_companies WHERE owner_user_id = ?",
            (uid,)
        )
        row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "office_level": int(row["office_level"] or 0)
    }
async def _get_construction_resources(db: aiosqlite.Connection, company_id: int):
    cursor = await db.execute(
        "SELECT workers, materials, land FROM construction_resources WHERE company_id = ?",
        (company_id,)
    )
    row = await cursor.fetchone()
    if not row:
        await db.execute(
            "INSERT INTO construction_resources (company_id, workers, materials, land) VALUES (?, 0, 0, 0)",
            (company_id,)
        )
        await db.commit()
        return {"workers": 0, "materials": 0, "land": 0}
    return {"workers": int(row[0] or 0), "materials": int(row[1] or 0), "land": int(row[2] or 0)}
async def _get_construction_project(db: aiosqlite.Connection, company_id: int):
    cursor = await db.execute(
        "SELECT project_code, income, risk, started_at, ends_at FROM construction_projects WHERE company_id = ?",
        (company_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "project_code": row[0],
        "income": int(row[1] or 0),
        "risk": int(row[2] or 0),
        "started_at": int(row[3] or 0),
        "ends_at": int(row[4] or 0),
    }
def _calc_construction_income(project: dict, office: dict):
    mult = office["income_mult"] if office else 1.0
    income = int(project["base_income"] * mult)
    risk = int(project["base_risk"] + (office["risk_add"] if office else 0))
    return max(1, income), min(95, max(0, risk))
async def build_construction_menu(uid: int):
    company = await _get_construction_company(uid)
    if not company:
        text = "🏗️ <b>Строительная компания</b>\n\n"
        text += "У вас нет строительной компании.\n"
        text += f"Стоимость создания: <b>{format_money(CONSTRUCTION_CREATE_COST)}</b>\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Создать СК", callback_data="sc_create")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
        ])
        return text, keyboard
    async with aiosqlite.connect(DB_PATH) as db:
        resources = await _get_construction_resources(db, company["id"])
        project = await _get_construction_project(db, company["id"])
    office = get_construction_office(company["office_level"])
    office_name = office["name"] if office else "Не выбран"
    text = "🏗️ <b>Строительная компания</b>\n\n"
    text += f"Название: <b>{html.escape(company['name'])}</b>\n"
    text += f"Офис: <b>{office_name}</b>\n"
    text += f"Рабочие: <b>{resources['workers']}</b>\n"
    text += f"Материалы: <b>{resources['materials']}</b>\n"
    text += f"Территория: <b>{resources['land']}</b>\n"
    if project:
        proj = get_construction_project(project["project_code"])
        proj_name = proj["name"] if proj else project["project_code"]
        remaining = max(0, project["ends_at"] - int(time.time()))
        text += "\nАктивный объект:\n"
        text += f"• Объект: <b>{proj_name}</b>\n"
        text += f"• Доход: <b>{format_money(project['income'])}</b>\n"
        text += f"• Риск: <b>{project['risk']}%</b>\n"
        if remaining > 0:
            text += f"• До завершения: {format_duration(remaining)}\n"
        else:
            text += "• Готов к завершению\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Офисы", callback_data="sc_offices"),
            InlineKeyboardButton(text="Ресурсы", callback_data="sc_resources")
        ],
        [InlineKeyboardButton(text="Объекты", callback_data="sc_projects")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    return text, keyboard
async def build_construction_offices(uid: int):
    company = await _get_construction_company(uid)
    if not company:
        return await build_construction_menu(uid)
    current_level = company["office_level"]
    text = "🏢 <b>Офисы строительной компании</b>\n\n"
    for office in CONSTRUCTION_OFFICES:
        bonus = int(round((office["income_mult"] - 1) * 100))
        current = " (выбран)" if office["level"] == current_level else ""
        text += (
            f"Ур. {office['level']}: {office['name']} - {format_money(office['price'])} "
            f"(+{bonus}% доход, +{office['risk_add']}% риск){current}\n"
        )
    keyboard = []
    for office in CONSTRUCTION_OFFICES:
        if office["level"] <= current_level:
            continue
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить ур. {office['level']} за {format_money(office['price'])}",
                callback_data=f"sc_buy_office_{office['level']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sc_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_construction_resources(uid: int):
    company = await _get_construction_company(uid)
    if not company:
        return await build_construction_menu(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        resources = await _get_construction_resources(db, company["id"])
    text = "🧱 <b>Ресурсы</b>\n\n"
    text += f"Рабочие: <b>{resources['workers']}</b>\n"
    text += f"Материалы: <b>{resources['materials']}</b>\n"
    text += f"Территория: <b>{resources['land']}</b>\n\n"
    text += "Покупка ресурсов:\n"
    text += f"• Рабочие: {format_money(CONSTRUCTION_RESOURCE_PRICES['workers'])} за 1\n"
    text += f"• Материалы: {format_money(CONSTRUCTION_RESOURCE_PRICES['materials'])} за 1\n"
    text += f"• Территория: {format_money(CONSTRUCTION_RESOURCE_PRICES['land'])} за 1\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Рабочие x10", callback_data="sc_buy_workers_10"),
            InlineKeyboardButton(text="Рабочие x50", callback_data="sc_buy_workers_50")
        ],
        [
            InlineKeyboardButton(text="Материалы x100", callback_data="sc_buy_materials_100"),
            InlineKeyboardButton(text="Материалы x500", callback_data="sc_buy_materials_500")
        ],
        [
            InlineKeyboardButton(text="Территория x1", callback_data="sc_buy_land_1"),
            InlineKeyboardButton(text="Территория x5", callback_data="sc_buy_land_5")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="sc_menu")]
    ])
    return text, keyboard
async def build_construction_projects(uid: int):
    company = await _get_construction_company(uid)
    if not company:
        return await build_construction_menu(uid)
    office = get_construction_office(company["office_level"])
    if not office:
        text = "🏗️ <b>Объекты</b>\n\nСначала купите офис."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Офисы", callback_data="sc_offices")],
            [InlineKeyboardButton(text="Назад", callback_data="sc_menu")]
        ])
        return text, keyboard
    async with aiosqlite.connect(DB_PATH) as db:
        project = await _get_construction_project(db, company["id"])
    if project:
        proj = get_construction_project(project["project_code"])
        proj_name = proj["name"] if proj else project["project_code"]
        remaining = max(0, project["ends_at"] - int(time.time()))
        text = "🏗️ <b>Активный объект</b>\n\n"
        text += f"Объект: <b>{proj_name}</b>\n"
        text += f"Доход: <b>{format_money(project['income'])}</b>\n"
        text += f"Риск: <b>{project['risk']}%</b>\n"
        if remaining > 0:
            text += f"До завершения: {format_duration(remaining)}\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Обновить", callback_data="sc_projects")],
                [InlineKeyboardButton(text="Назад", callback_data="sc_menu")]
            ])
        else:
            text += "Объект готов к сдаче.\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сдать объект", callback_data="sc_finish")],
                [InlineKeyboardButton(text="Назад", callback_data="sc_menu")]
            ])
        return text, keyboard
    text = "🏗️ <b>Выберите объект</b>\n\n"
    text += f"Офис: <b>{office['name']}</b>\n\n"
    keyboard = []
    for proj in CONSTRUCTION_PROJECTS:
        if proj["min_level"] > company["office_level"]:
            continue
        income, risk = _calc_construction_income(proj, office)
        text += (
            f"{proj['name']} | "
            f"Рабочие {proj['workers']}, Материалы {proj['materials']}, Территория {proj['land']} | "
            f"Доход {format_money(income)} | Риск {risk}% | Время {format_duration(proj['duration'])}\n"
        )
        keyboard.append([
            InlineKeyboardButton(
                text=f"Начать: {proj['name']}",
                callback_data=f"sc_start_{proj['code']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sc_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.message(F.text.lower().in_(["ск", "строительная компания", "стройкомп", "строй-комп", "строительнаякомпания"]))
async def construction_company_cmd(msg: Message):
    text, reply_markup = await build_construction_menu(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower() == "моя ск")
async def construction_company_my_cmd(msg: Message):
    text, reply_markup = await build_construction_menu(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "sc_menu")
async def construction_company_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_construction_menu(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "sc_create")
async def construction_company_create_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    company = await _get_construction_company(uid)
    if company:
        await cb.answer("У вас уже есть СК.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < CONSTRUCTION_CREATE_COST:
        await cb.answer("Недостаточно денег для создания СК.", show_alert=True)
        return
    creating_construction_company[uid] = True
    logger.info(f"SC create prompt set uid={uid}")
    await cb.answer()
    await cb.message.answer("Введите название СК или напишите 'отмена'.")
@router.callback_query(F.data == "sc_offices")
async def construction_company_offices_cb(cb: CallbackQuery):
    text, reply_markup = await build_construction_offices(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("sc_buy_office_"))
async def construction_company_buy_office_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    level_str = cb.data.replace("sc_buy_office_", "")
    if not level_str.isdigit():
        await cb.answer("Офис не найден.", show_alert=True)
        return
    level = int(level_str)
    office = get_construction_office(level)
    if not office:
        await cb.answer("Офис не найден.", show_alert=True)
        return
    company = await _get_construction_company(uid)
    if not company:
        await cb.answer("Сначала создайте СК.", show_alert=True)
        return
    if company["office_level"] >= level:
        await cb.answer("Офис уже куплен.", show_alert=True)
        return
    user = await get_user(uid)
    if user["balance"] < office["price"]:
        await cb.answer("Недостаточно денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (office["price"], uid)
        )
        await db.execute(
            "UPDATE construction_companies SET office_level = ? WHERE owner_user_id = ?",
            (level, uid)
        )
        await db.commit()
    await cb.answer(f"Офис улучшен до уровня {level}.", show_alert=True)
    text, reply_markup = await build_construction_offices(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "sc_resources")
async def construction_company_resources_cb(cb: CallbackQuery):
    text, reply_markup = await build_construction_resources(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
async def _buy_construction_resource(uid: int, resource: str, qty: int):
    company = await _get_construction_company(uid)
    if not company:
        return False, "Сначала создайте СК."
    price_per = CONSTRUCTION_RESOURCE_PRICES.get(resource, 0)
    if price_per <= 0:
        return False, "Ресурс не найден."
    total_cost = price_per * qty
    user = await get_user(uid)
    if user["balance"] < total_cost:
        return False, "Недостаточно денег."
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?",
            (total_cost, uid)
        )
        await db.execute(
            f"UPDATE construction_resources SET {resource} = {resource} + ? WHERE company_id = ?",
            (qty, company["id"])
        )
        await db.commit()
    return True, f"Куплено: {resource} x{qty}"
@router.callback_query(F.data.startswith("sc_buy_workers_"))
async def construction_company_buy_workers_cb(cb: CallbackQuery):
    qty = int(cb.data.replace("sc_buy_workers_", "") or 0)
    success, msg = await _buy_construction_resource(cb.from_user.id, "workers", qty)
    await cb.answer(msg, show_alert=True)
    text, reply_markup = await build_construction_resources(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("sc_buy_materials_"))
async def construction_company_buy_materials_cb(cb: CallbackQuery):
    qty = int(cb.data.replace("sc_buy_materials_", "") or 0)
    success, msg = await _buy_construction_resource(cb.from_user.id, "materials", qty)
    await cb.answer(msg, show_alert=True)
    text, reply_markup = await build_construction_resources(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("sc_buy_land_"))
async def construction_company_buy_land_cb(cb: CallbackQuery):
    qty = int(cb.data.replace("sc_buy_land_", "") or 0)
    success, msg = await _buy_construction_resource(cb.from_user.id, "land", qty)
    await cb.answer(msg, show_alert=True)
    text, reply_markup = await build_construction_resources(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "sc_projects")
async def construction_company_projects_cb(cb: CallbackQuery):
    text, reply_markup = await build_construction_projects(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("sc_start_"))
async def construction_company_start_project_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    code = cb.data.replace("sc_start_", "")
    project = get_construction_project(code)
    if not project:
        await cb.answer("Объект не найден.", show_alert=True)
        return
    company = await _get_construction_company(uid)
    if not company:
        await cb.answer("Сначала создайте СК.", show_alert=True)
        return
    office = get_construction_office(company["office_level"])
    if not office or company["office_level"] < project["min_level"]:
        await cb.answer("Недостаточный уровень офиса.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        resources = await _get_construction_resources(db, company["id"])
        active = await _get_construction_project(db, company["id"])
        if active:
            await cb.answer("У вас уже есть активный объект.", show_alert=True)
            return
        if resources["workers"] < project["workers"] or resources["materials"] < project["materials"] or resources["land"] < project["land"]:
            await cb.answer("Недостаточно ресурсов.", show_alert=True)
            return
        income, risk = _calc_construction_income(project, office)
        now = int(time.time())
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE construction_resources SET workers = workers - ?, materials = materials - ?, land = land - ? WHERE company_id = ?",
            (project["workers"], project["materials"], project["land"], company["id"])
        )
        await db.execute(
            "INSERT INTO construction_projects (company_id, project_code, income, risk, started_at, ends_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (company["id"], code, income, risk, now, now + project["duration"])
        )
        await db.commit()
    await cb.answer("Объект в работе.", show_alert=True)
    text, reply_markup = await build_construction_projects(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "sc_finish")
async def construction_company_finish_project_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    company = await _get_construction_company(uid)
    if not company:
        await cb.answer("Сначала создайте СК.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        project = await _get_construction_project(db, company["id"])
        if not project:
            await cb.answer("Активного объекта нет.", show_alert=True)
            return
        now = int(time.time())
        if project["ends_at"] > now:
            remaining = project["ends_at"] - now
            await cb.answer(f"До завершения: {format_duration(remaining)}", show_alert=True)
            return
        success = random.random() >= (project["risk"] / 100)
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "DELETE FROM construction_projects WHERE company_id = ?",
            (company["id"],)
        )
        if success:
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (project["income"], uid)
            )
        await db.commit()
    if success:
        await cb.answer(f"Объект сдан! Доход: {format_money(project['income'])}", show_alert=True)
    else:
        await cb.answer("Обрушение! Объект провален, дохода нет.", show_alert=True)
    text, reply_markup = await build_construction_menu(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
ORE_CONFIG = {
    "stone": {"name": "Камень", "price": 50_000},
    "coal": {"name": "Уголь", "price": 120_000},
    "copper": {"name": "Медь", "price": 200_000},
    "iron": {"name": "Железо", "price": 350_000},
    "emerald": {"name": "Изумруд", "price": 800_000},
    "diamond": {"name": "Алмаз", "price": 1_500_000},
    "ancient": {"name": "Древний обломок", "price": 5_000_000},
}
ORE_KEYS = list(ORE_CONFIG.keys())
PICKAXE_CONFIG = [
    {"level": 1, "name": "Деревянная кирка", "price": 5_000_000, "weights": [60, 20, 10, 7, 2, 1, 0]},
    {"level": 2, "name": "Каменная кирка", "price": 10_000_000, "weights": [40, 25, 15, 10, 6, 3, 1]},
    {"level": 3, "name": "Железная кирка", "price": 25_000_000, "weights": [25, 20, 20, 15, 10, 7, 3]},
    {"level": 4, "name": "Алмазная кирка", "price": 50_000_000, "weights": [15, 18, 20, 17, 13, 12, 5]},
    {"level": 5, "name": "Незеритовая кирка", "price": 120_000_000, "weights": [8, 12, 18, 20, 18, 16, 8]},
]
BOSS_TEMPLATES = [
    {"name": "Капитан Лутер", "tier": 1, "max_hp": 1_200_000, "attack_power": 8_000},
    {"name": "Техномонстр Грейд", "tier": 2, "max_hp": 3_500_000, "attack_power": 15_000},
    {"name": "Барон Пустоты", "tier": 3, "max_hp": 8_000_000, "attack_power": 30_000},
    {"name": "Генерал Армагеддон", "tier": 4, "max_hp": 18_000_000, "attack_power": 70_000},
    {"name": "Император Облом", "tier": 5, "max_hp": 40_000_000, "attack_power": 140_000},
    {"name": "ЖИРНЫЙ СИГМА ЯРИК", "tier": 6, "max_hp": 180_000_000, "attack_power": 250_000},
]
BOSS_REWARD_CONFIG = {
    1: {"money": 50_000, "plasma": 1, "unique_chance": 0.01},
    2: {"money": 100_000, "plasma": 2, "unique_chance": 0.02},
    3: {"money": 200_000, "plasma": 3, "unique_chance": 0.03},
    4: {"money": 350_000, "plasma": 5, "unique_chance": 0.04},
    5: {"money": 500_000, "plasma": 7, "unique_chance": 0.05},
    6: {"money": 800_000, "plasma": 10, "unique_chance": 0.06},
}
BOSS_REWARD_MULTIPLIER = 15

UNIQUE_ITEMS = [
    {
        "item_id": "U1_LUTER_BADGE",
        "boss_tier": 1,
        "name": "Жетон Лутера",
        "item_type": "artifact",
        "slot": "support",
        "power_flat": 500,
        "boss_damage_mult": 0.05,
        "rarity": "rare",
        "description": "Полевой символ капитана Лутера.",
    },
    {
        "item_id": "U1_LUTER_MANUAL",
        "boss_tier": 1,
        "name": "Полевой Устав Лутера",
        "item_type": "relic",
        "slot": "relic",
        "people_loss_reduction": 0.08,
        "rarity": "rare",
        "description": "Снижает потери людей в бою.",
    },
    {
        "item_id": "U2_GRADE_AI",
        "boss_tier": 2,
        "name": "ИИ-Модуль Грейда",
        "item_type": "module",
        "slot": "core",
        "power_mult": 0.08,
        "boss_damage_mult": 0.10,
        "upkeep_mult": 0.05,
        "rarity": "epic",
        "description": "Усиливает тактику и расходы на содержание.",
    },
    {
        "item_id": "U2_GRADE_PLATES",
        "boss_tier": 2,
        "name": "Пластины Грейда",
        "item_type": "module",
        "slot": "support",
        "vehicle_loss_reduction": 0.10,
        "rarity": "epic",
        "description": "Снижает потери техники.",
    },
    {
        "item_id": "U3_VOID_SPHERE",
        "boss_tier": 3,
        "name": "Сфера Пустоты",
        "item_type": "relic",
        "slot": "core",
        "power_mult": 0.10,
        "people_loss_reduction": 0.12,
        "rarity": "epic",
        "description": "Усиливает армию и снижает потери людей.",
    },
    {
        "item_id": "U3_VOID_SEAL",
        "boss_tier": 3,
        "name": "Печать Пустоты",
        "item_type": "artifact",
        "slot": "support",
        "boss_damage_mult": 0.12,
        "rarity": "epic",
        "description": "Увеличивает урон по боссам.",
    },
    {
        "item_id": "U4_ARMAGEDDON_CORE",
        "boss_tier": 4,
        "name": "Ядро Армагеддона",
        "item_type": "module",
        "slot": "core",
        "power_mult": 0.14,
        "vehicle_loss_reduction": 0.12,
        "upkeep_mult": 0.10,
        "rarity": "legendary",
        "description": "Сильный модуль с повышенным содержанием.",
    },
    {
        "item_id": "U4_ARMAGEDDON_MAP",
        "boss_tier": 4,
        "name": "Карта Операций Армагеддона",
        "item_type": "relic",
        "slot": "relic",
        "power_flat": 2500,
        "boss_damage_mult": 0.08,
        "rarity": "legendary",
        "description": "Тактическая карта боевых действий.",
    },
    {
        "item_id": "U5_OBLOM_RELICT_T34",
        "boss_tier": 5,
        "name": "Т-34: Реликт Облома",
        "item_type": "vehicle",
        "slot": "core",
        "power_flat": 6000,
        "vehicle_loss_reduction": 0.18,
        "rarity": "legendary",
        "description": "Уникальная техника с бонусом к силе.",
    },
    {
        "item_id": "U5_OBLOM_CROWN",
        "boss_tier": 5,
        "name": "Корона Облома",
        "item_type": "relic",
        "slot": "support",
        "power_mult": 0.18,
        "upkeep_mult": 0.12,
        "rarity": "legendary",
        "description": "Сильный буст силы ценой содержания.",
    },
    {
        "item_id": "U6_YARIK_SIGMA_DILDO",
        "boss_tier": 6,
        "name": "Дилдо Сигмы Ярика",
        "item_type": "relic",
        "slot": "core",
        "power_mult": 0.22,
        "boss_damage_mult": 0.18,
        "ignore_defense": 0.10,
        "upkeep_mult": 0.15,
        "rarity": "mythic",
        "description": "Мем-артефакт с сильными эффектами.",
    },
    {
        "item_id": "U6_YARIK_MAGIC_PANTIES",
        "boss_tier": 6,
        "name": "Волшебные Труселя Сигмы Ярика",
        "item_type": "artifact",
        "slot": "support",
        "people_loss_reduction": 0.20,
        "vehicle_loss_reduction": 0.15,
        "power_flat": 4000,
        "rarity": "mythic",
        "description": "Снижает потери и усиливает армию.",
    },
    {
        "item_id": "U6_YARIK_SIGMA_BADGE",
        "boss_tier": 6,
        "name": "Титул: Сигма-Ярик",
        "item_type": "cosmetic",
        "slot": None,
        "rarity": "mythic",
        "description": "Косметический титул без боевых бонусов.",
    },
]
UNIQUE_LOOT_CHANCES = {
    1: 0.08,
    2: 0.06,
    3: 0.05,
    4: 0.04,
    5: 0.03,
    6: 0.02,
}
UNIQUE_TOP_BONUS = {
    1: 0.03,
    2: 0.02,
    3: 0.01,
}
UNIQUE_POWER_MULT_CAP = 0.40
UNIQUE_BOSS_DMG_CAP = 0.30
UNIQUE_LOSS_REDUCTION_CAP = 0.25
# ========== МАЙНИНГ БИТКОИНОВ ==========
class BitcoinMining:
    """Класс для майнинга биткоинов"""
    @staticmethod
    def calculate_hashrate(gpu_count: int, gpu_level: int) -> float:
        """Вычисляет хешрейт на основе видеокарт"""
        base_hashrate = 10_000_000
        # Множители - высшие уровни ВЫГОДНЕЕ
        level_multipliers = {
            1: 1.0,    # ×1 (база)
            2: 4.0,    # ×4 (в 4 раза мощнее уровня 1)
            3: 20.0,   # ×20 (в 5 раз мощнее уровня 2)
            4: 120.0,  # ×120 (в 6 раз мощнее уровня 3)
            5: 840.0   # ×840 (в 7 раз мощнее уровня 4)
        }
        multiplier = level_multipliers.get(gpu_level, 1.0)
        return gpu_count * base_hashrate * multiplier
    @staticmethod
    def calculate_btc_per_hour(hashrate: float) -> float:
        """Вычисляет сколько BTC добывается в час"""
        # 10 миллионов MH/s = 0.04 BTC/час
        return (hashrate / 10_000_000) * 0.04 * 5.0 * INCOME_MULTIPLIER
    @staticmethod
    def get_bitcoin_price() -> float:
        """Текущая цена биткоина в $"""
        base_price = 150_000  # 90к$ за BTC (было 60к)
        fluctuation = random.uniform(-0.05, 0.05)  # ±5%
        return base_price * (1 + fluctuation)
    @staticmethod
    def get_gpu_price(gpu_level: int) -> int:
        """Цена видеокарты"""
        base_prices = {
            1: 7_200_000,      # 7.2М
            2: 20_000_000,     # 20М (в 2.78 раза дороже уровня 1)
            3: 80_000_000,     # 80М (в 4 раза дороже уровня 2)
            4: 400_000_000,    # 400М (в 5 раз дороже уровня 3)
            5: 2_400_000_000   # 2.4Б (в 6 раз дороже уровня 4)
        }
        return scale_price(base_prices.get(gpu_level, 7_200_000))
    # ========== КЛАСС ДЛЯ УПРАВЛЕНИЯ ИГРОЙ КРАШ ==========
class CrashGameManager:
    @staticmethod
    def is_game_active(user_id: int) -> bool:
        """Проверяет, есть ли активная игра у пользователя"""
        if user_id in crash_games:
            game = crash_games[user_id]
            # Проверяем, не устарела ли игра (максимум 5 минут)
            if "timestamp" in game and time.time() - game["timestamp"] > 300:
                del crash_games[user_id]
                return False
            return game.get("active", False)
        return False
    @staticmethod
    def start_game(user_id: int, bet: int, message_id: int):
        """Начинает новую игру"""
        crash_games[user_id] = {
            "active": True,
            "message_id": message_id,
            "bet": bet,
            "multiplier": 1.0,
            "crashed": False,
            "cashed_out": False,
            "cashout_multiplier": 0,
            "timestamp": time.time()
        }
    @staticmethod
    def update_multiplier(user_id: int, multiplier: float):
        """Обновляет текущий множитель"""
        if user_id in crash_games:
            crash_games[user_id]["multiplier"] = multiplier
    @staticmethod
    def cash_out(user_id: int):
        """Игрок забирает деньги"""
        if user_id in crash_games and crash_games[user_id]["active"]:
            game = crash_games[user_id]
            # Применяем house edge (комиссию) к выплате
            HOUSE_EDGE = 0.97  # 3% комиссия
            original_mul = float(game.get("multiplier", 1.0))
            effective_mul = round(original_mul * HOUSE_EDGE, 2)
            game["cashed_out"] = True
            # храним оригинальный и эффективный множитель
            game["cashout_multiplier_raw"] = original_mul
            game["cashout_multiplier"] = effective_mul
            # сохраняем рассчитанную выплату (целое число монет)
            try:
                bet = int(game.get("bet", 0))
            except:
                bet = 0
            game["payout"] = int(math.floor(bet * effective_mul)) if bet > 0 else 0
            game["active"] = False
            return True, effective_mul
        return False, 0
    @staticmethod
    def crash_game(user_id: int):
        """Игра крашится"""
        if user_id in crash_games:
            crash_games[user_id]["crashed"] = True
            crash_games[user_id]["active"] = False
    @staticmethod
    def end_game(user_id: int):
        """Завершает игру"""
        if user_id in crash_games:
            del crash_games[user_id]
    @staticmethod
    def get_game_info(user_id: int):
        """Получает информацию об игре"""
        return crash_games.get(user_id)
    # ========== ОТДЕЛЬНЫЕ ФУНКЦИИ ДЛЯ НАКОПЛЕНИЙ ==========
async def calculate_and_update_mining(uid: int):
    """Рассчитать и обновить накопленные BTC - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT mining_gpu_count, mining_gpu_level, bitcoin, last_mining_claim FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if not row or row['mining_gpu_count'] == 0:
                logger.debug(f"⛏️ У пользователя {uid} нет видеокарт для майнинга")
                return 0
            current_time = int(time.time())
            if not row['last_mining_claim']:
                await db.execute(
                    "UPDATE users SET last_mining_claim = ? WHERE id = ?",
                    (current_time, uid)
                )
                await db.commit()
                return 0
            last_claim = row['last_mining_claim']
            # Рассчитываем накопления
            hashrate = BitcoinMining.calculate_hashrate(
                row['mining_gpu_count'],
                row['mining_gpu_level']
            )
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            # Применить эффекты мирового события
            world_effects = await get_world_event_effects()
            mining_effect = world_effects.get('mining', 0.0)
            btc_per_hour *= (1 + mining_effect)
            time_passed = current_time - last_claim
            # Минимум 10 секунд для предотвращения спама
            if time_passed < 10:
                logger.debug(f"⏳ Слишком мало времени прошло: {time_passed} сек")
                return 0
            # Максимум 30 дней накопления
            max_seconds = 30 * 24 * 3600
            time_passed = min(time_passed, max_seconds)
            btc_mined = btc_per_hour * (time_passed / 3600)
            logger.info(f"⛏️ Расчет для {uid}: {time_passed} сек = {btc_mined:.8f} BTC")
            if btc_mined > 0:
                # НЕ обнуляем last_mining_claim, только начисляем BTC!
                await db.execute(
                    "UPDATE users SET bitcoin = bitcoin + ?, last_mining_claim = ? WHERE id = ?",
                    (btc_mined, current_time, uid)
                )
                await db.commit()
                logger.info(f"✅ Начислено BTC для {uid}: {btc_mined:.6f} за {time_passed/3600:.1f} часов")
                return btc_mined
            return 0
    except Exception as e:
        logger.error(f"❌ Ошибка calculate_and_update_mining для {uid}: {e}")
        return 0
async def calculate_and_update_plasma(uid: int):
    """Рассчитать и обновить накопленную плазму (вызывать только при открытии панели планет)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем планеты пользователя
            cursor = await db.execute("SELECT * FROM planets WHERE user_id = ?", (uid,))
            rows = await cursor.fetchall()
            if not rows:
                return 0
            current_time = int(time.time())
            total_plasma_mined = 0
            for row in rows:
                planet_id = row['planet_id']
                if planet_id in PLANETS:
                    planet_info = PLANETS[planet_id]
                    last_collected = row['last_collected'] or current_time
                    # Рассчитываем сколько плазмы накопилось
                    time_passed = current_time - last_collected
                    if time_passed > 0:
                        # Максимум 30 дней накопления
                        max_seconds = 30 * 24 * 3600
                        time_passed = min(time_passed, max_seconds)
                        plasma_per_hour = planet_info['plasma_per_hour']
                        plasma_mined = int((time_passed / 3600) * plasma_per_hour)
                        if plasma_mined > 0:
                            total_plasma_mined += plasma_mined
                            # Обновляем время последнего сбора для планеты
                            await db.execute("""
                                UPDATE planets
                                SET last_collected = ?
                                WHERE user_id = ? AND planet_id = ?
                            """, (current_time, uid, planet_id))
            if total_plasma_mined > 0:
                # Начисляем плазму
                await db.execute(
                    "UPDATE users SET plasma = plasma + ? WHERE id = ?",
                    (total_plasma_mined, uid)
                )
                await db.commit()
                logger.info(f"✅ Начислено плазмы для {uid}: {total_plasma_mined}")
                return total_plasma_mined
            return 0
    except Exception as e:
        logger.error(f"❌ Ошибка calculate_and_update_plasma для {uid}: {e}")
        return 0
async def lazy_update_plasma(uid: int, min_interval: int = 120):
    """Ленивое автоначисление плазмы с in-memory троттлингом.
    Вызывать при любом действии пользователя (middleware или начало handler).
    Не должно быть сайд-эффектов в get_user().
    """
    try:
        now = time.time()
        last = last_plasma_tick.get(uid, 0)
        if now - last < min_interval:
            return 0
        # Обновляем метку сразу, чтобы избегать параллельных вызовов
        last_plasma_tick[uid] = now
        # Вызов функции начисления (она сама обновляет БД и возвращает начисленную плазму)
        added = await calculate_and_update_plasma(uid)
        return added
    except Exception as e:
        logger.error(f"Ошибка lazy_update_plasma для {uid}: {e}")
        return 0
    # ========== КРАШ ИГРА ==========
class CrashGame:
    @staticmethod
    def generate_multiplier():
        """Генерирует множитель с вероятностью краха"""
        # Базовый алгоритм: 95% шанс что множитель будет от 1.1x до 10x
        if random.random() < 0.95:
            # Плавное распределение: чаще маленькие множители
            base = random.uniform(1.1, 3.0)
            # 30% шанс на большой множитель
            if random.random() < 0.3:
                base = random.uniform(2.0, 10.0)
            return round(base, 2)
        else:
            # 5% шанс на крах (множитель 0)
            return 0
    @staticmethod
    def get_potential_win(bet: int, multiplier: float):
        """Рассчитать потенциальный выигрыш"""
        if multiplier == 0:
            return 0
        return int(bet * multiplier)
    @staticmethod
    def get_crash_point():
        """Генерирует точку краха (когда игра остановится)"""
        # Новое распределение для краша:
        # - Небольшой шанс instant crash (1.00) ~8-12%
        # - Большая часть выпадов даёт маленькие множители (1.02-1.3), чтобы снизить RTP
        # - Редкие большие множители дают джекпоты
        p_instant = 0.10  # целевой ~10% (между 8 и 12%)
        if random.random() < p_instant:
            return 1.00
        r = random.random()
        # 55% — маленькие множители 1.02–1.30
        if r < 0.55:
            return round(random.uniform(1.02, 1.30), 2)
        # 30% — средние 1.30–2.00
        if r < 0.85:
            return round(random.uniform(1.30, 2.00), 2)
        # 10% — большие 2.00–5.00
        if r < 0.95:
            return round(random.uniform(2.00, 5.00), 2)
        # 5% — редкие огромные множители 5.00–20.00
        return round(random.uniform(5.00, 20.00), 2)
# ========== ЛОТЕРЕЙНАЯ СИСТЕМА ==========
LOTTERY_TICKETS = {
    1: {
        'name': '🎫 Бронзовый билет',
        'price': 50_000_000,  # 50М
        'prize_pool_percent': 0.7,  # 70% от всех продаж идет в призовой фонд
        'min_prize': 100_000_000,  # Минимальный приз 100М
        'emoji': '🥉'
    },
    2: {
        'name': '🎫 Золотой билет',
        'price': 100_000_000,  # 100М
        'prize_pool_percent': 0.8,  # 80% от всех продаж идет в призовой фонд
        'min_prize': 250_000_000,  # Минимальный приз 250М
        'emoji': '🥇'
    }
}
# Глобальная переменная для хранения данных лотереи
lottery_data = {
    'last_reset': time.time(),
    'bronze_tickets_sold': 0,
    'bronze_prize_pool': 0,
    'bronze_players': [],  # Список кортежей (user_id, ticket_count)
    'gold_tickets_sold': 0,
    'gold_prize_pool': 0,
    'gold_players': [],   # Список кортежей (user_id, ticket_count)
    'last_winners': []
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
# ========== ПРОДАЖА ПЛАЗМЫ ==========
PLASMA_PRICE_PER_UNIT = 5_500_000  # 5.5М за 1 единицу плазмы
PLASMA_PRICE_FLUCTUATION = 0.1     # ±10% колебания цены
PLUTONIUM_PRICE_PER_UNIT = 25_000_000  # 25М за 1 единицу плутония
ARTIFACT_PRICE_PER_UNIT = 50_000_000  # 50М за 1 артефакт
def get_plasma_price():
    """Текущая цена плазмы с колебаниями"""
    base_price = PLASMA_PRICE_PER_UNIT
    fluctuation = random.uniform(-PLASMA_PRICE_FLUCTUATION, PLASMA_PRICE_FLUCTUATION)
    return int(base_price * (1 + fluctuation))
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
def apply_economy_scaling():
    global TAXI_PARK_UPGRADE_COSTS
    global TRANSPORT_CREATE_COST
    global CONSTRUCTION_CREATE_COST
    for data in BUSINESS_DEFS.values():
        data["base_cost"] = scale_price(data.get("base_cost", 0))
    for data in LEGACY_BUSINESS_DEFS.values():
        data["price"] = scale_price(data.get("price", 0))
    for tech in SPACE_TECH_CONFIG:
        tech["cost_plasma"] = scale_price(tech.get("cost_plasma", 0))
        tech["cost_plutonium"] = scale_price(tech.get("cost_plutonium", 0))
    for data in BUILDING_CONFIG.values():
        data["base_cost"] = scale_price(data.get("base_cost", 0))
    for data in ITEM_CONFIG.values():
        data["price_money"] = scale_price(data.get("price_money", 0))
        data["price_plutonium"] = scale_price(data.get("price_plutonium", 0))
        data["price_plasma"] = scale_price(data.get("price_plasma", 0))
    TAXI_PARK_UPGRADE_COSTS = [scale_price(cost) for cost in TAXI_PARK_UPGRADE_COSTS]
    for car in TAXI_CAR_CONFIG:
        car["price"] = scale_price(car.get("price", 0))
        car["work_min"] = scale_income(car.get("work_min", 0))
        car["work_max"] = scale_income(car.get("work_max", 0))
        car["park_min"] = scale_income(car.get("park_min", 0))
        car["park_max"] = scale_income(car.get("park_max", 0))
    TRANSPORT_CREATE_COST = scale_price(TRANSPORT_CREATE_COST)
    for office in TRANSPORT_OFFICES:
        office["price"] = scale_price(office.get("price", 0))
    for truck in TRANSPORT_TRUCKS:
        truck["price"] = scale_price(truck.get("price", 0))
    for cargo in TRANSPORT_CARGO:
        cargo["base_income"] = scale_income(cargo.get("base_income", 0))
    CONSTRUCTION_CREATE_COST = scale_price(CONSTRUCTION_CREATE_COST)
    CONSTRUCTION_RESOURCE_PRICES["workers"] = scale_price(CONSTRUCTION_RESOURCE_PRICES.get("workers", 0))
    CONSTRUCTION_RESOURCE_PRICES["materials"] = scale_price(CONSTRUCTION_RESOURCE_PRICES.get("materials", 0))
    CONSTRUCTION_RESOURCE_PRICES["land"] = scale_price(CONSTRUCTION_RESOURCE_PRICES.get("land", 0))
    for office in CONSTRUCTION_OFFICES:
        office["price"] = scale_price(office.get("price", 0))
    for project in CONSTRUCTION_PROJECTS:
        project["base_income"] = scale_income(project.get("base_income", 0))
    for pickaxe in PICKAXE_CONFIG:
        pickaxe["price"] = scale_price(pickaxe.get("price", 0))
    for boat in FISHING_BOATS:
        boat["price"] = scale_price(boat.get("price", 0))
    for rod in FISHING_RODS:
        rod["price"] = scale_price(rod.get("price", 0))
    for tackle in FISHING_TACKLE:
        tackle["price"] = scale_price(tackle.get("price", 0))
    for planet in PLANETS.values():
        planet["price_dollars"] = scale_price(planet.get("price_dollars", 0))
        planet["price_plasma"] = scale_price(planet.get("price_plasma", 0))
        planet["plasma_per_hour"] = scale_income(planet.get("plasma_per_hour", 0))
    for reward in BOSS_REWARD_CONFIG.values():
        reward["money"] = scale_income(reward.get("money", 0))
        reward["plasma"] = scale_income(reward.get("plasma", 0))
    for colony in SPACE_COLONY_TYPES.values():
        colony["yield_plasma"] = scale_income(colony.get("yield_plasma", 0))
        colony["yield_plutonium"] = scale_income(colony.get("yield_plutonium", 0))
        colony["yield_artifacts"] = scale_income(colony.get("yield_artifacts", 0))
        colony["yield_tech"] = scale_income(colony.get("yield_tech", 0))
    for inv in INVESTMENTS.values():
        inv["profit_multiplier"] = inv.get("profit_multiplier", 0) * INCOME_MULTIPLIER

apply_economy_scaling()
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
def calculate_total_income_bonus(buildings, businesses) -> float:
    total_bonus = 0.0
    for b in buildings:
        btype = b["building_type"] if isinstance(b, aiosqlite.Row) else b[0]
        level = b["level"] if isinstance(b, aiosqlite.Row) else b[1]
        effects = BUILDING_CONFIG.get(btype, {}).get("effects", {})
        income_bonus_pct = effects.get("income_bonus", 0)
        if level > 0 and income_bonus_pct:
            total_bonus += (income_bonus_pct * level) / 100.0
    for code, level in businesses.items():
        bdef = BUSINESS_DEFS.get(code)
        if not bdef or level <= 0:
            continue
        total_bonus += bdef.get("income_bonus", 0.0) * level
    return total_bonus
def calculate_business_income_range_per_day(businesses) -> tuple[int, int]:
    min_total = 0
    max_total = 0
    for code, level in businesses.items():
        if level <= 0:
            continue
        bdef = BUSINESS_DEFS.get(code)
        if not bdef:
            continue
        min_day = int(bdef.get("income_min_day", 0)) * level
        max_day = int(bdef.get("income_max_day", 0)) * level
        if max_day <= 0:
            continue
        min_total += min_day
        max_total += max_day
    return int(min_total * COUNTRY_INCOME_MULTIPLIER), int(max_total * COUNTRY_INCOME_MULTIPLIER)
def calculate_business_income_for_period(businesses, hours_passed: float) -> int:
    if hours_passed <= 0:
        return 0
    days = hours_passed / 24.0
    total = 0
    for code, level in businesses.items():
        if level <= 0:
            continue
        bdef = BUSINESS_DEFS.get(code)
        if not bdef:
            continue
        min_day = int(bdef.get("income_min_day", 0))
        max_day = int(bdef.get("income_max_day", 0))
        if max_day <= 0:
            continue
        daily = random.randint(min_day, max_day)
        total += int(daily * level * days)
    return int(total * COUNTRY_INCOME_MULTIPLIER)
def calculate_country_income_hour(level: int, stability: int, income_bonus: float) -> float:
    base_income = max(1, int(level)) * 1000
    stability_clamped = max(0, min(100, int(stability)))
    stability_factor = 0.5 + (stability_clamped / 100.0)
    total_multiplier = 1.0 + income_bonus
    if total_multiplier < 0:
        total_multiplier = 0
    return base_income * stability_factor * total_multiplier * COUNTRY_INCOME_MULTIPLIER
async def get_space_station_level(db: aiosqlite.Connection, country_id: int) -> int:
    cursor = await db.execute("SELECT level FROM country_buildings WHERE country_id = ? AND building_type = 'space_station'", (country_id,))
    row = await cursor.fetchone()
    return int(row[0]) if row else 0
async def get_user_space_access(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        country_id = await get_user_country_id(db, uid)
        if not country_id:
            return False, None, 0
        station_level = await get_space_station_level(db, country_id)
        if station_level <= 0:
            return False, country_id, 0
        return True, country_id, station_level
async def get_user_space_techs(db: aiosqlite.Connection, uid: int) -> set:
    cursor = await db.execute("SELECT tech_code FROM user_space_tech WHERE user_id = ? AND researched = 1", (uid,))
    rows = await cursor.fetchall()
    return {row[0] for row in rows}
def get_max_active_expeditions(station_level: int, techs: set) -> int:
    base = SPACE_MAX_ACTIVE_EXPEDITIONS_BASE
    bonus = station_level // 3
    if 'nav_array' in techs:
        bonus += 1
    return max(1, base + bonus)
def pick_weighted(items, weight_key='weight'):
    total = sum(item.get(weight_key, 0) for item in items)
    if total <= 0:
        return random.choice(items)
    r = random.uniform(0, total)
    upto = 0
    for item in items:
        upto += item.get(weight_key, 0)
        if upto >= r:
            return item
    return items[-1]
def resolve_expedition_outcome(expedition_type: str, station_level: int, techs: set) -> dict:
    cfg = SPACE_EXPEDITION_TYPES[expedition_type]
    base_fail = cfg['base_fail']
    risk_reduction = station_level * 0.02
    if 'nav_array' in techs:
        risk_reduction += 0.05
    if 'defense_matrix' in techs:
        risk_reduction += 0.05
    fail_chance = max(0.05, base_fail - risk_reduction)
    roll = random.random()
    outcome = 'success'
    if roll < fail_chance:
        outcome = random.choice(['ship_lost', 'crew_dead', 'threat'])
    else:
        if random.random() < 0.25:
            outcome = 'partial'
    loot = {'plasma': 0, 'plutonium': 0, 'artifacts': 0, 'tech_data': 0}
    if outcome in ('success', 'partial'):
        scale = 0.5 if outcome == 'partial' else 1.0
        ai_bonus = 1.15 if 'ai_core' in techs else 1.0
        for key, rng in cfg['loot'].items():
            amount = random.randint(rng[0], rng[1])
            loot[key] = int(amount * scale * ai_bonus)
        for key in loot:
            loot[key] = scale_income(loot[key])
    discovery = None
    if outcome in ('success', 'partial'):
        chance = cfg['discovery_chance']
        if 'anomaly_scanner' in techs:
            chance += 0.10
        if random.random() < chance:
            discovery = pick_weighted(SPACE_DISCOVERY_TYPES)
    elif outcome == 'threat':
        discovery = {'type': 'sigma_anomaly', 'rarity': 'legendary', 'description': 'unknown'}
    return {'outcome': outcome, 'loot': loot, 'discovery': discovery}
async def change_plutonium(uid: int, delta: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET plutonium = plutonium + ? WHERE id = ?", (delta, uid))
            await db.commit()
    except Exception as e:
        logger.error(f"\u041e\u0448\u0438\u0431\u043a\u0430 change_plutonium: {e}")
async def change_artifacts(uid: int, delta: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET artifacts = artifacts + ? WHERE id = ?", (delta, uid))
            await db.commit()
    except Exception as e:
        logger.error(f"\u041e\u0448\u0438\u0431\u043a\u0430 change_artifacts: {e}")
async def change_tech_data(uid: int, delta: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET tech_data = tech_data + ? WHERE id = ?", (delta, uid))
            await db.commit()
    except Exception as e:
        logger.error(f"\u041e\u0448\u0438\u0431\u043a\u0430 change_tech_data: {e}")
async def change_space_prestige(uid: int, delta: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET space_prestige = space_prestige + ? WHERE id = ?", (delta, uid))
            await db.commit()
    except Exception as e:
        logger.error(f"\u041e\u0448\u0438\u0431\u043a\u0430 change_space_prestige: {e}")
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
# ========== ОТЛАДОЧНЫЕ КОМАНДЫ ==========
@router.message(F.text.lower() == "проверка")
async def simple_check_cmd(msg: Message):
    """Проверить текущий баланс BTC"""
    user = await get_user(msg.from_user.id)
    current_time = int(time.time())
    last_claim = user.get('last_mining_claim', current_time)
    text = f"""
🔍 <b>ПРОВЕРКА МАЙНИНГА</b>
📊 <b>Данные:</b>
• Видеокарт: {user['mining_gpu_count']}
• Уровень: {user['mining_gpu_level']}
• BTC баланс: {user['bitcoin']:.8f}
• Последний сбор: {last_claim}
• Прошло времени: {current_time - last_claim} сек
💡 <b>Статус:</b>
"""
    if user['mining_gpu_count'] == 0:
        text += "❌ У вас нет видеокарт\n"
        text += "Купите: <code>купить видеокарту</code>"
    elif user['bitcoin'] <= 0:
        text += "❌ BTC еще не накопились\n"
        text += "Подождите 2-3 минуты"
    else:
        text += f"✅ Можно собрать: {user['bitcoin']:.8f} BTC"
    await msg.reply(text, parse_mode="HTML")
@router.message(F.text.lower() == "форсфикс")
async def force_fix_cmd(msg: Message):
    """Принудительный фикс майнинга - ТОЛЬКО ДЛЯ АДМИНОВ"""
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Устанавливаем время на 1 час назад и даем немного BTC
            new_time = int(time.time()) - 3600
            await db.execute("""
                UPDATE users
                SET last_mining_claim = ?,
                    bitcoin = 0.001,
                    mining_gpu_count = CASE WHEN mining_gpu_count = 0 THEN 5 ELSE mining_gpu_count END
                WHERE id = ?
            """, (new_time, uid))
            await db.commit()
        await msg.reply(
            "✅ <b>АДМИН-ФИКС ПРИМЕНЕН!</b>\n\n"
            "• Время сброшено на 1 час назад\n"
            "• Добавлено 0.001 BTC\n"
            "• Если не было видеокарт - добавлено 5 шт\n\n"
            "🔄 <b>Теперь проверьте:</b>\n"
            "- <code>проверка</code> - статус майнинга\n"
            "- <code>забрать биткоины</code> - собрать BTC\n"
            "- <code>майнинг</code> - панель майнинга",
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
@router.message(F.text.lower() == "гарантия")
async def guarantee_cmd(msg: Message):
    """Гарантированная выдача BTC"""
    uid = msg.from_user.id
    # Устанавливаем гарантированное количество BTC
    guaranteed_btc = 0.01
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET bitcoin = bitcoin + ?,
                mining_gpu_count = CASE WHEN mining_gpu_count = 0 THEN 1 ELSE mining_gpu_count END
            WHERE id = ?
        """, (guaranteed_btc, uid))
        await db.commit()
    await msg.reply(
        f"✅ <b>ГАРАНТИЯ!</b>\n\n"
        f"💰 <b>Добавлено:</b> {guaranteed_btc:.8f} BTC\n"
        f"🎮 <b>Видеокарты:</b> минимум 1 шт\n\n"
        f"Теперь попробуйте: <code>забрать биткоины</code>",
        parse_mode="HTML"
    )
@router.message(F.text.lower() == "сбросить майнинг")
async def reset_mining_cmd(msg: Message):
    """Полный сброс майнинга"""
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Полный сброс с начальными значениями
            await db.execute("""
                UPDATE users
                SET mining_gpu_count = 5,
                    mining_gpu_level = 1,
                    bitcoin = 0.01,
                    last_mining_claim = ?
                WHERE id = ?
            """, (int(time.time()) - 7200, uid))
            await db.commit()
        await msg.reply(
            "🔄 <b>МАЙНИНГ ПОЛНОСТЬЮ СБРОШЕН И НАСТРОЕН!</b>\n\n"
            "✅ Установлено:\n"
            "• 5 видеокарт уровня 1\n"
            "• 0.01 BTC для сбора\n"
            "• Время на 2 часа назад\n\n"
            "🎮 <b>Теперь попробуйте:</b>\n"
            "- <code>забрать биткоины</code> - собрать BTC\n"
            "- <code>майнинг</code> - открыть панель",
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.reply(f"❌ Ошибка сброса: {e}")
# ========== БАЗА ДАННЫХ ==========
async def migrate_legacy_businesses(db: aiosqlite.Connection):
    try:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='businesses'"
        )
        if not await cursor.fetchone():
            return
        cursor = await db.execute("SELECT user_id, business_id, level FROM businesses")
        rows = await cursor.fetchall()
        refunds = {}
        for row in rows:
            user_id, business_id, level = row
            legacy = LEGACY_BUSINESS_DEFS.get(business_id)
            if not legacy:
                continue
            price = legacy["price"]
            mult = legacy["upgrade_multiplier"]
            total_investment = price
            for lvl in range(1, max(1, level)):
                total_investment += int(price * (mult ** lvl))
            refunds[user_id] = refunds.get(user_id, 0) + int(total_investment * 0.7)
        for user_id, amount in refunds.items():
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, user_id)
            )
        await db.execute("DROP TABLE IF EXISTS businesses")
    except Exception as e:
        logger.error(f"Ошибка миграции старых бизнесов: {e}")
async def ensure_countries_name_not_unique(db: aiosqlite.Connection):
    try:
        cursor = await db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='countries'"
        )
        row = await cursor.fetchone()
        if not row or not row[0]:
            return
        table_sql = row[0]
        if "name TEXT UNIQUE" not in table_sql and "UNIQUE (name)" not in table_sql and "UNIQUE(name)" not in table_sql:
            return
        await db.execute("BEGIN IMMEDIATE")
        await db.execute("ALTER TABLE countries RENAME TO countries_old")
        new_sql = table_sql.replace("name TEXT UNIQUE NOT NULL", "name TEXT NOT NULL")
        new_sql = new_sql.replace(", UNIQUE (name)", "")
        new_sql = new_sql.replace(", UNIQUE(name)", "")
        new_sql = new_sql.replace("UNIQUE (name)", "")
        new_sql = new_sql.replace("UNIQUE(name)", "")
        await db.execute(new_sql)
        cursor = await db.execute("PRAGMA table_info(countries_old)")
        old_cols = await cursor.fetchall()
        cursor = await db.execute("PRAGMA table_info(countries)")
        new_cols = {r[1] for r in await cursor.fetchall()}
        for col in old_cols:
            name = col[1]
            if name in new_cols:
                continue
            col_type = col[2] or ""
            notnull = bool(col[3])
            dflt_value = col[4]
            col_def = f"{name} {col_type}".strip()
            if dflt_value is not None:
                col_def += f" DEFAULT {dflt_value}"
                if notnull:
                    col_def += " NOT NULL"
            await db.execute(f"ALTER TABLE countries ADD COLUMN {col_def}")
        cols = [r[1] for r in old_cols]
        cols_csv = ", ".join(cols)
        await db.execute(
            f"INSERT INTO countries ({cols_csv}) SELECT {cols_csv} FROM countries_old"
        )
        await db.execute("DROP TABLE countries_old")
        await db.commit()
    except Exception as e:
        logger.error(f"Не удалось убрать UNIQUE из countries.name: {e}")
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
                'last_collected': 'INTEGER DEFAULT 0',
                'plasma': 'BIGINT DEFAULT 0',
                'plutonium': 'BIGINT DEFAULT 0',
                'artifacts': 'BIGINT DEFAULT 0',
                'tech_data': 'BIGINT DEFAULT 0',
                'space_prestige': 'INTEGER DEFAULT 0',
                'bitcoin': 'REAL DEFAULT 0',
                'mining_gpu_count': 'INTEGER DEFAULT 0',
                'mining_gpu_level': 'INTEGER DEFAULT 1',
                'last_mining_claim': 'INTEGER DEFAULT 0',
                'wins': 'INTEGER DEFAULT 0',
                'losses': 'INTEGER DEFAULT 0',
                'last_daily_claim': 'INTEGER DEFAULT NULL',
                'daily_streak': 'INTEGER DEFAULT 0',
                'last_game_time': 'INTEGER DEFAULT 0',
                'weapons_shop_unlocked': 'INTEGER DEFAULT 1',
                'weapons_shop_unlock_until': 'INTEGER DEFAULT 0',
                'energy': 'INTEGER DEFAULT 100',
                'energy_max': 'INTEGER DEFAULT 100',
                'energy_last_ts': 'INTEGER DEFAULT 0',
                'reputation': 'INTEGER DEFAULT 0',
                'income_boost_percent': 'REAL DEFAULT 0',
                'income_boost_until_ts': 'INTEGER DEFAULT 0',
                'total_wagered_today': 'BIGINT DEFAULT 0',
                'wagered_reset_ts': 'INTEGER DEFAULT 0',
                'pickaxe_level': 'INTEGER DEFAULT 0',
                'mine_last_ts': 'INTEGER DEFAULT 0',
                'ore_stone': 'BIGINT DEFAULT 0',
                'ore_coal': 'BIGINT DEFAULT 0',
                'ore_copper': 'BIGINT DEFAULT 0',
                'ore_iron': 'BIGINT DEFAULT 0',
                'ore_emerald': 'BIGINT DEFAULT 0',
                'ore_diamond': 'BIGINT DEFAULT 0',
                'ore_ancient': 'BIGINT DEFAULT 0',
                'fishing_boat_level': 'INTEGER DEFAULT 0',
                'fishing_rod_level': 'INTEGER DEFAULT 0',
                'fishing_tackle_level': 'INTEGER DEFAULT 0',
                'fishing_last_ts': 'INTEGER DEFAULT 0',
                'fishing_exp': 'INTEGER DEFAULT 0',
                'fishing_level': 'INTEGER DEFAULT 1',
                'fishing_location': 'INTEGER DEFAULT 1',
                'fish_caught_total': 'INTEGER DEFAULT 0',
                'taxi_active_car': 'TEXT',
                'taxi_last_ts': 'INTEGER DEFAULT 0'
            }
            for column, col_type in new_columns.items():
                if column not in column_names:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
            await db.commit()  # Фиксируем изменения пользовательской таблицы
            # 1. Создаем таблицу для планет (если еще нет)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS planets (
                    user_id INTEGER,
                    planet_id INTEGER,
                    last_collected INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, planet_id)
                )
            """)
            # 3. Создаем таблицу для инвестиций (если еще нет)
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
            await db.execute("CREATE TABLE IF NOT EXISTS user_taxi_cars (user_id INTEGER, car_code TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (user_id, car_code))")
            await db.execute("CREATE TABLE IF NOT EXISTS user_taxi_park (user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, last_collect_ts INTEGER DEFAULT 0)")
            await db.execute("CREATE TABLE IF NOT EXISTS user_taxi_park_cars (user_id INTEGER, car_code TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (user_id, car_code))")
            await db.execute("CREATE TABLE IF NOT EXISTS user_fish (user_id INTEGER, fish_code TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (user_id, fish_code))")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transport_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_user_id INTEGER UNIQUE NOT NULL,
                    office_code TEXT DEFAULT NULL,
                    active_truck_code TEXT DEFAULT NULL,
                    created_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transport_trucks (
                    company_id INTEGER NOT NULL,
                    truck_code TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (company_id, truck_code)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transport_orders (
                    company_id INTEGER PRIMARY KEY,
                    cargo_code TEXT NOT NULL,
                    income INTEGER NOT NULL,
                    risk INTEGER NOT NULL,
                    started_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS construction_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_user_id INTEGER UNIQUE NOT NULL,
                    office_level INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS construction_resources (
                    company_id INTEGER PRIMARY KEY,
                    workers INTEGER DEFAULT 0,
                    materials INTEGER DEFAULT 0,
                    land INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS construction_projects (
                    company_id INTEGER PRIMARY KEY,
                    project_code TEXT NOT NULL,
                    income INTEGER NOT NULL,
                    risk INTEGER NOT NULL,
                    started_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL
                )
            """)
            # 4. Таблица для лотереи (уже в правильном месте!)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lottery_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticket_type INTEGER,
                    prize_amount BIGINT,
                    position INTEGER,
                    draw_date INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            await db.commit()  # Финальный коммит для всех созданных таблиц
            # Таблица для отмеченных обработанных callback'ов (id колбека, метка времени)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_callbacks (
                    id TEXT PRIMARY KEY,
                    ts INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referral_progress (
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER PRIMARY KEY,
                    actions_count INTEGER DEFAULT 0,
                    actions_required INTEGER DEFAULT 20,
                    reward_remaining BIGINT DEFAULT 0,
                    rep_remaining INTEGER DEFAULT 0,
                    created_ts INTEGER DEFAULT 0
                )
            """)
            # Новые таблицы для стран и кланов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS countries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_user_id INTEGER NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    treasury INTEGER NOT NULL DEFAULT 0,
                    stability INTEGER NOT NULL DEFAULT 70,
                    tax_rate REAL NOT NULL DEFAULT 0.10,
                    last_tick INTEGER NOT NULL DEFAULT 0,
                    last_war_end_ts INTEGER NOT NULL DEFAULT 0
                )
            """)
            await ensure_countries_name_not_unique(db)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_buildings (
                    country_id INTEGER NOT NULL,
                    building_type TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, building_type)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS business_defs (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_cost INTEGER NOT NULL,
                    max_level INTEGER NOT NULL,
                    income_bonus REAL NOT NULL,
                    jobs INTEGER NOT NULL,
                    upkeep_day INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_businesses (
                    country_id INTEGER NOT NULL,
                    business_code TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    last_upkeep_ts INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, business_code)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_limits (
                    country_id INTEGER PRIMARY KEY,
                    people_limit INTEGER DEFAULT 100,
                    tech_limit INTEGER DEFAULT 20
                )
            """)
            # Клановые боссы
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_bosses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    tier INTEGER NOT NULL,
                    max_hp INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    attack_power INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    phase INTEGER NOT NULL DEFAULT 1,
                    spawned_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_boss_hits (
                    boss_id INTEGER NOT NULL,
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    country_id INTEGER NOT NULL,
                    damage INTEGER NOT NULL,
                    ts INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_boss_rewards_claimed (
                    boss_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
            """)
            # Добавляем новые колонки для населения
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN population INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN army_people INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN population_cap INTEGER DEFAULT 100000")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN jobs_available INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN employment_rate REAL DEFAULT 0.0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN literacy INTEGER DEFAULT 50")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN crime INTEGER DEFAULT 20")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN happiness INTEGER DEFAULT 70")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN birth_rate REAL DEFAULT 0.003")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN death_rate REAL DEFAULT 0.001")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN last_population_tick INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN specialization TEXT DEFAULT NULL")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN last_specialization_change INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE countries ADD COLUMN last_war_end_ts INTEGER DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE clans ADD COLUMN is_open INTEGER NOT NULL DEFAULT 1")
            except:
                pass
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    treasury_money INTEGER NOT NULL DEFAULT 0,
                    treasury_plasma INTEGER NOT NULL DEFAULT 0,
                    bonus_income REAL NOT NULL DEFAULT 0.02,
                    is_open INTEGER NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_members (
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY(clan_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_join_requests (
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(clan_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clan_id INTEGER NOT NULL,
                    actor_user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS clan_join_requests (
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(clan_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS armies (
                    country_id INTEGER NOT NULL,
                    unit_type TEXT NOT NULL,
                    amount INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, unit_type)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS wars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_country_id INTEGER NOT NULL,
                    defender_country_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    started_at INTEGER NOT NULL,
                    last_round_at INTEGER NOT NULL DEFAULT 0,
                    attacker_progress INTEGER NOT NULL DEFAULT 0,
                    defender_progress INTEGER NOT NULL DEFAULT 0,
                    rounds_played INTEGER NOT NULL DEFAULT 0,
                    winner_country_id INTEGER DEFAULT NULL,
                    tribute_amount INTEGER NOT NULL DEFAULT 0,
                    ends_at INTEGER NOT NULL DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS war_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    war_id INTEGER NOT NULL,
                    actor_country_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    power INTEGER NOT NULL,
                    losses_people INTEGER NOT NULL,
                    losses_weapons INTEGER NOT NULL DEFAULT 0,
                    losses_tech INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS credits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lender_id INTEGER,
                    borrower_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    interest REAL NOT NULL,
                    total_due INTEGER NOT NULL,
                    issued_at INTEGER NOT NULL,
                    due_at INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS credit_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credit_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    paid_at INTEGER NOT NULL
                )
            """)
            try:
                await db.execute("ALTER TABLE wars ADD COLUMN rounds_played INTEGER NOT NULL DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE wars ADD COLUMN winner_country_id INTEGER DEFAULT NULL")
            except:
                pass
            try:
                await db.execute("ALTER TABLE wars ADD COLUMN tribute_amount INTEGER NOT NULL DEFAULT 0")
            except:
                pass
            try:
                await db.execute("ALTER TABLE war_logs ADD COLUMN losses_weapons INTEGER NOT NULL DEFAULT 0")
            except:
                pass
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bosses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    tier INTEGER NOT NULL,
                    max_hp INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    attack_power INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    phase INTEGER DEFAULT 1,
                    spawned_at INTEGER NOT NULL,
                    ends_at INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_hits (
                    boss_id INTEGER NOT NULL,
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    country_id INTEGER NOT NULL,
                    damage INTEGER NOT NULL,
                    ts INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_rewards_claimed (
                    boss_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS unique_items (
                    item_id TEXT PRIMARY KEY,
                    boss_tier INTEGER,
                    name TEXT,
                    item_type TEXT,
                    slot TEXT,
                    power_flat INTEGER DEFAULT 0,
                    power_mult REAL DEFAULT 0.0,
                    boss_damage_mult REAL DEFAULT 0.0,
                    vehicle_loss_reduction REAL DEFAULT 0.0,
                    people_loss_reduction REAL DEFAULT 0.0,
                    ignore_defense REAL DEFAULT 0.0,
                    upkeep_mult REAL DEFAULT 0.0,
                    rarity TEXT,
                    description TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_unique_items (
                    user_id INTEGER,
                    item_id TEXT,
                    obtained_at INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_unique_slots (
                    country_id INTEGER PRIMARY KEY,
                    core_item_id TEXT NULL,
                    support_item_id TEXT NULL,
                    relic_item_id TEXT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_loot_rolls (
                    boss_id INTEGER,
                    user_id INTEGER,
                    rolled_at INTEGER,
                    PRIMARY KEY(boss_id, user_id)
                )
            """)
            for item in UNIQUE_ITEMS:
                await db.execute("""
                    INSERT OR IGNORE INTO unique_items
                    (item_id, boss_tier, name, item_type, slot, power_flat, power_mult, boss_damage_mult,
                     vehicle_loss_reduction, people_loss_reduction, ignore_defense, upkeep_mult, rarity, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["item_id"],
                    item["boss_tier"],
                    item["name"],
                    item["item_type"],
                    item.get("slot"),
                    item.get("power_flat", 0),
                    item.get("power_mult", 0.0),
                    item.get("boss_damage_mult", 0.0),
                    item.get("vehicle_loss_reduction", 0.0),
                    item.get("people_loss_reduction", 0.0),
                    item.get("ignore_defense", 0.0),
                    item.get("upkeep_mult", 0.0),
                    item.get("rarity"),
                    item.get("description"),
                ))
            # Бэкап-миграции для старых таблиц
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN tier INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN attack_power INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN phase INTEGER DEFAULT 1")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN status TEXT")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN max_hp INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN hp INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN spawned_at INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN ends_at INTEGER")
            except:
                pass
            try:
                await db.execute("ALTER TABLE bosses ADD COLUMN level INTEGER DEFAULT 1")
            except:
                pass
            try:
                await db.execute("ALTER TABLE boss_hits ADD COLUMN country_id INTEGER")
            except:
                pass
            try:
                await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_boss_hits_unique ON boss_hits (boss_id, user_id)")
            except:
                pass
            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    category TEXT,
                    name TEXT,
                    tier INTEGER,
                    power INTEGER,
                    upkeep_day INTEGER,
                    price_money INTEGER,
                    price_plutonium INTEGER DEFAULT 0,
                    price_plasma INTEGER DEFAULT 0,
                    req_building TEXT DEFAULT NULL,
                    req_building_level INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_items (
                    user_id INTEGER,
                    item_id TEXT,
                    amount INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS unique_items (
                    item_id TEXT PRIMARY KEY,
                    boss_tier INTEGER,
                    name TEXT,
                    item_type TEXT,
                    slot TEXT,
                    power_flat INTEGER DEFAULT 0,
                    power_mult REAL DEFAULT 0.0,
                    boss_damage_mult REAL DEFAULT 0.0,
                    vehicle_loss_reduction REAL DEFAULT 0.0,
                    people_loss_reduction REAL DEFAULT 0.0,
                    ignore_defense REAL DEFAULT 0.0,
                    upkeep_mult REAL DEFAULT 0.0,
                    rarity TEXT,
                    description TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_unique_items (
                    user_id INTEGER,
                    item_id TEXT,
                    obtained_at INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_unique_slots (
                    country_id INTEGER PRIMARY KEY,
                    core_item_id TEXT NULL,
                    support_item_id TEXT NULL,
                    relic_item_id TEXT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_loot_rolls (
                    boss_id INTEGER,
                    user_id INTEGER,
                    rolled_at INTEGER,
                    PRIMARY KEY(boss_id, user_id)
                )
            """)
            for item in UNIQUE_ITEMS:
                await db.execute("""
                    INSERT OR IGNORE INTO unique_items
                    (item_id, boss_tier, name, item_type, slot, power_flat, power_mult, boss_damage_mult,
                     vehicle_loss_reduction, people_loss_reduction, ignore_defense, upkeep_mult, rarity, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["item_id"],
                    item["boss_tier"],
                    item["name"],
                    item["item_type"],
                    item.get("slot"),
                    item.get("power_flat", 0),
                    item.get("power_mult", 0.0),
                    item.get("boss_damage_mult", 0.0),
                    item.get("vehicle_loss_reduction", 0.0),
                    item.get("people_loss_reduction", 0.0),
                    item.get("ignore_defense", 0.0),
                    item.get("upkeep_mult", 0.0),
                    item.get("rarity"),
                    item.get("description"),
                ))
            # Вставка предметов
            for item_id, data in ITEM_CONFIG.items():
                await db.execute("""
                    INSERT OR IGNORE INTO items
                    (item_id, category, name, tier, power, upkeep_day, price_money, price_plutonium, price_plasma, req_building, req_building_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, data['category'], data['name'], data['tier'], data['power'], data['upkeep_day'],
                    data['price_money'], data.get('price_plutonium', 0), data.get('price_plasma', 0),
                    data.get('req_building'), data.get('req_building_level', 0)
                ))
            # Вставка начальных стран
            await db.execute("""
                INSERT OR IGNORE INTO countries (name, level, treasury, stability, tax_rate, last_tick) VALUES
                ('Аркадия', 1, 1000000, 70, 0.10, 0),
                ('Аурелион', 1, 1000000, 70, 0.10, 0),
                ('Златория', 1, 1000000, 70, 0.10, 0),
                ('Валория', 1, 1000000, 70, 0.10, 0),
                ('Меркатия', 1, 1000000, 70, 0.10, 0),
                ('Люменсия', 1, 1000000, 70, 0.10, 0),
                ('Санктерия', 1, 1000000, 70, 0.10, 0),
                ('Эвентия', 1, 1000000, 70, 0.10, 0),
                ('Новалис', 1, 1000000, 70, 0.10, 0),
                ('Гармония', 1, 1000000, 70, 0.10, 0),
                ('Ноксара', 1, 1000000, 70, 0.10, 0),
                ('Кратосия', 1, 1000000, 70, 0.10, 0),
                ('Фортекс', 1, 1000000, 70, 0.10, 0),
                ('Бастион', 1, 1000000, 70, 0.10, 0),
                ('Доминия', 1, 1000000, 70, 0.10, 0),
                ('Технолис', 1, 1000000, 70, 0.10, 0),
                ('Индустрия', 1, 1000000, 70, 0.10, 0),
                ('Логистар', 1, 1000000, 70, 0.10, 0),
                ('Энерголия', 1, 1000000, 70, 0.10, 0),
                ('Мегаполис', 1, 1000000, 70, 0.10, 0),
                ('Астрея', 1, 1000000, 70, 0.10, 0),
                ('Орбитон', 1, 1000000, 70, 0.10, 0),
                ('Сингуля', 1, 1000000, 70, 0.10, 0),
                ('Космариум', 1, 1000000, 70, 0.10, 0),
                ('Нова-Прайм', 1, 1000000, 70, 0.10, 0),
                ('Эквилибриум', 1, 1000000, 70, 0.10, 0),
                ('Вальдхейм', 1, 1000000, 70, 0.10, 0),
                ('Цивилис', 1, 1000000, 70, 0.10, 0),
                ('Прогресса', 1, 1000000, 70, 0.10, 0),
                ('Альянсия', 1, 1000000, 70, 0.10, 0)
            """)
            # Создаем таблицы для системы титулов
            await db.execute("DELETE FROM countries WHERE owner_user_id IS NULL")
            for country in START_COUNTRIES:
                await db.execute(
                    "INSERT OR IGNORE INTO countries (name, level, treasury, stability, tax_rate, last_tick) "
                    "VALUES (?, 1, 1000000, 70, 0.10, 0)",
                    (country["name"],)
                )
            await db.execute("""
                CREATE TABLE IF NOT EXISTS titles (
                    id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    bonus_type TEXT,
                    bonus_value REAL,
                    permanent INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_titles (
                    user_id INTEGER,
                    title_code TEXT,
                    obtained_at INTEGER,
                    PRIMARY KEY(user_id, title_code)
                )
            """)
            # Вставка титулов
            for title in TITLES_CONFIG:
                await db.execute("""
                    INSERT OR IGNORE INTO titles
                    (code, name, description, bonus_type, bonus_value, permanent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    title['code'], title['name'], title['description'],
                    title['bonus_type'], title['bonus_value'], title['permanent']
                ))
            # Создаем таблицу мировых событий
            await db.execute("""
                CREATE TABLE IF NOT EXISTS world_events (
                    id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    effect_type TEXT,
                    effect_value REAL,
                    start_ts INTEGER,
                    end_ts INTEGER
                )
            """)
            for code, data in BUSINESS_DEFS.items():
                await db.execute("""
                    INSERT OR REPLACE INTO business_defs
                    (code, name, base_cost, max_level, income_bonus, jobs, upkeep_day)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    code, data["name"], data["base_cost"], data["max_level"],
                    data["income_bonus"], data["jobs"], data["upkeep_day"]
                ))
            await migrate_legacy_businesses(db)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS space_expeditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    country_id INTEGER,
                    expedition_type TEXT,
                    started_at INTEGER,
                    ends_at INTEGER,
                    status TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS space_expedition_results (
                    expedition_id INTEGER PRIMARY KEY,
                    outcome TEXT,
                    loot_plasma INTEGER DEFAULT 0,
                    loot_plutonium INTEGER DEFAULT 0,
                    loot_artifacts INTEGER DEFAULT 0,
                    loot_tech INTEGER DEFAULT 0,
                    discovery_id INTEGER DEFAULT NULL,
                    message TEXT,
                    created_at INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS space_discoveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    discovery_type TEXT,
                    rarity TEXT,
                    description TEXT,
                    discovered_at INTEGER,
                    status TEXT DEFAULT 'new',
                    resolved_at INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS space_colonies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER,
                    colony_type TEXT,
                    stability INTEGER,
                    bonus_type TEXT,
                    created_at INTEGER,
                    last_yield INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS space_tech (
                    tech_code TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    cost_plasma INTEGER,
                    cost_plutonium INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_space_tech (
                    user_id INTEGER,
                    tech_code TEXT,
                    researched INTEGER,
                    PRIMARY KEY (user_id, tech_code)
                )
            """)
            for tech in SPACE_TECH_CONFIG:
                await db.execute(
                    "INSERT OR IGNORE INTO space_tech (tech_code, name, description, cost_plasma, cost_plutonium) VALUES (?, ?, ?, ?, ?)",
                    (tech['tech_code'], tech['name'], tech['description'], tech['cost_plasma'], tech['cost_plutonium'])
                )
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
                    plutonium BIGINT DEFAULT 0,
                    artifacts BIGINT DEFAULT 0,
                    tech_data BIGINT DEFAULT 0,
                    space_prestige INTEGER DEFAULT 0,
                    bitcoin REAL DEFAULT 0,
                    mining_gpu_count INTEGER DEFAULT 0,
                    mining_gpu_level INTEGER DEFAULT 1,
                    last_mining_claim INTEGER DEFAULT 0,
                    energy INTEGER DEFAULT 100,
                    energy_max INTEGER DEFAULT 100,
                    energy_last_ts INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    income_boost_percent REAL DEFAULT 0,
                    income_boost_until_ts INTEGER DEFAULT 0,
                    total_wagered_today BIGINT DEFAULT 0,
                    wagered_reset_ts INTEGER DEFAULT 0,
                    pickaxe_level INTEGER DEFAULT 0,
                    mine_last_ts INTEGER DEFAULT 0,
                    ore_stone BIGINT DEFAULT 0,
                    ore_coal BIGINT DEFAULT 0,
                    ore_copper BIGINT DEFAULT 0,
                    ore_iron BIGINT DEFAULT 0,
                    ore_emerald BIGINT DEFAULT 0,
                    ore_diamond BIGINT DEFAULT 0,
                    ore_ancient BIGINT DEFAULT 0,
                    fishing_boat_level INTEGER DEFAULT 0,
                    fishing_rod_level INTEGER DEFAULT 0,
                    fishing_tackle_level INTEGER DEFAULT 0,
                    fishing_last_ts INTEGER DEFAULT 0,
                    fishing_exp INTEGER DEFAULT 0,
                    fishing_level INTEGER DEFAULT 1,
                    fishing_location INTEGER DEFAULT 1,
                    fish_caught_total INTEGER DEFAULT 0,
                    weapons_shop_unlocked INTEGER DEFAULT 1,
                    weapons_shop_unlock_until INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_callbacks (
                    id TEXT PRIMARY KEY,
                    ts INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referral_progress (
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER PRIMARY KEY,
                    actions_count INTEGER DEFAULT 0,
                    actions_required INTEGER DEFAULT 20,
                    reward_remaining BIGINT DEFAULT 0,
                    rep_remaining INTEGER DEFAULT 0,
                    created_ts INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_fish (
                    user_id INTEGER,
                    fish_code TEXT,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, fish_code)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    category TEXT,
                    name TEXT,
                    tier INTEGER,
                    power INTEGER,
                    upkeep_day INTEGER,
                    price_money INTEGER,
                    price_plutonium INTEGER DEFAULT 0,
                    price_plasma INTEGER DEFAULT 0,
                    req_building TEXT DEFAULT NULL,
                    req_building_level INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_items (
                    user_id INTEGER,
                    item_id TEXT,
                    amount INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
            """)
            # Вставка предметов
            for item_id, data in ITEM_CONFIG.items():
                await db.execute("""
                    INSERT OR IGNORE INTO items
                    (item_id, category, name, tier, power, upkeep_day, price_money, price_plutonium, price_plasma, req_building, req_building_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, data['category'], data['name'], data['tier'], data['power'], data['upkeep_day'],
                    data['price_money'], data.get('price_plutonium', 0), data.get('price_plasma', 0),
                    data.get('req_building'), data.get('req_building_level', 0)
                ))
            await db.commit()
            logger.info("✅ База данных создана")
            await update_db_structure()
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
async def get_user(uid: int):
    """Получить пользователя - всегда свежие данные"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # ВАЖНО: timeout для предотвращения блокировок
            await db.execute("PRAGMA busy_timeout = 5000")
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if not row:
                # Создаем пользователя если нет
                referral_code = generate_referral_code(uid)
                await db.execute(
                    "INSERT INTO users (id, balance, referral_code) VALUES (?, ?, ?)",
                    (uid, 0, referral_code)
                )
                await db.commit()
                cursor = await db.execute("SELECT * FROM users WHERE id = ?", (uid,))
                row = await cursor.fetchone()
            # Преобразуем в словарь
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"❌ Ошибка get_user для {uid}: {e}", exc_info=True)
        return None
async def is_callback_processed(cb_id: str) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT 1 FROM processed_callbacks WHERE id = ?", (cb_id,))
            row = await cursor.fetchone()
            return bool(row)
    except Exception as e:
        logger.error(f"Ошибка is_callback_processed: {e}")
        return False
async def mark_callback_processed(cb_id: str):
    try:
        now = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO processed_callbacks (id, ts) VALUES (?, ?)", (cb_id, now))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка mark_callback_processed: {e}")
# ========== ФУНКЦИИ СИСТЕМЫ ТИТУЛОВ ==========
async def get_user_titles(uid: int):
    """Получить все титулы пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT t.*, ut.obtained_at
                FROM titles t
                JOIN user_titles ut ON t.code = ut.title_code
                WHERE ut.user_id = ?
                ORDER BY ut.obtained_at DESC
            """, (uid,))
            return [dict(row) for row in await cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка get_user_titles: {e}")
        return []
async def check_and_award_titles(uid: int):
    """Проверить и выдать титулы пользователю"""
    try:
        user = await get_user(uid)
        if not user:
            return
        async with aiosqlite.connect(DB_PATH) as db:
            # Получить уже имеющиеся титулы
            cursor = await db.execute("SELECT title_code FROM user_titles WHERE user_id = ?", (uid,))
            existing_titles = {row[0] for row in await cursor.fetchall()}
            new_titles = []
            # Проверка условий титулов
            for title in TITLES_CONFIG:
                if title['code'] in existing_titles:
                    continue
                awarded = False
                if title['code'] == 'iron_ruler':
                    # 30 дней без бунтов - проверка стабильности страны
                    country_id = await get_user_country_id(db, uid)
                    if country_id:
                        cursor = await db.execute("SELECT stability FROM countries WHERE id = ?", (country_id,))
                        row = await cursor.fetchone()
                        if row and row[0] >= 80:
                            awarded = True
                elif title['code'] == 'military_maniac':
                    # 50 побед в войнах
                    if user.get('wins', 0) >= 50:
                        awarded = True
                elif title['code'] == 'casino_magnate':
                    # оборот ставок > 10B - пока что просто по балансу
                    if user.get('balance', 0) >= 10000000000:  # 10B
                        awarded = True
                elif title['code'] == 'sigma_killer':
                    # победа над боссом - проверка по логам или флагу
                    # Пока что не реализовано, можно добавить позже
                    pass
                elif title['code'] == 'wealthy_trader':
                    # баланс > 100B
                    if user.get('balance', 0) >= 100000000000:  # 100B
                        awarded = True
                elif title['code'] == 'plasma_master':
                    # плазма > 1M
                    if user.get('plasma', 0) >= 1000000:
                        awarded = True
                elif title['code'] == 'space_pioneer':
                    cursor = await db.execute("SELECT COUNT(1) FROM space_discoveries WHERE user_id = ?", (uid,))
                    row = await cursor.fetchone()
                    if row and row[0] >= 1:
                        awarded = True
                elif title['code'] == 'void_conqueror':
                    cursor = await db.execute("SELECT COUNT(1) FROM space_discoveries WHERE user_id = ?", (uid,))
                    row = await cursor.fetchone()
                    if row and row[0] >= 5:
                        awarded = True
                elif title['code'] == 'sigma_witness':
                    cursor = await db.execute("SELECT 1 FROM space_discoveries WHERE user_id = ? AND discovery_type = 'sigma_anomaly' LIMIT 1", (uid,))
                    if await cursor.fetchone():
                        awarded = True
                elif title['code'] == 'referral_guru':
                    # 100+ рефералов
                    if user.get('referral_count', 0) >= 100:
                        awarded = True
                elif title['code'] == 'mining_tycoon':
                    # 100+ видеокарт
                    if user.get('mining_gpu_count', 0) >= 100:
                        awarded = True
                elif title['code'] == 'business_empire':
                    country_id = await get_user_country_id(db, uid)
                    if country_id:
                        businesses, _ = await get_country_businesses(db, country_id)
                        max_level_businesses = sum(
                            1 for code, level in businesses.items()
                            if level >= BUSINESS_DEFS.get(code, {}).get("max_level", 0)
                        )
                        if max_level_businesses == len(BUSINESS_DEFS):
                            awarded = True
                elif title['code'] == 'war_hero':
                    # 100+ побед в войнах
                    if user.get('wins', 0) >= 100:
                        awarded = True
                if awarded:
                    now = int(time.time())
                    await db.execute(
                        "INSERT OR IGNORE INTO user_titles (user_id, title_code, obtained_at) VALUES (?, ?, ?)",
                        (uid, title['code'], now)
                    )
                    new_titles.append(title)
            await db.commit()
            return new_titles
    except Exception as e:
        logger.error(f"Ошибка check_and_award_titles: {e}")
        return []
async def calculate_title_bonuses(uid: int):
    """Рассчитать бонусы от титулов пользователя"""
    try:
        titles = await get_user_titles(uid)
        bonuses = {
            'income': 0.0,
            'combat': 0.0,
            'casino': 0.0,
            'boss': 0.0
        }
        for title in titles:
            bonus_type = title['bonus_type']
            bonus_value = title['bonus_value']
            if bonus_type in bonuses:
                bonuses[bonus_type] += bonus_value
        # Ограничение суммарного бонуса <= 5%
        for key in bonuses:
            bonuses[key] = min(bonuses[key], 0.05)
        return bonuses
    except Exception as e:
        logger.error(f"Ошибка calculate_title_bonuses: {e}")
        return {'income': 0.0, 'combat': 0.0, 'casino': 0.0, 'boss': 0.0}
# ========== ФУНКЦИИ МИРОВЫХ СОБЫТИЙ ==========
async def get_current_world_event():
    """Получить текущее активное мировое событие"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            now = int(time.time())
            cursor = await db.execute(
                "SELECT * FROM world_events WHERE start_ts <= ? AND end_ts > ? ORDER BY start_ts DESC LIMIT 1",
                (now, now)
            )
            event = await cursor.fetchone()
            return dict(event) if event else None
    except Exception as e:
        logger.error(f"Ошибка get_current_world_event: {e}")
        return None
async def start_random_world_event():
    """Запустить случайное мировое событие"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверить, есть ли активное событие
            now = int(time.time())
            cursor = await db.execute(
                "SELECT COUNT(*) FROM world_events WHERE start_ts <= ? AND end_ts > ?",
                (now, now)
            )
            active_count = (await cursor.fetchone())[0]
            if active_count > 0:
                return None  # Уже есть активное событие
            # Выбрать случайное событие
            event_config = random.choice(WORLD_EVENTS_CONFIG)
            duration_seconds = event_config['duration_hours'] * 3600
            start_ts = now
            end_ts = now + duration_seconds
            # Вставить новое событие
            await db.execute("""
                INSERT INTO world_events (code, name, description, effect_type, effect_value, start_ts, end_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_config['code'], event_config['name'], event_config['description'],
                event_config['effect_type'], event_config['effect_value'], start_ts, end_ts
            ))
            await db.commit()
            # Вернуть информацию о событии
            return {
                'code': event_config['code'],
                'name': event_config['name'],
                'description': event_config['description'],
                'effect_type': event_config['effect_type'],
                'effect_value': event_config['effect_value'],
                'start_ts': start_ts,
                'end_ts': end_ts
            }
    except Exception as e:
        logger.error(f"Ошибка start_random_world_event: {e}")
        return None
async def check_and_start_world_event():
    """Проверить и запустить новое мировое событие если нужно"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            now = int(time.time())
            # Проверить время последнего события
            cursor = await db.execute(
                "SELECT end_ts FROM world_events ORDER BY end_ts DESC LIMIT 1"
            )
            last_event = await cursor.fetchone()
            if last_event:
                last_end = last_event[0]
                # События запускаются каждые 3-7 дней (259200 - 604800 секунд)
                next_event_time = last_end + random.randint(259200, 604800)
                if now < next_event_time:
                    return None
            else:
                # Если нет событий, запустить первое
                pass
            # Запустить новое событие
            return await start_random_world_event()
    except Exception as e:
        logger.error(f"Ошибка check_and_start_world_event: {e}")
        return None
async def get_world_event_effects():
    """Получить текущие эффекты мирового события"""
    event = await get_current_world_event()
    if not event:
        return {}
    return {
        event['effect_type']: event['effect_value']
    }
async def check_random_events(db: aiosqlite.Connection, country_id: int, uid: int):
    """Заглушка для случайных событий (пока без логики)."""
    return None
# ========== ФУНКЦИИ СПЕЦИАЛИЗАЦИЙ СТРАНЫ ==========
async def get_country_specialization(uid: int):
    """Получить текущую специализацию страны пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT specialization, specialization_changed_ts FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if row and row['specialization']:
                return {
                    'type': row['specialization'],
                    'changed_ts': row['specialization_changed_ts'] or 0
                }
            return None
    except Exception as e:
        logger.error(f"Ошибка get_country_specialization для {uid}: {e}")
        return None
async def set_country_specialization(uid: int, specialization_type: str):
    """Установить специализацию страны для пользователя"""
    try:
        # Проверить, существует ли такая специализация
        if specialization_type not in COUNTRY_SPECIALIZATIONS:
            return False, "Неверный тип специализации"
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверить cooldown
            cursor = await db.execute(
                "SELECT specialization_changed_ts FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if row and row[0]:
                last_change = row[0]
                now = int(time.time())
                if now - last_change < SPECIALIZATION_CHANGE_COOLDOWN:
                    remaining_seconds = SPECIALIZATION_CHANGE_COOLDOWN - (now - last_change)
                    remaining_days = remaining_seconds // (24 * 3600)
                    return False, f"Специализацию можно менять раз в 7 дней. Осталось {remaining_days} дней."
            # Установить новую специализацию
            now = int(time.time())
            await db.execute(
                "UPDATE users SET specialization = ?, specialization_changed_ts = ? WHERE id = ?",
                (specialization_type, now, uid)
            )
            await db.commit()
            spec_info = COUNTRY_SPECIALIZATIONS[specialization_type]
            return True, f"✅ Специализация страны изменена на '{spec_info['name']}'"
    except Exception as e:
        logger.error(f"Ошибка set_country_specialization для {uid}: {e}")
        return False, "Ошибка при изменении специализации"
async def get_country_specialization_bonuses(uid: int):
    """Получить бонусы и штрафы от специализации страны"""
    try:
        spec = await get_country_specialization(uid)
        if not spec or spec['type'] not in COUNTRY_SPECIALIZATIONS:
            return {}, {}
        spec_config = COUNTRY_SPECIALIZATIONS[spec['type']]
        bonuses = {}
        penalties = {}
        # Преобразовать бонусы
        for bonus in spec_config['bonuses']:
            bonuses[bonus['type']] = bonus['value']
        # Преобразовать штрафы
        for penalty in spec_config['penalties']:
            penalties[penalty['type']] = penalty['value']
        return bonuses, penalties
    except Exception as e:
        logger.error(f"Ошибка get_country_specialization_bonuses для {uid}: {e}")
        return {}, {}
async def reset_lottery():
    ...
async def buy_lottery_ticket(uid: int, ticket_type: int, count: int = 1):
    ...
async def draw_lottery():
    ...
async def save_lottery_winners():
    ...
async def get_last_winners():
    ...
async def show_lottery_info(msg: Message = None, cb: CallbackQuery = None):
    ...
async def show_my_tickets(uid: int, msg: Message = None, cb: CallbackQuery = None):
    ...
async def create_user_if_not_exists(uid: int, username: str = None):
    """Создать пользователя если не существует"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id FROM users WHERE id = ?", (uid,))
            user_exists = await cursor.fetchone()
            if not user_exists:
                referral_code = generate_referral_code(uid)
                await db.execute(
                    "INSERT INTO users (id, username, referral_code) VALUES (?, ?, ?)",
                    (uid, username, referral_code)
                )
                await db.commit()
                logger.info(f"✅ Создан новый пользователь: {uid}")
                return True
            return False
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        return False
async def update_username(uid: int, username: str):
    """Обновить имя пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
            await db.commit()
    except:
        pass
async def change_balance(uid: int, delta: int) -> bool:
    """Изменить баланс пользователя - ФИКСИРОВАННАЯ ВЕРСИЯ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # ВАЖНО: Изоляция транзакции
            await db.execute("BEGIN IMMEDIATE")
            # 1. Убедимся что пользователь существует
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (uid, 0))
            # 2. Изменяем баланс
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (delta, uid))
            # 3. СРАЗУ получаем обновленный баланс в той же транзакции
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            new_balance = row[0] if row else 0
            # 4. Фиксируем транзакцию
            await db.commit()
            logger.info(f"💰 Баланс {uid}: {delta:+} (стало: {new_balance:,})")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка change_balance для {uid}: {e}", exc_info=True)
        try:
            await db.rollback()
        except:
            pass
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
            # Проверить и выдать титулы после обновления статистики
            await check_and_award_titles(uid)
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
async def auto_accumulate_bitcoin(uid: int):
    """Автоматическое накопление BTC для пользователя при каждом обращении"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT mining_gpu_count, mining_gpu_level, bitcoin, last_mining_claim FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if not row or row['mining_gpu_count'] == 0:
                return 0  # Нет видеокарт - нечего накапливать
            user_data = dict(row)
            current_time = int(time.time())
            if not user_data.get('last_mining_claim', 0):
                await db.execute(
                    "UPDATE users SET last_mining_claim = ? WHERE id = ?",
                    (current_time, uid)
                )
                await db.commit()
                return 0
            last_claim = user_data.get('last_mining_claim')
            # Рассчитываем накопления
            hashrate = BitcoinMining.calculate_hashrate(
                user_data['mining_gpu_count'],
                user_data['mining_gpu_level']
            )
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            time_passed = current_time - last_claim
            if time_passed < 60:  # Минимум 1 минута для накопления
                return 0
            # Максимум 720 часов (30 дней) накопления
            max_hours = 720
            hours_passed = min(time_passed / 3600, max_hours)
            btc_mined = btc_per_hour * hours_passed
            if btc_mined > 0:
                # Начисляем BTC
                await db.execute(
                    "UPDATE users SET bitcoin = bitcoin + ?, last_mining_claim = ? WHERE id = ?",
                    (btc_mined, current_time, uid)
                )
                await db.commit()
                logger.debug(f"Автонакопление для {uid}: {btc_mined:.6f} BTC за {hours_passed:.1f} часов")
                return btc_mined
            return 0
    except Exception as e:
        logger.error(f"Ошибка auto_accumulate_bitcoin: {e}")
        return 0
async def run_simple_crash_game(game_id: int, bet: int, crash_point: float, message: Message):
    """Запускает игру Краш в фоне"""
    try:
        current_multiplier = 1.0
        for i in range(1, 101):  # 100 обновлений = 50 секунд
            # Проверяем, активна ли еще игра
            if game_id not in active_crash_games:
                break
            game = active_crash_games[game_id]
            # Если игрок уже забрал или игра крашнулась
            if game.get("cashed_out", False) or game.get("crashed", False):
                break
            # Увеличиваем множитель
            increment = random.uniform(0.02, 0.08)
            current_multiplier += increment
            current_multiplier = round(current_multiplier, 2)
            # Обновляем множитель в памяти
            active_crash_games[game_id]["multiplier"] = current_multiplier
            # Проверяем крах
            if current_multiplier >= crash_point:
                # КРАХ!
                active_crash_games[game_id]["crashed"] = True
                if game.get("cashed_out", False):
                    # Игрок уже забрал
                    cashout_multiplier = game.get("cashout_multiplier", 1.0)
                    win_amount = int(bet * cashout_multiplier)
                    result_text = f"💥 <b>КРАХ на {crash_point}x!</b>\n\n✅ Вы успели забрать {cashout_multiplier}x!\n💰 Выигрыш: {format_money(win_amount)}"
                else:
                    # Игрок не успел
                    result_text = f"💥 <b>КРАХ на {crash_point}x!</b>\n\n❌ Вы проиграли {format_money(bet)}"
                try:
                    await message.edit_text(
                        f"💥 <b>КРАШ!</b>\n\n"
                        f"💰 Ставка: {format_money(bet)}\n"
                        f"🎯 Точка краха: <b>{crash_point}x</b>\n"
                        f"📈 Достигнуто: <b>{current_multiplier}x</b>\n\n"
                        f"{result_text}\n\n"
                        f"🎮 Игра завершена",
                        parse_mode="HTML"
                    )
                except:
                    pass
                # Удаляем игру через 5 секунд
                await asyncio.sleep(5)
                if game_id in active_crash_games:
                    del active_crash_games[game_id]
                break
            # Обновляем сообщение
            potential_win = int(bet * current_multiplier)
            try:
                await message.edit_text(
                    f"🚀 <b>КРАШ ИГРА</b>\n\n"
                    f"💰 Ставка: {format_money(bet)}\n"
                    f"🎯 Точка краха: <b>???</b>\n\n"
                    f"📈 Текущий множитель: <b>{current_multiplier}x</b>\n"
                    f"💰 Потенциальный выигрыш: <b>{format_money(potential_win)}</b>\n"
                    f"🎯 Прибыль: <b>+{format_money(potential_win - bet)}</b>\n\n"
                    f"<i>Нажми 'Забрать сейчас' чтобы получить {current_multiplier}x!</i>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💰 Забрать сейчас", callback_data=f"crash_cashout_{game['user_id']}")]
                    ])
                )
            except:
                pass
            await asyncio.sleep(0.5)  # Пауза между обновлениями
        # Если игра не завершилась в цикле
        if game_id in active_crash_games and not active_crash_games[game_id].get("crashed", False):
            # Автоматический крах
            try:
                await message.edit_text(
                    f"💥 <b>КРАШ!</b>\n\n"
                    f"💰 Ставка: {format_money(bet)}\n"
                    f"🎯 Точка краха: <b>{current_multiplier}x</b>\n\n"
                    f"❌ Игра завершена по таймауту\n"
                    f"💸 Проигрыш: {format_money(bet)}",
                    parse_mode="HTML"
                )
            except:
                pass
            # Удаляем игру
            if game_id in active_crash_games:
                del active_crash_games[game_id]
    except Exception as e:
        logger.error(f"Ошибка в run_simple_crash_game: {e}")
        # Очищаем игру в случае ошибки
        if game_id in active_crash_games:
            del active_crash_games[game_id]
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
    """Process referral with delayed payout after activity"""
    try:
        if not referral_code or referral_code == "start":
            return False, 0, None
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, username FROM users WHERE referral_code = ?", (referral_code,))
            referrer_data = await cursor.fetchone()
            if not referrer_data:
                return False, 0, None
            referrer_id = referrer_data["id"]
            if referrer_id == new_user_id:
                return False, 0, None
            cursor = await db.execute("SELECT referred_by FROM users WHERE id = ?", (new_user_id,))
            existing_user = await cursor.fetchone()
            if existing_user and existing_user[0] is not None:
                return False, 0, None
            cursor = await db.execute("SELECT 1 FROM referral_progress WHERE referred_id = ?", (new_user_id,))
            if await cursor.fetchone():
                return False, 0, None
            reward_total = scale_income(random.randint(30_000_000, 50_000_000))
            invited_bonus = scale_income(10_000_000)
            rep_total = random.randint(10, 30)
            immediate_reward = int(reward_total * 0.2)
            immediate_rep = max(1, int(rep_total * 0.2)) if rep_total > 0 else 0
            reward_remaining = reward_total - immediate_reward
            rep_remaining = rep_total - immediate_rep
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT 1 FROM users WHERE id = ?", (new_user_id,))
            user_exists = await cursor.fetchone()
            if user_exists:
                await db.execute("UPDATE users SET referred_by = ? WHERE id = ?", (referrer_id, new_user_id))
            else:
                referral_code_new = generate_referral_code(new_user_id)
                await db.execute(
                    "INSERT INTO users (id, referred_by, referral_code) VALUES (?, ?, ?)",
                    (new_user_id, referrer_id, referral_code_new)
                )
            await db.execute("""
                UPDATE users
                SET balance = balance + ?,
                    reputation = reputation + ?,
                    referral_count = referral_count + 1,
                    total_referral_earned = total_referral_earned + ?
                WHERE id = ?
            """, (immediate_reward, immediate_rep, immediate_reward, referrer_id))
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (invited_bonus, new_user_id)
            )
            await db.execute("""
                INSERT INTO referral_progress
                (referrer_id, referred_id, actions_count, actions_required, reward_remaining, rep_remaining, created_ts)
                VALUES (?, ?, 0, ?, ?, ?, ?)
            """, (referrer_id, new_user_id, REFERRAL_ACTIONS_REQUIRED, reward_remaining, rep_remaining, int(time.time())))
            await db.commit()
        referrer_username = referrer_data["username"] or f"ID {referrer_id}"
        if bot:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎁 <b>Новый реферал!</b>\n\n"
                    f"💵 <b>Награда сейчас:</b> {format_money(immediate_reward)}\n"
                    f"⭐ <b>Репутация:</b> +{immediate_rep}\n",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления реферала: {e}")
            try:
                await bot.send_message(
                    new_user_id,
                    f"🎁 <b>Бонус за приглашение</b>\n\n"
                    f"Вы получили: <b>{format_money(invited_bonus)}</b>\n"
                    f"Пригласил: <b>{referrer_username}</b>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления приглашенного: {e}")
        return True, immediate_reward, referrer_username
    except Exception as e:
        logger.error(f"Ошибка process_referral: {e}")
        return False, 0, None
async def add_referral_action(uid: int, count: int = 1):
    """Increment referral activity and release pending reward if ready."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT referrer_id, actions_count, actions_required, reward_remaining, rep_remaining
                FROM referral_progress
                WHERE referred_id = ? AND reward_remaining > 0
            """, (uid,))
            row = await cursor.fetchone()
            if not row:
                return
            new_count = min(row["actions_required"], row["actions_count"] + count)
            await db.execute("UPDATE referral_progress SET actions_count = ? WHERE referred_id = ?", (new_count, uid))
            if new_count >= row["actions_required"]:
                await db.execute("""
                    UPDATE users
                    SET balance = balance + ?,
                        reputation = reputation + ?,
                        total_referral_earned = total_referral_earned + ?
                    WHERE id = ?
                """, (row["reward_remaining"], row["rep_remaining"], row["reward_remaining"], row["referrer_id"]))
                await db.execute("UPDATE referral_progress SET reward_remaining = 0, rep_remaining = 0 WHERE referred_id = ?", (uid,))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка add_referral_action: {e}")
async def handle_referral_start(msg: Message, referral_code: str):
    """Обработка старта с реферальной ссылкой"""
    uid = msg.from_user.id
    username = html.escape(msg.from_user.username or msg.from_user.first_name)
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
🎉 <b>Добро пожаловать в MURASAKI EMPIRE, {username}!</b>
👤 <b>Тебя пригласил:</b> {referrer_name}
💰 <b>Бонус за приглашения:</b> 30-100М за друга
🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>
👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>
💡 <b>Главные команды:</b>
- <code>меню</code> — показать все возможности
- <code>профиль</code> — ваша статистика
- <code>рефералы</code> — пригласить друзей
🎯 <b>Удачи в зарабатывании миллионов!</b>
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
   Напишите <code>бонус</code> для получения 1-5М
3. 💼 <b>Выполните первую работу!</b>
   Напишите <code>работа</code> для заработка 100k-1М
4. 👥 <b>Пригласите своих друзей!</b>
   Вы получите 30-100М за каждого друга!
🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>
👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>
💡 <b>Главные команды:</b>
- <code>меню</code> — показать все возможности
- <code>профиль</code> — ваша статистика
- <code>рефералы</code> — пригласить друзей
🎯 <b>Удачи в зарабатывании миллионов!</b>
"""
    else:
        logger.warning(f"Реферальный код {referral_code} недействителен или произошла ошибка для пользователя {uid}")
        text = f"""
🎌 <b>ДОБРО ПОЖАЛОВАТЬ В MURASAKI EMPIRE, {username}!</b>
⚠️ <b>Реферальная ссылка недействительна или устарела</b>
✨ <b>Но это не проблема! Вы все равно можете:</b>
🎁 <b>Получать бонусы каждый час:</b> 1-5М!
💼 <b>Работать каждые 5 минут:</b> 100k-1М!
👥 <b>Приглашать друзей:</b> 30-100М за каждого!
🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>
👤 <b>Ваш баланс:</b> <code>{user['balance']:,}</code>
💡 <b>Начните прямо сейчас:</b>
Напишите <code>стартбонус</code> для получения стартового бонуса 10М!
"""
    await msg.answer(text, parse_mode="HTML")
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
    """Собрать плазму с планеты - учитывает автонакопление"""
    user_planets = await get_user_planets(uid)
    if planet_id not in user_planets:
        return False, "У вас нет этой планеты"
    planet_data = PLANETS[planet_id]
    user_planet = user_planets[planet_id]
    current_time = int(time.time())
    last_collected = user_planet.get('last_collected', 0) or current_time
    # Если время не обновлялось (автонакопление уже сделало это)
    if last_collected >= current_time - 60:  # Если обновлялось менее минуты назад
        plasma_collected = 0
    else:
        plasma_per_hour = planet_data['plasma_per_hour']
        time_passed = current_time - last_collected
        plasma_collected = int((time_passed / 3600) * plasma_per_hour)
    if plasma_collected <= 0:
        return False, "Плазма еще не накопилась"
    # Применить эффекты мирового события
    world_effects = await get_world_event_effects()
    plasma_effect = world_effects.get('plasma', 0.0)
    plasma_collected = int(plasma_collected * (1 + plasma_effect))
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
async def sell_plasma(uid: int, amount: int = None):
    """Продать плазму за деньги"""
    user = await get_user(uid)
    if user['plasma'] <= 0:
        return False, 0, "У вас нет плазмы", 0
    if amount is None:
        amount = user['plasma']
    elif amount > user['plasma']:
        return False, 0, f"Недостаточно плазмы. У вас: {user['plasma']}", 0
    elif amount <= 0:
        return False, 0, "Укажите положительное количество", 0
    plasma_price = get_plasma_price()
    total_price = amount * plasma_price
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET plasma = plasma - ?, balance = balance + ? WHERE id = ?",
                           (amount, total_price, uid))
            await db.commit()
            return True, amount, total_price, plasma_price
    except Exception as e:
        logger.error(f"Ошибка sell_plasma: {e}")
        return False, 0, 0, 0
async def sell_plutonium(uid: int, amount: int = None):
    """Продать плутоний за деньги"""
    user = await get_user(uid)
    if user['plutonium'] <= 0:
        return False, 0, "У вас нет плутония", 0
    if amount is None:
        amount = user['plutonium']
    elif amount > user['plutonium']:
        return False, 0, f"Недостаточно плутония. У вас: {user['plutonium']}", 0
    elif amount <= 0:
        return False, 0, "Укажите положительное количество", 0
    total_price = amount * PLUTONIUM_PRICE_PER_UNIT
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET plutonium = plutonium - ?, balance = balance + ? WHERE id = ?",
                (amount, total_price, uid)
            )
            await db.commit()
            return True, amount, total_price, PLUTONIUM_PRICE_PER_UNIT
    except Exception as e:
        logger.error(f"Ошибка sell_plutonium: {e}")
        return False, 0, 0, 0
async def sell_artifacts(uid: int, amount: int = None):
    """Продать артефакты за деньги"""
    user = await get_user(uid)
    if user['artifacts'] <= 0:
        return False, 0, "У вас нет артефактов", 0
    if amount is None:
        amount = user['artifacts']
    elif amount > user['artifacts']:
        return False, 0, f"Недостаточно артефактов. У вас: {user['artifacts']}", 0
    elif amount <= 0:
        return False, 0, "Укажите положительное количество", 0
    total_price = amount * ARTIFACT_PRICE_PER_UNIT
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET artifacts = artifacts - ?, balance = balance + ? WHERE id = ?",
                (amount, total_price, uid)
            )
            await db.commit()
            return True, amount, total_price, ARTIFACT_PRICE_PER_UNIT
    except Exception as e:
        logger.error(f"Ошибка sell_artifacts: {e}")
        return False, 0, 0, 0
    # db.py (или где у тебя БД-функции)
async def get_active_investments(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT type, name, amount, income, start_time, end_time
            FROM investments
            WHERE user_id = ? AND active = 1
            ORDER BY start_time DESC
        """, (uid,))
        return await cursor.fetchall()
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
    """Забрать намайненые биткоины - ИСПРАВЛЕННАЯ РАБОЧАЯ ВЕРСИЯ"""
    try:
        logger.info(f"🔄 CLAIM_MINING_PROFIT вызвана для {uid}")
        # 1. Получаем данные пользователя
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT mining_gpu_count, mining_gpu_level, bitcoin, last_mining_claim
                FROM users WHERE id = ?
            """, (uid,))
            row = await cursor.fetchone()
            if not row:
                logger.error(f"❌ Пользователь {uid} не найден")
                return False, 0, "Пользователь не найден"
            user_data = dict(row)
        # 2. Проверяем наличие видеокарт
        if user_data['mining_gpu_count'] == 0:
            return False, 0, "❌ У вас нет майнинг фермы. Купите видеокарты!"
        # 3. Проверяем наличие BTC для сбора
        current_btc = user_data.get('bitcoin', 0) or 0
        logger.info(f"📊 BTC для {uid}: {current_btc:.8f}")
        if current_btc <= 0:
            # Рассчитываем сколько должно быть
            hashrate = BitcoinMining.calculate_hashrate(
                user_data['mining_gpu_count'],
                user_data['mining_gpu_level']
            )
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            current_time = int(time.time())
            last_claim_val = user_data.get('last_mining_claim', 0) or 0
            if not last_claim_val:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE users SET last_mining_claim = ? WHERE id = ?",
                        (current_time, uid)
                    )
                    await db.commit()
                return False, 0, "Майнинг запущен. Проверьте позже."
            last_claim = last_claim_val
            time_passed = current_time - last_claim
            potential_btc = btc_per_hour * (time_passed / 3600)
            logger.info(f"⏳ Рассчитано потенциально: {potential_btc:.8f} BTC")
            if potential_btc <= 0:
                return False, 0, (
                    f"⏳ <b>БИТКОИНЫ ЕЩЕ НЕ НАКОПИЛИСЬ</b>\n\n"
                    f"🎮 Ваша ферма:\n"
                    f"• Видеокарт: {user_data['mining_gpu_count']} шт.\n"
                    f"• Уровень: {user_data['mining_gpu_level']}/5\n\n"
                    f"⚡ Хешрейт: {hashrate:,.0f} MH/s\n"
                    f"₿ Майнинг: {btc_per_hour:.8f} BTC/час\n\n"
                    f"💡 Подождите 2-3 минуты."
                )
            else:
                # Если есть потенциальные BTC - начисляем их!
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("BEGIN IMMEDIATE")
                    await db.execute("""
                        UPDATE users
                        SET bitcoin = bitcoin + ?,
                            last_mining_claim = ?
                        WHERE id = ?
                    """, (potential_btc, current_time, uid))
                    await db.commit()
                # Обновляем current_btc
                current_btc = potential_btc
        # 4. Если есть BTC - забираем их
        if current_btc > 0:
            logger.info(f"💰 Собираем {current_btc:.8f} BTC для {uid}")
            btc_price = BitcoinMining.get_bitcoin_price()
            usd_value = current_btc * btc_price
            # Применяем буф дохода если активен (для отображения)
            current_ts = int(time.time())
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT income_boost_percent, income_boost_until_ts FROM users WHERE id = ?",
                    (uid,)
                )
                boost_row = await cursor.fetchone()
                if boost_row and boost_row[0] > 0 and current_ts < boost_row[1]:
                    usd_value *= (1 + boost_row[0])
                    usd_value = int(usd_value)
            logger.info(f"🎉 Успешно собрано для {uid}: {current_btc:.8f} BTC = ${usd_value:.2f}")
            return True, current_btc, usd_value
        return False, 0, "❌ Не удалось собрать биткоины"
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ошибка в claim_mining_profit для {uid}: {e}", exc_info=True)
        return False, 0, f"❌ Произошла ошибка: {str(e)}"
async def sell_bitcoin(uid: int, amount: float = None):
    """Продать биткоины - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        logger.info(f"💰 sell_bitcoin вызвана для {uid}, amount={amount}")
        # 1. Получаем данные пользователя
        user = await get_user(uid)
        now_ts = int(time.time())
        # Продажа BTC не зависит от состояния военного магазина
        current_btc = user.get('bitcoin', 0) or 0
        logger.info(f"📊 Текущий BTC баланс {uid}: {current_btc:.8f}")
        if current_btc <= 0:
            return False, 0, "❌ У вас нет биткоинов"
        # 2. Определяем количество для продажи
        btc_to_sell = 0
        if amount is None:
            btc_to_sell = current_btc
            logger.info(f"🔄 Продаем ВСЕ BTC: {btc_to_sell:.8f}")
        elif amount == 'все' or str(amount).lower() == 'all':
            btc_to_sell = current_btc
            logger.info(f"🔄 Продаем ВСЕ BTC: {btc_to_sell:.8f}")
        elif isinstance(amount, (int, float)):
            if amount > current_btc:
                return False, 0, f"❌ Недостаточно биткоинов. У вас: {current_btc:.8f} BTC"
            if amount <= 0:
                return False, 0, "❌ Укажите положительное количество"
            btc_to_sell = float(amount)
            logger.info(f"🔄 Продаем {btc_to_sell:.8f} BTC из {current_btc:.8f}")
        else:
            return False, 0, "❌ Неверный формат количества"
        # 3. Получаем текущую цену
        btc_price = BitcoinMining.get_bitcoin_price()
        usd_amount = btc_to_sell * btc_price
        # Комиссия 5%
        usd_amount *= 0.95
        usd_amount = int(usd_amount)
        logger.info(f"💵 Продажа {btc_to_sell:.8f} BTC по цене ${btc_price:,.2f} = ${usd_amount:,.2f} (после 5% комиссии)")
        # 4. Выполняем продажу
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT bitcoin FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if not row or row[0] < btc_to_sell:
                await db.rollback()
                return False, 0, "❌ Недостаточно BTC для продажи"
            await db.execute(
                "UPDATE users SET bitcoin = bitcoin - ?, balance = balance + ? WHERE id = ?",
                (btc_to_sell, int(usd_amount), uid)
            )
            await db.commit()
            logger.info(f"? ???????? ??????? BTC ??? {uid}: {btc_to_sell:.8f} BTC ? ${usd_amount:,.2f}")
            return True, btc_to_sell, int(usd_amount)
    except Exception as e:
        logger.error(f"❌ Ошибка sell_bitcoin для {uid}: {e}", exc_info=True)
        return False, 0, f"❌ Ошибка при продаже: {str(e)}"
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
    """Проверка кулдауна на бонус (1 час)"""
    try:
        user = await get_user(uid)
        last_bonus = user.get('bonus_time', 0) or 0
        total_bonus = user.get('total_bonus', 0) or 0
        current_time = time.time()
        if last_bonus == 0:
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        time_passed = current_time - last_bonus
        if time_passed >= BONUS_COOLDOWN:
            return True, 0, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
        remaining = BONUS_COOLDOWN - time_passed
        return False, remaining, {'bonus_time': last_bonus, 'total_bonus': total_bonus}
    except Exception as e:
        logger.error(f"Ошибка check_bonus_cooldown: {e}")
        return True, 0, {'bonus_time': 0, 'total_bonus': 0}
async def refresh_energy(uid: int):
    """Восстановить энергию: +1 каждые 180 сек"""
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT energy, energy_max, energy_last_ts FROM users WHERE id = ?", (uid,))
        row = await cursor.fetchone()
        if not row:
            return
        energy, energy_max, last_ts = row
        if last_ts == 0:
            await db.execute("UPDATE users SET energy_last_ts = ? WHERE id = ?", (now, uid))
            await db.commit()
            return
        elapsed = now - last_ts
        regen = elapsed // 180  # +1 per 3 min
        if regen > 0:
            new_energy = min(energy_max, energy + regen)
            await db.execute("UPDATE users SET energy = ?, energy_last_ts = ? WHERE id = ?", (new_energy, now, uid))
            await db.commit()
async def give_bonus(uid: int):
    """Выдать бонус 1-5M, +энергия, шанс бустера"""
    try:
        await refresh_energy(uid)
        amount = random.randint(1_000_000, 5_000_000)
        # Применить бонусы от титулов
        title_bonuses = await calculate_title_bonuses(uid)
        income_bonus = title_bonuses.get('income', 0.0)
        amount = int(amount * (1 + income_bonus))
        # Применить эффекты мирового события
        world_effects = await get_world_event_effects()
        income_effect = world_effects.get('income', 0.0)
        amount = int(amount * (1 + income_effect))
        current_time = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            # +энергия
            await db.execute("UPDATE users SET energy = min(energy_max, energy + 50) WHERE id = ?", (uid,))
            # Бонус
            await db.execute("""
                UPDATE users
                SET balance = balance + ?,
                    bonus_time = ?,
                    total_bonus = COALESCE(total_bonus, 0) + ?
                WHERE id = ?
            """, (amount, current_time, amount, uid))
            # Шанс бустера 10%
            if random.random() < 0.1:
                boost_until = current_time + 7200  # 2 часа
                await db.execute("UPDATE users SET income_boost_percent = 0.2, income_boost_until_ts = ? WHERE id = ?", (boost_until, uid))
            await db.commit()
            logger.info(f"✅ Бонус выдан пользователю {uid}: {amount}")
            return amount, True
    except Exception as e:
        logger.error(f"Ошибка выдачи бонуса: {e}")
        return 0, False
async def check_work_cooldown(uid: int):
    """Проверка кулдауна на работу (5 минут)"""
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
async def check_game_cooldown(uid: int, game_type: str):
    """Проверка кулдауна для игр (5 секунд)"""
    # Кулдауны для игр отключены — всегда разрешаем играть.
    # Эта функция оставлена для совместимости вызовов.
    return True, 0
async def update_game_cooldown(uid: int, game_type: str):
    """Обновить время последней игры"""
    # Кулдауны отключены — ничего не делаем (оставлено для совместимости).
    return
def get_casino_limits(reputation: int):
    if reputation < 20:
        return 100_000, 2_000_000
    if reputation < 50:
        return 500_000, 10_000_000
    if reputation < 100:
        return 2_000_000, 50_000_000
    return 10_000_000, 200_000_000
async def check_daily_wager_limit(uid: int, bet: int):
    """Check daily wager limits and max bet"""
    try:
        return True, None
    except Exception as e:
        logger.error(f"Ошибка check_daily_wager_limit: {e}")
        return True, None
async def update_daily_wager(uid: int, bet: int):
    """Обновить дневной счетчик ставок"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET total_wagered_today = total_wagered_today + ? WHERE id = ?", (bet, uid))
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка обновления wager: {e}")
async def give_work_reward(uid: int):
    """Выдать награду за работу 100k-1M, -15 энергии, бонус от репутации, шанс x2"""
    try:
        await refresh_energy(uid)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT energy, reputation FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if not row or row[0] < 15:
                return 0, False  # Недостаточно энергии
            energy, reputation = row
            amount = random.randint(100_000, 1_000_000)
            amount *= (1 + reputation * 0.02)
            # Применить бонусы от титулов
            title_bonuses = await calculate_title_bonuses(uid)
            income_bonus = title_bonuses.get('income', 0.0)
            amount *= (1 + income_bonus)
            # Применить эффекты мирового события
            world_effects = await get_world_event_effects()
            income_effect = world_effects.get('income', 0.0)
            amount *= (1 + income_effect)
            amount = int(amount)
            # Шанс x2
            if random.random() < 0.05 and energy >= 30:
                amount *= 2
            current_time = int(time.time())
            await db.execute("UPDATE users SET energy = energy - 15 WHERE id = ?", (uid,))
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
async def handle_all_commands(msg: Message):
    """Обработчик всех команд - и с / и без /"""
    text = msg.text.strip()
    # Ленивое автоначисление плазмы при любом действии пользователя
    try:
        await lazy_update_plasma(msg.from_user.id)
    except Exception:
        pass
    if not text:
        return
    parts = text.split()
    cmd = text.lower()
    if cmd == 'проверка':
        await simple_check_cmd(msg)
        return
    if cmd == 'форсфикс':
        await force_fix_cmd(msg)
        return
    if cmd == 'гарантия':
        await guarantee_cmd(msg)
        return
# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
async def check_user_has_country(uid: int) -> bool:
    """Проверяет, есть ли у пользователя своя страна"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id FROM countries WHERE owner_user_id = ?", (uid,))
            row = await cursor.fetchone()
            return row is not None
    except Exception as e:
        logger.error(f"Ошибка проверки страны пользователя {uid}: {e}")
        return False
async def get_taken_country_names() -> set:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name FROM countries WHERE owner_user_id IS NOT NULL"
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows if row and row[0]}
    except Exception as e:
        logger.error(f"Ошибка загрузки занятых названий стран: {e}")
        return set()
async def build_start_country_selection(uid: int, username: str):
    line1 = "\u0412\u042b\u0411\u041e\u0420 \u0421\u0422\u0410\u0420\u0422\u041e\u0412\u041e\u0419 \u0421\u0422\u0420\u0410\u041d\u042b"
    line3 = "\u041a\u0430\u0436\u0434\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0430 \u0438\u043c\u0435\u0435\u0442 \u0443\u043d\u0438\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u0431\u043e\u043d\u0443\u0441\u044b, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u043f\u043e\u0432\u043b\u0438\u044f\u044e\u0442 \u043d\u0430 \u0432\u0430\u0448\u0435 \u0440\u0430\u0437\u0432\u0438\u0442\u0438\u0435!"
    line4 = "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0442\u0440\u0430\u043d\u0443, \u043a\u043e\u0442\u043e\u0440\u0430\u044f \u0441\u0442\u0430\u043d\u0435\u0442 \u0432\u0430\u0448\u0438\u043c \u0434\u043e\u043c\u043e\u043c \u0438 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u043c \u0441\u0438\u043b\u044b:"
    text = (
        f"\U0001F3F0 {line1}\n\n"
        f"\u041f\u0440\u0438\u0432\u0435\u0442, {username}!\n\n"
        f"\U0001F30D {line3}\n\n"
        f"{line4}\n"
    )
    kb_buttons = []
    countries_list = START_COUNTRIES.copy()
    # Добавляем особую страну для создателя
    if uid == CREATOR_ID:
        countries_list.append(CREATOR_COUNTRY)
    taken_names = await get_taken_country_names()
    countries_list = [c for c in countries_list if c.get("name") not in taken_names]
    if not countries_list:
        return None, None
    for country in countries_list:
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{country['name']} - {country['description']}",
                callback_data=f"select_country_{country['code']}"
            )
        ])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    return text, kb
async def show_country_selection(msg: Message):
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    text, kb = await build_start_country_selection(uid, username)
    if not text:
        await msg.answer("??? ????????? ?????? ??? ??????. ????? ?? ??.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)
async def create_user_country(uid: int, country_code: str):
    """Создает страну для пользователя на основе выбранного кода"""
    try:
        # Находим страну в конфиге
        selected_country = None
        if uid == CREATOR_ID and country_code == 'sigma_empire':
            selected_country = CREATOR_COUNTRY
        else:
            for country in START_COUNTRIES:
                if country['code'] == country_code:
                    selected_country = country
                    break
        if not selected_country:
            return False
        # Генерируем начальные параметры
        population = random.randint(80_000, 150_000)
        stability = random.randint(55, 75)
        literacy = random.randint(40, 60)
        crime = random.randint(20, 35)
        happiness = random.randint(45, 65)
        # Применяем бонусы
        if selected_country['bonus_type'] == 'stability':
            stability += selected_country['bonus_value']
        elif selected_country['bonus_type'] == 'happiness':
            happiness += selected_country['bonus_value']
        elif selected_country['bonus_type'] == 'literacy':
            literacy += selected_country['bonus_value']
        elif selected_country['bonus_type'] == 'crime':
            crime += selected_country['bonus_value']
        elif selected_country['bonus_type'] == 'creator_bonuses':
            stability += selected_country['bonus_value']['stability']
            happiness += selected_country['bonus_value']['happiness']
        # Ограничиваем значения
        stability = min(100, max(0, stability))
        literacy = min(100, max(0, literacy))
        crime = min(100, max(0, crime))
        happiness = min(100, max(0, happiness))
        treasury = 1_000_000  # Базовая казна
        if selected_country['bonus_type'] == 'start_treasury':
            treasury = int(treasury * (1 + selected_country['bonus_value']))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT 1 FROM countries WHERE name = ? AND owner_user_id IS NOT NULL",
                (selected_country["name"],)
            )
            if await cursor.fetchone():
                await db.rollback()
                return False
            # Создаем страну
            cursor = await db.execute(
                "SELECT id FROM countries WHERE name = ? AND owner_user_id IS NULL",
                (selected_country["name"],)
            )
            existing = await cursor.fetchone()
            if existing:
                country_id = existing[0]
                try:
                    await db.execute("""
                        UPDATE countries
                        SET owner_user_id = ?, level = 1, treasury = ?, stability = ?, tax_rate = 0.10,
                            last_tick = ?, population = ?, literacy = ?, crime = ?, happiness = ?
                        WHERE id = ?
                    """, (uid, treasury, stability, int(time.time()),
                          population, literacy, crime, happiness, country_id))
                except Exception:
                    await db.execute("""
                        UPDATE countries
                        SET owner_user_id = ?, level = 1, treasury = ?, stability = ?, tax_rate = 0.10, last_tick = ?
                        WHERE id = ?
                    """, (uid, treasury, stability, int(time.time()), country_id))
            else:
                try:
                    cursor = await db.execute("""
                        INSERT INTO countries (name, owner_user_id, level, treasury, stability, tax_rate, last_tick,
                                             population, literacy, crime, happiness)
                        VALUES (?, ?, 1, ?, ?, 0.10, ?, ?, ?, ?, ?)
                    """, (selected_country['name'], uid, treasury, stability, int(time.time()),
                          population, literacy, crime, happiness))
                except Exception:
                    cursor = await db.execute("""
                        INSERT INTO countries (name, owner_user_id, level, treasury, stability, tax_rate, last_tick)
                        VALUES (?, ?, 1, ?, ?, 0.10, ?)
                    """, (selected_country['name'], uid, treasury, stability, int(time.time())))
                country_id = cursor.lastrowid
            # Создаем стартовые здания
            await db.execute("""
                INSERT OR IGNORE INTO country_buildings (country_id, building_type, level) VALUES
                (?, 'parks', 1),
                (?, 'school', 1),
                (?, 'police', 1),
                (?, 'barracks', 1)
            """, (country_id, country_id, country_id, country_id))
            await db.commit()
            logger.info(f"✅ Создана страна {selected_country['name']} для пользователя {uid}")
            return True
    except Exception as e:
        logger.error(f"Ошибка создания страны для {uid}: {e}")
        return False
def split_long_message(text: str, max_len: int = 3500):
    if len(text) <= max_len:
        return [text]
    parts = text.split('\n\n')
    chunks = []
    current = ''
    for part in parts:
        candidate = part if not current else current + '\n\n' + part
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(part) <= max_len:
            current = part
        else:
            # hard split if a single paragraph is too long
            for i in range(0, len(part), max_len):
                chunks.append(part[i:i + max_len])
            current = ''
    if current:
        chunks.append(current)
    return chunks
def split_html_message(text: str, max_len: int = 3500):
    if len(text) <= max_len:
        return [text]
    tag_re = re.compile(r"(<\/?b>|<\/?code>)")
    tokens = tag_re.split(text)
    chunks = []
    current = ""
    stack = []
    def open_tags():
        return "".join(f"<{t}>" for t in stack)
    def close_tags():
        return "".join(f"</{t}>" for t in reversed(stack))
    def stack_close_len():
        return sum(len(f"</{t}>") for t in stack)
    for token in tokens:
        if token in ("<b>", "</b>", "<code>", "</code>"):
            token_tag = token.strip("<>/")
            if token.startswith("</"):
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i] == token_tag:
                        stack.pop(i)
                        break
            else:
                stack.append(token_tag)
            if len(current) + len(token) + stack_close_len() > max_len and current:
                current += close_tags()
                chunks.append(current)
                current = open_tags()
            current += token
            continue
        text_part = token
        while text_part:
            available = max_len - len(current) - stack_close_len()
            if available <= 0:
                current += close_tags()
                chunks.append(current)
                current = open_tags()
                continue
            if len(text_part) <= available:
                current += text_part
                text_part = ""
                continue
            split_pos = text_part.rfind("\n", 0, available)
            if split_pos == -1:
                split_pos = text_part.rfind(" ", 0, available)
            if split_pos == -1:
                split_pos = available
            current += text_part[:split_pos]
            text_part = text_part[split_pos:]
            current += close_tags()
            chunks.append(current)
            current = open_tags()
    if current:
        current += close_tags()
        chunks.append(current)
    return chunks
def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "менее минуты"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}ч {minutes}м"
    if hours:
        return f"{hours}ч"
    if minutes:
        return f"{minutes}м"
    return "менее минуты"
def format_timestamp(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
async def send_welcome_message(msg: Message, force_menu: bool = False, edit: bool = False):
    """Приветственное сообщение"""
    user = await get_user(msg.from_user.id)
    username = msg.from_user.username or msg.from_user.first_name
    # Проверяем, выбрал ли пользователь страну
    has_country = await check_user_has_country(msg.from_user.id)
    if not has_country and not force_menu:
        await show_country_selection(msg)
        return
    welcome_text = f"""
👋 <b>Добро пожаловать в MURASAKI EMPIRE, {username}!</b>
Murasaki — Lord of Empires 🗿
Добро пожаловать в стратегическую RPG-игру в Telegram.
Ты начинаешь с нуля и со временем становишься правителем, полководцем и архитектором собственной империи.
🌍 Государства и власть
— В начале ты выбираешь страну и становишься её владельцем
— У каждой страны есть население и армия
— Население растёт со временем, часть людей можно мобилизовать
— Ты управляешь:
• экономикой
• налогами
• стабильностью
• преступностью
• грамотностью
— Страну можно развивать зданиями:
школы, больницы, парки, полиция, казармы, АЭС, космическая станция и другие
💼 Экономика и бизнес
— Покупай и улучшай бизнесы внутри страны
— Бизнесы дают рабочие места и усиливают доход государства
— Экономика — основа силы, без неё война невозможна
💰 Заработок
— Работа — активный заработок с кулдауном
— Ежедневный бонус — серия входа 30 дней с умеренной прибылью
— Пассивный доход — страны и бизнесы копят прибыль
🎰 Казино
Казино — это риск.
Здесь можно как выиграть, так и потерять деньги.
Азарт влияет на баланс и судьбу империи.
👥 Кланы
— Создавай кланы, приглашай игроков
— Общая казна и логи операций
— Совместные рейды и боссы
— Кланы — путь к доминированию
🐉 Боссы и рейды
— Клановые боссы атакуются военной силой стран
— Награды:
• деньги
• плазма
• плутоний
• уникальные предметы
— Финальный враг мира —
Жирный Сигма Ярик 😈
⚔️ Войны между странами
— Покупай оружие и технику (танки, бронетехника и др.)
— Войны идут раундами
— Есть потери армии, техники и контрибуция
— Победа требует стратегии, а не кликов
🎁 Уникальные предметы
— Выпадают с боссов и редких событий
— Не покупаются
— Дают бонусы к войнам и рейдам
— Включают легендарные артефакты Сигмы Ярика
🌌 Космос (эндгейм)
— После космостанции открываются экспедиции
— Открытия, риск, аномалии и колонии на других планетах
— Космос даёт:
• плазму
• плутоний
• технологии
• престижь
Это путь для сильнейших.
💳 Кредиты
— Можно брать кредиты у игроков
— Или у Сигмы (жёсткие условия)
— Не вернул — будут последствия
📌 Напиши хелп, чтобы увидеть доступные команды
📌 Игра развивается — мир Murasaki живёт и меняется
Murasaki — Lord of Empires
Здесь создаются империи.
💰 <b>Ваш баланс:</b> {format_money(user['balance'])}
⚡ <b>Плазма:</b> {user['plasma']}
₿ <b>Биткоин:</b> {user['bitcoin']:.8f}
✨ <b>Основные системы:</b>
💼 <b>БИЗНЕСЫ СТРАНЫ</b> - развивайте экономику внутри страны
- <code>страна</code> - ваша страна
• В стране: Экономика → Бизнесы
🪐 <b>ПЛАНЕТЫ</b> - Колонизируйте планеты и собирайте плазму!
- <code>планеты</code> - список планет
- <code>купить планету [id]</code> - купить планету
- <code>собрать плазму [id]</code> - собрать плазму
⛏️ <b>МАЙНИНГ</b> - Майните биткоины и продавайте их!
- <code>майнинг</code> - информация о майнинге
- <code>купить видеокарту</code> - купить видеокарту
- <code>улучшить видеокарты</code> - улучшить все видеокарты
- <code>забрать биткоины</code> - забрать намайненые BTC
- <code>продать биткоин [кол-во]</code> - продать BTC
💼 <b>ИНВЕСТИЦИИ</b> - Инвестируйте и получайте прибыль!
- <code>инвестиции</code> - список инвестиций
- <code>начать инвестицию [id]</code> - начать инвестицию (с кнопками)
- <code>начать инвестицию [id] [сумма]</code> - начать инвестицию
- <code>завершить инвестицию [id]</code> - завершить инвестицию
🎰 <b>КАЗИНО И ИГРЫ:</b>
- <code>монетка [ставка]</code> - игра в монетку
- <code>кости [ставка]</code> - игра в кости
- <code>слоты [ставка]</code> - игровые автоматы
- <code>рулетка [ставка] [тип]</code> - рулетка
- <code>блекджек [ставка]</code> - игра в блэкджек
🌍 <b>СТРАНЫ И КЛАНЫ:</b>
- <code>страны</code> - список стран
- <code>моя страна</code> - управление вашей страной
- <code>кланы</code> - список кланов
- <code>мой клан</code> - управление вашим кланом
⚔️ <b>ВОЙНЫ И БОССЫ:</b>
- <code>войны</code> - текущие войны
- <code>боссы</code> - рейды на боссов
🎮 <b>ОСНОВНЫЕ КОМАНДЫ:</b>
- <code>бонус</code> - получить бонус (1-5М каждый час)
- <code>работа</code> - выполнить работу (100k-1М каждые 5 мин)
- <code>стартбонус</code> - получить стартовый бонус 10М
- <code>профиль</code> - ваша статистика
- <code>рефералы</code> - пригласить друзей
- <code>топ</code> - топ игроков
🔗 <b>Ваша реферальная ссылка:</b>
<code>https://t.me/{(await msg.bot.get_me()).username}?start={user['referral_code']}</code>
🎯 <b>Удачи в зарабатывании!</b>
"""
    tag_placeholders = {
        "<b>": "__TAG_B_OPEN__",
        "</b>": "__TAG_B_CLOSE__",
        "<code>": "__TAG_CODE_OPEN__",
        "</code>": "__TAG_CODE_CLOSE__",
    }
    safe_text = welcome_text
    for tag, placeholder in tag_placeholders.items():
        safe_text = safe_text.replace(tag, placeholder)
    safe_text = html.escape(safe_text)
    for tag, placeholder in tag_placeholders.items():
        safe_text = safe_text.replace(placeholder, tag)
    welcome_text = safe_text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎣 Рыбалка", callback_data="show_fishing")],
        [InlineKeyboardButton(text="🪐 Планеты", callback_data="show_planets")],
        [InlineKeyboardButton(text="⛏️ Майнинг", callback_data="show_mining"),
         InlineKeyboardButton(text="💼 Инвестиции", callback_data="show_investments")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="get_bonus"),
         InlineKeyboardButton(text="💼 Работа", callback_data="get_work")],
        [InlineKeyboardButton(text="📊 Профиль", callback_data="show_profile"),
         InlineKeyboardButton(text="🏆 Топ", callback_data="show_top")],
        [InlineKeyboardButton(text="🌍 Страны", callback_data="show_countries"),
         InlineKeyboardButton(text="👥 Кланы", callback_data="show_clans")],
        [InlineKeyboardButton(text="⚔️ Войны", callback_data="show_wars"),
         InlineKeyboardButton(text="🐉 Боссы", callback_data="show_bosses")],
        [InlineKeyboardButton(text="🛒 Военный магазин", callback_data="show_weapons_shop")]
    ])
    chunks = split_html_message(welcome_text)
    if edit:
        try:
            await msg.edit_text(chunks[0], parse_mode="HTML", reply_markup=kb)
        except Exception:
            await msg.answer(chunks[0], parse_mode="HTML", reply_markup=kb)
    else:
        await msg.answer(chunks[0], parse_mode="HTML", reply_markup=kb)
    for chunk in chunks[1:]:
        await msg.answer(chunk, parse_mode="HTML")
async def process_bonus(msg: Message):
    """Handle bonus command"""
    uid = msg.from_user.id
    can_get_bonus, remaining, bonus_data = await check_bonus_cooldown(uid)
    if not can_get_bonus:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        progress_percent = int((BONUS_COOLDOWN - remaining) / BONUS_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        await msg.reply(
            f"❌ <b>Бонус еще не готов!</b>\n\n"
            f"⏳ <b>Следующий бонус через:</b>\n"
            f"{minutes} мин {seconds} сек\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕒 <b>Доступен в:</b> {next_str}\n"
            f"💵 <b>Всего бонусов:</b> {bonus_data.get('total_bonus', 0):,}",
            parse_mode="HTML"
        )
        return
    amount, success = await give_bonus(uid)
    if not success:
        await msg.reply("? ?????? ????????? ??????", parse_mode="HTML")
        return
    await add_referral_action(uid)
    updated_user = await get_user(uid)
    next_time = time.time() + BONUS_COOLDOWN
    next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
    await msg.reply(
        f"🎁 <b>Бонус получен!</b>\n\n"
        f"💵 <b>Сумма:</b> {amount:,}\n"
        f"💳 <b>Баланс:</b> {updated_user.get('balance', 0):,}\n\n"
        f"⏱ <b>Следующий бонус:</b> {next_str}",
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
            f"✨ <b>Следующий бонус:</b> 1-5М",
            parse_mode="HTML"
        )
    else:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        progress_percent = int((BONUS_COOLDOWN - remaining) / BONUS_COOLDOWN * 100)
        progress_bar = create_progress_bar(progress_percent)
        next_time = time.time() + remaining
        next_str = time.strftime('%H:%M:%S', time.localtime(next_time))
        await msg.reply(
            f"⏳ <b>До следующего бонуса:</b>\n"
            f"<b>{minutes} минут {seconds} секунд</b>\n\n"
            f"{progress_bar} {progress_percent}%\n\n"
            f"🕐 <b>Будет доступен в:</b> {next_str}\n\n"
            f"💰 Всего получено: <code>{bonus_data.get('total_bonus', 0):,}</code>\n"
            f"🎯 <b>Следующий бонус:</b> 1-5М",
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
    if success:
        await add_referral_action(uid)
    if not success:
        user_data = await get_user(uid)
        await msg.reply(
            f"⚠️ <b>Не удалось выполнить работу</b>\n\n"
            f"💰 <b>Текущий баланс:</b> <code>{user_data.get('balance', 0):,}</code>\n"
            f"💼 <b>Всего заработано:</b> <code>{user_data.get('total_work', 0):,}</code>",
            parse_mode="HTML"
        )
        return
# Получаем СВЕЖИЕ данные без кэша
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
        f"⏰ <b>Следующая работа через 5 минут:</b>\n"
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
            f"• Написать <code>бонус</code> для получения 1-5М\n"
            f"• Написать <code>работа</code> для заработка 100k-1М\n"
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
    """????????? ??????? ???????"""
    # Reuse the existing profile renderer to send a message in chat.
    await profile_cmd(msg)
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
🏢 Бизнесов страны: {await count_user_country_businesses(user_id)}
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
        progress_percent = int((BONUS_COOLDOWN - remaining_bonus) / BONUS_COOLDOWN * 100)
        bonus_bar = create_progress_bar(progress_percent)
        bonus_status = f"⏳ <b>Через:</b> {minutes}м {seconds}с"
        bonus_time = f"{bonus_bar} {progress_percent}%"
    if can_work:
        work_status = "✅ <b>Доступна сейчас!</b>"
        work_time = "Следующая через 5 минут"
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
        f"🎁 <b>Ежечасный бонус (1-5М):</b>\n"
        f"• Статус: {bonus_status}\n"
        f"• {bonus_time}\n"
        f"• Всего получено: {user.get('total_bonus', 0):,}\n\n"
        f"💼 <b>Работа раз в 5 минут (100k-1М):</b>\n"
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
                "- <code>бонус</code> - 1-5М каждый час\n"
                "- <code>работа</code> - 100k-1М каждые 5 мин\n"
                "- <code>страна</code> - развивайте экономику страны\n"
                "- <code>инвестиции</code> - вкладывайте и получайте доход",
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
            f"✨ <b>Следующая работа:</b> 100k-1М",
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
            f"🎯 <b>Следующая работа:</b> 100k-1М",
            parse_mode="HTML"
        )
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
    planets_list += "- <code>купить планету [id]</code> - купить планету\n"
    planets_list += "- <code>собрать плазму [id]</code> - собрать плазму\n"
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
- <code>купить видеокарту</code> - купить видеокарту ({format_money(BitcoinMining.get_gpu_price(user['mining_gpu_level']))})
- <code>улучшить видеокарты</code> - улучшить все видеокарты
- <code>забрать биткоины</code> - забрать намайненые BTC
- <code>продать биткоин [кол-во]</code> - продать BTC
- <code>продать биткоин все</code> - продать все BTC
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
    investments_list += "- <code>начать инвестицию [id] [сумма]</code> - начать инвестицию\n"
    investments_list += "- <code>завершить инвестицию [id]</code> - завершить инвестицию\n"
    await msg.reply(investments_list, parse_mode="HTML")
# ========== ИГРОВЫЕ ФУНКЦИИ ИЗ ТВОЕГО КОДА ==========
async def process_coin(msg: Message, parts: list):
    """Обработка команды монетка с КД 5 секунд"""
    # Проверяем КД
    can_play, remaining = await check_game_cooldown(msg.from_user.id, "coin")
    if not can_play:
        seconds = int(remaining)
        await msg.reply(f"⏳ Подождите {seconds} секунд перед следующей игрой!")
        return
    # В конце функции ДОБАВЬТЕ:
    await update_game_cooldown(msg.from_user.id, "coin")
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
    # Проверка дневного лимита ставок
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
        return
    await update_game_cooldown(msg.from_user.id, "coin")
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
    """Обработка команды кости с КД 5 секунд"""
    # Проверяем КД
    can_play, remaining = await check_game_cooldown(msg.from_user.id, "dice")
    if not can_play:
        seconds = int(remaining)
        await msg.reply(f"⏳ Подождите {seconds} секунд перед следующей игрой!")
        return
    """Обработка команды кости"""
    if len(parts) < 2:
        await msg.reply("❌ Укажите ставку!\nПример: <code>кости 1000</code> или <code>кости 1к</code> или <code>кости 1кк</code>", parse_mode="HTML")
        await update_game_cooldown(msg.from_user.id, "dice")
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
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
        return
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    # Обновляем дневной счетчик ставок
    await update_daily_wager(msg.from_user.id, bet)
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
    # Проверка дневного лимита ставок
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
        return
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    # Обновляем дневной счетчик ставок
    await update_daily_wager(msg.from_user.id, bet)
    symbols = ["🍒", "🔔", "💎", "7️⃣", "🍋", "⭐"]
    loading_msg = await msg.reply("🎰 <b>Крутим слоты...</b>\n┃ 🎰 ┃ 🎰 ┃ 🎰 ┃", parse_mode="HTML")
    for i in range(2):
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)
        await loading_msg.edit_text(f"🎰 <b>Крутим слоты...</b>\n┃ {slot1} ┃ {slot2} ┃ {slot3} ┃", parse_mode="HTML")
        await asyncio.sleep(0.05)
    for i in range(3):
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
def extract_text_command_parts(text, aliases):
    """Return parts if the first word matches one of the aliases."""
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    parts = stripped.split()
    if not parts:
        return None
    if parts[0].lower() in aliases:
        return parts
    return None
async def process_roulette(msg: Message, parts: list):
    """Обработка команды рулетка"""
    if len(parts) < 3:
        await msg.reply(
            "🎰 <b>Рулетка - Помощь</b>\n\n"
            "🎯 <b>Формат:</b> <code>рулетка [ставка] [тип]</code>\n"
            "🎯 <b>Коротко:</b> <code>рул [ставка] [тип]</code>\n\n"
            "🎯 <b>Типы ставок:</b>\n"
            "- <code>красное</code> / <code>крас</code> (x2)\n"
            "- <code>черное</code> / <code>черн</code> (x2)\n"
            "- <code>зеленое</code> / <code>зел</code> (x36)\n"
            "- <code>четное</code> / <code>чет</code> (x2)\n"
            "- <code>нечетное</code> / <code>нечет</code> (x2)\n"
            "- <code>1-18</code> / <code>19-36</code> (x2)\n"
            "- <code>1-12</code> / <code>13-24</code> / <code>25-36</code> (x3)\n"
            "- <code>[число от 0 до 36]</code> (x36)\n\n"
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
    # Проверка дневного лимита ставок
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
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
    # Обновляем дневной счетчик ставок
    await update_daily_wager(msg.from_user.id, bet)
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
            "- <code>дротик 1000</code>\n"
            "- <code>дротик 1к</code>\n"
            "- <code>дротик 1кк</code>",
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
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
        return
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    # ????????? ??????? ??????? ??????
    await update_daily_wager(msg.from_user.id, bet)
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
    # Проверка дневного лимита ставок
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
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
    # Обновляем дневной счетчик ставок
    await update_daily_wager(uid, bet)
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
# Добавь глобальную переменную для хранения игр
active_crash_games = {}  # {message_id: {"bet": int, "multiplier": float, "user_id": int, "crashed": bool}}
async def process_crash(msg: Message, parts: list):
    """Обработка команды краш - ФИКСИРОВАННАЯ ВЕРСИЯ"""
    # Проверяем КД
    can_play, remaining = await check_game_cooldown(msg.from_user.id, "crash")
    if not can_play:
        seconds = int(remaining)
        await msg.reply(f"⏳ Подождите {seconds} секунд перед следующей игрой!")
        return
    if len(parts) < 2:
        await msg.reply("🎮 Используйте: <code>краш [ставка]</code>\nПример: краш 1000 или краш 1к")
        return
    bet_str = parts[1]
    bet = parse_amount(bet_str)
    if bet <= 0:
        await msg.reply("❌ Неправильная ставка! Используйте: 1000, 1к, 1кк")
        return
    user = await get_user(msg.from_user.id)
    if bet > user['balance']:
        await msg.reply(f"❌ Не хватает денег. Баланс: {format_money(user['balance'])}")
        return
    can_wager, error_msg = await check_daily_wager_limit(msg.from_user.id, bet)
    if not can_wager:
        await msg.reply(error_msg, parse_mode="HTML")
        return
    success = await change_balance(msg.from_user.id, -bet)
    if not success:
        await msg.reply("❌ Ошибка при списании средств")
        return
    # ????????? ??????? ??????? ??????
    await update_daily_wager(msg.from_user.id, bet)
    # Обновляем КД
    await update_game_cooldown(msg.from_user.id, "crash")
    # Генерируем точку краха
    crash_point = CrashGame.get_crash_point()
    crash_point_rounded = round(crash_point, 2)
    # Создаем клавиатуру для игры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Забрать сейчас", callback_data=f"crash_cashout_{msg.from_user.id}")]
    ])
    # Начинаем игру
    message = await msg.reply(
        f"🚀 <b>КРАШ ИГРА НАЧАЛАСЬ!</b>\n\n"
        f"💰 Ставка: {format_money(bet)}\n"
        f"🎯 Точка краха: <b>???</b>\n\n"
        f"⏳ Множитель растет...\n"
        f"📈 Текущий: <b>1.00x</b>\n\n"
        f"<i>Нажми 'Забрать сейчас' чтобы получить выигрыш!</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    # Сохраняем игру в память
    active_crash_games[message.message_id] = {
        "bet": bet,
        "multiplier": 1.0,
        "user_id": msg.from_user.id,
        "crashed": False,
        "cashed_out": False,
        "cash_point": crash_point_rounded
    }
    # Запускаем игру в фоне
    asyncio.create_task(run_simple_crash_game(message.message_id, bet, crash_point_rounded, message))
async def process_transfer(msg: Message, parts: list):
    """Обработка команды передачи денег"""
    if len(parts) < 2:
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
    recipient_id_from_reply = None
    recipient_username = parts[2].lower().replace('@', '') if len(parts) > 2 else ""
    if msg.reply_to_message and msg.reply_to_message.from_user:
        recipient_id_from_reply = msg.reply_to_message.from_user.id
        await create_user_if_not_exists(
            recipient_id_from_reply,
            msg.reply_to_message.from_user.username or msg.reply_to_message.from_user.first_name
        )
    if not recipient_id_from_reply and len(parts) < 3:
        await msg.reply("¢?? ?‘?õ?>‘?ú‘?ü‘'ç: <code>õç‘?ç?ø‘'‘? [‘?‘???ø] @‘?úç‘??çü?</code>\n?‘?ñ?ç‘?: õç‘?ç?ø‘'‘? 1000 @username", parse_mode="HTML")
        return
    if recipient_username.isdigit() and not recipient_id_from_reply:
        await msg.reply("❌ Укажите @юзернейм, а не ID")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if recipient_id_from_reply:
                row = {'id': recipient_id_from_reply}
            else:
                cursor = await db.execute(
                    "SELECT id, username FROM users WHERE username = ? COLLATE NOCASE",
                    (recipient_username,)
                )
                row = await cursor.fetchone()
                if not row:
                    await msg.reply(
                        f"??? ?????>???????????'???>?? @{recipient_username} ???? ???????????? ?? ???????'??????."
                        f"???????'?? ???? ?????????????' ?+???'?? /start, ???'???+?< ???????????????'?????????????'??????."
                    )
                    return
            recipient_id = row['id']
            if recipient_id == sender_id:
                await msg.reply("❌ Нельзя переводить деньги самому себе!")
                return
            # Атомарный перевод в одной транзакции
            try:
                await db.execute("BEGIN IMMEDIATE")
                # Проверяем текущий баланс отправителя
                cur = await db.execute("SELECT balance FROM users WHERE id = ?", (sender_id,))
                srow = await cur.fetchone()
                sbalance = srow[0] if srow else 0
                if sbalance < amount:
                    await db.rollback()
                    await msg.reply(f"❌ Недостаточно средств! Баланс: {sbalance:,}", parse_mode="HTML")
                    return
                # Выполняем списание и зачисление
                fee = int(amount * 0.02)
                net_amount = amount - fee
                await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, sender_id))
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (net_amount, recipient_id))
                await db.commit()
            except Exception as e:
                try:
                    await db.rollback()
                except:
                    pass
                logger.error(f"Ошибка в атомарном переводе: {e}")
                await msg.reply("❌ Ошибка при переводе. Попробуйте позже.")
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
@router.message(F.text.lower() == "админ майнинг")
async def admin_mining_panel(msg: Message):
    """Админ-панель управления майнингом"""
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Форс-фикс для себя", callback_data="admin_force_fix_self"),
         InlineKeyboardButton(text="🔧 Форс-фикс по ID", callback_data="admin_force_fix_id")],
        [InlineKeyboardButton(text="📊 Статистика майнинга", callback_data="admin_mining_stats"),
         InlineKeyboardButton(text="🎮 Выдать видеокарты", callback_data="admin_give_gpu")],
        [InlineKeyboardButton(text="💰 Выдать BTC", callback_data="admin_give_btc"),
         InlineKeyboardButton(text="🔄 Сбросить время всем", callback_data="admin_reset_all_time")]
    ])
    await msg.reply(
        "⚙️ <b>АДМИН-ПАНЕЛЬ МАЙНИНГА</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
@router.message(F.text.lower() == "розыгрыш лотереи")
async def draw_lottery_cmd(msg: Message):
    """Принудительный розыгрыш лотереи (админ)"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    winners = await draw_lottery()
    if not winners:
        await msg.reply("🎰 Нет участников для розыгрыша")
        return
    text = "🎉 <b>РОЗЫГРЫШ ЛОТЕРЕИ ЗАВЕРШЕН!</b>\n\n"
    for lottery in winners:
        ticket_name = LOTTERY_TICKETS[lottery['ticket_type']]['name']
        text += f"<b>{ticket_name}</b>\n"
        text += f"💰 Призовой фонд: {format_money(lottery['prize_pool'])}\n\n"
        for winner in lottery['winners']:
            user = await get_user(winner['user_id'])
            username = user.get('username', f"ID {winner['user_id']}")
            if winner['position'] == 1:
                emoji = "🥇"
            elif winner['position'] == 2:
                emoji = "🥈"
            else:
                emoji = "🥉"
            text += f"{emoji} {username} - {format_money(winner['prize'])}\n"
        text += "\n"
    await msg.reply(text, parse_mode="HTML")
    # Уведомляем победителей
    for lottery in winners:
        for winner in lottery['winners']:
            try:
                await msg.bot.send_message(
                    winner['user_id'],
                    f"🎉 <b>ВЫ ВЫИГРАЛИ В ЛОТЕРЕЕ!</b>\n\n"
                    f"🎫 Тип билета: {LOTTERY_TICKETS[lottery['ticket_type']]['name']}\n"
                    f"🏆 Место: {winner['position']}\n"
                    f"💰 Выигрыш: {format_money(winner['prize'])}\n\n"
                    f"🎰 Поздравляем!",
                    parse_mode="HTML"
                )
            except:
                pass  # Если пользователь заблокировал бота
@router.message(F.text.lower() == "сбросить лотерею")
async def reset_lottery_cmd(msg: Message):
    """Сбросить лотерею (админ)"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    await reset_lottery()
    await msg.reply("✅ Лотерея сброшена! Новый день начался.")
async def process_admin_give_reply(msg: Message, parts: list):
    """Админ: выдать деньги по ответу"""
    # Проверяем, что сообщение является ответом
    if not msg.reply_to_message:
        await msg.reply("❌ Используйте команду <code>выдать [сумма]</code> в ответ на сообщение пользователя")
        return
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
    """Админ: забрать деньги по ID/юзернейму - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if len(parts) < 3:
        await msg.reply("❌ Используйте: <code>забрать @юзернейм [сумма]</code> или <code>забрать ID [сумма]</code>", parse_mode="HTML")
        return
    target_arg = parts[1]
    amount_str = parts[2]
    amount = parse_amount(amount_str)
    target_id = None
    target_username = ""
    if target_arg.isdigit():
        target_id = int(target_arg)
        target_username = f"ID {target_id}"
    elif target_arg.startswith('@'):
        username = target_arg[1:]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, username FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            if row:
                target_id = row['id']
                target_username = f"@{row['username']}"
            else:
                await msg.reply(f"❌ Пользователь @{username} не найден")
                return
    else:
        await msg.reply("❌ Укажите ID или @юзернейм")
        return
    if amount <= 0:
        await msg.reply("❌ Сумма должна быть больше 0")
        return
    # Получаем текущий баланс пользователя
    target_user = await get_user(target_id)
    if not target_user:
        await msg.reply(f"❌ Пользователь {target_username} не найден в базе данных")
        return
    if target_user['balance'] < amount:
        await msg.reply(f"❌ У пользователя только {format_money(target_user['balance'])}")
        return
    # **ИСПРАВЛЕНИЕ: Используем транзакцию для гарантированного списания**
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Начинаем транзакцию
            await db.execute("BEGIN")
            # Списываем деньги
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (amount, target_id)
            )
            # Получаем новый баланс для проверки
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (target_id,))
            new_balance_row = await cursor.fetchone()
            new_balance = new_balance_row[0] if new_balance_row else 0
            # Подтверждаем транзакцию
            await db.commit()
            logger.info(f"✅ Админ {msg.from_user.id} забрал {amount:,} у пользователя {target_id}")
            await msg.reply(
                f"✅ <b>Деньги успешно забраны!</b>\n\n"
                f"💸 <b>Сумма:</b> {format_money(amount)}\n"
                f"👤 <b>Пользователь:</b> {target_username} (ID: {target_id})\n"
                f"💰 <b>Новый баланс пользователя:</b> {format_money(new_balance)}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка при списании денег: {e}")
        await msg.reply(f"❌ Ошибка при списании: {e}")
# Также нужно исправить функцию process_admin_take_reply:
async def process_admin_take_reply(msg: Message, parts: list):
    """Админ: забрать деньги по ответу - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if len(parts) < 2:
        await msg.reply("❌ Используйте: <code>забрать [сумма]</code> в ответ на сообщение", parse_mode="HTML")
        return
    amount_str = parts[1]
    amount = parse_amount(amount_str)
    if amount <= 0:
        await msg.reply("❌ Сумма должна быть больше 0")
        return
    target_id = msg.reply_to_message.from_user.id
    target_username = msg.reply_to_message.from_user.username or f"ID {target_id}"
    # Получаем текущий баланс
    target_user = await get_user(target_id)
    if target_user['balance'] < amount:
        await msg.reply(f"❌ У пользователя только {format_money(target_user['balance'])}")
        return
    # **ИСПРАВЛЕНИЕ: Используем транзакцию**
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN")
            # Списываем деньги
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (amount, target_id)
            )
            # Получаем новый баланс
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (target_id,))
            new_balance_row = await cursor.fetchone()
            new_balance = new_balance_row[0] if new_balance_row else 0
            await db.commit()
            logger.info(f"✅ Админ {msg.from_user.id} забрал {amount:,} у пользователя {target_id}")
            await msg.reply(
                f"✅ <b>Деньги успешно забраны!</b>\n\n"
                f"💸 <b>Сумма:</b> {format_money(amount)}\n"
                f"👤 <b>Пользователь:</b> {target_username} (ID: {target_id})\n"
                f"💰 <b>Новый баланс пользователя:</b> {format_money(new_balance)}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка при списании денег: {e}")
        await msg.reply(f"❌ Ошибка при списании: {e}")
# =======================================
#        ХЭНДЛЕРЫ АДМИН-КОМАНД
# =======================================
@router.message(F.text.lower().startswith("выдать"))
async def cmd_give_text(msg: Message):
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if msg.reply_to_message:
        await process_admin_give_reply(msg, parts)
    else:
        await process_admin_give(msg, parts)
@router.message(F.text.lower().startswith("завершить игру "))
async def force_end_game_cmd(msg: Message):
    """Принудительно завершить игру (админ)"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply("❌ Используйте: завершить игру [ID пользователя]")
        return
    try:
        target_uid = int(parts[2])
    except:
        await msg.reply("❌ ID должен быть числом")
        return
    if target_uid not in crash_games:
        await msg.reply(f"❌ У пользователя {target_uid} нет активной игры")
        return
    # Завершаем игру
    game_info = crash_games[target_uid]
    bet = game_info.get("bet", 0)
    # Возвращаем ставку если игрок еще не забрал
    if not game_info.get("cashed_out", False):
        await change_balance(target_uid, bet)
    # Удаляем игру
    del crash_games[target_uid]
    await msg.reply(
        f"✅ <b>Игра принудительно завершена для пользователя {target_uid}</b>\n\n"
        f"💰 Ставка: {format_money(bet)} (возвращена если не был кэшаут)\n"
        f"📈 Множитель: {game_info.get('multiplier', 1.0)}x\n"
        f"🎮 Статус: Завершена администратором",
        parse_mode="HTML"
    )
@router.message(F.text.lower().startswith("забрать"))
async def cmd_take_text(msg: Message):
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
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
            "- <code>красное</code> (x2)\n"
            "- <code>черное</code> (x2)\n"
            "- <code>зеленое</code> (x36)\n"
            "- <code>четное</code> / <code>нечетное</code> (x2)\n"
            "- <code>1-18</code> / <code>19-36</code> (x2)\n"
            "- <code>1-12</code> / <code>13-24</code> / <code>25-36</code> (x3)\n"
            "- <code>[число от 0 до 36]</code> (x36)\n\n"
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
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if msg.reply_to_message:
        await process_admin_give_reply(msg, parts)
    else:
        await process_admin_give(msg, parts)
@router.message(Command("забрать"))
async def cmd_take_slash(msg: Message):
    # Проверяем права администратора
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if msg.reply_to_message:
        await process_admin_take_reply(msg, parts)
    else:
        await process_admin_take(msg, parts)
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
@router.message(F.text.lower().in_(["ежедневная", "ежедневка", "ежедневный", "ежеднев", "daily", "дэйли"]))
@router.message(Command("daily", "ежедневная", "ежедневный", "ежеднев"))
async def daily_reward_cmd(msg: Message):
    await process_daily_reward(msg)
@router.message(Command("рефералы", "реферал", "ref"))
@router.message(F.text.lower().strip().in_(["рефералы", "мои рефералы", "пригласить", "реферал", "реф"]))
async def referrals_cmd_fixed(msg: Message):
    uid = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    await create_user_if_not_exists(uid, username)
    user = await get_user(uid)
    if not user:
        await msg.reply("Ошибка: пользователь не найден.", parse_mode="HTML")
        return
    referral_code = user.get("referral_code")
    if not referral_code:
        referral_code = generate_referral_code(uid)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET referral_code = ? WHERE id = ?",
                    (referral_code, uid)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления referral_code для {uid}: {e}")
    bot_username = (await msg.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    text = (
        "📣 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"📨 <b>Ваш код:</b> <code>{referral_code}</code>\n\n"
        f"👤 <b>Приглашено:</b> {user.get('referral_count', 0)}\n"
        f"💰 <b>Заработано:</b> {format_money(user.get('total_referral_earned', 0))}\n\n"
        "🎁 <b>Награда за реферала:</b> 30–100М\n"
        "⏳ Награда выдаётся после активности (20 действий) и команды /start"
    )
    await msg.reply(text, parse_mode="HTML")
async def process_daily_reward(msg: Message):
    uid = msg.from_user.id
    now = int(time.time())
    day_seconds = 24 * 3600
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT balance, last_daily_claim, daily_streak FROM users WHERE id = ?",
            (uid,)
        )
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            await msg.reply("Ошибка: пользователь не найден.", parse_mode="HTML")
            return
        last_claim = int(row[1] or 0)
        streak = int(row[2] or 0)
        if last_claim and now - last_claim < day_seconds:
            remaining = day_seconds - (now - last_claim)
            next_streak = min(30, max(1, streak + 1))
            next_reward = get_daily_reward_amount(next_streak)
            await db.rollback()
            await msg.reply(
                "⏳ <b>Ежедневный бонус уже получен</b>\n\n"
                f"До следующего: {format_duration(remaining)}\n"
                f"Следующая награда (день {next_streak}/30): {format_money(next_reward)}",
                parse_mode="HTML"
            )
            return
        if last_claim and now - last_claim >= 2 * day_seconds:
            streak = 0
        streak = min(30, streak + 1)
        reward = get_daily_reward_amount(streak)
        await db.execute(
            "UPDATE users SET balance = balance + ?, last_daily_claim = ?, daily_streak = ? WHERE id = ?",
            (reward, now, streak, uid)
        )
        await db.commit()
    text = "✅ <b>Ежедневный бонус получен!</b>\n\n"
    text += f"День: <b>{streak}/30</b>\n"
    text += f"Награда: <b>{format_money(reward)}</b>\n"
    if last_claim and now - last_claim >= 2 * day_seconds:
        text += "\n⚠️ Серия была сброшена из-за пропуска.\n"
    await msg.reply(text, parse_mode="HTML")
@router.message(F.text.lower().startswith(("кд", "cd", "кулдаун")))
async def cd_text_cmd(msg: Message):
    await check_bonus_cd(msg)
@router.message(F.text.lower().startswith(("кдработы", "работакд", "workcd")))
async def work_cd_text_cmd(msg: Message):
    await check_work_cd(msg)
@router.message(F.text.lower() == "профиль")
@router.message(F.text.lower() == "пр")
@router.message(F.text.lower() == "стата")
@router.message(F.text.lower() == "profile")
@router.message(F.text.lower() == "stats")
async def profile_text_cmd(msg: Message):
    await process_profile(msg)
@router.message(F.text.lower().startswith(("топ", "лидеры", "top")))
async def top_text_cmd(msg: Message):
    if not extract_text_command_parts(msg.text, ("топ", "лидеры", "top")):
        return
    await process_top(msg)
@router.message(F.text.lower().startswith(("монетка", "coin", "мн")))
async def coin_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("монетка", "coin", "мн"))
    if not parts:
        return
    await process_coin(msg, parts)
@router.message(F.text.lower().startswith(("дротик", "дартс", "дрот")))
async def darts_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("дротик", "дартс", "дрот"))
    if not parts:
        return
    await process_darts(msg, parts)
@router.message(F.text.lower().startswith(("кости", "dice", "кст")))
async def dice_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("кости", "dice", "кст"))
    if not parts:
        return
    await process_dice(msg, parts)
@router.message(F.text.lower().startswith(("слоты", "slots", "сл")))
async def slots_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("слоты", "slots", "сл"))
    if not parts:
        return
    await process_slots(msg, parts)
@router.message(F.text.lower().startswith(("рулетка", "рул")))
async def roulette_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("рулетка", "рул"))
    if not parts:
        return
    await process_roulette(msg, parts)
@router.message(F.text.lower().startswith(("блекджек", "блэкджек", "бж", "bj")))
async def bj_text_cmd(msg: Message):
    parts = extract_text_command_parts(msg.text, ("блекджек", "блэкджек", "бж", "bj"))
    if not parts:
        return
    await process_bj(msg, parts)
@router.message(F.text.lower().startswith("краш"))
async def crash_text_cmd(msg: Message):
    """Команда для игры Краш"""
    parts = extract_text_command_parts(msg.text, ("краш",))
    if not parts:
        return
    await process_crash(msg, parts)
@router.message(F.text.lower().startswith("продать биткоин"))
async def sell_bitcoin_cmd(msg: Message):
    """Продать биткоины - команда из чата"""
    uid = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "💸 <b>ПРОДАЖА БИТКОИНОВ</b>\n\n"
            "📝 <b>Формат:</b>\n"
            "- <code>продать биткоин все</code> - продать все BTC\n"
            "- <code>продать биткоин 0.01</code> - продать 0.01 BTC\n"
            "- <code>продать биткоин 0.5</code> - продать 0.5 BTC\n\n"
            "💰 <b>Примеры:</b>\n"
            "<code>продать биткоин все</code>\n"
            "<code>продать биткоин 0.1</code>\n"
            "<code>продать биткоин 0.05</code>",
            parse_mode="HTML"
        )
        return
    amount_str = parts[2].lower()
    try:
        if amount_str == "все":
            amount = None  # Продать все
        else:
            amount = float(amount_str)
        success, btc_sold, usd_received = await sell_bitcoin(uid, amount)
        if success:
            user = await get_user(uid)
            await msg.reply(
                f"✅ <b>БИТКОИНЫ ПРОДАНЫ!</b>\n\n"
                f"💰 <b>Продано:</b> {btc_sold:.8f} BTC\n"
                f"💵 <b>Получено:</b> {format_money(usd_received)}$\n"
                f"📊 <b>Осталось BTC:</b> {user['bitcoin']:.8f}\n"
                f"💳 <b>Новый баланс:</b> {format_money(user['balance'])}",
                parse_mode="HTML"
            )
        else:
            await msg.reply(f"❌ {usd_received}", parse_mode="HTML")
    except ValueError:
        await msg.reply(
            "❌ <b>Неверный формат!</b>\n\n"
            "Используйте число:\n"
            "- <code>продать биткоин 0.1</code>\n"
            "- <code>продать биткоин все</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка продажи BTC: {e}")
        await msg.reply(f"❌ Ошибка при продаже: {str(e)}")
@router.message(F.text.lower().startswith("продать плазму"))
async def sell_plasma_cmd(msg: Message):
    """Продать плазму через текстовую команду"""
    uid = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "💎 <b>Продажа плазмы</b>\n\n"
            "Формат:\n"
            "- <code>продать плазму 10</code>\n"
            "- <code>продать плазму все</code>",
            parse_mode="HTML"
        )
        return
    amount_str = parts[2].lower()
    if amount_str in {"все", "всё"}:
        amount = None
    else:
        try:
            amount = int(amount_str)
        except ValueError:
            await msg.reply("❌ Неверный формат. Пример: <code>продать плазму 10</code>", parse_mode="HTML")
            return
    success, plasma_sold, money_received, price_per_unit = await sell_plasma(uid, amount)
    if success:
        user = await get_user(uid)
        await msg.reply(
            f"✅ <b>Плазма продана</b>\n\n"
            f"💎 Продано: {plasma_sold} ед.\n"
            f"💰 Получено: {format_money(money_received)}$\n"
            f"⚡ Цена: {format_money(price_per_unit)}$ за 1\n"
            f"📦 Осталось: {user['plasma']} ед.",
            parse_mode="HTML"
        )
    else:
        await msg.reply(f"❌ {money_received}", parse_mode="HTML")
@router.message(F.text.lower().startswith("продать плутоний"))
async def sell_plutonium_cmd(msg: Message):
    """Продать плутоний через текстовую команду"""
    uid = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "🔸 <b>Продажа плутония</b>\n\n"
            "Формат:\n"
            "- <code>продать плутоний 5</code>\n"
            "- <code>продать плутоний все</code>",
            parse_mode="HTML"
        )
        return
    amount_str = parts[2].lower()
    if amount_str in {"все", "всё"}:
        amount = None
    else:
        try:
            amount = int(amount_str)
        except ValueError:
            await msg.reply("❌ Неверный формат. Пример: <code>продать плутоний 5</code>", parse_mode="HTML")
            return
    success, plutonium_sold, money_received, price_per_unit = await sell_plutonium(uid, amount)
    if success:
        user = await get_user(uid)
        await msg.reply(
            f"✅ <b>Плутоний продан</b>\n\n"
            f"🔸 Продано: {plutonium_sold} ед.\n"
            f"💰 Получено: {format_money(money_received)}$\n"
            f"⚡ Цена: {format_money(price_per_unit)}$ за 1\n"
            f"📦 Осталось: {user['plutonium']} ед.",
            parse_mode="HTML"
        )
    else:
        await msg.reply(f"❌ {money_received}", parse_mode="HTML")
@router.message(F.text.lower().startswith(("продать артефакт", "продать артефакты")))
async def sell_artifacts_cmd(msg: Message):
    """Продать артефакты через текстовую команду"""
    uid = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply(
            "🧩 <b>Продажа артефактов</b>\n\n"
            "Формат:\n"
            "- <code>продать артефакты 3</code>\n"
            "- <code>продать артефакты все</code>",
            parse_mode="HTML"
        )
        return
    amount_str = parts[2].lower()
    if amount_str in {"все", "всё"}:
        amount = None
    else:
        try:
            amount = int(amount_str)
        except ValueError:
            await msg.reply("❌ Неверный формат. Пример: <code>продать артефакты 3</code>", parse_mode="HTML")
            return
    success, artifacts_sold, money_received, price_per_unit = await sell_artifacts(uid, amount)
    if success:
        user = await get_user(uid)
        await msg.reply(
            f"✅ <b>Артефакты проданы</b>\n\n"
            f"🧩 Продано: {artifacts_sold} ед.\n"
            f"💰 Получено: {format_money(money_received)}$\n"
            f"⚡ Цена: {format_money(price_per_unit)}$ за 1\n"
            f"📦 Осталось: {user['artifacts']} ед.",
            parse_mode="HTML"
        )
    else:
        await msg.reply(f"❌ {money_received}", parse_mode="HTML")
@router.message(Command("краш", "crash"))
async def crash_slash_cmd(msg: Message, command: CommandObject = None):
    """Команда /краш"""
    if command and command.args:
        parts = ["краш"] + command.args.split()
    else:
        parts = ["краш"]
    await process_crash(msg, parts)
@router.message(F.text.lower().startswith(("передать", "transfer")))
async def transfer_text_cmd(msg: Message):
    parts = msg.text.split()
    await process_transfer(msg, parts)
@router.message(F.text)
async def transfer_text_cmd_ru(msg: Message):
    if not msg.text:
        return
    low = msg.text.lower().strip()
    if not low.startswith(("\u043f\u0435\u0440\u0435\u0434\u0430\u0442\u044c", "transfer")):
        return
    parts = msg.text.split()
    await process_transfer(msg, parts)
@router.message(F.text.lower().startswith(("выдать",)))
async def give_text_cmd(msg: Message):
    await handle_all_commands(msg)
@router.message(F.text.lower().startswith(("забрать",)))
async def take_text_cmd(msg: Message):
    await handle_all_commands(msg)
@router.message(F.text.lower().startswith(("майнинг", "mining")))
async def mining_text_cmd(msg: Message):
    await show_mining_info(msg)
@router.message(F.text.lower().startswith(("планеты", "planets")))
async def planets_text_cmd(msg: Message):
    await show_planets(msg)
@router.message(F.text.lower().startswith(("инвестиции", "investments")))
async def investments_text_cmd(msg: Message):
    await show_investments(msg)
@router.message(F.text.lower() == "забрать биткоины")
@router.message(F.text.lower().startswith("забрать биткоин"))
@router.message(F.text.lower().startswith("собрать биткоин"))
async def collect_btc_text_cmd(msg: Message):
    """Текстовая команда для сбора BTC"""
    success, btc_amount, result = await claim_mining_profit(msg.from_user.id)
    if success:
        btc_price = BitcoinMining.get_bitcoin_price()
        usd_value = result if isinstance(result, (int, float)) else btc_amount * btc_price
        await msg.reply(
            f"✅ <b>БИТКОИНЫ СОБРАНЫ!</b>\n\n"
            f"💰 <b>Количество:</b> {btc_amount:.8f} BTC\n"
            f"💵 <b>Стоимость:</b> {format_money(int(usd_value))}$\n"
            f"📈 <b>Курс BTC:</b> {format_money(int(btc_price))}$\n\n"
            f"🎉 <b>Успешно добавлено к вашему балансу BTC!</b>",
            parse_mode="HTML"
        )
    else:
        error_msg = str(result)
        # Предлагаем решение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Проверка", callback_data="check_mining_now"),
             InlineKeyboardButton(text="🔄 Форс-фикс", callback_data="force_fix_now")],
            [InlineKeyboardButton(text="⛏️ Панель майнинга", callback_data="show_mining")]
        ])
        await msg.reply(
            f"❌ <b>Не удалось собрать BTC</b>\n\n"
            f"⚠️ <b>Причина:</b> {error_msg}\n\n"
            f"💡 <b>Что делать:</b>\n"
            f"1. Нажмите 'Проверка' для диагностики\n"
            f"2. Если проблема - нажмите 'Форс-фикс'\n"
            f"3. Подождите 2-3 минуты",
            parse_mode="HTML",
            reply_markup=keyboard
        )
# ========== CALLBACK ОБРАБОТЧИКИ ==========
# ========== АДМИН ОБРАБОТЧИКИ МАЙНИНГА ==========
@router.callback_query(F.data == "admin_force_fix_self")
async def admin_force_fix_self_callback(cb: CallbackQuery):
    """Форс-фикс для админа"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    # Просто вызываем обычный форс-фикс
    await force_fix_now_callback(cb)
@router.callback_query(F.data == "admin_force_fix_id")
async def admin_force_fix_id_callback(cb: CallbackQuery):
    """Форс-фикс по ID пользователя"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    await cb.answer("📝 Введите: форсфикс [ID пользователя]\nНапример: форсфикс 123456789", show_alert=True)
@router.callback_query(F.data == "admin_mining_stats")
async def admin_mining_stats_callback(cb: CallbackQuery):
    """Статистика майнинга для админа"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Общая статистика
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total_users,
                    SUM(mining_gpu_count) as total_gpus,
                    AVG(mining_gpu_count) as avg_gpus,
                    SUM(bitcoin) as total_btc,
                    SUM(balance) as total_balance
                FROM users
                WHERE mining_gpu_count > 0
            """)
            stats = await cursor.fetchone()
            # Топ майнеров
            cursor = await db.execute("""
                SELECT id, username, mining_gpu_count, mining_gpu_level, bitcoin, balance
                FROM users
                WHERE mining_gpu_count > 0
                ORDER BY mining_gpu_count DESC
                LIMIT 10
            """)
            top_miners = await cursor.fetchall()
        if stats:
            text = f"""
📊 <b>СТАТИСТИКА МАЙНИНГА</b>
👥 <b>Общая информация:</b>
• Всего майнеров: {stats['total_users'] or 0}
• Всего видеокарт: {stats['total_gpus'] or 0}
• Среднее на игрока: {stats['avg_gpus'] or 0:.1f}
• Всего BTC в системе: {stats['total_btc'] or 0:.8f}
• Общая стоимость BTC: {format_money(int((stats['total_btc'] or 0) * BitcoinMining.get_bitcoin_price()))}$
🏆 <b>Топ-10 майнеров:</b>
"""
            for i, miner in enumerate(top_miners, 1):
                username = miner['username'] or f"ID {miner['id']}"
                text += f"{i}. {username[:15]}\n"
                text += f"   🎮 {miner['mining_gpu_count']} карт (ур. {miner['mining_gpu_level']})\n"
                text += f"   ₿ {miner['bitcoin']:.4f} BTC\n"
            await cb.message.edit_text(text, parse_mode="HTML")
        else:
            await cb.message.edit_text("📊 Нет данных о майнерах", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка admin_mining_stats_callback: {e}")
        await cb.answer("❌ Ошибка получения статистики", show_alert=True)
@router.callback_query(F.data == "admin_give_gpu")
async def admin_give_gpu_callback(cb: CallbackQuery):
    """Выдать видеокарты"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 10 карт себе", callback_data="admin_give_gpu_self_10"),
         InlineKeyboardButton(text="🎮 50 карт себе", callback_data="admin_give_gpu_self_50")],
        [InlineKeyboardButton(text="⚡ Улучшить всем", callback_data="admin_upgrade_all"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await cb.message.edit_text(
        "🎮 <b>ВЫДАТЬ ВИДЕОКАРТЫ</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await cb.answer()
@router.callback_query(F.data.startswith("admin_give_gpu_self_"))
async def admin_give_gpu_self_callback(cb: CallbackQuery):
    """Выдать видеокарты себе"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    try:
        count = int(cb.data.split("_")[4])  # admin_give_gpu_self_10 → 10
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users
                SET mining_gpu_count = mining_gpu_count + ?
                WHERE id = ?
            """, (count, cb.from_user.id))
            await db.commit()
        await cb.answer(f"✅ Добавлено {count} видеокарт!")
        await admin_mining_panel(cb.message)
    except Exception as e:
        await cb.answer(f"❌ Ошибка: {e}")
@router.callback_query(F.data == "admin_upgrade_all")
async def admin_upgrade_all_callback(cb: CallbackQuery):
    """Улучшить всем видеокарты"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users
                SET mining_gpu_level = 5
                WHERE mining_gpu_count > 0
            """)
            await db.commit()
        await cb.answer("✅ Все видеокарты улучшены до 5 уровня!")
        await admin_mining_panel(cb.message)
    except Exception as e:
        await cb.answer(f"❌ Ошибка: {e}")
@router.callback_query(F.data == "admin_give_btc")
async def admin_give_btc_callback(cb: CallbackQuery):
    """Выдать BTC"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    await cb.answer("📝 Введите: выдать биткоин [ID] [количество]\nПример: выдать биткоин 123456789 0.1", show_alert=True)
@router.callback_query(F.data == "admin_reset_all_time")
async def admin_reset_all_time_callback(cb: CallbackQuery):
    """Сбросить время всем"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    try:
        new_time = int(time.time()) - 3600
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users
                SET last_mining_claim = ?
                WHERE mining_gpu_count > 0
            """, (new_time,))
            await db.commit()
        await cb.answer("✅ Время сброшено всем майнерам на 1 час назад!")
        await admin_mining_panel(cb.message)
    except Exception as e:
        await cb.answer(f"❌ Ошибка: {e}")
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
    try:
        await cb.answer()
    except TelegramBadRequest:
        pass
    await send_welcome_message(cb.message, force_menu=True, edit=True)
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
@router.callback_query(F.data == "get_daily")
async def get_daily_callback(cb: CallbackQuery):
    await process_daily_reward(cb.message)
    await cb.answer()
@router.callback_query(F.data == "play_crash")
async def play_crash_callback(cb: CallbackQuery):
    """Обработка нажатия на кнопку Краш"""
    await cb.answer("🎮 Введите: краш [ставка]\nНапример: краш 1000 или краш 1к")
@router.callback_query(F.data == "get_work")
async def get_work_cb(cb: CallbackQuery):
    await process_work(cb.message)
    await cb.answer()
@router.callback_query(F.data == "show_planets")
async def show_planets_cb(cb: CallbackQuery):
    await show_planets(cb.message)
    await cb.answer()
@router.callback_query(F.data == "show_mining")
async def show_mining_cb(cb: CallbackQuery):
    await show_mining_panel(cb=cb)
    await cb.answer()
@router.callback_query(F.data == "show_fishing")
async def show_fishing_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_panel(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "show_investments")
async def show_investments_callback(cb: CallbackQuery):
    await show_investments_panel(cb=cb)
    await cb.answer()
@router.callback_query(F.data == "show_weapons_shop")
async def show_weapons_shop_cb(cb: CallbackQuery):
    """Военный магазин"""
    uid = cb.from_user.id
    try:
        user = await get_user(uid)
        text = "🛒 <b>Военный магазин</b>\n\n"
        text += "Выберите категорию товаров:\n\n"
        text += "🔫 <b>Оружие:</b> Пистолеты, автоматы, снайперки\n"
        text += "🛡️ <b>Броня:</b> Комплекты защиты\n"
        text += "🚗 <b>Техника:</b> БТР, танки, артиллерия\n"
        keyboard = [
            [InlineKeyboardButton(text="🔫 Оружие", callback_data="shop_category_weapon")],
            [InlineKeyboardButton(text="🛡️ Броня", callback_data="shop_category_armor")],
            [InlineKeyboardButton(text="🚗 Техника", callback_data="shop_category_vehicle")],
            [InlineKeyboardButton(text="📦 Инвентарь", callback_data="show_inventory")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ]
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка show_weapons_shop_cb: {e}")
        await cb.answer("❌ Ошибка загрузки магазина")
@router.callback_query(F.data.startswith("shop_category_"))
async def shop_category_cb(cb: CallbackQuery):
    """Категория товаров в магазине"""
    category = cb.data.split("_")[2]
    uid = cb.from_user.id
    category_names = {
        'weapon': 'Оружие',
        'armor': 'Броня',
        'vehicle': 'Техника'
    }
    if category not in category_names:
        await cb.answer("❌ Неизвестная категория")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE category = ? ORDER BY tier, price_money", (category,))
            items = await cursor.fetchall()
        text = f"🛒 <b>{category_names[category]}</b>\n\n"
        keyboard = []
        for item in items:
            price_text = format_money(item['price_money'])
            if item['price_plutonium']:
                price_text += f" + {item['price_plutonium']}🔸"
            if item['price_plasma']:
                price_text += f" + {item['price_plasma']}🔹"
            keyboard.append([InlineKeyboardButton(
                text=f"{item['name']} (ур.{item['tier']}) - {price_text}",
                callback_data=f"buy_item_{item['item_id']}"
            )])
        keyboard.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="show_weapons_shop")])
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка shop_category_cb: {e}")
        await cb.answer("❌ Ошибка загрузки категории")
@router.callback_query(F.data.startswith("buy_item_"))
async def buy_item_cb(cb: CallbackQuery):
    """Покупка предмета"""
    item_id = cb.data.split("_", 2)[2]
    uid = cb.from_user.id
    if item_id not in ITEM_CONFIG:
        await cb.answer("❌ Предмет не найден")
        return
    item_data = ITEM_CONFIG[item_id]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance, plasma FROM users WHERE id = ?", (uid,))
            user = await cursor.fetchone()
            if not user:
                await db.rollback()
                await cb.answer("❌ Пользователь не найден")
                return
            # Проверяем ресурсы
            cost_money = item_data['price_money']
            cost_plutonium = item_data.get('price_plutonium', 0)
            cost_plasma = item_data.get('price_plasma', 0)
            # Проверяем требования зданий
            req_building = item_data.get('req_building')
            req_level = item_data.get('req_building_level', 0)
            if req_building:
                cursor = await db.execute("SELECT level FROM country_buildings cb JOIN countries c ON cb.country_id = c.id WHERE c.owner_user_id = ? AND cb.building_type = ?", (uid, req_building))
                building_level = (await cursor.fetchone() or [0])[0]
                if building_level < req_level:
                    await db.rollback()
                    await cb.answer(f"❌ Требуется {req_building} уровня {req_level}")
                    return
            if user['balance'] < cost_money:
                await db.rollback()
                await cb.answer(f"❌ Недостаточно денег ({format_money(cost_money)} нужно)")
                return
            if user['plasma'] < cost_plutonium:
                await db.rollback()
                await cb.answer(f"❌ Недостаточно плутония ({cost_plutonium} нужно)")
                return
            # Списываем ресурсы
            await db.execute("UPDATE users SET balance = balance - ?, plasma = plasma - ? WHERE id = ?",
                           (cost_money, cost_plutonium, uid))
            # Добавляем предмет
            cursor = await db.execute("SELECT amount FROM user_items WHERE user_id = ? AND item_id = ?", (uid, item_id))
            existing = await cursor.fetchone()
            if existing:
                await db.execute("UPDATE user_items SET amount = amount + 1 WHERE user_id = ? AND item_id = ?", (uid, item_id))
            else:
                await db.execute("INSERT INTO user_items (user_id, item_id, amount) VALUES (?, ?, 1)", (uid, item_id))
            await db.commit()
        await cb.answer(f"✅ {item_data['name']} куплен!")
        # Возвращаемся к категории
        category = item_data['category']
        cb.data = f"shop_category_{category}"
        await shop_category_cb(cb)
    except Exception as e:
        logger.error(f"Ошибка buy_item_cb: {e}")
        await cb.answer("❌ Ошибка покупки")
@router.callback_query(F.data == "show_inventory")
async def show_inventory_cb(cb: CallbackQuery):
    """Показать инвентарь армии"""
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT ui.amount, i.name, i.category, i.power, i.upkeep_day
                FROM user_items ui
                JOIN items i ON ui.item_id = i.item_id
                WHERE ui.user_id = ? AND ui.amount > 0
                ORDER BY i.category, i.tier
            """, (uid,))
            items = await cursor.fetchall()
        text = "📦 <b>Инвентарь армии</b>\n\n"
        if not items:
            text += "Ваш инвентарь пуст.\n\nКупите оружие и технику в военном магазине!"
        else:
            total_power = 0
            total_upkeep = 0
            for item in items:
                text += f"• {item['name']} x{item['amount']} (⚔️{item['power']}, 💰{item['upkeep_day']}/день)\n"
                total_power += item['power'] * item['amount']
                total_upkeep += item['upkeep_day'] * item['amount']
            text += f"\n<b>Общая сила:</b> {total_power}\n"
            text += f"<b>Общее содержание:</b> {format_money(total_upkeep)}/день\n"
        keyboard = [[InlineKeyboardButton(text="🛒 В магазин", callback_data="show_weapons_shop")],
                    [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]]
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка show_inventory_cb: {e}")
        await cb.answer("❌ Ошибка загрузки инвентаря")
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
@router.callback_query(F.data.startswith("crash_cashout_"))
async def crash_cashout_callback(cb: CallbackQuery):
    """Обработка кэшаута в игре Краш - РАБОЧАЯ ВЕРСИЯ"""
    try:
        # Уникальный id обработки — используем id callback'a
        cb_id = str(cb.id)
        # Дедупликация: если уже обрабатывали этот callback — выходим
        if await is_callback_processed(cb_id):
            await cb.answer("✅ Обработано", show_alert=False)
            return
        player_id = int(cb.data.split("_")[2])
        # Проверяем, что это тот же пользователь
        if cb.from_user.id != player_id:
            await cb.answer("❌ Это не ваша игра!", show_alert=True)
            return
        # Ищем активную игру пользователя
        game_id = None
        game_data = None
        for msg_id, game in active_crash_games.items():
            if game["user_id"] == player_id and not game.get("cashed_out", False) and not game.get("crashed", False):
                game_id = msg_id
                game_data = game
                break
        if not game_id or not game_data:
            await cb.answer("❌ Нет активной игры или игра уже завершена!", show_alert=True)
            return
        # Получаем текущий множитель и считаем выплату с house edge
        multiplier = float(game_data["multiplier"])
        bet = int(game_data["bet"])
        # Проверяем минимальный множитель для кэшаута
        if multiplier < 1.10:
            await cb.answer("❌ Минимальный множитель для вывода: 1.10x", show_alert=True)
            return
        HOUSE_EDGE = 0.97
        effective_mul = round(multiplier * HOUSE_EDGE, 2)
        payout = int(math.floor(bet * effective_mul))
        # Выполняем атомарную операцию в БД: пометим callback как обработанный и начислим payout
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("BEGIN IMMEDIATE")
                cursor = await db.execute("SELECT 1 FROM processed_callbacks WHERE id = ?", (cb_id,))
                if await cursor.fetchone():
                    await db.rollback()
                    await cb.answer("✅ Обработано", show_alert=False)
                    return
                # Помечаем callback
                now_ts = int(time.time())
                await db.execute("INSERT INTO processed_callbacks (id, ts) VALUES (?, ?)", (cb_id, now_ts))
                # Начисляем деньги и увеличиваем счетчик побед
                await db.execute("UPDATE users SET balance = balance + ?, wins = COALESCE(wins,0) + 1 WHERE id = ?", (payout, player_id))
                await db.commit()
            except Exception as e:
                try:
                    await db.rollback()
                except:
                    pass
                logger.error(f"Ошибка БД в crash_cashout_callback: {e}")
                await cb.answer("❌ Ошибка при выплате", show_alert=True)
                return
        # Отмечаем в памяти, что игрок забрал
        active_crash_games[game_id]["cashed_out"] = True
        active_crash_games[game_id]["cashout_multiplier"] = multiplier
        # Удаляем игру из активных, чтобы остановить её немедленно
        del active_crash_games[game_id]
        # Обновляем сообщение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Уже забрали", callback_data="no_action")]
        ])
        await cb.message.edit_text(
            f"💰 <b>ВЫ УСПЕЛИ ЗАБРАТЬ!</b>\n\n"
            f"🎯 Множитель: <b>{multiplier}x</b>\n"
            f"💰 Ставка: {format_money(bet)}\n"
            f"💵 Выигрыш: <b>{format_money(payout)}</b>\n\n"
            f"✅ <b>+{format_money(payout - bet)}</b>\n\n"
            f"🎉 Поздравляем с победой!\n"
            f"⚠️ Ждите краха для завершения игры",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await cb.answer(f"✅ Выигрыш: {format_money(payout)}! Ждите завершения игры.")
    except Exception as e:
        logger.error(f"Ошибка crash_cashout_callback: {e}", exc_info=True)
        await cb.answer("❌ Ошибка вывода", show_alert=True)
@router.callback_query(F.data.startswith("coin_"))
async def coin_flip_cb(cb: CallbackQuery):
    try:
        _, bet_str, choice = cb.data.split("_")
        bet = int(bet_str)
    except:
        await cb.answer("❌ Ошибка")
        return
    uid = cb.from_user.id
    # Deduplicate callbacks and perform atomic DB updates
    cb_id = str(cb.id)
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT 1 FROM processed_callbacks WHERE id = ?", (cb_id,))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("✅ Обработано", show_alert=False)
                return
            # Check balance
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            if balance < bet:
                await db.rollback()
                await cb.answer("❌ Недостаточно средств", show_alert=True)
                return
            # Reserve: mark callback and deduct bet
            now_ts = int(time.time())
            await db.execute("INSERT INTO processed_callbacks (id, ts) VALUES (?, ?)", (cb_id, now_ts))
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (bet, uid))
            # Flip the coin
            await db.commit()
            # Обновляем дневной счетчик ставок
            await update_daily_wager(uid, bet)
        except Exception as e:
            try:
                await db.rollback()
            except:
                pass
            logger.error(f"Ошибка БД в coin_flip_cb (reserve): {e}")
            await cb.answer("❌ Ошибка", show_alert=True)
            return
    # После успешного резервирования — делаем бросок и финализируем (с отдельной транзакцией)
    await cb.message.edit_text("🎲 Подбрасываем монетку...")
    await asyncio.sleep(1.5)
    result = random.choice(["orel", "reshka"])
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")
            if result == choice:
                win = bet * 2
                await db.execute("UPDATE users SET balance = balance + ?, wins = COALESCE(wins,0) + 1 WHERE id = ?", (win, uid))
                result_text = f"✅ <b>ВЫИГРЫШ!</b>\n💰 +{bet:,}"
            else:
                await db.execute("UPDATE users SET losses = COALESCE(losses,0) + 1 WHERE id = ?", (uid,))
                result_text = f"❌ <b>ПРОИГРЫШ</b>\n💸 -{bet:,}"
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except:
                pass
            logger.error(f"Ошибка БД в coin_flip_cb (finalize): {e}")
            await cb.answer("❌ Ошибка при выплате", show_alert=True)
            return
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
# ========== НОВЫЕ MESSAGE ХЕНДЛЕРЫ ==========
@router.message(Command("countries"))
@router.message(Command("страны"))
@router.message(F.text.lower().in_(["страны", "countries", "/страны", "/countries", "🌍 страны"]))
async def countries_command(msg: Message):
    """Команда 'страны'"""
    logger.info(f"CMD countries hit uid={msg.from_user.id} text={msg.text!r}")
    await show_country_selection(msg)
async def show_my_country_msg(msg: Message):
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            country_id = await get_user_country_id(db, uid)
        if not country_id:
            await msg.reply("❌ У вас нет страны. Используйте команду «страны», чтобы выбрать.")
            return
        text, reply_markup = await build_country_view(country_id, uid)
        if not text:
            await msg.reply("❌ Страна не найдена.")
            return
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка show_my_country_msg: {e}")
        await msg.reply("❌ Ошибка загрузки страны.")
@router.message(Command("страна", "country"))
async def my_country_slash_cmd(msg: Message):
    await show_my_country_msg(msg)
@router.message(F.text.lower().in_(["страна", "моя страна", "country", "my country"]))
async def my_country_text_cmd(msg: Message):
    await show_my_country_msg(msg)
@router.message(F.text.lower().in_(["кланы", "clans"]))
async def clans_command(msg: Message):
    """Команда 'кланы'"""
    try:
        text, reply_markup = await build_clans_view()
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в clans_command: {e}")
        await msg.reply("Ошибка загрузки списка кланов.")
@router.message(F.text.lower().in_(["\u043a\u0440\u0435\u0434\u0438\u0442\u044b", "credits"]))
async def credits_command(msg: Message):
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db, uid)
            cursor = await db.execute("SELECT * FROM credits WHERE borrower_id = ? ORDER BY issued_at DESC, id DESC LIMIT 5", (uid,))
            borrowed = await cursor.fetchall()
            cursor = await db.execute("SELECT c.*, u.username FROM credits c LEFT JOIN users u ON u.id = c.borrower_id WHERE c.lender_id = ? ORDER BY c.issued_at DESC, c.id DESC LIMIT 5", (uid,))
            lent = await cursor.fetchall()
            borrowed_lines = []
            for credit in borrowed:
                status = credit["status"]
                interest_pct = int(round((credit["interest"] or 0) * 100))
                total_due = int(credit["total_due"] or 0)
                if status == "pending":
                    days = max(1, int((credit["due_at"] or 0) // 86400))
                    status_text = f"\u041e\u0436\u0438\u0434\u0430\u0435\u0442 \u043a\u0440\u0435\u0434\u0438\u0442\u043e\u0440\u0430, \u0441\u0440\u043e\u043a {days}\u0434"
                    remaining = total_due
                else:
                    paid = await get_credit_paid_sum(db, credit["id"])
                    remaining = max(0, total_due - paid)
                    if status == "active":
                        due_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(credit["due_at"]))
                        status_text = f"\u0410\u043a\u0442\u0438\u0432\u0435\u043d \u0434\u043e {due_str}"
                    elif status == "repaid":
                        status_text = "\u041f\u043e\u0433\u0430\u0448\u0435\u043d"
                    elif status == "defaulted":
                        status_text = "\u0414\u0435\u0444\u043e\u043b\u0442"
                    else:
                        status_text = status
                borrowed_lines.append(
                    f"- ID {credit['id']} - {status_text}. \u0421\u0443\u043c\u043c\u0430: {format_money(credit['amount'])}, \u043f\u0440\u043e\u0446\u0435\u043d\u0442: {interest_pct}%, \u043e\u0441\u0442\u0430\u0442\u043e\u043a: {format_money(remaining)}"
                )
            lent_lines = []
            for credit in lent:
                status = credit["status"]
                interest_pct = int(round((credit["interest"] or 0) * 100))
                total_due = int(credit["total_due"] or 0)
                paid = await get_credit_paid_sum(db, credit["id"]) if status != "pending" else 0
                remaining = max(0, total_due - paid)
                borrower_name = credit["username"] or str(credit["borrower_id"])
                if status == "active":
                    due_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(credit["due_at"]))
                    status_text = f"\u0410\u043a\u0442\u0438\u0432\u0435\u043d \u0434\u043e {due_str}"
                elif status == "repaid":
                    status_text = "\u041f\u043e\u0433\u0430\u0448\u0435\u043d"
                elif status == "defaulted":
                    status_text = "\u0414\u0435\u0444\u043e\u043b\u0442"
                else:
                    status_text = status
                lent_lines.append(
                    f"- ID {credit['id']} - {borrower_name}. {status_text}. \u0421\u0443\u043c\u043c\u0430: {format_money(credit['amount'])}, \u043f\u0440\u043e\u0446\u0435\u043d\u0442: {interest_pct}%, \u043e\u0441\u0442\u0430\u0442\u043e\u043a: {format_money(remaining)}"
                )
        text = "<b>\u041a\u0440\u0435\u0434\u0438\u0442\u044b</b>\n\n"
        if borrowed_lines:
            text += "<b>\u0412\u0430\u0448\u0438 \u043a\u0440\u0435\u0434\u0438\u0442\u044b:</b>\n" + "\n".join(borrowed_lines) + "\n\n"
        else:
            text += "<b>\u0412\u0430\u0448\u0438 \u043a\u0440\u0435\u0434\u0438\u0442\u044b:</b> \u043d\u0435\u0442.\n\n"
        if lent_lines:
            text += "<b>\u0412\u044b \u0432\u044b\u0434\u0430\u043b\u0438:</b>\n" + "\n".join(lent_lines) + "\n\n"
        else:
            text += "<b>\u0412\u044b \u0432\u044b\u0434\u0430\u043b\u0438:</b> \u043d\u0435\u0442.\n\n"
        text += (
            "<b>\u041a\u043e\u043c\u0430\u043d\u0434\u044b:</b>\n"
            "- <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u0442\u044c &lt;\u0441\u0443\u043c\u043c\u0430&gt; &lt;\u043f\u0440\u043e\u0446\u0435\u043d\u0442&gt; &lt;\u0434\u043d\u0435\u0439&gt;</code>\n"
            "- <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f</code>\n"
            "- <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0438\u043d\u044f\u0442\u044c &lt;id&gt;</code>\n"
            "- <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u043b\u0430\u0442\u0438\u0442\u044c &lt;id&gt; &lt;\u0441\u0443\u043c\u043c\u0430&gt;</code>\n"
            "- <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u0441\u0438\u0433\u043c\u0430 &lt;\u0441\u0443\u043c\u043c\u0430&gt;</code>\n"
        )
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка credits_command: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u043a\u0440\u0435\u0434\u0438\u0442\u043e\u0432.")
@router.message(F.text.lower().startswith("\u043a\u0440\u0435\u0434\u0438\u0442 \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u0442\u044c"))
async def credit_request_cmd(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 5:
        await msg.reply("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: \u043a\u0440\u0435\u0434\u0438\u0442 \u0437\u0430\u043f\u0440\u043e\u0441\u0438\u0442\u044c <\u0441\u0443\u043c\u043c\u0430> <\u043f\u0440\u043e\u0446\u0435\u043d\u0442> <\u0434\u043d\u0435\u0439>")
        return
    amount = parse_amount(parts[2])
    try:
        interest_str = parts[3].replace('%', '').replace(',', '.')
        interest_pct = float(interest_str)
        days = int(parts[4])
    except Exception:
        await msg.reply("\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0435 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b.")
        return
    if interest_pct < CREDIT_MIN_INTEREST_PCT or interest_pct > CREDIT_MAX_INTEREST_PCT:
        await msg.reply(f"\u041f\u0440\u043e\u0446\u0435\u043d\u0442 \u043e\u0442 {CREDIT_MIN_INTEREST_PCT}% \u0434\u043e {CREDIT_MAX_INTEREST_PCT}%.")
        return
    if days < CREDIT_MIN_DAYS or days > CREDIT_MAX_DAYS:
        await msg.reply(f"\u0421\u0440\u043e\u043a \u043e\u0442 {CREDIT_MIN_DAYS} \u0434\u043e {CREDIT_MAX_DAYS} \u0434\u043d\u0435\u0439.")
        return
    interest = interest_pct / 100
    total_due = amount + int(amount * interest)
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db, uid)
            ok, reason = await check_credit_eligibility(db, uid, amount, False)
            if not ok:
                await msg.reply(reason)
                return
            await db.execute(
                "INSERT INTO credits (lender_id, borrower_id, amount, interest, total_due, issued_at, due_at, status) VALUES (NULL, ?, ?, ?, ?, 0, ?, 'pending')",
                (uid, amount, interest, total_due, days * 86400)
            )
            await db.commit()
            logger.info(f"Создан запрос кредита: заемщик={uid} сумма={amount} процент={interest} дней={days}")
        await msg.reply("\u0417\u0430\u043f\u0440\u043e\u0441 \u0441\u043e\u0437\u0434\u0430\u043d. \u041f\u043e\u0438\u0449\u0438\u0442\u0435 \u043a\u0440\u0435\u0434\u0438\u0442\u043e\u0440\u0430: <code>\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f</code>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка credit_request_cmd: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f \u0437\u0430\u043f\u0440\u043e\u0441\u0430.")
@router.message(F.text.lower().in_(["\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f"]))
async def credit_offers_cmd(msg: Message):
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db)
            cursor = await db.execute(
                "SELECT c.*, u.username FROM credits c LEFT JOIN users u ON u.id = c.borrower_id WHERE c.status = 'pending' AND c.lender_id IS NULL AND c.borrower_id != ? ORDER BY c.id DESC LIMIT 10",
                (uid,)
            )
            offers = await cursor.fetchall()
        if not offers:
            await msg.reply("\u041d\u0435\u0442 \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0445 \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432.")
            return
        lines = []
        for credit in offers:
            borrower_name = credit["username"] or str(credit["borrower_id"])
            interest_pct = int(round((credit["interest"] or 0) * 100))
            days = max(1, int((credit["due_at"] or 0) // 86400))
            lines.append(
                f"- ID {credit['id']} - {borrower_name}. \u0421\u0443\u043c\u043c\u0430: {format_money(credit['amount'])}, \u043f\u0440\u043e\u0446\u0435\u043d\u0442: {interest_pct}%, \u0441\u0440\u043e\u043a: {days}\u0434"
            )
        text = "<b>\u0417\u0430\u043f\u0440\u043e\u0441\u044b \u043d\u0430 \u043a\u0440\u0435\u0434\u0438\u0442</b>\n\n" + "\n".join(lines) + "\n\n<code>\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0438\u043d\u044f\u0442\u044c &lt;id&gt;</code>"
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка credit_offers_cmd: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0439.")
@router.message(F.text.lower().startswith("\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0438\u043d\u044f\u0442\u044c"))
async def credit_accept_cmd(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 3:
        await msg.reply("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: \u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u0440\u0438\u043d\u044f\u0442\u044c <id>")
        return
    try:
        credit_id = int(parts[2])
    except Exception:
        await msg.reply("\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 ID.")
        return
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db)
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT * FROM credits WHERE id = ? AND status = 'pending' AND lender_id IS NULL",
                (credit_id,)
            )
            credit = await cursor.fetchone()
            if not credit:
                await db.rollback()
                await msg.reply("\u041d\u0435\u0442 \u0442\u0430\u043a\u043e\u0433\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0430.")
                return
            borrower_id = int(credit["borrower_id"])
            if borrower_id == uid:
                await db.rollback()
                await msg.reply("\u041d\u0435\u043b\u044c\u0437\u044f \u043f\u0440\u0438\u043d\u044f\u0442\u044c \u0441\u0432\u043e\u0439 \u0436\u0435 \u0437\u0430\u043f\u0440\u043e\u0441.")
                return
            cursor = await db.execute(
                "SELECT 1 FROM credits WHERE borrower_id = ? AND status = 'active'",
                (borrower_id,)
            )
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u0443\u0436\u0435 \u0435\u0441\u0442\u044c \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u043a\u0440\u0435\u0434\u0438\u0442.")
                return
            cursor = await db.execute(
                "SELECT 1 FROM credits WHERE borrower_id = ? AND status = 'pending' AND id != ?",
                (borrower_id, credit_id)
            )
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u0443\u0436\u0435 \u0435\u0441\u0442\u044c \u0434\u0440\u0443\u0433\u043e\u0439 \u043e\u0436\u0438\u0434\u0430\u044e\u0449\u0438\u0439 \u043a\u0440\u0435\u0434\u0438\u0442.")
                return
            if await has_defaulted_credit(db, borrower_id):
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u0434\u0435\u0444\u043e\u043b\u0442 \u043f\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0443.")
                return
            country_id = await get_user_country_id(db, borrower_id)
            if not country_id:
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u043d\u0435\u0442 \u0441\u0442\u0440\u0430\u043d\u044b.")
                return
            cursor = await db.execute("SELECT stability FROM countries WHERE id = ?", (country_id,))
            row = await cursor.fetchone()
            stability = int(row[0] or 0) if row else 0
            if stability < CREDIT_MIN_STABILITY:
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u043d\u0438\u0437\u043a\u0430\u044f \u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c.")
                return
            if await get_active_war_for_country(db, country_id):
                await db.rollback()
                await msg.reply("\u0423 \u0437\u0430\u0435\u043c\u0449\u0438\u043a\u0430 \u0430\u043a\u0442\u0438\u0432\u043d\u0430\u044f \u0432\u043e\u0439\u043d\u0430.")
                return
            amount = int(credit["amount"] or 0)
            interest = float(credit["interest"] or 0)
            requested_days = int((credit["due_at"] or 0) // 86400)
            if requested_days <= 0:
                requested_days = CREDIT_MIN_DAYS
            days = max(CREDIT_MIN_DAYS, min(CREDIT_MAX_DAYS, requested_days))
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (uid, 0))
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (borrower_id, 0))
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            lender_balance = int(row[0] or 0)
            if lender_balance < amount:
                await db.rollback()
                await msg.reply("\u041d\u0435\u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u0441\u0440\u0435\u0434\u0441\u0442\u0432 \u0434\u043b\u044f \u0432\u044b\u0434\u0430\u0447\u0438.")
                return
            now_ts = int(time.time())
            due_at = now_ts + days * 86400
            total_due = amount + int(amount * interest)
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, uid))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, borrower_id))
            await db.execute(
                "UPDATE credits SET lender_id = ?, status = 'active', issued_at = ?, due_at = ?, total_due = ? WHERE id = ?",
                (uid, now_ts, due_at, total_due, credit_id)
            )
            await db.commit()
            logger.info(f"Кредит принят: id={credit_id} кредитор={uid} заемщик={borrower_id} сумма={amount}")
        await msg.reply("\u041a\u0440\u0435\u0434\u0438\u0442 \u0432\u044b\u0434\u0430\u043d.")
    except Exception as e:
        logger.error(f"Ошибка credit_accept_cmd: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u0432\u044b\u0434\u0430\u0447\u0435 \u043a\u0440\u0435\u0434\u0438\u0442\u0430.")
@router.message(F.text.lower().startswith("\u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u043b\u0430\u0442\u0438\u0442\u044c"))
async def credit_pay_cmd(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 4:
        await msg.reply("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: \u043a\u0440\u0435\u0434\u0438\u0442 \u043f\u043b\u0430\u0442\u0438\u0442\u044c <id> <\u0441\u0443\u043c\u043c\u0430>")
        return
    try:
        credit_id = int(parts[2])
    except Exception:
        await msg.reply("\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 ID.")
        return
    amount = parse_amount(parts[3])
    if amount <= 0:
        await msg.reply("\u0421\u0443\u043c\u043c\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0443\u043b\u044f.")
        return
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db, uid)
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM credits WHERE id = ? AND borrower_id = ?", (credit_id, uid))
            credit = await cursor.fetchone()
            if not credit:
                await db.rollback()
                await msg.reply("\u041a\u0440\u0435\u0434\u0438\u0442 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
                return
            if credit["status"] != "active":
                await db.rollback()
                status = credit["status"]
                if status == "pending":
                    status_text = "??????? ?????????"
                elif status == "repaid":
                    status_text = "???????"
                elif status == "defaulted":
                    status_text = "??????"
                else:
                    status_text = str(status)
                await msg.reply(f"??????? ????? ?????? ???????? ??????. ??????: {status_text}.")
                return
            paid = await get_credit_paid_sum(db, credit_id)
            total_due = int(credit["total_due"] or 0)
            remaining = max(0, total_due - paid)
            if remaining <= 0:
                await db.execute("UPDATE credits SET status = 'repaid' WHERE id = ?", (credit_id,))
                await db.commit()
                await msg.reply("\u041a\u0440\u0435\u0434\u0438\u0442 \u0443\u0436\u0435 \u043f\u043e\u0433\u0430\u0448\u0435\u043d.")
                return
            if amount > remaining:
                amount = remaining
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            balance = int(row[0] or 0) if row else 0
            if balance < amount:
                await db.rollback()
                await msg.reply(f"\u041d\u0435\u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u0434\u0435\u043d\u0435\u0433. \u041d\u0443\u0436\u043d\u043e: {format_money(amount)}")
                return
            lender_id = int(credit["lender_id"] or 0)
            now_ts = int(time.time())
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, uid))
            if lender_id != 0:
                await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (lender_id, 0))
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, lender_id))
            await db.execute(
                "INSERT INTO credit_payments (credit_id, amount, paid_at) VALUES (?, ?, ?)",
                (credit_id, amount, now_ts)
            )
            remaining -= amount
            if remaining <= 0:
                await db.execute("UPDATE credits SET status = 'repaid' WHERE id = ?", (credit_id,))
            await db.commit()
            logger.info(f"Платеж по кредиту: id={credit_id} заемщик={uid} сумма={amount} остаток={remaining}")
        if remaining <= 0:
            await msg.reply("\u041a\u0440\u0435\u0434\u0438\u0442 \u043f\u043e\u0433\u0430\u0448\u0435\u043d.")
        else:
            await msg.reply(f"\u041f\u043b\u0430\u0442\u0435\u0436 \u043f\u0440\u0438\u043d\u044f\u0442. \u041e\u0441\u0442\u0430\u0442\u043e\u043a: {format_money(remaining)}")
    except Exception as e:
        logger.error(f"Ошибка credit_pay_cmd: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u043f\u043b\u0430\u0442\u044b \u043a\u0440\u0435\u0434\u0438\u0442\u0430.")
@router.message(F.text.lower().startswith("\u043a\u0440\u0435\u0434\u0438\u0442 \u0441\u0438\u0433\u043c\u0430"))
async def credit_sigma_cmd(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 3:
        await msg.reply("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: \u043a\u0440\u0435\u0434\u0438\u0442 \u0441\u0438\u0433\u043c\u0430 <\u0441\u0443\u043c\u043c\u0430>")
        return
    amount = parse_amount(parts[2])
    uid = msg.from_user.id
    interest = CREDIT_SIGMA_INTEREST_PCT / 100
    total_due = amount + int(amount * interest)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db, uid)
            ok, reason = await check_credit_eligibility(db, uid, amount, True)
            if not ok:
                await msg.reply(reason)
                return
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (uid, 0))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, uid))
            now_ts = int(time.time())
            due_at = now_ts + CREDIT_SIGMA_DAYS * 86400
            await db.execute(
                "INSERT INTO credits (lender_id, borrower_id, amount, interest, total_due, issued_at, due_at, status) VALUES (0, ?, ?, ?, ?, ?, ?, 'active')",
                (uid, amount, interest, total_due, now_ts, due_at)
            )
            await db.commit()
            logger.info(f"Сигма-кредит выдан: заемщик={uid} сумма={amount} процент={interest} дней={CREDIT_SIGMA_DAYS}")
        await msg.reply(
            f"\u041a\u0440\u0435\u0434\u0438\u0442 \u043e\u0442 \u0421\u0438\u0433\u043c\u044b \u0432\u044b\u0434\u0430\u043d. \u0421\u0442\u0430\u0432\u043a\u0430: {CREDIT_SIGMA_INTEREST_PCT}%, \u0441\u0440\u043e\u043a: {CREDIT_SIGMA_DAYS}\u0434.\u0422\u043e\u043b\u044c\u043a\u043e \u0431\u0443\u0434\u044c\u0442\u0435 \u043e\u0441\u0442\u043e\u0440\u043e\u0436\u043d\u044b."
        )
    except Exception as e:
        logger.error(f"Ошибка credit_sigma_cmd: {e}")
        await msg.reply("\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u044f \u043a\u0440\u0435\u0434\u0438\u0442\u0430 \u0421\u0438\u0433\u043c\u044b.")
@router.message(F.text.lower().in_(["войны", "wars"]))
async def wars_command(msg: Message):
    """Команда 'войны'"""
    text, reply_markup = await build_wars_view(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().in_(["война", "war"]))
async def war_command(msg: Message):
    """Команда 'война'"""
    text, reply_markup = await build_war_view(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
async def _handle_war_confirm(msg: Message, token=None):
    uid = msg.from_user.id
    challenge = war_challenges.get(uid)
    if not challenge:
        return
    if int(time.time()) > challenge["expires_at"]:
        war_challenges.pop(uid, None)
        await msg.reply("Подтверждение истекло. Запустите атаку заново.")
        return
    if token and token.upper() != challenge["token"]:
        await msg.reply("Неверный токен подтверждения.")
        return
    now = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await process_credit_defaults(db, uid)
            if await has_defaulted_credit(db, uid):
                await msg.reply("\u0423 \u0432\u0430\u0441 \u0434\u0435\u0444\u043e\u043b\u0442 \u043f\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0443. \u0412\u043e\u0439\u043d\u044b \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u044b.")
                return
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT id, owner_user_id, population, last_war_end_ts FROM countries WHERE id = ?",
                (challenge["attacker_country_id"],)
            )
            attacker = await cursor.fetchone()
            cursor = await db.execute(
                "SELECT id, owner_user_id, population, last_war_end_ts FROM countries WHERE id = ?",
                (challenge["defender_country_id"],)
            )
            defender = await cursor.fetchone()
            if not attacker or attacker["owner_user_id"] != uid:
                await db.rollback()
                await msg.reply("Ваша страна не найдена.")
                return
            if not defender or not defender["owner_user_id"] or defender["owner_user_id"] == uid:
                await db.rollback()
                await msg.reply("Цель недоступна.")
                return
            if int(attacker["population"] or 0) < WAR_MIN_PEOPLE_START:
                await db.rollback()
                await msg.reply("Недостаточно армии для начала войны.")
                return
            cursor = await db.execute("""
                SELECT 1 FROM wars
                WHERE status = 'active'
                  AND (
                        attacker_country_id IN (?, ?)
                     OR defender_country_id IN (?, ?)
                  )
                LIMIT 1
            """, (attacker["id"], defender["id"], attacker["id"], defender["id"]))
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("Одна из стран уже в активной войне.")
                return
            a_cooldown_left = (attacker["last_war_end_ts"] or 0) + WAR_COOLDOWN - now
            d_cooldown_left = (defender["last_war_end_ts"] or 0) + WAR_COOLDOWN - now
            if a_cooldown_left > 0 or d_cooldown_left > 0:
                await db.rollback()
                await msg.reply("Одна из стран на кулдауне после войны.")
                return
            await db.execute("""
                INSERT INTO wars
                (attacker_country_id, defender_country_id, status, started_at, last_round_at,
                 attacker_progress, defender_progress, rounds_played, ends_at)
                VALUES (?, ?, 'active', ?, ?, 0, 0, 0, 0)
            """, (attacker["id"], defender["id"], now, now))
            await db.commit()
        war_challenges.pop(uid, None)
        await msg.reply("⚔️ Война объявлена! Первый раунд через 5 минут.")
    except Exception as e:
        logger.error(f"Ошибка запуска войны: {e}")
        await msg.reply("Ошибка запуска войны.")
@router.message(F.text.lower().startswith("подтверждаю"))
async def war_confirm_token_msg(msg: Message):
    parts = msg.text.strip().split()
    token = parts[1] if len(parts) > 1 else ""
    await _handle_war_confirm(msg, token)
@router.message(F.text.lower() == "да")
async def war_confirm_yes_msg(msg: Message):
    await _handle_war_confirm(msg, None)
@router.message(Command("bosses"))
@router.message(Command("боссы"))
@router.message(F.text.lower().in_(["боссы", "bosses", "/боссы", "/bosses", "🐉 боссы", "👹 боссы"]))
async def bosses_command(msg: Message):
    """Команда 'боссы'"""
    logger.info(f"CMD bosses hit uid={msg.from_user.id} text={msg.text!r}")
    text, reply_markup = await build_bosses_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
# Глобальная переменная для создания клана (MVP)
# Command handlers for core economy features
def _missing_country_message() -> str:
    return "Сначала выбери страну: напиши 'выбор страны'."
@router.message(F.text.lower() == "выбор страны")
async def choose_country_cmd(msg: Message):
    uid = msg.from_user.id
    if await check_user_has_country(uid):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT name, treasury, stability, population FROM countries WHERE owner_user_id = ?",
                (uid,)
            )
            country = await cursor.fetchone()
        if not country:
            await msg.answer("Не удалось найти твой выбор. Напиши 'выбор страны'.")
            return
        text = (
            f"🌍 <b>Твоя страна</b>\n\n"
            f"Название: {country['name']}\n"
            f"Население: {country['population']:,}\n"
            f"Казна: {country['treasury']:,}\n"
            f"Стабильность: {country['stability']}%\n\n"
            "Смена страны пока недоступна, но можно продолжать развивать текущую."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Моя страна", callback_data="show_my_country")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="back_to_menu")]
        ])
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await show_country_selection(msg)
@router.message(F.text.lower() == "собрать доход")
async def collect_income_cmd(msg: Message):
    uid = msg.from_user.id
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    result = await collect_country_income_for_user(uid, country_id)
    if not result["success"]:
        await msg.answer(result["error"])
        return
    lines = [
        f"Income collected: {result['total_income']:,}",
        f"Accumulated: {format_duration(result['accumulated_seconds'])} (max 24 h)",
        f"Next collection: {format_timestamp(result['next_available'])}"
    ]
    response = "\n".join(lines)
    if result.get("event_message"):
        response += "\n\n" + result['event_message']
    await msg.answer(response)
@router.message(F.text.lower().startswith("внести в казну"))
async def deposit_treasury_cmd(msg: Message):
    uid = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 4:
        await msg.reply(
            "❌ Используйте: <code>внести в казну [сумма]</code>\n"
            "Пример: <code>внести в казну 1к</code>",
            parse_mode="HTML"
        )
        return
    amount = parse_amount(parts[3])
    if amount <= 0:
        await msg.reply("❌ Неверная сумма.", parse_mode="HTML")
        return
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id, treasury FROM countries WHERE id = ?", (country_id,))
            row = await cursor.fetchone()
            if not row or row[0] != uid:
                await db.rollback()
                await msg.reply("❌ Вы не владелец этой страны.", parse_mode="HTML")
                return
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            user_row = await cursor.fetchone()
            balance = int(user_row[0] or 0) if user_row else 0
            if balance < amount:
                await db.rollback()
                await msg.reply(f"❌ Недостаточно средств. Баланс: {format_money(balance)}", parse_mode="HTML")
                return
            new_balance = balance - amount
            new_treasury = int(row[1] or 0) + amount
            await db.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, uid))
            await db.execute("UPDATE countries SET treasury = ? WHERE id = ?", (new_treasury, country_id))
            await db.commit()
        await msg.reply(
            f"✅ Внесено в казну: {format_money(amount)}\n"
            f"💰 Казна: {format_money(new_treasury)}\n"
            f"💳 Баланс: {format_money(new_balance)}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка deposit_treasury_cmd: {e}")
        await msg.reply("❌ Ошибка пополнения казны.", parse_mode="HTML")
@router.message(F.text.lower() == "улучшения")
async def improvements_cmd(msg: Message):
    uid = msg.from_user.id
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    text, markup, err = await build_upgrade_country_menu(country_id, uid)
    if err == "not_owner":
        await msg.answer("Сначала нужно стать владельцем страны.")
        return
    if err:
        await msg.answer("Ошибка загрузки меню улучшений.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=markup)
@router.message(F.text.lower() == "бизнесы")
async def businesses_cmd(msg: Message):
    uid = msg.from_user.id
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    text, markup, err = await build_country_businesses_view(country_id, uid)
    if err == "not_owner":
        await msg.answer("Ты не владелец страны.")
        return
    if err == "not_found":
        await msg.answer("Страна не найдена.")
        return
    if err:
        await msg.answer("Ошибка загрузки списка бизнесов.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=markup)
@router.message(F.text.lower() == "бизнес собственный")
async def own_businesses_cmd(msg: Message):
    await businesses_cmd(msg)
@router.message(F.text.lower() == "налоги")
async def taxes_cmd(msg: Message):
    uid = msg.from_user.id
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    text, markup, err = await build_tax_menu(country_id, uid)
    if err == "not_owner":
        await msg.answer("Ты не владелец своей страны.")
        return
    if err:
        await msg.answer("Ошибка открытия меню налогов.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=markup)
@router.message(F.text.lower() == "экономика")
async def economy_cmd(msg: Message):
    uid = msg.from_user.id
    country_id = await get_user_country_id_simple(uid)
    if not country_id:
        await msg.answer(_missing_country_message())
        return
    text, markup = await build_country_view(country_id, uid)
    if not text:
        await msg.answer("Не удалось показать экономику страны.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=markup)
# "... (MVP)
creating_clan = {}
creating_transport_company = {}
creating_construction_company = {}


async def _create_transport_company_from_name(uid: int, name: str, msg: Message):
    if not name:
        return
    logger.info(f"TC create attempt uid={uid} name='{name}'")
    cancel_words = {"otmena", "nazad", "отмена", "назад"}
    if name.lower() in cancel_words:
        creating_transport_company.pop(uid, None)
        await msg.reply("Создание ТК отменено.")
        return
    if name.startswith("/"):
        await msg.reply("Название ТК не должно начинаться с команды. Напишите другое имя.")
        return
    if len(name) < 3 or len(name) > 30:
        await msg.reply("Название ТК должно быть от 3 до 30 символов.")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            balance = (await cursor.fetchone())[0]
            if balance < TRANSPORT_CREATE_COST:
                await db.rollback()
                await msg.reply("Недостаточно денег для создания ТК.")
                return
            cursor = await db.execute(
                "SELECT 1 FROM transport_companies WHERE owner_user_id = ?",
                (uid,)
            )
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("У вас уже есть транспортная компания.")
                return
            now = int(time.time())
            await db.execute(
                "INSERT INTO transport_companies (name, owner_user_id, created_at) VALUES (?, ?, ?)",
                (name, uid, now)
            )
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (TRANSPORT_CREATE_COST, uid)
            )
            await db.commit()
        creating_transport_company.pop(uid, None)
        await msg.reply(f"Транспортная компания '{name}' создана!")
        text, reply_markup = await build_transport_menu(uid)
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка create_transport_company_name_from_prompt: {e}")
        await msg.reply("Ошибка создания ТК.")


async def _create_construction_company_from_name(uid: int, name: str, msg: Message):
    if not name:
        return
    logger.info(f"SC create attempt uid={uid} name='{name}'")
    cancel_words = {"otmena", "nazad", "отмена", "назад"}
    if name.lower() in cancel_words:
        creating_construction_company.pop(uid, None)
        await msg.reply("Создание СК отменено.")
        return
    if name.startswith("/"):
        await msg.reply("Название СК не должно начинаться с команды. Напишите другое имя.")
        return
    if len(name) < 3 or len(name) > 30:
        await msg.reply("Название СК должно быть от 3 до 30 символов.")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            balance = (await cursor.fetchone())[0]
            if balance < CONSTRUCTION_CREATE_COST:
                await db.rollback()
                await msg.reply("Недостаточно денег для создания СК.")
                return
            cursor = await db.execute(
                "SELECT 1 FROM construction_companies WHERE owner_user_id = ?",
                (uid,)
            )
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("У вас уже есть строительная компания.")
                return
            now = int(time.time())
            cursor = await db.execute(
                "INSERT INTO construction_companies (name, owner_user_id, created_at) VALUES (?, ?, ?)",
                (name, uid, now)
            )
            company_id = cursor.lastrowid
            await db.execute(
                "INSERT INTO construction_resources (company_id, workers, materials, land) VALUES (?, 0, 0, 0)",
                (company_id,)
            )
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (CONSTRUCTION_CREATE_COST, uid)
            )
            await db.commit()
        creating_construction_company.pop(uid, None)
        await msg.reply(f"Строительная компания '{name}' создана!")
        text, reply_markup = await build_construction_menu(uid)
        await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка create_construction_company_name_from_prompt: {e}")
        await msg.reply("Ошибка создания СК.")
@router.message(F.text.lower().startswith("создать клан "))
async def create_clan_name(msg: Message):
    """Создание клана с названием"""
    uid = msg.from_user.id
    name = msg.text[13:].strip()  # После "создать клан "
    if len(name) < 3 or len(name) > 20:
        await msg.reply("❌ Название клана должно быть 3-20 символов")
        return
    price = scale_price(1_000_000)  # 1M
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            balance = (await cursor.fetchone())[0]
            if balance < price:
                await db.rollback()
                await msg.reply("❌ Недостаточно средств для создания клана")
                return
            cursor = await db.execute("SELECT 1 FROM clans WHERE owner_user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("❌ У вас уже есть клан")
                return
            cursor = await db.execute("SELECT 1 FROM clan_members WHERE user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("❌ Вы уже в клане")
                return
            now = int(time.time())
            cursor = await db.execute("INSERT INTO clans (name, owner_user_id, created_at) VALUES (?, ?, ?)", (name, uid, now))
            clan_id = cursor.lastrowid
            await db.execute("INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, 'owner', ?)", (clan_id, uid, now))
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, uid))
            await db.commit()
        creating_clan.pop(uid, None)
        await msg.reply(f"✅ Клан '{name}' создан! Стоимость: {price:,}")
    except Exception as e:
        logger.error(f"Ошибка create_clan_name: {e}")
        await msg.reply("❌ Ошибка создания клана")
@router.message(F.text.lower().in_(["хелп", "помощь"]))
async def help_command(msg: Message):
    is_admin = msg.from_user.id in ADMIN_IDS
    await msg.answer(build_help_text(is_admin))
@router.message(lambda msg: bool(msg.text) and creating_clan.get(msg.from_user.id))
async def create_clan_name_from_prompt(msg: Message):
    """Handle clan name input after prompt"""
    uid = msg.from_user.id
    if not creating_clan.get(uid):
        return
    name = msg.text.strip() if msg.text else ""
    if not name:
        return
    cancel_words = {"otmena", "\u043e\u0442\u043c\u0435\u043d\u0430"}
    if name.lower() in cancel_words:
        creating_clan.pop(uid, None)
        await msg.reply("Создание клана отменено.")
        return
    if name.startswith("/"):
        await msg.reply("Отправьте название клана или напишите 'отмена'.")
        return
    if len(name) < 3 or len(name) > 20:
        await msg.reply("Название клана должно быть 3-20 символов.")
        return
    price = scale_price(1_000_000)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            balance = (await cursor.fetchone())[0]
            if balance < price:
                await db.rollback()
                await msg.reply("Недостаточно денег для создания клана.")
                return
            cursor = await db.execute("SELECT 1 FROM clans WHERE owner_user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("У вас уже есть свой клан.")
                return
            cursor = await db.execute("SELECT 1 FROM clan_members WHERE user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await msg.reply("Вы уже состоите в клане.")
                return
            now = int(time.time())
            cursor = await db.execute(
                "INSERT INTO clans (name, owner_user_id, created_at) VALUES (?, ?, ?)",
                (name, uid, now)
            )
            clan_id = cursor.lastrowid
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, 'owner', ?)",
                (clan_id, uid, now)
            )
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, uid))
            await db.commit()
        creating_clan.pop(uid, None)
        await msg.reply(f"Клан '{name}' создан. Потрачено: {price:,}.")
    except Exception as e:
        logger.error(f"Ошибка create_clan_name_from_prompt: {e}")
        await msg.reply("Ошибка создания клана.")
@router.message(lambda msg: bool(msg.text) and creating_transport_company.get(msg.from_user.id))
async def create_transport_company_name_from_prompt(msg: Message):
    uid = msg.from_user.id
    if not creating_transport_company.get(uid):
        return
    name = msg.text.strip() if msg.text else ""
    await _create_transport_company_from_name(uid, name, msg)


@router.message(F.text.lower().startswith(("создать тк ", "тк ")))
async def create_transport_company_inline_cmd(msg: Message):
    text = msg.text.strip()
    lower = text.lower()
    if lower.startswith("создать тк "):
        name = text[len("создать тк "):].strip()
    else:
        name = text[3:].strip()
    uid = msg.from_user.id
    await _create_transport_company_from_name(uid, name, msg)


@router.message(F.text.lower() == "создать тк")
async def create_transport_company_prompt_cmd(msg: Message):
    uid = msg.from_user.id
    creating_transport_company[uid] = True
    logger.info(f"TC create prompt set via text uid={uid}")
    await msg.reply("Введите название ТК или напишите 'отмена'.")
@router.message(lambda msg: bool(msg.text) and creating_construction_company.get(msg.from_user.id))
async def create_construction_company_name_from_prompt(msg: Message):
    uid = msg.from_user.id
    if not creating_construction_company.get(uid):
        return
    name = msg.text.strip() if msg.text else ""
    await _create_construction_company_from_name(uid, name, msg)


@router.message(F.text.lower().startswith(("создать ск ", "ск ")))
async def create_construction_company_inline_cmd(msg: Message):
    text = msg.text.strip()
    lower = text.lower()
    if lower.startswith("создать ск "):
        name = text[len("создать ск "):].strip()
    else:
        name = text[3:].strip()
    uid = msg.from_user.id
    await _create_construction_company_from_name(uid, name, msg)


@router.message(F.text.lower() == "создать ск")
async def create_construction_company_prompt_cmd(msg: Message):
    uid = msg.from_user.id
    creating_construction_company[uid] = True
    logger.info(f"SC create prompt set via text uid={uid}")
    await msg.reply("Введите название СК или напишите 'отмена'.")
# ========== ОБНОВЛЕНИЕ ЮЗЕРНЕЙМА ==========
@router.message(F.text & ~F.text.lower().in_([
    "страны", "/страны", "countries", "/countries", "🌍 страны",
    "боссы", "/боссы", "bosses", "/bosses", "🐉 боссы", "👹 боссы",
    "шахта", "/шахта", "mine", "/mine"
]))
async def update_username_handler(msg: Message):
    uid = msg.from_user.id
    username = msg.from_user.username
    if msg.text:
        if creating_transport_company.get(uid):
            await _create_transport_company_from_name(uid, msg.text.strip(), msg)
            return
        if creating_construction_company.get(uid):
            await _create_construction_company_from_name(uid, msg.text.strip(), msg)
            return
    await auto_accumulate_bitcoin(uid)
    if username:
        await update_username(uid, username)
    raise SkipHandler
# ========== ФУНКЦИИ ИЗ ДОПОЛНЕНИЯ ==========
async def cleanup_old_games():
    """Очистка старых игр"""
    try:
        current_time = time.time()
        to_remove = []
        for user_id, game in crash_games.items():
            # Если игра старше 5 минут - удаляем
            if current_time - game.get("timestamp", 0) > 300:
                to_remove.append(user_id)
        for user_id in to_remove:
            del crash_games[user_id]
            logger.info(f"🗑️ Очищена старая игра краш для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка очистки игр: {e}")
async def periodic_cleanup():
    """Периодическая очистка"""
    while True:
        await asyncio.sleep(60)  # Каждую минуту
        await cleanup_old_games()
async def show_mining_panel(msg: Message = None, cb: CallbackQuery = None):
    """Показать красивую inline-панель майнинга"""
    if msg:
        uid = msg.from_user.id
        message_obj = msg
    elif cb:
        uid = cb.from_user.id
        message_obj = cb.message
    else:
        return
    # 1. Сначала ОБЯЗАТЕЛЬНО обновляем накопления
    await calculate_and_update_mining(uid)
    # 2. Получаем ОБНОВЛЕННЫЕ данные
    user = await get_user(uid)
    # 3. Проверяем админ ли пользователь
    is_admin = uid in ADMIN_IDS
    # 4. Делаем расчеты
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    btc_price = BitcoinMining.get_bitcoin_price()
    usd_per_hour = btc_per_hour * btc_price
    # 5. Создаем клавиатуру (разную для админов и обычных пользователей)
    if is_admin:
        # Клавиатура для админа
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить 1 карту", callback_data="mining_buy_gpu_1"),
                InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim")
            ],
            [
                InlineKeyboardButton(text="⚡ Улучшить", callback_data="mining_upgrade_gpu"),
                InlineKeyboardButton(text="🔧 Форс-фикс", callback_data="force_fix_now")
            ],
            [
                InlineKeyboardButton(text="💸 Продать BTC", callback_data="mining_sell"),
                InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_mining_panel")
            ],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ])
    else:
        # Клавиатура для обычного пользователя
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Купить 1 карту", callback_data="mining_buy_gpu_1"),
                InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim")
            ],
            [
                InlineKeyboardButton(text="⚡ Улучшить", callback_data="mining_upgrade_gpu"),
                InlineKeyboardButton(text="🔍 Проверить", callback_data="check_mining_now")
            ],
            [
                InlineKeyboardButton(text="💸 Продать BTC", callback_data="mining_sell"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="mining_refresh")
            ],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ])
    # 6. Формируем текст (немного разный для админа)
    if is_admin:
        text = f"""
⛏️ <b>МАЙНИНГ ФЕРМА [АДМИН]</b>
📊 <b>Ваша ферма:</b>
• 🎮 Видеокарт: {user['mining_gpu_count']} шт.
• ⭐ Уровень: {user['mining_gpu_level']}/5
• ⚡ Хешрейт: {hashrate:,.0f} MH/s
💰 <b>Доходность:</b>
• ₿ BTC/час: {btc_per_hour:.6f}
• 💰 $/час: {format_money(int(usd_per_hour))}
• 📈 Курс BTC: {format_money(int(btc_price))}$
💎 <b>Ваши BTC:</b> {user['bitcoin']:.8f}
🛠️ <b>Админ-панель доступна!</b>
"""
    else:
        # Показываем сколько уже накопилось
        current_time = int(time.time())
        last_claim = user.get('last_mining_claim', current_time)
        time_passed = current_time - last_claim
        if time_passed < 60:
            btc_mined = 0
            time_text = "⏳ Еще не прошла минута"
        else:
            btc_mined = btc_per_hour * (time_passed / 3600)
            time_text = f"✅ Накоплено: {btc_mined:.8f} BTC"
        text = f"""
⛏️ <b>МАЙНИНГ ФЕРМА</b>
📊 <b>Ваша ферма:</b>
• 🎮 Видеокарт: {user['mining_gpu_count']} шт.
• ⭐ Уровень: {user['mining_gpu_level']}/5
• ⚡ Хешрейт: {hashrate:,.0f} MH/s
💰 <b>Доходность:</b>
• ₿ BTC/час: {btc_per_hour:.6f}
• 💰 $/час: {format_money(int(usd_per_hour))}
• 📈 Курс BTC: {format_money(int(btc_price))}$
💎 <b>Накопления:</b>
• Всего BTC: {user['bitcoin']:.8f}
• {time_text}
• Прошло времени: {time_passed} сек
"""
    # 7. Отправляем/редактируем сообщение
    if cb:
        try:
            await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
    elif msg:
        await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
async def show_my_planets_panel(msg: Message = None, cb: CallbackQuery = None):
    """Показать панель 'Мои планеты' - ТОЛЬКО ЗДЕСЬ обновляем плазму"""
    # Получаем ID пользователя
    if msg:
        uid = msg.from_user.id
        message_obj = msg
    elif cb:
        uid = cb.from_user.id
        message_obj = cb.message
    else:
        return
    # ВАЖНО: УДАЛИТЬ этот вызов:
    # await get_user(uid)  # Он активировал автонакопление
    # ВМЕСТО ЭТОГО: Рассчитываем и обновляем плазму (только здесь!)
    accumulated_plasma = await calculate_and_update_plasma(uid)
    if accumulated_plasma > 0:
        logger.info(f"🪐 Автонакопление плазмы для {uid}: {accumulated_plasma}")
    # Теперь получаем ОБНОВЛЕННЫЕ данные пользователя
    user = await get_user(uid)
    # ... остальной код функции без изменений ...
    # Получаем список планет пользователя
    user_planets = await get_user_planets(uid)
    if not user_planets:
        # Если нет планет - показываем сообщение с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪐 Смотреть все планеты", callback_data="show_planets"),
             InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")]
        ])
        # Если это callback, редактируем сообщение
        if cb:
            try:
                await message_obj.edit_text(
                    "🪐 <b>У вас пока нет планет</b>\n\n"
                    "Купите первую планету, чтобы начать получать плазму!\n\n"
                    "💡 <b>Как купить:</b>\n"
                    "• Напишите <code>планеты</code> - список планет\n"
                    "• Напишите <code>купить планету [id]</code>\n\n"
                    "⚡ <b>Плазма накапливается автоматически!</b>\n"
                    "Просто зайдите сюда, и плазма добавится к балансу.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except:
                await message_obj.answer(
                    "🪐 <b>У вас пока нет планет</b>\n\n"
                    "Купите первую планету, чтобы начать получать плазму!\n\n"
                    "💡 <b>Как купить:</b>\n"
                    "• Напишите <code>планеты</code> - список планет\n"
                    "• Напишите <code>купить планету [id]</code>\n\n"
                    "⚡ <b>Плазма накапливается автоматически!</b>\n"
                    "Просто зайдите сюда, и плазма добавится к балансу.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        # Если это сообщение, отправляем новое
        elif msg:
            await message_obj.answer(
                "🪐 <b>У вас пока нет планет</b>\n\n"
                "Купите первую планету, чтобы начать получать плазму!\n\n"
                "💡 <b>Как купить:</b>\n"
                    "• Напишите <code>планеты</code> - список планет\n"
                    "• Напишите <code>купить планету [id]</code>\n\n"
                    "⚡ <b>Плазма накапливается автоматически!</b>\n"
                    "Просто зайдите сюда, и плазма добавится к балансу.",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        return
    # 🔥 СОЗДАЕМ ТЕКСТ ДЛЯ ПАНЕЛИ С ПЛАНЕТАМИ
    text = "🪐 <b>МОИ ПЛАНЕТЫ</b>\n\n"
    # Показываем общее количество плазмы (уже с автонакоплением)
    text += f"⚡ <b>Ваша плазма:</b> {user['plasma']} единиц\n\n"
    # Создаем кнопки для inline-клавиатуры
    keyboard_buttons = []
    # Показываем информацию о каждой планете
    for planet_id, planet_data in user_planets.items():
        if planet_id in PLANETS:
            planet_info = PLANETS[planet_id]
            # 🔥 ВАЖНО: Не показываем "накоплено плазмы", так как она уже начислена
            # Вместо этого показываем только генерацию в час
            # Добавляем информацию о планете в текст
            text += f"• <b>{planet_info['name']}</b>\n"
            text += f"  ⚡ Генерация: {planet_info['plasma_per_hour']} плазмы/час\n"
            text += f"  📝 {planet_info['description']}\n\n"
            # 🔥 ИЗМЕНЕНИЕ: Вместо кнопки "Собрать" делаем кнопку "Инфо"
            # Потому что плазма теперь накапливается автоматически
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🪐 {planet_info['name']} - Информация",
                    callback_data=f"planet_info_{planet_id}"
                )
            ])
    # 🔥 ОБНОВЛЕННЫЕ КНОПКИ ДЛЯ ПАНЕЛИ:
    # 1. Продать плазму
    # 2. Обновить панель
    keyboard_buttons.append([
        InlineKeyboardButton(text="💰 Продать плазму", callback_data="sell_plasma_menu"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="planets_refresh")
    ])
    # 3. Кнопка назад в меню
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Меню", callback_data="back_to_menu")
    ])
    # Создаем inline-клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    # 🔥 ДОБАВЛЯЕМ ПОЯСНЕНИЕ ОБ АВТОНАКОПЛЕНИИ
    text += "💡 <b>Плазма теперь накапливается автоматически!</b>\n"
    text += "Просто зайдите в профиль или откройте эту панель, и плазма будет добавлена к вашему балансу.\n\n"
    text += "💰 <b>Продать плазму:</b> 1 единица = ~5-6М$\n"
    text += f"💵 <b>Примерная стоимость:</b> {format_money(user['plasma'] * get_plasma_price())}$"
    # 🔥 ОТПРАВЛЯЕМ ИЛИ РЕДАКТИРУЕМ СООБЩЕНИЕ
    # Если это callback, редактируем существующее сообщение
    if cb:
        try:
            await message_obj.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except:
            # Если не получается редактировать (старое сообщение), отправляем новое
            await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
    # Если это сообщение, отправляем новое
    elif msg:
        await message_obj.answer(text, parse_mode="HTML", reply_markup=keyboard)
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
@router.callback_query(F.data == "admin_mining_panel")
async def admin_mining_panel_callback(cb: CallbackQuery):
    """Админ-панель майнинга через callback"""
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Нет прав!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Форс-фикс для себя", callback_data="admin_force_fix_self"),
         InlineKeyboardButton(text="🔧 Форс-фикс по ID", callback_data="admin_force_fix_id")],
        [InlineKeyboardButton(text="📊 Статистика майнинга", callback_data="admin_mining_stats"),
         InlineKeyboardButton(text="🎮 Выдать видеокарты", callback_data="admin_give_gpu")],
        [InlineKeyboardButton(text="💰 Выдать BTC", callback_data="admin_give_btc"),
         InlineKeyboardButton(text="🔄 Сбросить время всем", callback_data="admin_reset_all_time")],
        [InlineKeyboardButton(text="⛏️ Вернуться в майнинг", callback_data="show_mining")]
    ])
    await cb.message.edit_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ МАЙНИНГА</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await cb.answer()
@router.message(F.text.lower() == "активные игры")
async def active_games_cmd(msg: Message):
    """Показать активные игры (админ)"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    if not crash_games:
        await msg.reply("🎮 Нет активных игр Краш")
        return
    text = "🎮 <b>АКТИВНЫЕ ИГРЫ КРАШ</b>\n\n"
    for user_id, game in crash_games.items():
        if game.get("active", False):
            time_passed = int(time.time() - game.get("timestamp", time.time()))
            text += f"👤 ID: {user_id}\n"
            text += f"💰 Ставка: {format_money(game['bet'])}\n"
            text += f"📈 Множитель: {game.get('multiplier', 1.0)}x\n"
            text += f"⏳ Длится: {time_passed} сек\n"
            text += f"🆔 Сообщение: {game.get('message_id', 'N/A')}\n"
            text += "─" * 30 + "\n"
    await msg.reply(text, parse_mode="HTML")
@router.message(F.text.lower() == "активные игры")
async def active_games_cmd(msg: Message):
    """Показать активные игры (админ)"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    if not crash_games:
        await msg.reply("🎮 Нет активных игр Краш")
        return
    text = "🎮 <b>АКТИВНЫЕ ИГРЫ КРАШ</b>\n\n"
    for user_id, game in crash_games.items():
        if game.get("active", False):
            time_passed = int(time.time() - game.get("timestamp", time.time()))
            text += f"👤 ID: {user_id}\n"
            text += f"💰 Ставка: {format_money(game['bet'])}\n"
            text += f"📈 Множитель: {game.get('multiplier', 1.0)}x\n"
            text += f"⏳ Длится: {time_passed} сек\n"
            text += f"🆔 Сообщение: {game.get('message_id', 'N/A')}\n"
            text += "─" * 30 + "\n"
    await msg.reply(text, parse_mode="HTML")
@router.callback_query(F.data.startswith("mining_buy_gpu_"))
async def mining_buy_gpu_callback(cb: CallbackQuery):
    """Купить видеокарты (1 или 10)"""
    try:
        # Извлекаем количество из callback_data: mining_buy_gpu_1 или mining_buy_gpu_10
        parts = cb.data.split("_")
        count = int(parts[3])  # последняя часть - количество
        uid = cb.from_user.id
        user = await get_user(uid)
        gpu_level = user['mining_gpu_level']
        # Получаем цену одной видеокарты
        single_gpu_price = BitcoinMining.get_gpu_price(gpu_level)
        total_price = single_gpu_price * count
        if user['balance'] < total_price:
            await cb.answer(f"❌ Не хватает {format_money(total_price - user['balance'])}")
            return
        # Покупка
        async with aiosqlite.connect(DB_PATH) as db:
            # Снимаем деньги
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (total_price, uid))
            # Увеличиваем количество видеокарт
            new_gpu_count = user['mining_gpu_count'] + count
            await db.execute("UPDATE users SET mining_gpu_count = ? WHERE id = ?", (new_gpu_count, uid))
            current_time = int(time.time())
            await db.execute(
                "UPDATE users SET last_mining_claim = CASE WHEN last_mining_claim = 0 THEN ? ELSE last_mining_claim END WHERE id = ?",
                (current_time, uid)
            )
            await db.commit()
        # Рассчитываем новую доходность
        new_hashrate = BitcoinMining.calculate_hashrate(new_gpu_count, gpu_level)
        new_btc_per_hour = BitcoinMining.calculate_btc_per_hour(new_hashrate)
        btc_price = BitcoinMining.get_bitcoin_price()
        new_usd_per_hour = new_btc_per_hour * btc_price
        new_daily_income = new_usd_per_hour * 24
        # Расчет окупаемости
        total_investment = single_gpu_price * new_gpu_count  # упрощенный расчет
        roi_days = total_investment / new_daily_income if new_daily_income > 0 else 0
        await cb.answer(f"✅ Куплено {count} видеокарт уровня {gpu_level} за {format_money(total_price)}!")
        # Обновляем панель майнинга
        await show_mining_panel(cb=cb)
    except Exception as e:
        logger.error(f"Ошибка покупки видеокарт: {e}")
        await cb.answer("❌ Ошибка покупки")
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
    """Обработка кнопки 'Забрать BTC' - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        uid = cb.from_user.id
        # Показываем сообщение о начале сбора
        await cb.answer("⛏️ Собираем BTC...")
        # Получаем данные перед сбором
        user_before = await get_user(uid)
        # Вызываем сбор BTC
        success, btc_amount, result = await claim_mining_profit(uid)
        if success:
            await add_referral_action(uid)
            btc_price = BitcoinMining.get_bitcoin_price()
            usd_value = result if isinstance(result, (int, float)) else btc_amount * btc_price
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💸 Продать BTC", callback_data="mining_sell")],
                [InlineKeyboardButton(text="⛏️ Вернуться в майнинг", callback_data="show_mining")]
            ])
            await cb.message.edit_text(
                f"✅ <b>БИТКОИНЫ СОБРАНЫ!</b>\n\n"
                f"💰 <b>Количество:</b> {btc_amount:.8f} BTC\n"
                f"💵 <b>Стоимость:</b> {format_money(int(usd_value))}$\n"
                f"📈 <b>Курс BTC:</b> {format_money(int(btc_price))}$\n\n"
                f"🎉 <b>Поздравляем с успешным майнингом!</b>\n\n"
                f"⚡ Ферма продолжает работать автоматически",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            # Если не удалось собрать
            error_msg = str(result)
            # Проверяем почему не удалось
            user_after = await get_user(uid)
            debug_text = f"""
🔍 <b>ДИАГНОСТИКА ПРОБЛЕМЫ:</b>
📊 <b>До:</b>
• BTC: {user_before.get('bitcoin', 0):.8f}
• Видеокарт: {user_before.get('mining_gpu_count', 0)}
📊 <b>После:</b>
• BTC: {user_after.get('bitcoin', 0):.8f}
• Видеокарт: {user_after.get('mining_gpu_count', 0)}
⚠️ <b>Проблема:</b> {error_msg}
"""
            # Создаем кнопки для решения проблемы
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Форс-фикс", callback_data="force_fix_now"),
                 InlineKeyboardButton(text="🎮 Купить видеокарты", callback_data="mining_buy_gpu_1")],
                [InlineKeyboardButton(text="🔧 Проверка", callback_data="check_mining_now")]
            ])
            await cb.message.edit_text(
                f"❌ <b>НЕ УДАЛОСЬ СОБРАТЬ BTC</b>\n\n"
                f"{debug_text}\n\n"
                f"💡 <b>Попробуйте:</b>\n"
                f"1. Подождать 2-3 минуты\n"
                f"2. Нажать 'Форс-фикс'\n"
                f"3. Купить видеокарты",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка mining_claim_callback: {e}", exc_info=True)
        await cb.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
@router.callback_query(F.data == "force_fix_now")
async def force_fix_now_callback(cb: CallbackQuery):
    """Форс-фикс через callback - ТОЛЬКО ДЛЯ АДМИНОВ"""
    # Проверяем права администратора
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("❌ Эта команда доступна только администраторам!", show_alert=True)
        return
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Устанавливаем время на 1 час назад
            new_time = int(time.time()) - 3600
            await db.execute("""
                UPDATE users
                SET last_mining_claim = ?,
                    bitcoin = bitcoin + 0.001
                WHERE id = ?
            """, (new_time, uid))
            await db.commit()
        await cb.answer("✅ АДМИН-ФИКС ПРИМЕНЕН! Теперь попробуйте снова 'Забрать BTC'")
        # Обновляем сообщение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim")]
        ])
        await cb.message.edit_text(
            "✅ <b>Админ-фикс применен!</b>\n\n"
            "• Время сброшено на 1 час назад\n"
            "• Добавлено 0.001 BTC\n\n"
            "🔄 <b>Теперь попробуйте снова:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        await cb.answer(f"❌ Ошибка: {e}")
@router.callback_query(F.data == "check_mining_now")
async def check_mining_now_callback(cb: CallbackQuery):
    """Проверка майнинга через callback"""
    uid = cb.from_user.id
    user = await get_user(uid)
    text = f"""
🔍 <b>ПРОВЕРКА МАЙНИНГА</b>
🎮 <b>Видеокарты:</b> {user.get('mining_gpu_count', 0)} шт.
⭐ <b>Уровень:</b> {user.get('mining_gpu_level', 1)}/5
₿ <b>BTC:</b> {user.get('bitcoin', 0):.8f}
⏰ <b>Последний сбор:</b> {user.get('last_mining_claim', 0)}
⏳ <b>Прошло времени:</b> {int(time.time()) - user.get('last_mining_claim', time.time())} сек
💡 <b>Рекомендации:</b>
"""
    if user.get('mining_gpu_count', 0) == 0:
        text += "1. Купите видеокарты\n2. Подождите 2-3 минуты"
    elif user.get('bitcoin', 0) <= 0:
        text += "1. Подождите 2-3 минуты\n2. Если не поможет - нажмите 'Форс-фикс'"
    else:
        text += "✅ Всё отлично! Можете собирать BTC"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim"),
         InlineKeyboardButton(text="🔄 Форс-фикс", callback_data="force_fix_now")],
        [InlineKeyboardButton(text="🛒 Купить видеокарту", callback_data="mining_buy_gpu_1")]
    ])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await cb.answer("✅ Проверка завершена")
@router.callback_query(F.data == "mining_sell")
async def mining_sell_callback(cb: CallbackQuery):
    """Обработка кнопки 'Продать BTC'"""
    try:
        uid = cb.from_user.id
        user = await get_user(uid)
        if user['bitcoin'] <= 0:
            await cb.answer("❌ У вас нет биткоинов для продажи", show_alert=True)
            return
        # Создаем клавиатуру с вариантами продажи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 25% BTC", callback_data="sell_btc_25"),
                InlineKeyboardButton(text="💰 50% BTC", callback_data="sell_btc_50"),
                InlineKeyboardButton(text="💰 100% BTC", callback_data="sell_btc_100")
            ],
            [
                InlineKeyboardButton(text="💎 0.01 BTC", callback_data="sell_btc_0.01"),
                InlineKeyboardButton(text="💎 0.1 BTC", callback_data="sell_btc_0.1")
            ],
            [
                InlineKeyboardButton(text="📝 Своя сумма", callback_data="sell_btc_custom"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="show_mining")
            ]
        ])
        btc_price = BitcoinMining.get_bitcoin_price()
        total_value = user['bitcoin'] * btc_price
        await cb.message.edit_text(
            f"💸 <b>ПРОДАЖА БИТКОИНОВ</b>\n\n"
            f"💰 <b>Ваши BTC:</b> {user['bitcoin']:.8f}\n"
            f"💵 <b>Стоимость:</b> {format_money(int(total_value))}$\n"
            f"📈 <b>Курс:</b> 1 BTC = {format_money(int(btc_price))}$\n\n"
            f"🎯 <b>Выберите сколько продать:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка mining_sell_callback: {e}")
        await cb.answer("❌ Ошибка", show_alert=True)
@router.callback_query(F.data.startswith("sell_btc_"))
async def sell_btc_percent_callback(cb: CallbackQuery):
    """Продажа определенного процента BTC"""
    try:
        uid = cb.from_user.id
        data = cb.data
        # Получаем данные пользователя
        user = await get_user(uid)
        current_btc = user['bitcoin']
        if current_btc <= 0:
            await cb.answer("❌ У вас нет биткоинов", show_alert=True)
            return
        # Определяем сколько продавать
        if data == "sell_btc_25":
            btc_to_sell = current_btc * 0.25
            text_percent = "25%"
        elif data == "sell_btc_50":
            btc_to_sell = current_btc * 0.50
            text_percent = "50%"
        elif data == "sell_btc_100":
            btc_to_sell = current_btc
            text_percent = "100%"
        elif data == "sell_btc_0.01":
            btc_to_sell = 0.01
            text_percent = "0.01 BTC"
        elif data == "sell_btc_0.1":
            btc_to_sell = 0.1
            text_percent = "0.1 BTC"
        elif data == "sell_btc_custom":
            await cb.answer("📝 Введите: продать биткоин [количество]\nНапример: продать биткоин 0.05", show_alert=True)
            return
        else:
            await cb.answer("❌ Неизвестная команда", show_alert=True)
            return
        # Проверяем, что не продаем больше чем есть
        if btc_to_sell > current_btc:
            btc_to_sell = current_btc
            text_percent = "все"
        # Продаем
        success, btc_sold, usd_received = await sell_bitcoin(uid, btc_to_sell)
        if success:
            updated_user = await get_user(uid)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💸 Продать еще", callback_data="mining_sell")],
                [InlineKeyboardButton(text="⛏️ Вернуться в майнинг", callback_data="show_mining")]
            ])
            await cb.message.edit_text(
                f"✅ <b>БИТКОИНЫ ПРОДАНЫ!</b>\n\n"
                f"📊 <b>Продано:</b> {text_percent}\n"
                f"💰 <b>Количество BTC:</b> {btc_sold:.8f}\n"
                f"💵 <b>Получено:</b> {format_money(usd_received)}$\n\n"
                f"📈 <b>Осталось BTC:</b> {updated_user['bitcoin']:.8f}\n"
                f"💳 <b>Новый баланс:</b> {format_money(updated_user['balance'])}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await cb.answer(f"✅ Получено {format_money(usd_received)}$!")
        else:
            await cb.answer(f"❌ {usd_received}", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка sell_btc_percent_callback: {e}")
        await cb.answer("❌ Ошибка при продаже", show_alert=True)
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
@router.callback_query(F.data.startswith("planet_info_"))
async def planet_info_callback(cb: CallbackQuery):
    """Показать подробную информацию о планете с расчетами доходности"""
    try:
        # Извлекаем ID планеты из callback_data: "planet_info_1"
        planet_id = int(cb.data.split("_")[2])
        uid = cb.from_user.id
        # Получаем планеты пользователя
        user_planets = await get_user_planets(uid)
        # Проверяем, есть ли у пользователя эта планета
        if planet_id not in user_planets:
            await cb.answer("❌ У вас нет этой планеты", show_alert=True)
            return
        # Получаем информацию о планете
        if planet_id not in PLANETS:
            await cb.answer("❌ Планета не найдена в системе", show_alert=True)
            return
        planet_info = PLANETS[planet_id]
        planet_data = user_planets[planet_id]
        # Получаем текущую цену плазмы для расчетов
        plasma_price = get_plasma_price()
        # 🔥 РАСЧЕТЫ ДОХОДНОСТИ:
        plasma_per_hour = planet_info['plasma_per_hour']
        plasma_per_day = plasma_per_hour * 24
        plasma_per_week = plasma_per_day * 7
        plasma_per_month = plasma_per_day * 30
        # Рассчитываем доход в деньгах
        income_per_hour = plasma_per_hour * plasma_price
        income_per_day = plasma_per_day * plasma_price
        income_per_week = plasma_per_week * plasma_price
        income_per_month = plasma_per_month * plasma_price
        # 🔥 РАСЧЕТ ОКУПАЕМОСТИ:
        investment_cost = 0
        currency_type = ""
        if planet_info['price_dollars'] > 0:
            investment_cost = planet_info['price_dollars']
            currency_type = "$"
        else:
            investment_cost = planet_info['price_plasma'] * plasma_price
            currency_type = "$ (в пересчете)"
        # Рассчитываем срок окупаемости (в днях)
        payback_days = 0
        if income_per_day > 0:
            payback_days = investment_cost / income_per_day
        # 🔥 СТАТУС ПЛАНЕТЫ:
        current_time = int(time.time())
        last_collected = planet_data.get('last_collected', 0) or current_time
        # Время с последнего обновления (в часах)
        hours_since_update = (current_time - last_collected) / 3600
        # Если плазма собиралась недавно, показываем активный статус
        if hours_since_update < 1:
            status = "🟢 АКТИВНА (собирает плазму)"
            status_desc = f"Планета активно генерирует плазму. Следующее обновление через {60 - int(hours_since_update * 60)} мин."
        elif hours_since_update < 24:
            status = "🟡 РАБОТАЕТ (в фоне)"
            status_desc = "Планета работает в фоновом режиме. Плазма накапливается автоматически."
        else:
            status = "🔴 ТРЕБУЕТ ВНИМАНИЯ"
            status_desc = "Зайдите в бота, чтобы активировать генерацию плазмы."
        # 🔥 СОЗДАЕМ КЛАВИАТУРУ:
        keyboard_buttons = [
            # Кнопка для быстрой продажи плазмы с этой планеты
            [InlineKeyboardButton(
                text="💰 Продать плазму сейчас",
                callback_data=f"sell_plasma_from_planet_{planet_id}"
            )],
            # Кнопки навигации
            [InlineKeyboardButton(text="🪐 Все мои планеты", callback_data="planets_refresh"),
             InlineKeyboardButton(text="💰 Продать всю плазму", callback_data="sell_plasma_all")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        # 🔥 СОЗДАЕМ ТЕКСТ С ПОДРОБНОЙ ИНФОРМАЦИЕЙ:
        text = f"""
🪐 <b>ПОДРОБНАЯ ИНФОРМАЦИЯ О ПЛАНЕТЕ</b>
📛 <b>Название:</b> {planet_info['name']}
📝 <b>Описание:</b> {planet_info['description']}
📊 <b>Статус:</b> {status}
💡 {status_desc}
💰 <b>Инвестиции:</b>
"""
        # Показываем стоимость планеты
        if planet_info['price_dollars'] > 0:
            text += f"• Стоимость покупки: {format_money(planet_info['price_dollars'])} $\n"
        else:
            text += f"• Стоимость покупки: {planet_info['price_plasma']} плазмы\n"
            text += f"• (~{format_money(investment_cost)} $ по текущему курсу)\n"
        text += f"""
⚡ <b>Генерация плазмы:</b>
• В час: {plasma_per_hour} единиц
• В день: {plasma_per_day:,} единиц
• В неделю: {plasma_per_week:,} единиц
• В месяц: {plasma_per_month:,} единиц
💵 <b>Финансовые показатели:</b>
"""
        # Показываем доход в деньгах
        text += f"• Доход в час: ~{format_money(income_per_hour)} $\n"
        text += f"• Доход в день: ~{format_money(income_per_day)} $\n"
        text += f"• Доход в неделю: ~{format_money(income_per_week)} $\n"
        text += f"• Доход в месяц: ~{format_money(income_per_month)} $\n"
        # Показываем окупаемость если есть инвестиции
        if investment_cost > 0:
            text += f"\n📈 <b>Окупаемость:</b>\n"
            text += f"• Стоимость: {format_money(investment_cost)} {currency_type}\n"
            if payback_days > 0:
                if payback_days < 1:
                    text += f"• Окупится за: {int(payback_days * 24)} часов\n"
                elif payback_days < 30:
                    text += f"• Окупится за: {payback_days:.1f} дней\n"
                else:
                    text += f"• Окупится за: {payback_days/30:.1f} месяцев\n"
                # Показываем дату окупаемости
                payback_date = time.time() + (payback_days * 24 * 3600)
                payback_str = time.strftime("%d.%m.%Y", time.localtime(payback_date))
                text += f"• Дата окупаемости: {payback_str}\n"
            else:
                text += f"• Уже окупилась! ✅\n"
        # 🔥 ПОЛЕЗНЫЕ СОВЕТЫ:
        text += f"""
💡 <b>Как это работает:</b>
1. Плазма генерируется автоматически 24/7
2. При любой активности в боте плазма начисляется на баланс
3. Продавайте плазму, когда цена высокая
🎯 <b>Оптимальная стратегия:</b>
• Продавайте плазму при цене выше {format_money(plasma_price * 1.2)}$ за единицу
• Накапливайте плазму 2-3 дня для максимальной выгоды
• Следите за колебаниями цены (она меняется ±10%)
⚡ <b>Текущая цена плазмы:</b> {format_money(plasma_price)}$ за 1 единицу
"""
        # 🔥 ОТПРАВЛЯЕМ СООБЩЕНИЕ:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            # Если не получается редактировать, отправляем новое сообщение
            await cb.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            logger.error(f"Ошибка редактирования сообщения: {e}")
        await cb.answer(f"Информация о {planet_info['name']}")
    except Exception as e:
        logger.error(f"❌ Ошибка в planet_info_callback: {e}")
        await cb.answer("❌ Ошибка загрузки информации о планете", show_alert=True)
@router.callback_query(F.data.startswith("sell_plasma_from_planet_"))
async def sell_plasma_from_planet_callback(cb: CallbackQuery):
    """Быстрая продажа плазмы с конкретной планеты"""
    try:
        planet_id = int(cb.data.split("_")[4])
        uid = cb.from_user.id
        # Получаем пользователя (чтобы активировать автонакопление)
        user = await get_user(uid)
        # Получаем планеты пользователя
        user_planets = await get_user_planets(uid)
        # Проверяем, есть ли планета
        if planet_id not in user_planets or planet_id not in PLANETS:
            await cb.answer("❌ Планета не найдена")
            return
        planet_info = PLANETS[planet_id]
        # Рассчитываем примерное количество плазмы за последние 24 часа
        plasma_per_hour = planet_info['plasma_per_hour']
        estimated_plasma = plasma_per_hour * 24  # За последние сутки
        # Ограничиваем максимумом - доступной плазмой пользователя
        if estimated_plasma > user['plasma']:
            estimated_plasma = user['plasma']
        if estimated_plasma <= 0:
            await cb.answer("❌ Недостаточно плазмы для продажи")
            return
        # Продаем рассчитанное количество плазмы
        success, plasma_sold, money_received, price_per_unit = await sell_plasma(uid, estimated_plasma)
        if success:
            # Обновляем данные пользователя
            updated_user = await get_user(uid)
            # Создаем клавиатуру для возврата
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪐 Вернуться к планетам", callback_data="planets_refresh")],
                [InlineKeyboardButton(text="💰 Продать еще", callback_data=f"sell_plasma_from_planet_{planet_id}")]
            ])
            await cb.message.edit_text(
                f"✅ <b>Плазма продана успешно!</b>\n\n"
                f"🪐 <b>Планета:</b> {planet_info['name']}\n"
                f"💎 <b>Продано плазмы:</b> {plasma_sold} единиц\n"
                f"💰 <b>Цена за единицу:</b> {format_money(price_per_unit)} $\n"
                f"💵 <b>Получено:</b> {format_money(money_received)} $\n\n"
                f"⚡ <b>Осталось плазмы:</b> {updated_user['plasma']} единиц\n"
                f"💸 <b>Новый баланс:</b> {format_money(updated_user['balance'])} $\n\n"
                f"🔄 <b>Планета продолжает генерировать плазму автоматически!</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await cb.answer(f"💰 Получено {format_money(money_received)}$!")
        else:
            await cb.answer(f"❌ {money_received}")
    except Exception as e:
        logger.error(f"Ошибка sell_plasma_from_planet_callback: {e}")
        await cb.answer("❌ Ошибка продажи плазмы")
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
        logger.info(f"invest_start_callback получен: {cb.data}, parts: {parts}")
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
# ========== ФИКС КОМАНДЫ ПРОФИЛЬ ==========
@router.message(F.text.lower().in_(["профиль", "пр", "стата", "profile", "stats"]))
async def fix_profile_cmd(msg: Message):
    """Фикс для команды профиль"""
    await process_profile(msg)
@router.message(Command("профиль", "пр", "стата", "profile", "stats"))
async def fix_profile_slash(msg: Message):
    """Фикс для команды профиль с /"""
    await process_profile(msg)
# ========== ФИКС ДЛЯ КОМАНДЫ ПРОФИЛЬ ==========
@router.message(F.text.lower() == "профиль")
@router.message(F.text.lower() == "пр")
@router.message(F.text.lower() == "стата")
@router.message(F.text.lower() == "profile")
@router.message(F.text.lower() == "stats")
async def fix_profile_cmd(msg: Message):
    await process_profile(msg)
@router.message(F.text.lower().startswith("форсфикс "))
async def force_fix_for_user_cmd(msg: Message):
    """Форс-фикс для другого пользователя - ТОЛЬКО АДМИН"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply("❌ Используйте: форсфикс [ID пользователя]")
        return
    try:
        target_uid = int(parts[1])
    except ValueError:
        await msg.reply("❌ ID должен быть числом")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Устанавливаем время на 1 час назад
            new_time = int(time.time()) - 3600
            await db.execute("""
                UPDATE users
                SET last_mining_claim = ?,
                    bitcoin = bitcoin + 0.001,
                    mining_gpu_count = CASE WHEN mining_gpu_count = 0 THEN 5 ELSE mining_gpu_count END
                WHERE id = ?
            """, (new_time, target_uid))
            await db.commit()
        await msg.reply(
            f"✅ <b>Форс-фикс применен для пользователя ID {target_uid}!</b>\n\n"
            "• Время сброшено на 1 час назад\n"
            "• Добавлено 0.001 BTC\n"
            "• Если не было видеокарт - добавлено 5 шт",
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
@router.message(F.text.lower().startswith("выдать биткоин "))
async def give_bitcoin_cmd(msg: Message):
    """Выдать биткоины пользователю - ТОЛЬКО АДМИН"""
    if msg.from_user.id not in ADMIN_IDS:
        await msg.reply("❌ Эта команда доступна только администраторам!")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply("❌ Используйте: выдать биткоин [ID] [количество]\nПример: выдать биткоин 123456789 0.1")
        return
    try:
        target_uid = int(parts[2])
        amount = float(parts[3])
        if amount <= 0:
            await msg.reply("❌ Количество должно быть больше 0")
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET bitcoin = bitcoin + ? WHERE id = ?",
                           (amount, target_uid))
            await db.commit()
        await msg.reply(
            f"✅ <b>Выдано {amount:.8f} BTC пользователю ID {target_uid}!</b>\n\n"
            f"Теперь он может собрать их командой: <code>забрать биткоины</code>",
            parse_mode="HTML"
        )
    except ValueError:
        await msg.reply("❌ Неверный формат. Используйте: выдать биткоин [ID] [число]")
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
@router.callback_query(F.data == "sell_plasma_menu")
async def sell_plasma_menu_callback(cb: CallbackQuery):
    """Меню продажи плазмы"""
    user = await get_user(cb.from_user.id)
    plasma_price = get_plasma_price()
    text = f"""
💰 <b>ПРОДАЖА ПЛАЗМЫ</b>
⚡ <b>Ваша плазма:</b> {user['plasma']} единиц
💰 <b>Текущая цена:</b> {format_money(plasma_price)} за 1 единицу
💎 <b>Примерная стоимость:</b>
• 1 плазма → {format_money(plasma_price)}
• 10 плазмы → {format_money(plasma_price * 10)}
• 100 плазмы → {format_money(plasma_price * 100)}
• Вся плазма → {format_money(plasma_price * user['plasma'])}
📝 <b>Команды для продажи:</b>
- <code>продать плазму 10</code> - продать 10 единиц
- <code>продать плазму все</code> - продать всю плазму
- <code>продать плазму 50</code> - продать 50 единиц
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 10 единиц", callback_data="sell_plasma_10"),
            InlineKeyboardButton(text="💎 50 единиц", callback_data="sell_plasma_50")
        ],
        [
            InlineKeyboardButton(text="💎 100 единиц", callback_data="sell_plasma_100"),
            InlineKeyboardButton(text="💎 Всю плазму", callback_data="sell_plasma_all")
        ],
        [InlineKeyboardButton(text="🔙 Назад к планетам", callback_data="planets_refresh")]
    ])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await cb.answer()
@router.callback_query(F.data.startswith("sell_plasma_"))
async def sell_plasma_callback(cb: CallbackQuery):
    """Продажа плазмы через кнопку"""
    try:
        amount_str = cb.data.split("_")[2]
        uid = cb.from_user.id
        user = await get_user(uid)
        if amount_str == "all":
            amount = user['plasma']
        else:
            amount = int(amount_str)
        if amount <= 0:
            await cb.answer("❌ Недостаточно плазмы")
            return
        success, plasma_sold, money_received, price_per_unit = await sell_plasma(uid, amount)
        if success:
            updated_user = await get_user(uid)
            await cb.message.edit_text(
                f"✅ <b>Плазма продана!</b>\n\n"
                f"💎 Продано: {plasma_sold} единиц плазмы\n"
                f"💰 Цена за единицу: {format_money(price_per_unit)}\n"
                f"💵 Получено: {format_money(money_received)}\n\n"
                f"⚡ Осталось плазмы: {updated_user['plasma']}\n"
                f"💰 Новый баланс: {format_money(updated_user['balance'])}",
                parse_mode="HTML"
            )
            await cb.answer(f"✅ Получено {format_money(money_received)}!")
        else:
            await cb.answer(f"❌ {money_received}")
    except Exception as e:
        logger.error(f"Ошибка sell_plasma_callback: {e}")
        await cb.answer("❌ Ошибка продажи")
@router.message(F.text.lower() == "продать биткоины")
@router.message(F.text.lower() == "продать все биткоины")
@router.message(F.text.lower() == "продать весь биткоин")
async def sell_all_btc_cmd(msg: Message):
    """Продать все биткоины"""
    success, btc_sold, usd_received = await sell_bitcoin(msg.from_user.id, None)
    if success:
        user = await get_user(msg.from_user.id)
        await msg.reply(
            f"✅ <b>ВСЕ БИТКОИНЫ ПРОДАНЫ!</b>\n\n"
            f"💰 <b>Продано:</b> {btc_sold:.8f} BTC\n"
            f"💵 <b>Получено:</b> {format_money(usd_received)}$\n"
            f"💳 <b>Новый баланс:</b> {format_money(user['balance'])}",
            parse_mode="HTML"
        )
    else:
        await msg.reply(f"❌ {usd_received}", parse_mode="HTML")
@router.message(F.text.lower() == "сбросить время")
async def reset_time_cmd(msg: Message):
    """Сбросить время майнинга (для теста)"""
    uid = msg.from_user.id
    current_time = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        # Ставим время на 1 час назад
        await db.execute("UPDATE users SET last_mining_claim = ? WHERE id = ?",
                       (current_time - 3600, uid))
        await db.commit()
    await msg.reply(
        "🕐 <b>Время сброшено на 1 час назад!</b>\n\n"
        "Теперь майнинг должен работать.\n"
        "Проверьте через 2 минуты командой:\n"
        "<code>забрать биткоины</code>",
        parse_mode="HTML"
    )
@router.message(F.text.lower() == "статус майнинга")
async def mining_status_cmd(msg: Message):
    """Детальный статус майнинга"""
    uid = msg.from_user.id
    user = await get_user(uid)
    current_time = int(time.time())
    last_claim = user.get('last_mining_claim', current_time)
    time_passed = current_time - last_claim
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    btc_per_minute = btc_per_hour / 60
    btc_per_second = btc_per_minute / 60
    # Сколько уже должно было накопиться
    btc_accumulated = btc_per_hour * (time_passed / 3600)
    # Когда будет 0.001 BTC (минимальная сумма для сбора)
    if btc_per_hour > 0:
        time_to_001 = (0.001 / btc_per_hour) * 3600
        minutes_to_001 = int(time_to_001 // 60)
        seconds_to_001 = int(time_to_001 % 60)
    else:
        time_to_001 = 0
        minutes_to_001 = 0
        seconds_to_001 = 0
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сбросить время", callback_data="force_fix_now"),
         InlineKeyboardButton(text="💰 Забрать BTC", callback_data="mining_claim")],
        [InlineKeyboardButton(text="⛏️ Панель майнинга", callback_data="show_mining")]
    ])
    text = f"""
🔍 <b>СТАТУС МАЙНИНГА</b>
📊 <b>Ферма:</b>
• Видеокарт: {user['mining_gpu_count']} шт.
• Уровень: {user['mining_gpu_level']}/5
• Хешрейт: {hashrate:,.0f} MH/s
💰 <b>Доходность:</b>
• В секунду: {btc_per_second:.10f} BTC
• В минуту: {btc_per_minute:.8f} BTC
• В час: {btc_per_hour:.6f} BTC
• В день: {btc_per_hour * 24:.4f} BTC
⏳ <b>Время:</b>
• Последний сброс: {time.ctime(last_claim)}
• Прошло: {time_passed} секунд ({time_passed/60:.1f} минут)
• Накоплено (расчетно): {btc_accumulated:.8f} BTC
📈 <b>Прогноз:</b>
• 0.001 BTC будет через: {minutes_to_001} мин {seconds_to_001} сек
• 0.01 BTC будет через: {int((0.01 / btc_per_hour) * 3600 // 60)} минут
💎 <b>Текущий баланс BTC:</b> {user['bitcoin']:.8f}
"""
    await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)
# Команда для просмотра баланса BTC
@router.message(F.text.lower() == "мои биткоины")
@router.message(F.text.lower() == "биткоины")
@router.message(F.text.lower() == "btc")
async def my_btc_cmd(msg: Message):
    """Показать мои биткоины"""
    user = await get_user(msg.from_user.id)
    btc_price = BitcoinMining.get_bitcoin_price()
    total_value = user['bitcoin'] * btc_price
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Продать BTC", callback_data="mining_sell")],
        [InlineKeyboardButton(text="⛏️ Майнинг ферма", callback_data="show_mining")]
    ])
    await msg.reply(
        f"₿ <b>ВАШИ БИТКОИНЫ</b>\n\n"
        f"💰 <b>Количество:</b> {user['bitcoin']:.8f} BTC\n"
        f"💵 <b>Стоимость:</b> {format_money(int(total_value))}$\n"
        f"📈 <b>Курс BTC:</b> {format_money(int(btc_price))}$ за 1 BTC\n\n"
        f"💡 <b>Команды для продажи:</b>\n"
        f"- <code>продать биткоин все</code>\n"
        f"- <code>продать биткоин 0.1</code>\n"
        f"- <code>продать биткоины</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
@router.callback_query(F.data == "no_action")
async def no_action_callback(cb: CallbackQuery):
    """Обработчик для заблокированных кнопок (когда нельзя собирать прибыль)"""
    await cb.answer("⏳ Подождите, пока истечет время до следующего сбора!", show_alert=True)
# ========== ТЕСТОВЫЙ ХЕНДЛЕР ==========
@router.message(F.text.lower() == "тест")
async def test_handler(msg: Message):
    """Тестовый хендлер для проверки работы бота"""
    await msg.answer("✅ Тест работает! Бот отвечает.")
@router.message(F.text.lower() == "проверитьбаланс")
async def check_balance_test(msg: Message):
    """Тестовая команда для проверки баланса"""
    uid = msg.from_user.id
    # Проверяем 3 раза подряд (как было раньше)
    for i in range(1, 4):
        user = await get_user(uid)
        await msg.reply(
            f"🔍 Проверка #{i}:\n"
            f"💰 Баланс: {user['balance']:,}\n"
            f"₿ BTC: {user['bitcoin']:.6f}\n"
            f"⚡ Плазма: {user['plasma']}\n"
            f"⏰ Время: {time.time()}"
        )
        await asyncio.sleep(1)  # Пауза 1 секунда
    await msg.reply("✅ Проверка завершена. Баланс не должен меняться сам по себе!")
async def check_mining_debug(uid: int):
    """Детальная диагностика майнинга"""
    user = await get_user(uid)
    text = f"""
🔍 <b>ДИАГНОСТИКА МАЙНИНГА</b>
👤 <b>Пользователь:</b> {uid}
📊 <b>Данные из БД:</b>
• Видеокарт: {user['mining_gpu_count']}
• Уровень: {user['mining_gpu_level']}
• BTC баланс: {user['bitcoin']:.8f}
• Последний сбор: {user.get('last_mining_claim', 0)}
• Время последнего сбора: {time.ctime(user.get('last_mining_claim', 0))}
⚡ <b>Расчеты:</b>
• Хешрейт: {BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level']):,.0f} MH/s
• BTC/час: {BitcoinMining.calculate_btc_per_hour(BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])):.8f}
🕐 <b>Время:</b>
• Текущее: {time.time()} ({time.ctime()})
• Прошло с последнего сбора: {time.time() - user.get('last_mining_claim', time.time()):.0f} сек
• Часов: {(time.time() - user.get('last_mining_claim', time.time())) / 3600:.2f}
💡 <b>Потенциальные BTC:</b>
• За прошедшее время: {BitcoinMining.calculate_btc_per_hour(BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])) * ((time.time() - user.get('last_mining_claim', time.time())) / 3600):.8f}
"""
    return text
# ========== ФИКС-КОМАНДЫ ==========
@router.message(F.text.lower() == "фиксмайнинг")
async def fix_mining_cmd(msg: Message):
    """Экстренный фикс майнинга"""
    uid = msg.from_user.id
    current_time = int(time.time())
    # Устанавливаем время на 2 часа назад
    two_hours_ago = current_time - (2 * 3600)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_mining_claim = ? WHERE id = ?",
                       (two_hours_ago, uid))
        await db.commit()
    await msg.reply(
        f"✅ <b>Майнинг пофикшен!</b>\n\n"
        f"🕐 Время установлено на 2 часа назад\n"
        f"⏳ Теперь у вас должно быть BTC\n\n"
        f"Попробуйте: <code>собрать биткоины</code>",
        parse_mode="HTML"
    )
@router.message(F.text.lower() == "дебагмайнинг")
async def debug_mining_cmd(msg: Message):
    """Дебаг майнинга"""
    uid = msg.from_user.id
    user = await get_user(uid)
    current_time = int(time.time())
    last_claim = user.get('last_mining_claim', 0)
    time_passed = current_time - last_claim
    hashrate = BitcoinMining.calculate_hashrate(user['mining_gpu_count'], user['mining_gpu_level'])
    btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
    potential_btc = btc_per_hour * (time_passed / 3600)
    text = f"""
🔧 <b>ДЕБАГ МАЙНИНГА</b>
📊 <b>Данные:</b>
• Видеокарт: {user['mining_gpu_count']}
• Уровень: {user['mining_gpu_level']}
• Текущий BTC: {user['bitcoin']:.8f}
• last_mining_claim: {last_claim}
• Текущее время: {current_time}
• Разница: {time_passed} сек ({time_passed/60:.1f} мин)
⚡ <b>Расчеты:</b>
• Хешрейт: {hashrate:,.0f} MH/s
• BTC/час: {btc_per_hour:.8f}
• Потенциально: {potential_btc:.8f} BTC
💡 <b>Решение:</b>
"""
    if time_passed < 60:
        text += f"❌ Слишком мало времени: {time_passed} сек < 60 сек\n"
        text += f"Нужно подождать: {60 - time_passed} секунд"
    else:
        text += f"✅ Время прошло достаточно: {time_passed} сек\n"
        text += f"Должно накопиться: {potential_btc:.8f} BTC"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сбросить время", callback_data="reset_mining_time")]
    ])
    await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)
@router.callback_query(F.data == "reset_mining_time")
async def reset_mining_time_callback(cb: CallbackQuery):
    """Сбросить время майнинга через callback"""
    uid = cb.from_user.id
    current_time = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_mining_claim = ? WHERE id = ?",
                       (current_time - 7200, uid))  # 2 часа назад
        await db.commit()
    await cb.answer("✅ Время сброшено на 2 часа назад!")
    await debug_mining_cmd(cb.message)
    # ========== ЭКСТРЕННЫЕ КОМАНДЫ ==========
@router.message(F.text.lower() == "тест123")
async def test123_cmd(msg: Message):
    """Тестовая команда 123"""
    await msg.reply("✅ Бот жив!")
@router.message(F.text.lower() == "сброс")
async def reset_all_cmd(msg: Message):
    """Сброс всего майнинга"""
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Время на 5 часов назад
            new_time = int(time.time()) - 18000
            # Обновляем данные пользователя
            await db.execute("""
                UPDATE users
                SET last_mining_claim = ?,
                    bitcoin = 0.1,
                    mining_gpu_count = CASE WHEN mining_gpu_count = 0 THEN 5 ELSE mining_gpu_count END,
                    mining_gpu_level = CASE WHEN mining_gpu_level = 0 THEN 1 ELSE mining_gpu_level END
                WHERE id = ?
            """, (new_time, uid))
    except Exception as e:
        pass
@router.message(F.text.lower() == "майнинг2")
async def mining2_cmd(msg: Message):
    try:
        uid = msg.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT mining_gpu_count, bitcoin, mining_gpu_level, balance FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
        if row:
            # Рассчитываем хешрейт для информации
            hashrate = BitcoinMining.calculate_hashrate(row['mining_gpu_count'], row['mining_gpu_level'])
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            btc_price = BitcoinMining.get_bitcoin_price()
            await msg.reply(
                f"⛏️ <b>МАЙНИНГ 2.0</b>\n\n"
                f"🎮 Видеокарт: {row['mining_gpu_count']} (ур. {row['mining_gpu_level']})\n"
                f"⚡ Хешрейт: {hashrate:,.0f} MH/s\n"
                f"₿ BTC: {row['bitcoin']:.8f}\n"
                f"💰 Стоимость: {format_money(int(row['bitcoin'] * btc_price))}$\n"
                f"📈 Доход/час: {btc_per_hour:.6f} BTC\n\n"
                f"💳 Баланс: {format_money(row['balance'])}\n\n"
                f"💡 Команды:\n"
                f"- <code>сброс</code> - сбросить всё\n"
                f"- <code>забрать2</code> - забрать BTC\n"
                f"- <code>купитьгпу</code> - купить 10 карт\n"
                f"- <code>майнинг</code> - основная панель",
                parse_mode="HTML"
            )
        else:
            await msg.reply("❌ Пользователь не найден")
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
@router.message(F.text.lower() == "забрать2")
async def collect2_cmd(msg: Message):
    """Забрать BTC v2"""
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Получаем BTC пользователя
            cursor = await db.execute("SELECT bitcoin FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if not row:
                await msg.reply("❌ Пользователь не найден")
                return
            btc = row['bitcoin'] or 0
            # Если BTC нет, даем немного для теста
            if btc <= 0:
                btc = 0.05
                await db.execute("UPDATE users SET bitcoin = ? WHERE id = ?", (btc, uid))
            # Выдаем деньги (1 BTC = 100,000,000$)
            reward = int(btc * 100_000_000)
            current_time = int(time.time())
            # Обновляем баланс и сбрасываем BTC
            await db.execute("""
                UPDATE users
                SET balance = balance + ?,
                    bitcoin = 0,
                    last_mining_claim = ?
                WHERE id = ?
            """, (reward, current_time, uid))
            await db.commit()
            # Получаем новый баланс для отображения
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            new_balance_row = await cursor.fetchone()
            new_balance = new_balance_row['balance'] if new_balance_row else reward
            await msg.reply(
            f"✅ ЗАБРАНО {btc:.8f} BTC!\n\n"
            f"💰 <b>Начислено:</b> {reward:,}$\n"
            f"💳 <b>Новый баланс:</b> {format_money(new_balance)}\n\n"
            f"🎮 BTC обнулены, майнинг продолжается!"
        )
    except Exception as e:
        logger.error(f"Ошибка в collect2_cmd: {e}")
        await msg.reply(f"❌ Ошибка: {str(e)[:100]}")
@router.message(F.text.lower() == "купитьгпу")
async def buy_gpu_simple(msg: Message):
    """Купить видеокарты"""
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Сначала получаем текущие данные пользователя
            cursor = await db.execute(
                "SELECT mining_gpu_count, mining_gpu_level, balance FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if not row:
                await msg.reply("❌ Пользователь не найден")
                return
            current_gpu_count = row['mining_gpu_count'] or 0
            current_gpu_level = row['mining_gpu_level'] or 1
            # Добавляем 10 видеокарт уровня 1
            new_gpu_count = current_gpu_count + 10
            # Обновляем количество видеокарт и уровень если нужно
            await db.execute("""
                UPDATE users
                SET mining_gpu_count = ?,
                    mining_gpu_level = CASE WHEN mining_gpu_level = 0 THEN 1 ELSE mining_gpu_level END
                WHERE id = ?
            """, (new_gpu_count, uid))
            await db.commit()
            # Рассчитываем новую доходность для информации
            hashrate = BitcoinMining.calculate_hashrate(new_gpu_count, current_gpu_level)
            btc_per_hour = BitcoinMining.calculate_btc_per_hour(hashrate)
            btc_price = BitcoinMining.get_bitcoin_price()
            usd_per_hour = btc_per_hour * btc_price
        await msg.reply(
            f"✅ Куплено 10 видеокарт!\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Было: {current_gpu_count} видеокарт\n"
            f"• Стало: {new_gpu_count} видеокарт\n"
            f"• Уровень: {current_gpu_level}/5\n\n"
            f"⚡ <b>Новые показатели:</b>\n"
            f"• Хешрейт: {hashrate:,.0f} MH/s\n"
            f"• BTC/час: {btc_per_hour:.6f}\n"
            f"• $/час: {format_money(int(usd_per_hour))}\n\n"
            f"💡 Теперь майнинг будет приносить больше BTC!"
        )
    except Exception as e:
        logger.error(f"Ошибка в buy_gpu_simple: {e}")
        await msg.reply(f"❌ Ошибка: {str(e)[:100]}")
# ВСТАВИТЬ ПЕРЕД async def main():
# ========== ЗАПУСК ЛОТЕРЕЙНОЙ СИСТЕМЫ ==========
async def lottery_scheduler():
    """Планировщик для автоматического розыгрыша лотереи"""
    while True:
        try:
            # Проверяем каждую минуту
            await asyncio.sleep(60)
            # Проверяем, прошло ли 24 часа
            if await reset_lottery():
                # Если лотерея сбросилась (прошел день), проводим розыгрыш
                winners = await draw_lottery()
                if winners:
                    # Отправляем уведомление в чат
                    logger.info("🎰 Проведен автоматический розыгрыш лотереи")
        except Exception as e:
            logger.error(f"Ошибка в планировщике лотереи: {e}")
@router.message(F.text.lower() == "дебагбаланс")
async def debug_balance_cmd(msg: Message):
    """Дебаг баланса"""
    uid = msg.from_user.id
    # Делаем несколько запросов подряд
    balances = []
    for i in range(5):
        user = await get_user(uid)
        balances.append(user['balance'])
        await asyncio.sleep(0.1)
        await msg.reply(
        f"🔍 ДЕБАГ БАЛАНСА {uid}\n\n"
        f"Балансы за 5 запросов:\n"
        f"1. {balances[0]:,}\n"
        f"2. {balances[1]:,}\n"
        f"3. {balances[2]:,}\n"
        f"4. {balances[3]:,}\n"
        f"5. {balances[4]:,}\n\n"
        f"Разные? {'ДА' if len(set(balances)) > 1 else 'НЕТ'}"
        )
@router.message(F.text.lower() == "синхронизация")
async def sync_cmd(msg: Message):
    """Принудительная синхронизация баланса"""
    uid = msg.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем ТОЧНЫЙ баланс из БД
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            row = await cursor.fetchone()
            if row:
                real_balance = row[0]
                await msg.reply(
                    f"✅ ТОЧНЫЙ баланс из БД: {real_balance:,}\n\n"
                    f"Если в других командах показывается другое число - это ошибка."
                )
            else:
                await msg.reply("❌ Пользователь не найден")
    except Exception as e:
        await msg.reply(f"❌ Ошибка: {e}")
async def periodic_world_events():
    """Periodic world events tick."""
    while True:
        try:
            await check_and_start_world_event()
        except Exception as e:
            logger.error(f"Error in periodic_world_events: {e}")
        await asyncio.sleep(3600)

async def periodic_population_growth():
    """Hourly population growth tick for all countries."""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT id FROM countries")
                rows = await cursor.fetchall()
            for row in rows:
                await update_population(row[0])
        except Exception as e:
            logger.error(f"Error in periodic_population_growth: {e}")
        await asyncio.sleep(3600)

async def main():

    # Инициализируем БД
    await init_db()
    # Создаем бота и диспетчер
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    # Добавляем роутер
    dp.include_router(router)
    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем очистку старых игр
    asyncio.create_task(periodic_cleanup())
    # Запускаем проверку мировых событий
    asyncio.create_task(periodic_world_events())
    asyncio.create_task(periodic_population_growth())
    # Логируем запуск
    logger.info("✅ Бот запущен! Используйте команды:")
    logger.info("  /start или 'меню' - главное меню")
    logger.info("  'профиль' - ваш профиль")
    logger.info("  'бонус' - получить бонус 1-5М")
    logger.info("  'работа' - заработать 100k-1М")
    logger.info("  'страна' - ваша страна")
    logger.info("  'страны' - список стран")
    logger.info("  'кланы' - список кланов")
    logger.info("  'войны' - текущие войны")
    logger.info("  'боссы' - рейды на боссов")
    try:
        # Запускаем поллинг
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске поллинга: {e}")
        raise
    finally:
        # Закрываем сессию бота для избежания предупреждений
        await bot.close()
async def update_population(country_id):
    import random
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT population, last_population_tick, happiness FROM countries WHERE id = ?", (country_id,))
        row = await cursor.fetchone()
        if not row:
            return
        population = row[0]
        last_tick = row[1]
        happiness = row[2]
        if last_tick == 0:
            await db.execute("UPDATE countries SET last_population_tick = ? WHERE id = ?", (now, country_id))
            await db.commit()
            return
        days_passed = (now - last_tick) / 86400
        if days_passed < 1:
            return
        # Получить hospital_level
        cursor = await db.execute("SELECT level FROM country_buildings WHERE country_id = ? AND building_type = 'hospital'", (country_id,))
        hospital_row = await cursor.fetchone()
        hospital_level = hospital_row[0] if hospital_row else 0
        hospital_bonus = hospital_level * 0.1
        daily_births = population * 0.003 * (1 + happiness / 200) * (1 + hospital_bonus) * random.uniform(0.8, 1.2)
        births = daily_births * days_passed
        deaths = population * 0.001 * days_passed
        new_population = population + births - deaths
        new_population = max(0, int(new_population))
        await db.execute("UPDATE countries SET population = ?, last_population_tick = ? WHERE id = ?", (new_population, now, country_id))
        # Проверить jobs
        cursor = await db.execute("SELECT jobs_available FROM countries WHERE id = ?", (country_id,))
        jobs_row = await cursor.fetchone()
        jobs = jobs_row[0] if jobs_row else 0
        if new_population > jobs and jobs > 0:
            new_birth_rate = 0.003 * 0.5
            new_happiness = max(0, happiness - 10)
            await db.execute("UPDATE countries SET birth_rate = ?, happiness = ? WHERE id = ?", (new_birth_rate, new_happiness, country_id))
        await db.commit()
        await update_country_stats(country_id)
async def calculate_jobs_available(country_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
        buildings = await cursor.fetchall()
        jobs = 0
        for btype, level in buildings:
            if btype in BUILDING_CONFIG and level > 0:
                jobs += BUILDING_CONFIG[btype]['jobs_provided'] * level
        businesses, _ = await get_country_businesses(db, country_id)
        jobs += calculate_business_jobs(businesses)
        await db.execute("UPDATE countries SET jobs_available = ? WHERE id = ?", (jobs, country_id))
        await db.commit()
    return jobs
async def update_country_stats(country_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT tax_rate FROM countries WHERE id = ?", (country_id,))
        tax_row = await cursor.fetchone()
        tax_rate = tax_row[0] if tax_row else 0.1
        cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
        buildings = await cursor.fetchall()
        happiness = 70
        literacy = 50
        crime = 20
        for btype, level in buildings:
            if btype in BUILDING_CONFIG:
                effects = BUILDING_CONFIG[btype]['effects']
                happiness += effects.get('happiness_bonus', 0) * level
                literacy += effects.get('literacy_bonus', 0) * level
                crime -= effects.get('crime_reduction', 0) * level
        # Применить налоги
        if tax_rate > 0.1:
            happiness_penalty = (tax_rate - 0.1) * 50
            crime_bonus = (tax_rate - 0.1) * 20
            happiness -= happiness_penalty
            crime += crime_bonus
        happiness = max(0, min(100, happiness))
        literacy = max(0, min(100, literacy))
        crime = max(0, min(100, crime))
        await db.execute("UPDATE countries SET happiness = ?, literacy = ?, crime = ? WHERE id = ?", (happiness, literacy, crime, country_id))
        await db.commit()
# ========== НОВЫЕ ХЕНДЛЕРЫ ДЛЯ СТРАН, КЛАНОВ, ВОЙН, БОССОВ ==========
async def build_countries_view():
    max_len = 3500
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT c.id, c.name, c.level, c.owner_user_id, c.treasury, c.stability, c.tax_rate, c.population, c.employment_rate, c.literacy, cl.bonus_income, cl.name as clan_name
            FROM countries c
            LEFT JOIN clan_members cm ON c.owner_user_id = cm.user_id
            LEFT JOIN clans cl ON cm.clan_id = cl.id
            ORDER BY c.level DESC, c.treasury DESC
        """)
        countries = await cursor.fetchall()
    if not countries:
        text = "🌍 <b>СТРАНЫ</b>\n\nСтраны еще не созданы."
        return text, None
    text = "🌍 <b>Список стран</b>\n\n"
    keyboard = []
    for country in countries:
        owner = "Свободна" if not country['owner_user_id'] else f"Владелец: {country['owner_user_id']}"
        businesses, _ = await get_country_businesses(db, country['id'])
        biz_min_day, biz_max_day = calculate_business_income_range_per_day(businesses)
        base_income_per_day = int(calculate_country_income_hour(country['level'], country['stability'], 0.0) * 24)
        total_min_day = base_income_per_day + biz_min_day
        total_max_day = base_income_per_day + biz_max_day
        income_line = f"{total_min_day:,} - {total_max_day:,}" if biz_max_day > 0 else f"{base_income_per_day:,}"
        text += f"🏳️ <b>{country['name']}</b> (ур.{country['level']})\n"
        text += f"👤 {owner}\n"
        text += f"👥 Население: {country['population']:,}\n"
        text += f"💰 Казна: {country['treasury']:,}\n"
        text += f"📈 Доход/день: {income_line}\n"
        text += f"🛡️ Стабильность: {country['stability']}%\n\n"
        keyboard.append([InlineKeyboardButton(text=f"🏳️ {country['name']}", callback_data=f"view_country_{country['id']}")])
        if len(text) > max_len:
            text += "?\n\n?? <i>?????? ??????, ?????? ?? ??? ??? ?????? ??????.</i>\n"
            break
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_clans_view():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT c.id, c.name, c.owner_user_id, c.treasury_money, c.treasury_plasma, c.bonus_income,
                   COUNT(cm.user_id) as members_count
            FROM clans c
            LEFT JOIN clan_members cm ON c.id = cm.clan_id
            GROUP BY c.id ORDER BY members_count DESC
        """)
        clans = await cursor.fetchall()
    if not clans:
        text = "🏰 <b>Кланы</b>\n\nКланов еще нет."
        keyboard = [
            [InlineKeyboardButton(text="➕ Создать клан", callback_data="create_clan")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    text = "🏰 <b>Список кланов</b>\n\n"
    keyboard = []
    for clan in clans:
        text += f"⚔️ <b>{clan['name']}</b>\n"
        text += f"👑 Владелец: {clan['owner_user_id']}\n"
        text += f"👥 Участники: {clan['members_count']}\n"
        text += f"💰 Бонус дохода: +{clan['bonus_income']*100:.0f}%\n"
        text += f"💰 Казна: {clan['treasury_money']:,}\n"
        text += f"🔷 Плазма: {clan['treasury_plasma']}\n\n"
        keyboard.append([InlineKeyboardButton(text=f"⚔️ {clan['name']}", callback_data=f"view_clan_{clan['id']}")])
    keyboard.append([InlineKeyboardButton(text="➕ Создать клан", callback_data="create_clan")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_clan_view(clan_id: int, uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT c.*, COUNT(cm.user_id) as members_count
            FROM clans c
            LEFT JOIN clan_members cm ON c.id = cm.clan_id
            WHERE c.id = ?
            GROUP BY c.id
        """, (clan_id,))
        clan = await cursor.fetchone()
        if not clan:
            return None, None
        cursor = await db.execute(
            "SELECT clan_id, role FROM clan_members WHERE user_id = ?",
            (uid,)
        )
        my_row = await cursor.fetchone()
        my_clan_id = my_row["clan_id"] if my_row else None
        my_role = my_row["role"] if my_row else None
        cursor = await db.execute(
            "SELECT 1 FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
            (clan_id, uid)
        )
        has_request = await cursor.fetchone()
        req_count = 0
        if clan["owner_user_id"] == uid:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM clan_join_requests WHERE clan_id = ?",
                (clan_id,)
            )
            row = await cursor.fetchone()
            req_count = int(row[0] or 0)
    status_text = "открытый" if clan["is_open"] else "закрытый"
    text = "🏰 <b>Клан</b>\n\n"
    text += f"Название: <b>{clan['name']}</b>\n"
    text += f"Статус: {status_text}\n"
    text += f"Участников: {clan['members_count']}\n"
    text += f"Бонус дохода: +{clan['bonus_income']*100:.0f}%\n"
    text += f"Казна: {clan['treasury_money']:,}\n"
    text += f"Плазма: {clan['treasury_plasma']}\n\n"
    keyboard = []
    if my_clan_id == clan_id:
        text += "Вы состоите в этом клане.\n"
        if my_role == "owner":
            text += f"Заявок: {req_count}\n"
            keyboard.append([InlineKeyboardButton(
                text="⚙️ Открыть/закрыть",
                callback_data=f"clan_toggle_{clan_id}"
            )])
            keyboard.append([InlineKeyboardButton(
                text="📨 Заявки",
                callback_data=f"clan_requests_{clan_id}"
            )])
            keyboard.append([InlineKeyboardButton(
                text="🗑️ Удалить клан",
                callback_data=f"clan_delete_{clan_id}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                text="Покинуть клан",
                callback_data=f"clan_leave_{clan_id}"
            )])
    else:
        if my_clan_id:
            text += "Вы уже в другом клане.\n"
        else:
            if clan["is_open"]:
                keyboard.append([InlineKeyboardButton(
                    text="✅ Вступить",
                    callback_data=f"join_clan_{clan_id}"
                )])
            else:
                if has_request:
                    text += "Заявка уже отправлена.\n"
                else:
                    keyboard.append([InlineKeyboardButton(
                        text="📨 Подать заявку",
                        callback_data=f"request_clan_{clan_id}"
                    )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к кланам", callback_data="show_clans")])
    keyboard.append([InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_wars_view(uid: int):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        country_id = await get_user_country_id(db, uid)
        if not country_id:
            text = "⚔️ <b>Войны</b>\n\nУ вас нет страны."
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
            return text, reply_markup
        active_war = await get_active_war_for_country(db, country_id)
        winner_user_id = None
        if active_war:
            await db.execute("BEGIN IMMEDIATE")
            result = await process_war_rounds(db, active_war["id"])
            await db.commit()
            if result["ended"]:
                winner_user_id = result["winner_user_id"]
            cursor = await db.execute("SELECT * FROM wars WHERE id = ?", (active_war["id"],))
            active_war = await cursor.fetchone()
    if winner_user_id:
        await check_and_award_titles(winner_user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT attacker_country_id, defender_country_id
            FROM wars
            WHERE status = 'active'
        """)
        active_rows = await cursor.fetchall()
        active_set = set()
        for row in active_rows:
            active_set.add(row["attacker_country_id"])
            active_set.add(row["defender_country_id"])
        cursor = await db.execute("""
            SELECT id, name, population, last_war_end_ts
            FROM countries
            WHERE owner_user_id IS NOT NULL AND owner_user_id != ?
            ORDER BY level DESC, population DESC
            LIMIT 30
        """, (uid,))
        targets = await cursor.fetchall()
    text = "⚔️ <b>Войны</b>\n\n"
    keyboard = []
    allow_attack = True
    if active_war and active_war["status"] == "active":
        text += "🛡️ У вас есть активная война.\n"
        text += "Нажмите «Смотреть войну» для логов и таймера.\n\n"
        keyboard.append([InlineKeyboardButton(text="📜 Смотреть войну", callback_data="view_war")])
        allow_attack = False
    if not targets:
        text += "Нет доступных целей."
    else:
        text += "Доступные цели:\n"
        for t in targets:
            status = "готово"
            if t["id"] in active_set:
                status = "в войне"
            else:
                cooldown_left = max(0, (t["last_war_end_ts"] or 0) + WAR_COOLDOWN - now)
                if cooldown_left > 0:
                    hours = cooldown_left // 3600
                    minutes = (cooldown_left % 3600) // 60
                    status = f"кд {hours}ч {minutes}м"
            text += f"• {t['name']} (люди {t['population']:,}) — {status}\n"
            if status == "готово" and allow_attack:
                keyboard.append([InlineKeyboardButton(
                    text=f"⚔️ Атаковать {t['name']}",
                    callback_data=f"war_attack_{t['id']}"
                )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_war_view(uid: int):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        country_id = await get_user_country_id(db, uid)
        if not country_id:
            text = "⚔️ <b>Война</b>\n\nУ вас нет страны."
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="show_wars")]
            ])
            return text, reply_markup
        active_war = await get_active_war_for_country(db, country_id)
        winner_user_id = None
        if active_war:
            await db.execute("BEGIN IMMEDIATE")
            result = await process_war_rounds(db, active_war["id"])
            await db.commit()
            if result["ended"]:
                winner_user_id = result["winner_user_id"]
            cursor = await db.execute("SELECT * FROM wars WHERE id = ?", (active_war["id"],))
            active_war = await cursor.fetchone()
        if winner_user_id:
            await check_and_award_titles(winner_user_id)
        if not active_war:
            text = "⚔️ <b>Война</b>\n\nАктивных войн нет."
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="show_wars")]
            ])
            return text, reply_markup
        attacker_id = active_war["attacker_country_id"]
        defender_id = active_war["defender_country_id"]
        cursor = await db.execute("SELECT name, population FROM countries WHERE id = ?", (attacker_id,))
        a_row = await cursor.fetchone()
        cursor = await db.execute("SELECT name, population FROM countries WHERE id = ?", (defender_id,))
        d_row = await cursor.fetchone()
        a_name = a_row["name"] if a_row else "?"
        d_name = d_row["name"] if d_row else "?"
        a_people = int(a_row["population"] or 0) if a_row else 0
        d_people = int(d_row["population"] or 0) if d_row else 0
        last_round_at = active_war["last_round_at"] or active_war["started_at"]
        next_round_in = max(0, WAR_ROUND_INTERVAL - (now - last_round_at))
        nr_h = next_round_in // 3600
        nr_m = (next_round_in % 3600) // 60
        text = "⚔️ <b>Война</b>\n\n"
        text += f"{a_name} vs {d_name}\n"
        text += f"Счет раундов: {active_war['attacker_progress']} : {active_war['defender_progress']}\n"
        text += f"Раундов: {active_war['rounds_played']}/{WAR_MAX_ROUNDS}\n"
        text += f"Люди: {a_people:,} vs {d_people:,}\n"
        text += f"След. раунд через: {nr_h}ч {nr_m}м\n\n"
        cursor = await db.execute("""
            SELECT action, power, losses_people, losses_weapons, losses_tech, ts, actor_country_id
            FROM war_logs
            WHERE war_id = ?
            ORDER BY id DESC
            LIMIT 8
        """, (active_war["id"],))
        logs = await cursor.fetchall()
        if logs:
            text += "Последние события:\n"
            for log in logs:
                action = log["action"]
                actor = "Атакующий" if log["actor_country_id"] == attacker_id else "Защитник"
                if action == "round_win":
                    action_text = "победил в раунде"
                elif action == "round_loss":
                    action_text = "проиграл раунд"
                elif action == "round_draw":
                    action_text = "ничья в раунде"
                elif action == "war_end_win":
                    action_text = "победа в войне"
                elif action == "war_end_draw":
                    action_text = "ничья в войне"
                else:
                    action_text = action
                text += (
                    f"• {actor}: {action_text} | "
                    f"потери люд. {log['losses_people']}, "
                    f"оруж. {log['losses_weapons']}, техн. {log['losses_tech']}\n"
                )
        else:
            text += "Событий пока нет."
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к войнам", callback_data="show_wars")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")]
    ])
    return text, reply_markup
async def award_boss_rewards(boss_id: int):
    """Выдать награды за победу над боссом"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            # Получаем топ-3 участников по урону
            cursor = await db.execute("""
                SELECT user_id, damage
                FROM boss_hits
                WHERE boss_id = ? AND damage > 0
                ORDER BY damage DESC
                LIMIT 3
            """, (boss_id,))
            top_participants = await cursor.fetchall()
            # Получаем всех участников с уроном > 0
            cursor = await db.execute("""
                SELECT DISTINCT user_id, damage
                FROM boss_hits
                WHERE boss_id = ? AND damage > 0
            """, (boss_id,))
            all_participants = await cursor.fetchall()
            # Получить эффекты мирового события
            world_effects = await get_world_event_effects()
            boss_buff = world_effects.get('boss_buff', 0.0)
            reward_multiplier = (1 + boss_buff) * BOSS_REWARD_MULTIPLIER
            # Награды за участие
            for participant in all_participants:
                uid = participant['user_id']
                damage = participant['damage']
                money_reward = scale_income(int(min(50000, damage * 5) * reward_multiplier))
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (money_reward, uid))
                await db.execute("UPDATE users SET weapons_shop_unlocked = 1 WHERE id = ?", (uid,))
            # Дополнительные награды топ-3
            rewards = [
                (100000, 5, 2),  # 1 место: деньги, плутоний, плазма
                (75000, 3, 1),   # 2 место
                (50000, 2, 0)    # 3 место
            ]
            for i, participant in enumerate(top_participants):
                if i < len(rewards):
                    uid = participant['user_id']
                    money, plut, plasma = rewards[i]
                    money *= reward_multiplier
                    plut *= reward_multiplier
                    plasma *= reward_multiplier
                    money = scale_income(int(money))
                    plut = scale_income(int(plut))
                    plasma = scale_income(int(plasma))
                    await db.execute("UPDATE users SET balance = balance + ?, plasma = plasma + ? WHERE id = ?",
                                   (money, plasma, uid))
                    # Плазма не добавлена, но предположим есть поле для плазмы
            await db.commit()
            logger.info(f"Выданы награды за босса {boss_id}: {len(all_participants)} участников")
    except Exception as e:
        logger.error(f"Ошибка award_boss_rewards: {e}")
def build_bosses_view():
    text = (
        "👹 <b>Боссы</b>\n\n"
        "Рейды на боссов будут доступны в следующих обновлениях."
    )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    return text, reply_markup
async def ensure_active_bosses(db: aiosqlite.Connection):
    now = int(time.time())
    active_bosses = []
    for template in BOSS_TEMPLATES:
        tier = template["tier"]
        cursor = await db.execute("""
            SELECT * FROM bosses
            WHERE status = 'active' AND tier = ? AND ends_at > ?
            ORDER BY spawned_at DESC
            LIMIT 1
        """, (tier, now))
        boss = await cursor.fetchone()
        if not boss:
            spawned_at = now
            ends_at = now + BOSS_LIFETIME
            cursor = await db.execute("""
                INSERT INTO bosses (name, tier, max_hp, hp, attack_power, status, phase, spawned_at, ends_at, level)
                VALUES (?, ?, ?, ?, ?, 'active', 1, ?, ?, 1)
            """, (
                template["name"],
                template["tier"],
                template["max_hp"],
                template["max_hp"],
                template["attack_power"],
                spawned_at,
                ends_at,
            ))
            boss_id = cursor.lastrowid
            cursor = await db.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
            boss = await cursor.fetchone()
        active_bosses.append(boss)
    await db.commit()
    return active_bosses
async def get_user_clan_id(db: aiosqlite.Connection, uid: int):
    cursor = await db.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (uid,))
    row = await cursor.fetchone()
    return row[0] if row else None
async def get_user_country_id(db: aiosqlite.Connection, uid: int):
    cursor = await db.execute("SELECT id FROM countries WHERE owner_user_id = ? LIMIT 1", (uid,))
    row = await cursor.fetchone()
    return row[0] if row else None
async def get_user_country_id_simple(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        return await get_user_country_id(db, uid)
async def get_active_war_for_country(db: aiosqlite.Connection, country_id: int):
    cursor = await db.execute("""
        SELECT *
        FROM wars
        WHERE status = 'active' AND (attacker_country_id = ? OR defender_country_id = ?)
        ORDER BY started_at DESC
        LIMIT 1
    """, (country_id, country_id))
    return await cursor.fetchone()
async def has_active_or_pending_credit(db: aiosqlite.Connection, borrower_id: int) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM credits WHERE borrower_id = ? AND status IN ('pending', 'active')",
        (borrower_id,)
    )
    return bool(await cursor.fetchone())
async def has_defaulted_credit(db: aiosqlite.Connection, borrower_id: int) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM credits WHERE borrower_id = ? AND status = 'defaulted'",
        (borrower_id,)
    )
    return bool(await cursor.fetchone())
async def get_credit_paid_sum(db: aiosqlite.Connection, credit_id: int) -> int:
    cursor = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM credit_payments WHERE credit_id = ?",
        (credit_id,)
    )
    row = await cursor.fetchone()
    return int(row[0] or 0)
async def apply_credit_default_penalties(db: aiosqlite.Connection, borrower_id: int, is_sigma: bool):
    country_id = await get_user_country_id(db, borrower_id)
    if not country_id:
        return 0
    cursor = await db.execute(
        "SELECT stability, tax_rate, treasury FROM countries WHERE id = ?",
        (country_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return 0
    stability, tax_rate, treasury = row
    stability = int(stability or 0)
    tax_rate = float(tax_rate or 0.10)
    treasury = int(treasury or 0)
    if is_sigma:
        stability_penalty = SIGMA_DEFAULT_STABILITY_PENALTY
        tax_penalty = SIGMA_DEFAULT_TAX_PENALTY
        treasury_penalty_pct = SIGMA_DEFAULT_TREASURY_PENALTY_PCT
    else:
        stability_penalty = CREDIT_DEFAULT_STABILITY_PENALTY
        tax_penalty = CREDIT_DEFAULT_TAX_PENALTY
        treasury_penalty_pct = CREDIT_DEFAULT_TREASURY_PENALTY_PCT
    new_stability = max(0, stability - stability_penalty)
    new_tax = max(0.01, tax_rate - tax_penalty)
    fine = int(treasury * treasury_penalty_pct)
    new_treasury = max(0, treasury - fine)
    await db.execute(
        "UPDATE countries SET stability = ?, tax_rate = ?, treasury = ? WHERE id = ?",
        (new_stability, new_tax, new_treasury, country_id)
    )
    return fine
async def mark_debtor_title(db: aiosqlite.Connection, borrower_id: int, now_ts: int):
    await db.execute(
        "INSERT OR IGNORE INTO user_titles (user_id, title_code, obtained_at) VALUES (?, 'debtor', ?)",
        (borrower_id, now_ts)
    )
async def process_credit_defaults(db: aiosqlite.Connection, borrower_id=None) -> int:
    db.row_factory = aiosqlite.Row
    now_ts = int(time.time())
    params = [now_ts]
    query = "SELECT * FROM credits WHERE status = 'active' AND due_at > 0 AND due_at <= ?"
    if borrower_id is not None:
        query += " AND borrower_id = ?"
        params.append(borrower_id)
    cursor = await db.execute(query, params)
    overdue = await cursor.fetchall()
    if not overdue:
        return 0
    for credit in overdue:
        lender_id = int(credit["lender_id"] or 0)
        is_sigma = lender_id == 0
        await db.execute("UPDATE credits SET status = 'defaulted' WHERE id = ?", (credit["id"],))
        fine = await apply_credit_default_penalties(db, int(credit["borrower_id"]), is_sigma)
        await mark_debtor_title(db, int(credit["borrower_id"]), now_ts)
        logger.info(
            f"Credit default: id={credit['id']} borrower={credit['borrower_id']} lender={lender_id} fine={fine} sigma={is_sigma}"
        )
    await db.commit()
    return len(overdue)
async def check_credit_eligibility(db: aiosqlite.Connection, uid: int, amount: int, is_sigma: bool) -> tuple:
    if amount <= 0:
        return False, "\u0421\u0443\u043c\u043c\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0443\u043b\u044f."
    if await has_defaulted_credit(db, uid):
        return False, "\u0423 \u0432\u0430\u0441 \u0434\u0435\u0444\u043e\u043b\u0442 \u043f\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0443. \u041a\u0440\u0435\u0434\u0438\u0442\u044b \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b."
    if await has_active_or_pending_credit(db, uid):
        return False, "\u0423 \u0432\u0430\u0441 \u0443\u0436\u0435 \u0435\u0441\u0442\u044c \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0438\u043b\u0438 \u043e\u0436\u0438\u0434\u0430\u044e\u0449\u0438\u0439 \u043a\u0440\u0435\u0434\u0438\u0442."
    country_id = await get_user_country_id(db, uid)
    if not country_id:
        return False, "\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0441\u0442\u0440\u0430\u043d\u044b."
    cursor = await db.execute("SELECT stability FROM countries WHERE id = ?", (country_id,))
    row = await cursor.fetchone()
    stability = int(row[0] or 0) if row else 0
    if stability < CREDIT_MIN_STABILITY:
        return False, "\u0421\u043b\u0438\u0448\u043a\u043e\u043c \u043d\u0438\u0437\u043a\u0430\u044f \u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c \u0441\u0442\u0440\u0430\u043d\u044b."
    active_war = await get_active_war_for_country(db, country_id)
    if active_war:
        return False, "\u041d\u0435\u043b\u044c\u0437\u044f \u0431\u0440\u0430\u0442\u044c \u043a\u0440\u0435\u0434\u0438\u0442 \u0432\u043e \u0432\u0440\u0435\u043c\u044f \u0432\u043e\u0439\u043d\u044b."
    max_amount = CREDIT_SIGMA_MAX_AMOUNT if is_sigma else CREDIT_MAX_AMOUNT
    if amount < CREDIT_MIN_AMOUNT or amount > max_amount:
        return False, f"\u0421\u0443\u043c\u043c\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u0431\u044b\u0442\u044c \u043e\u0442 {format_money(CREDIT_MIN_AMOUNT)} \u0434\u043e {format_money(max_amount)}."
    return True, ""
async def get_country_army_state(db: aiosqlite.Connection, country_id: int):
    cursor = await db.execute(
        "SELECT owner_user_id, population FROM countries WHERE id = ?",
        (country_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    owner_user_id = row[0]
    people = int(row[1] or 0)
    cursor = await db.execute("""
        SELECT ui.item_id, ui.amount, i.power, i.category
        FROM user_items ui
        JOIN items i ON ui.item_id = i.item_id
        WHERE ui.user_id = ? AND ui.amount > 0
          AND i.category IN ('weapon', 'armor', 'vehicle')
    """, (owner_user_id,))
    rows = await cursor.fetchall()
    weapons_count = 0
    weapons_power = 0
    tech_count = 0
    tech_power = 0
    weapons_items = []
    tech_items = []
    for item_id, amount, power, category in rows:
        amount = int(amount or 0)
        power = int(power or 0)
        if category == "vehicle":
            tech_count += amount
            tech_power += amount * power
            tech_items.append((item_id, amount))
        else:
            weapons_count += amount
            weapons_power += amount * power
            weapons_items.append((item_id, amount))
    return {
        "owner_user_id": owner_user_id,
        "people": people,
        "weapons_count": weapons_count,
        "weapons_power": weapons_power,
        "tech_count": tech_count,
        "tech_power": tech_power,
        "weapons_items": weapons_items,
        "tech_items": tech_items,
    }
def _calc_loss_amount(total: int, pct_range):
    if total <= 0:
        return 0
    pct = random.uniform(pct_range[0], pct_range[1])
    return max(0, int(total * pct))
def _distribute_losses(items, loss_total: int):
    if loss_total <= 0:
        return {}
    total = sum(amount for _, amount in items)
    if total <= 0:
        return {}
    loss_total = min(loss_total, total)
    ratio = loss_total / total
    allocations = []
    for item_id, amount in items:
        raw = amount * ratio
        base = int(raw)
        frac = raw - base
        allocations.append([item_id, amount, base, frac])
    remaining = loss_total - sum(a[2] for a in allocations)
    allocations.sort(key=lambda x: x[3], reverse=True)
    for i in range(remaining):
        allocations[i % len(allocations)][2] += 1
    result = {}
    for item_id, amount, base, _ in allocations:
        if base <= 0:
            continue
        result[item_id] = min(base, amount)
    return result
async def _apply_category_losses(db: aiosqlite.Connection, owner_user_id: int, categories, loss_total: int):
    if loss_total <= 0:
        return 0
    placeholders = ",".join(["?"] * len(categories))
    cursor = await db.execute(
        f"""
        SELECT ui.item_id, ui.amount
        FROM user_items ui
        JOIN items i ON ui.item_id = i.item_id
        WHERE ui.user_id = ? AND ui.amount > 0 AND i.category IN ({placeholders})
        """,
        (owner_user_id, *categories)
    )
    rows = await cursor.fetchall()
    items = [(row[0], int(row[1] or 0)) for row in rows]
    total = sum(amount for _, amount in items)
    if total <= 0:
        return 0
    loss_total = min(loss_total, total)
    losses = _distribute_losses(items, loss_total)
    for item_id, loss in losses.items():
        await db.execute(
            "UPDATE user_items SET amount = amount - ? WHERE user_id = ? AND item_id = ?",
            (loss, owner_user_id, item_id)
        )
    return sum(losses.values())
async def apply_item_losses(db: aiosqlite.Connection, owner_user_id: int, weapons_loss: int, tech_loss: int):
    lost_weapons = await _apply_category_losses(db, owner_user_id, ("weapon", "armor"), weapons_loss)
    lost_tech = await _apply_category_losses(db, owner_user_id, ("vehicle",), tech_loss)
    return lost_weapons, lost_tech
async def process_war_rounds(db: aiosqlite.Connection, war_id: int):
    cursor = await db.execute("SELECT * FROM wars WHERE id = ?", (war_id,))
    war = await cursor.fetchone()
    if not war or war["status"] != "active":
        return {"changed": False, "ended": False, "winner_user_id": None}
    now = int(time.time())
    last_round_at = war["last_round_at"] or war["started_at"]
    rounds_due = (now - last_round_at) // WAR_ROUND_INTERVAL
    rounds_due = min(WAR_MAX_LAZY_ROUNDS, rounds_due)
    if rounds_due <= 0:
        return {"changed": False, "ended": False, "winner_user_id": None}
    attacker_id = war["attacker_country_id"]
    defender_id = war["defender_country_id"]
    attacker_score = war["attacker_progress"]
    defender_score = war["defender_progress"]
    rounds_played = war["rounds_played"]
    ended = False
    winner_country_id = None
    for _ in range(rounds_due):
        if rounds_played >= WAR_MAX_ROUNDS:
            break
        attacker_state = await get_country_army_state(db, attacker_id)
        defender_state = await get_country_army_state(db, defender_id)
        if not attacker_state or not defender_state:
            break
        a_people = attacker_state["people"]
        d_people = defender_state["people"]
        if a_people < WAR_MIN_PEOPLE_ACTIVE or d_people < WAR_MIN_PEOPLE_ACTIVE:
            if a_people < WAR_MIN_PEOPLE_ACTIVE and d_people < WAR_MIN_PEOPLE_ACTIVE:
                winner_country_id = None
            elif a_people < WAR_MIN_PEOPLE_ACTIVE:
                winner_country_id = defender_id
            else:
                winner_country_id = attacker_id
            ended = True
            break
        a_power = a_people + attacker_state["weapons_power"] + attacker_state["tech_power"]
        d_power = d_people + defender_state["weapons_power"] + defender_state["tech_power"]
        a_bonus = await get_country_combat_bonus(db, attacker_id)
        d_bonus = await get_country_combat_bonus(db, defender_id)
        a_power = int(a_power * a_bonus)
        d_power = int(d_power * d_bonus)
        if a_power > d_power:
            outcome = "attacker"
            attacker_score += 1
        elif d_power > a_power:
            outcome = "defender"
            defender_score += 1
        else:
            outcome = "draw"
        if outcome == "attacker":
            a_ranges = WAR_LOSS_RANGES["winner"]
            d_ranges = WAR_LOSS_RANGES["loser"]
            a_action = "round_win"
            d_action = "round_loss"
        elif outcome == "defender":
            a_ranges = WAR_LOSS_RANGES["loser"]
            d_ranges = WAR_LOSS_RANGES["winner"]
            a_action = "round_loss"
            d_action = "round_win"
        else:
            a_ranges = WAR_LOSS_RANGES["draw"]
            d_ranges = WAR_LOSS_RANGES["draw"]
            a_action = "round_draw"
            d_action = "round_draw"
        a_people_loss = _calc_loss_amount(a_people, a_ranges["people"])
        d_people_loss = _calc_loss_amount(d_people, d_ranges["people"])
        a_weapons_loss = _calc_loss_amount(attacker_state["weapons_count"], a_ranges["weapons"])
        d_weapons_loss = _calc_loss_amount(defender_state["weapons_count"], d_ranges["weapons"])
        a_tech_loss = _calc_loss_amount(attacker_state["tech_count"], a_ranges["tech"])
        d_tech_loss = _calc_loss_amount(defender_state["tech_count"], d_ranges["tech"])
        await db.execute(
            """
            UPDATE countries
            SET population = CASE WHEN population >= ? THEN population - ? ELSE 0 END
            WHERE id = ?
            """,
            (a_people_loss, a_people_loss, attacker_id)
        )
        await db.execute(
            """
            UPDATE countries
            SET population = CASE WHEN population >= ? THEN population - ? ELSE 0 END
            WHERE id = ?
            """,
            (d_people_loss, d_people_loss, defender_id)
        )
        a_owner = attacker_state["owner_user_id"]
        d_owner = defender_state["owner_user_id"]
        a_weapons_loss, a_tech_loss = await apply_item_losses(
            db, a_owner, a_weapons_loss, a_tech_loss
        )
        d_weapons_loss, d_tech_loss = await apply_item_losses(
            db, d_owner, d_weapons_loss, d_tech_loss
        )
        ts = int(time.time())
        await db.execute(
            """
            INSERT INTO war_logs
            (war_id, actor_country_id, action, power, losses_people, losses_weapons, losses_tech, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (war_id, attacker_id, a_action, a_power, a_people_loss, a_weapons_loss, a_tech_loss, ts)
        )
        await db.execute(
            """
            INSERT INTO war_logs
            (war_id, actor_country_id, action, power, losses_people, losses_weapons, losses_tech, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (war_id, defender_id, d_action, d_power, d_people_loss, d_weapons_loss, d_tech_loss, ts)
        )
        rounds_played += 1
        last_round_at += WAR_ROUND_INTERVAL
    if not ended and rounds_played >= WAR_MAX_ROUNDS:
        if attacker_score > defender_score:
            winner_country_id = attacker_id
        elif defender_score > attacker_score:
            winner_country_id = defender_id
        else:
            winner_country_id = None
        ended = True
    winner_user_id = None
    if ended:
        tribute_amount = 0
        if winner_country_id:
            loser_country_id = defender_id if winner_country_id == attacker_id else attacker_id
            cursor = await db.execute(
                "SELECT treasury, owner_user_id FROM countries WHERE id = ?",
                (loser_country_id,)
            )
            loser_row = await cursor.fetchone()
            loser_treasury = int(loser_row[0] or 0) if loser_row else 0
            loser_owner_id = loser_row[1] if loser_row else None
            pct = random.uniform(WAR_TRIBUTE_PCT_RANGE[0], WAR_TRIBUTE_PCT_RANGE[1])
            tribute_amount = min(WAR_TRIBUTE_CAP, int(loser_treasury * pct))
            tribute_amount = min(tribute_amount, loser_treasury)
            if tribute_amount > 0:
                await db.execute(
                    "UPDATE countries SET treasury = treasury - ? WHERE id = ?",
                    (tribute_amount, loser_country_id)
                )
                await db.execute(
                    "UPDATE countries SET treasury = treasury + ? WHERE id = ?",
                    (tribute_amount, winner_country_id)
                )
            if loser_owner_id:
                await db.execute(
                    "UPDATE users SET losses = COALESCE(losses,0) + 1 WHERE id = ?",
                    (loser_owner_id,)
                )
            cursor = await db.execute(
                "SELECT owner_user_id FROM countries WHERE id = ?",
                (winner_country_id,)
            )
            winner_row = await cursor.fetchone()
            winner_user_id = winner_row[0] if winner_row else None
            if winner_user_id:
                await db.execute(
                    "UPDATE users SET wins = COALESCE(wins,0) + 1 WHERE id = ?",
                    (winner_user_id,)
                )
        now_ts = int(time.time())
        await db.execute(
            """
            UPDATE wars
            SET status = ?, ends_at = ?, winner_country_id = ?, tribute_amount = ?,
                attacker_progress = ?, defender_progress = ?, rounds_played = ?, last_round_at = ?
            WHERE id = ?
            """,
            (
                "finished" if winner_country_id else "draw",
                now_ts,
                winner_country_id,
                tribute_amount,
                attacker_score,
                defender_score,
                rounds_played,
                last_round_at,
                war_id,
            )
        )
        await db.execute(
            "UPDATE countries SET last_war_end_ts = ? WHERE id IN (?, ?)",
            (now_ts, attacker_id, defender_id)
        )
        end_action = "war_end_draw" if not winner_country_id else "war_end_win"
        await db.execute(
            """
            INSERT INTO war_logs
            (war_id, actor_country_id, action, power, losses_people, losses_weapons, losses_tech, ts)
            VALUES (?, ?, ?, ?, 0, 0, 0, ?)
            """,
            (war_id, winner_country_id or attacker_id, end_action, 0, now_ts)
        )
    else:
        await db.execute(
            """
            UPDATE wars
            SET attacker_progress = ?, defender_progress = ?, rounds_played = ?, last_round_at = ?
            WHERE id = ?
            """,
            (attacker_score, defender_score, rounds_played, last_round_at, war_id)
        )
    return {"changed": True, "ended": ended, "winner_user_id": winner_user_id}
async def count_user_country_businesses(uid: int) -> int:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            country_id = await get_user_country_id(db, uid)
            if not country_id:
                return 0
            cursor = await db.execute(
                "SELECT COUNT(*) FROM country_businesses WHERE country_id = ? AND level > 0",
                (country_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Ошибка count_user_country_businesses: {e}")
        return 0
def calculate_business_upgrade_cost(bdef, next_level: int) -> int:
    return int(bdef["base_cost"] * (next_level ** 1.35))
async def get_country_businesses(db: aiosqlite.Connection, country_id: int):
    cursor = await db.execute(
        "SELECT business_code, level, last_upkeep_ts FROM country_businesses WHERE country_id = ?",
        (country_id,)
    )
    rows = await cursor.fetchall()
    businesses = {}
    upkeep_ts = {}
    for row in rows:
        code, level, last_ts = row
        businesses[code] = level
        upkeep_ts[code] = last_ts
    return businesses, upkeep_ts
async def apply_business_upkeep(db: aiosqlite.Connection, country_id: int) -> int:
    businesses, upkeep_ts = await get_country_businesses(db, country_id)
    now = int(time.time())
    total_upkeep = 0
    for code, level in businesses.items():
        if level <= 0:
            continue
        bdef = BUSINESS_DEFS.get(code)
        if not bdef:
            continue
        last_ts = upkeep_ts.get(code, 0)
        if last_ts <= 0:
            await db.execute(
                "UPDATE country_businesses SET last_upkeep_ts = ? WHERE country_id = ? AND business_code = ?",
                (now, country_id, code)
            )
            continue
        days = (now - last_ts) // 86400
        if days <= 0:
            continue
        total_upkeep += bdef["upkeep_day"] * level * days
        new_ts = last_ts + days * 86400
        await db.execute(
            "UPDATE country_businesses SET last_upkeep_ts = ? WHERE country_id = ? AND business_code = ?",
            (new_ts, country_id, code)
        )
    if total_upkeep > 0:
        await db.execute(
            "UPDATE countries SET treasury = CASE WHEN treasury >= ? THEN treasury - ? ELSE 0 END WHERE id = ?",
            (total_upkeep, total_upkeep, country_id)
        )
    return total_upkeep
async def ensure_active_boss(db: aiosqlite.Connection):
    """Гарантирует наличие активных боссов для tier 1-3"""
    now = int(time.time())
    for tier in range(1, 4):  # Tier 1, 2, 3
        cursor = await db.execute("SELECT 1 FROM bosses WHERE status = 'active' AND tier = ?", (tier,))
        if not await cursor.fetchone():
            # Создаём босса для этого tier
            template = next((b for b in BOSS_TEMPLATES if b["tier"] == tier), BOSS_TEMPLATES[0])
            spawned_at = now
            ends_at = now + BOSS_LIFETIME
            cursor = await db.execute("""
                INSERT INTO bosses (name, tier, max_hp, hp, attack_power, status, phase, spawned_at, ends_at, level)
                VALUES (?, ?, ?, ?, ?, 'active', 1, ?, ?, 1)
            """, (
                template["name"],
                tier,
                template["max_hp"],
                template["max_hp"],
                template["attack_power"],
                spawned_at,
                ends_at,
            ))
            await db.commit()
async def get_country_combat_bonus(db: aiosqlite.Connection, country_id: int) -> float:
    cursor = await db.execute("""
        SELECT building_type, level
        FROM country_buildings
        WHERE country_id = ? AND building_type IN ('miltech_center', 'military_academy')
    """, (country_id,))
    rows = await cursor.fetchall()
    total_bonus = 0.0
    for row in rows:
        btype = row[0]
        level = row[1]
        bonus = BUILDING_CONFIG.get(btype, {}).get("effects", {}).get("combat_bonus", 0)
        total_bonus += bonus * level
    return 1.0 + (total_bonus / 100.0)
async def get_boss_damage_bonus(db: aiosqlite.Connection, country_id: int) -> float:
    cursor = await db.execute("SELECT item_id FROM country_unique_items WHERE country_id = ?", (country_id,))
    rows = await cursor.fetchall()
    bonus = 0.0
    for row in rows:
        item_id = row[0]
        item = UNIQUE_ITEM_CONFIG.get(item_id)
        if not item:
            continue
        bonus += item.get("boss_damage_bonus_pct", 0)
    return 1.0 + (bonus / 100.0)
async def calculate_boss_damage(db: aiosqlite.Connection, uid: int, country_id: int) -> int:
    cursor = await db.execute("SELECT population FROM countries WHERE id = ?", (country_id,))
    country = await cursor.fetchone()
    people = int(country[0] or 0) if country else 0
    cursor = await db.execute("""
        SELECT ui.amount, i.power, i.category
        FROM user_items ui
        JOIN items i ON ui.item_id = i.item_id
        WHERE ui.user_id = ? AND i.category IN ('weapon', 'vehicle')
    """, (uid,))
    rows = await cursor.fetchall()
    weapons_power = 0
    vehicles_power = 0
    weapons_count = 0
    vehicles_count = 0
    for amount, power, category in rows:
        if category == "weapon":
            weapons_count += amount
            weapons_power += amount * power
        else:
            vehicles_count += amount
            vehicles_power += amount * power
    required_people = max(1, weapons_count + vehicles_count * 3)
    people_factor = min(1.0, people / required_people)
    weapons_power = weapons_power * people_factor
    base_damage = people + weapons_power + vehicles_power
    country_bonus = await get_country_combat_bonus(db, country_id)
    boss_bonus = await get_boss_damage_bonus(db, country_id)
    # Применить эффекты мирового события
    world_effects = await get_world_event_effects()
    boss_buff = world_effects.get('boss_buff', 0.0)
    boss_bonus *= (1 + boss_buff)
    rand_factor = random.uniform(0.9, 1.1)
    return max(1, int(base_damage * country_bonus * boss_bonus * rand_factor))
async def maybe_award_unique_item(db: aiosqlite.Connection, country_id: int, tier: int):
    reward = BOSS_REWARD_CONFIG.get(tier)
    if not reward:
        return None
    cursor = await db.execute("SELECT COUNT(*) FROM country_unique_items WHERE country_id = ?", (country_id,))
    count_row = await cursor.fetchone()
    if count_row and count_row[0] > 0:
        return None
    if random.random() > reward["unique_chance"]:
        return None
    item_id = random.choice(list(UNIQUE_ITEM_CONFIG.keys()))
    await db.execute("""
        INSERT OR IGNORE INTO country_unique_items (country_id, item_id, acquired_at)
        VALUES (?, ?, ?)
    """, (country_id, item_id, int(time.time())))
    return item_id
async def build_bosses_view(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Гарантируем наличие хотя бы одного активного босса
        await ensure_active_boss(db)
        cursor = await db.execute("""
            SELECT * FROM bosses
            ORDER BY spawned_at DESC
            LIMIT 10
        """)
        bosses = await cursor.fetchall()
        if not bosses:
            return "🐉 <b>Боссы</b>\n\nБоссы отсутствуют.", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        text = "🐉 <b>БОССЫ</b>\n\n"
        keyboard = []
        for boss in bosses:
            boss_id = boss["id"]
            max_hp = boss["max_hp"] or 0
            hp = max(0, boss["hp"] or 0)
            hp_pct = (hp / max_hp * 100) if max_hp else 0
            status_text = "🟢 жив" if boss["status"] == "active" else "✅ побеждён"
            phase_text = f"Фаза {boss['phase'] or 1}"
            text += f"• <b>{boss['name']}</b> (Тир {boss['tier']}) | {status_text}\n"
            text += f"  HP: {hp:,} / {max_hp:,} ({hp_pct:.1f}%)\n"
            text += f"  {phase_text}\n\n"
            # Проверяем, атаковал ли пользователь этого босса
            cursor = await db.execute("SELECT 1 FROM boss_hits WHERE boss_id = ? AND user_id = ?", (boss_id, uid))
            has_hit = await cursor.fetchone()
            if boss["status"] == "active":
                if has_hit:
                    keyboard.append([InlineKeyboardButton(text=f"⚔️ Атаковать {boss['name']}", callback_data=f"attack_boss_{boss_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(text=f"⚔️ Атаковать {boss['name']}", callback_data=f"attack_boss_{boss_id}")])
            else:
                if has_hit:
                    keyboard.append([InlineKeyboardButton(text=f"🎁 Забрать награду {boss['name']}", callback_data=f"claim_boss_{boss_id}")])
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_bosses_panel(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        bosses = await ensure_active_bosses(db)
        if not bosses:
            return "👹 <b>Боссы</b>\n\nНет доступных боссов.", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        text = "👹 <b>Боссы</b>\n\n"
        keyboard = []
        for boss in bosses:
            max_hp = boss["max_hp"] or 0
            hp = max(0, boss["hp"] or 0)
            hp_pct = (hp / max_hp * 100) if max_hp else 0
            status_text = "🟢 активен" if boss["status"] == "active" else "✅ повержен"
            text += f"• {boss['name']} (Тир {boss['tier']}) — {hp_pct:.1f}% HP — {status_text}\n"
            keyboard.append([InlineKeyboardButton(text=f"👹 {boss['name']}", callback_data=f"view_boss_{boss['id']}")])
        cursor = await db.execute("""
            SELECT b.id, b.name, b.tier
            FROM bosses b
            JOIN boss_hits bh ON bh.boss_id = b.id
            LEFT JOIN boss_rewards_claimed brc
                ON brc.boss_id = b.id AND brc.user_id = ?
            WHERE b.status = 'defeated' AND bh.user_id = ? AND brc.boss_id IS NULL
            ORDER BY b.spawned_at DESC
        """, (uid, uid))
        reward_rows = await cursor.fetchall()
        if reward_rows:
            text += "\n🎁 Доступные награды:\n"
            for row in reward_rows:
                text += f"• {row['name']} (Тир {row['tier']})\n"
                keyboard.append([InlineKeyboardButton(text=f"🎁 Забрать {row['name']}", callback_data=f"view_boss_{row['id']}")])
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_boss_view(uid: int, boss_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await ensure_active_bosses(db)
        cursor = await db.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
        boss = await cursor.fetchone()
        if not boss:
            return "👹 <b>Босс</b>\n\nБосс не найден.", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К списку", callback_data="show_bosses")]
            ])
        max_hp = boss["max_hp"] or 0
        hp = max(0, boss["hp"] or 0)
        hp_pct = (hp / max_hp * 100) if max_hp else 0
        cursor = await db.execute("""
            SELECT bh.user_id, bh.damage, u.username
            FROM boss_hits bh
            LEFT JOIN users u ON u.id = bh.user_id
            WHERE bh.boss_id = ?
            ORDER BY bh.damage DESC
            LIMIT 5
        """, (boss_id,))
        top_rows = await cursor.fetchall()
        cursor = await db.execute("SELECT ts FROM boss_hits WHERE boss_id = ? AND user_id = ?", (boss_id, uid))
        last_hit = await cursor.fetchone()
        now = int(time.time())
        cooldown_left = 0
        has_hit = bool(last_hit)
        if last_hit:
            cooldown_left = max(0, BOSS_COOLDOWN - (now - int(last_hit[0])))
        cursor = await db.execute("""
            SELECT 1 FROM boss_rewards_claimed WHERE boss_id = ? AND user_id = ?
        """, (boss_id, uid))
        claimed = await cursor.fetchone()
    status_text = "🟢 активен" if boss["status"] == "active" else "✅ повержен"
    phase_text = f"Фаза {boss['phase'] or 1}"
    text = f"👹 <b>Босс</b>\n\n"
    text += f"Имя: <b>{boss['name']}</b>\n"
    text += f"Тир: {boss['tier']} | {status_text}\n"
    text += f"{phase_text}\n"
    text += f"HP: {hp:,} / {max_hp:,} ({hp_pct:.1f}%)\n\n"
    if top_rows:
        text += "Топ урона:\n"
        for i, row in enumerate(top_rows, 1):
            uname = row["username"] or str(row["user_id"])
            text += f"{i}. {uname}: {row['damage']:,}\n"
        text += "\n"
    else:
        text += "Топ урона: пусто.\n\n"
    keyboard = []
    if boss["status"] == "active":
        if cooldown_left > 0:
            text += f"КД: {cooldown_left}с\n"
        else:
            keyboard.append([InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"attack_boss_{boss_id}")])
    else:
        if not claimed and has_hit:
            keyboard.append([InlineKeyboardButton(text="🎁 Забрать награду", callback_data=f"claim_boss_{boss_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 К списку", callback_data="show_bosses")])
    keyboard.append([InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data == "show_countries")
async def show_countries_cb(cb: CallbackQuery):
    """Показать список стран"""
    try:
        username = cb.from_user.username or cb.from_user.first_name
        text, reply_markup = await build_start_country_selection(cb.from_user.id, username)
        if not text:
            await cb.answer("Все стартовые страны уже заняты.", show_alert=True)
            return
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка show_countries_cb: {e}")
        await cb.answer("❌ Ошибка загрузки стран")
async def build_country_view(country_id: int, uid: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await apply_business_upkeep(db, country_id)
            cursor = await db.execute(
                "SELECT c.*, cl.bonus_income, cl.name as clan_name FROM countries c "
                "LEFT JOIN clan_members cm ON c.owner_user_id = cm.user_id "
                "LEFT JOIN clans cl ON cm.clan_id = cl.id WHERE c.id = ?",
                (country_id,)
            )
            country = await cursor.fetchone()
            if not country:
                return None, None
            cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
            buildings = await cursor.fetchall()
            buildings_dict = {b['building_type']: b['level'] for b in buildings}
            businesses, _ = await get_country_businesses(db, country_id)
        await update_population(country_id)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT jobs_available, population FROM countries WHERE id = ?", (country_id,))
            row = await cursor.fetchone()
            if row:
                jobs = row[0]
                pop = row[1]
                employment_rate = min(100, jobs / pop * 100) if pop > 0 else 0
                await db.execute("UPDATE countries SET employment_rate = ? WHERE id = ?", (employment_rate, country_id))
                await db.commit()
            else:
                employment_rate = 0
        owner = "Свободна" if not country['owner_user_id'] else ("Вы владелец" if country['owner_user_id'] == uid else f"Владелец: {country['owner_user_id']}")
        income_bonus = calculate_total_income_bonus(buildings, businesses)
        base_income_per_day = int(calculate_country_income_hour(country['level'], country['stability'], income_bonus) * 24)
        biz_min_day, biz_max_day = calculate_business_income_range_per_day(businesses)
        total_min_day = base_income_per_day + biz_min_day
        total_max_day = base_income_per_day + biz_max_day
        income_line = f"{total_min_day:,} - {total_max_day:,}" if biz_max_day > 0 else f"{base_income_per_day:,}"
        text = f"🏛️ <b>{country['name']}</b>\n\n"
        text += f"👑 {owner}\n"
        text += f"📊 Уровень: {country['level']}\n"
        text += f"👥 Население: {country['population']:,}\n"
        text += f"📊 Занятость: {employment_rate:.1f}%\n"
        text += f"🎓 Грамотность: {country['literacy']}%\n"
        text += f"😊 Счастье: {country['happiness']}%\n"
        text += f"🚔 Преступность: {country['crime']}%\n"
        text += f"💰 Казна: {country['treasury']:,}\n"
        text += f"📈 Доход/сутки: {income_line}\n"
        text += f"🛡️ Стабильность: {country['stability']}%\n"
        text += f"💸 Налог: {country['tax_rate']*100:.1f}%\n\n"
        text += "🏗️ <b>Улучшения:</b>\n"
        for btype, bdata in BUILDING_CONFIG.items():
            level = buildings_dict.get(btype, 0)
            text += f"• {bdata['name']}: {level}\n"
        keyboard = []
        if country['owner_user_id'] == uid:
            keyboard.append([InlineKeyboardButton(text="💰 Собрать доход", callback_data=f"collect_country_income_{country_id}")])
            keyboard.append([InlineKeyboardButton(text="💰 Внести в казну", callback_data="treasury_deposit_help")])
            keyboard.append([InlineKeyboardButton(text="🏗️ Улучшить", callback_data=f"upgrade_country_{country_id}")])
            keyboard.append([InlineKeyboardButton(text="💸 Налоги", callback_data=f"tax_country_{country_id}")])
        elif not country['owner_user_id']:
            keyboard.append([InlineKeyboardButton(text="💰 Купить страну", callback_data=f"buy_country_{country_id}")])
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка build_country_view: {e}")
        return None, None
@router.callback_query(F.data.startswith("view_country_"))
async def view_country_cb(cb: CallbackQuery):
    """Просмотр страны"""
    country_id = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    try:
        text, reply_markup = await build_country_view(country_id, uid)
        if not text:
            await cb.answer("❌ Страна не найдена")
            return
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка view_country_cb: {e}")
        await cb.answer("❌ Ошибка загрузки страны")
@router.callback_query(F.data == "show_my_country")
async def show_my_country_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            country_id = await get_user_country_id(db, uid)
        if not country_id:
            await cb.answer("❌ У вас нет страны", show_alert=True)
            return
        text, reply_markup = await build_country_view(country_id, uid)
        if not text:
            await cb.answer("❌ Страна не найдена", show_alert=True)
            return
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка show_my_country_cb: {e}")
        await cb.answer("❌ Ошибка загрузки страны", show_alert=True)
@router.callback_query(F.data == "treasury_deposit_help")
async def treasury_deposit_help_cb(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "💰 Внести в казну: <code>внести в казну [сумма]</code>\n"
        "Пример: <code>внести в казну 1к</code>",
        parse_mode="HTML"
    )
@router.callback_query(F.data.startswith("buy_country_"))
async def buy_country_cb(cb: CallbackQuery):
    """Купить страну"""
    country_id = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    price = scale_price(5_000_000)  # 5M
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (uid,))
            user_balance = (await cursor.fetchone())[0]
            if user_balance < price:
                await db.rollback()
                await cb.answer("❌ Недостаточно средств", show_alert=True)
                return
            cursor = await db.execute("SELECT owner_user_id FROM countries WHERE id = ?", (country_id,))
            owner = (await cursor.fetchone())[0]
            if owner:
                await db.rollback()
                await cb.answer("❌ Страна уже куплена", show_alert=True)
                return
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, uid))
            await db.execute("UPDATE countries SET owner_user_id = ? WHERE id = ?", (uid, country_id))
            import random
            population = random.randint(80000, 200000)
            await db.execute("UPDATE countries SET population = ?, last_population_tick = ? WHERE id = ?", (population, int(time.time()), country_id))
            await db.commit()
        await cb.answer("✅ Страна куплена!", show_alert=True)
        await view_country_cb(cb)  # Обновить вид
    except Exception as e:
        logger.error(f"Ошибка buy_country_cb: {e}")
        await cb.answer("❌ Ошибка покупки")
async def build_upgrade_country_menu(country_id: int, uid: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM countries WHERE id = ? AND owner_user_id = ?", (country_id, uid))
            country = await cursor.fetchone()
            if not country:
                return None, None, "not_owner"
            cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
            buildings = await cursor.fetchall()
            buildings_dict = {b['building_type']: b['level'] for b in buildings}
        header = f"🌆 <b>Улучшения страны {country['name']}</b>"
        prompt = "Выберите категорию, чтобы посмотреть доступные улучшения:"
        text = f"{header}\n\n{prompt}"
        keyboard = [
            [InlineKeyboardButton(text="💰 Экономика", callback_data=f"upgrade_cat_economy_{country_id}")],
            [InlineKeyboardButton(text="🏛 Инфраструктура", callback_data=f"upgrade_cat_infra_{country_id}")],
            [InlineKeyboardButton(text="🏭 Промышленность", callback_data=f"upgrade_cat_industry_{country_id}")],
            [InlineKeyboardButton(text="🔥 Военное", callback_data=f"upgrade_cat_military_{country_id}")],
            [InlineKeyboardButton(text="🚀 Космос", callback_data=f"upgrade_cat_space_{country_id}")],
            [InlineKeyboardButton(text="📄 Назад к стране", callback_data=f"view_country_{country_id}")]
        ]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard), None
    except Exception as e:
        logger.error(f"Ошибка build_upgrade_country_menu: {e}")
        return None, None, "error"
@router.callback_query(F.data.startswith("upgrade_country_"))
async def upgrade_country_cb(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) != 3 or not parts[2].isdigit():
        raise SkipHandler
    country_id = int(parts[2])
    uid = cb.from_user.id
    text, reply_markup, err = await build_upgrade_country_menu(country_id, uid)
    if err == "not_owner":
        await cb.answer("¢?? '‘< ?ç ?>ø?ç>ç‘Å ‘?‘'?ü ‘?‘'‘?ø?‘<")
        return
    if err:
        await cb.answer("¢?? ?‘?ñ+óø úø?‘?‘?úóñ ?ç?‘?")
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("upgrade_cat_"))
async def upgrade_cat_cb(cb: CallbackQuery):
    """Меню улучшений по категории"""
    parts = cb.data.split("_")
    category = parts[2]
    country_id = int(parts[3])
    uid = cb.from_user.id
    categories = {
        'economy': ['parks', 'tax_office', 'development_bank', 'trade_port'],
        'infra': ['police', 'court', 'hospital', 'power_grid'],
        'industry': ['logistics_hub', 'industrial_complex', 'nuclear_plant'],
        'military': ['barracks', 'miltech_center', 'weapons_factory', 'tank_factory', 'air_defense', 'intelligence'],
        'space': ['space_station', 'research_institute']
    }
    if category not in categories:
        await cb.answer("❌ Неизвестная категория")
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM countries WHERE id = ? AND owner_user_id = ?", (country_id, uid))
            country = await cursor.fetchone()
            if not country:
                await cb.answer("❌ Вы не владелец этой страны")
                return
            cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
            buildings = await cursor.fetchall()
            buildings_dict = {b['building_type']: b['level'] for b in buildings}
        text = f"🏗️ <b>Улучшения {category.title()}</b>\n\n"
        keyboard = []
        for btype in categories[category]:
            bdata = BUILDING_CONFIG[btype]
            level = buildings_dict.get(btype, 0)
            max_level = bdata['max_level']
            if level >= max_level:
                status = f"✅ Макс ({level})"
                can_upgrade = False
            else:
                next_level = level + 1
                cost = int(bdata['base_cost'] * (next_level ** 1.35))
                status = f"Ур.{level} → {next_level} ({format_money(cost)})"
                can_upgrade = True
            keyboard.append([InlineKeyboardButton(
                text=f"{bdata['name']}: {status}",
                callback_data=f"upgrade_building_{btype}_{country_id}" if can_upgrade else f"building_max_{btype}_{country_id}"
            )])
        if category == "economy":
            keyboard.append([InlineKeyboardButton(text="💼 Бизнесы", callback_data=f"country_businesses_{country_id}")])
        keyboard.append([InlineKeyboardButton(text="🔙 К категориям", callback_data=f"upgrade_country_{country_id}")])
        keyboard.append([InlineKeyboardButton(text="🏛️ К стране", callback_data=f"view_country_{country_id}")])
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка upgrade_cat_cb: {e}")
        await cb.answer("❌ Ошибка загрузки категории")
async def build_country_businesses_view(country_id: int, uid: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT owner_user_id, treasury FROM countries WHERE id = ?", (country_id,))
            country = await cursor.fetchone()
            if not country:
                return None, None, "not_found"
            if country["owner_user_id"] != uid:
                return None, None, "not_owner"
            await apply_business_upkeep(db, country_id)
            businesses, _ = await get_country_businesses(db, country_id)
        text = "💼 <b>Бизнесы страны</b>\n\n"
        text += "Развивайте бизнесы для роста дохода и рабочих мест.\n\n"
        keyboard = []
        for code, bdef in BUSINESS_DEFS.items():
            level = businesses.get(code, 0)
            display_level = max(1, level)
            min_day = int(int(bdef.get('income_min_day', 0)) * display_level * COUNTRY_INCOME_MULTIPLIER)
            max_day = int(int(bdef.get('income_max_day', 0)) * display_level * COUNTRY_INCOME_MULTIPLIER)
            income_text = f"{format_money(min_day)}-{format_money(max_day)}/????" if max_day > 0 else "?"
            max_level = bdef["max_level"]
            if level >= max_level:
                status = f"✅ Макс ({level})"
                callback = f"business_max_{code}_{country_id}"
            else:
                next_level = level + 1
                cost = calculate_business_upgrade_cost(bdef, next_level)
                status = f"Ур.{level} → {next_level} ({format_money(cost)})"
                callback = f"upgrade_country_business_{code}_{country_id}"
            keyboard.append([InlineKeyboardButton(text=f"{bdef['name']}: {status} | {income_text}", callback_data=callback)])
        keyboard.append([InlineKeyboardButton(text="🔙 К экономике", callback_data=f"upgrade_cat_economy_{country_id}")])
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard), None
    except Exception as e:
        logger.error(f"Ошибка build_country_businesses_view: {e}")
        return None, None, "error"
@router.callback_query(F.data.startswith("country_businesses_"))
async def country_businesses_cb(cb: CallbackQuery):
    try:
        country_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("❌ Неверные данные", show_alert=True)
        return
    uid = cb.from_user.id
    text, reply_markup, err = await build_country_businesses_view(country_id, uid)
    if err == "not_owner":
        await cb.answer("❌ Вы не владелец этой страны", show_alert=True)
        return
    if err == "not_found":
        await cb.answer("❌ Страна не найдена", show_alert=True)
        return
    if not text:
        await cb.answer("❌ Ошибка загрузки бизнесов", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("business_max_"))
async def business_max_cb(cb: CallbackQuery):
    await cb.answer("✅ Уже максимальный уровень")
@router.callback_query(F.data.startswith("upgrade_country_business_"))
async def upgrade_country_business_cb(cb: CallbackQuery):
    prefix = "upgrade_country_business_"
    data = cb.data[len(prefix):]
    try:
        code, country_id_str = data.rsplit("_", 1)
        country_id = int(country_id_str)
    except Exception:
        await cb.answer("❌ Неверные данные", show_alert=True)
        return
    uid = cb.from_user.id
    bdef = BUSINESS_DEFS.get(code)
    if not bdef:
        await cb.answer("❌ Бизнес не найден", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id, treasury FROM countries WHERE id = ?", (country_id,))
            country = await cursor.fetchone()
            if not country or country["owner_user_id"] != uid:
                await db.rollback()
                await cb.answer("❌ Вы не владелец этой страны", show_alert=True)
                return
            await apply_business_upkeep(db, country_id)
            cursor = await db.execute(
                "SELECT level, last_upkeep_ts FROM country_businesses WHERE country_id = ? AND business_code = ?",
                (country_id, code)
            )
            row = await cursor.fetchone()
            current_level = row["level"] if row else 0
            last_upkeep_ts = row["last_upkeep_ts"] if row else 0
            if current_level >= bdef["max_level"]:
                await db.rollback()
                await cb.answer("✅ Уже максимум", show_alert=True)
                return
            next_level = current_level + 1
            cost = calculate_business_upgrade_cost(bdef, next_level)
            if country["treasury"] < cost:
                await db.rollback()
                await cb.answer(f"❌ Недостаточно казны ({format_money(cost)} нужно)", show_alert=True)
                return
            await db.execute(
                "UPDATE countries SET treasury = treasury - ? WHERE id = ?",
                (cost, country_id)
            )
            if row:
                await db.execute(
                    "UPDATE country_businesses SET level = ? WHERE country_id = ? AND business_code = ?",
                    (next_level, country_id, code)
                )
            else:
                ts = int(time.time())
                await db.execute(
                    "INSERT INTO country_businesses (country_id, business_code, level, last_upkeep_ts) VALUES (?, ?, ?, ?)",
                    (country_id, code, next_level, ts if last_upkeep_ts == 0 else last_upkeep_ts)
                )
            await db.commit()
        await calculate_jobs_available(country_id)
        await update_country_stats(country_id)
        new_cb = cb.model_copy(update={"data": f"country_businesses_{country_id}"})
        await country_businesses_cb(new_cb)
    except Exception as e:
        logger.error(f"Ошибка upgrade_country_business_cb: {e}")
        await cb.answer("❌ Ошибка улучшения бизнеса", show_alert=True)
@router.callback_query(F.data.startswith("upgrade_building_"))
async def upgrade_building_cb(cb: CallbackQuery):
    """Улучшить здание"""
    prefix = "upgrade_building_"
    data = cb.data[len(prefix):]
    try:
        btype, country_id_str = data.rsplit("_", 1)
        country_id = int(country_id_str)
    except Exception:
        await cb.answer("¢?? ?çñú?ç‘?‘'?ø‘? óø‘'ç??‘?ñ‘?")
        return
    uid = cb.from_user.id
    if btype not in BUILDING_CONFIG:
        await cb.answer("❌ Неизвестное здание")
        return
    bdata = BUILDING_CONFIG[btype]
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM countries WHERE id = ? AND owner_user_id = ?", (country_id, uid))
            country = await cursor.fetchone()
            if not country:
                await db.rollback()
                await cb.answer("❌ Вы не владелец этой страны")
                return
            cursor = await db.execute("SELECT level FROM country_buildings WHERE country_id = ? AND building_type = ?", (country_id, btype))
            current_level = (await cursor.fetchone() or [0])[0]
            if current_level >= bdata['max_level']:
                await db.rollback()
                await cb.answer("❌ Максимальный уровень достигнут")
                return
            next_level = current_level + 1
            cost = int(bdata['base_cost'] * (next_level ** 1.35))
            if country['treasury'] < cost:
                await db.rollback()
                await cb.answer(f"❌ Недостаточно средств в казне ({format_money(cost)} нужно)")
                return
            # Списываем деньги
            await db.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (cost, country_id))
            # Обновляем уровень здания
            if current_level == 0:
                await db.execute("INSERT INTO country_buildings (country_id, building_type, level) VALUES (?, ?, ?)", (country_id, btype, 1))
            else:
                await db.execute("UPDATE country_buildings SET level = level + 1 WHERE country_id = ? AND building_type = ?", (country_id, btype))
            await db.commit()
        await calculate_jobs_available(country_id)
        await update_country_stats(country_id)
        await cb.answer(f"✅ {bdata['name']} улучшен до уровня {next_level}!")
        # Возвращаемся к меню категории
        cat_data = {
            'parks': 'economy', 'tax_office': 'economy', 'development_bank': 'economy', 'trade_port': 'economy',
            'police': 'infra', 'court': 'infra', 'hospital': 'infra', 'power_grid': 'infra',
            'logistics_hub': 'industry', 'industrial_complex': 'industry', 'nuclear_plant': 'industry',
            'barracks': 'military', 'miltech_center': 'military', 'weapons_factory': 'military', 'tank_factory': 'military', 'air_defense': 'military', 'intelligence': 'military',
            'space_station': 'space', 'research_institute': 'space'
        }
        category = cat_data.get(btype, 'economy')
        new_cb = cb.model_copy(update={"data": f"upgrade_cat_{category}_{country_id}"})
        await upgrade_cat_cb(new_cb)
    except Exception as e:
        logger.error(f"Ошибка upgrade_building_cb: {e}")
        await cb.answer("❌ Ошибка улучшения")
async def collect_country_income_for_user(uid: int, country_id: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id, level, stability, last_tick FROM countries WHERE id = ?", (country_id,))
            country = await cursor.fetchone()
            if not country or country[0] != uid:
                await db.rollback()
                return {"success": False, "error": "Вы не владелец страны."}
            now = int(time.time())
            last_tick = country[3] or 0
            elapsed = max(0, now - last_tick)
            collected_seconds = min(elapsed, 24 * 3600)
            hours_passed = collected_seconds / 3600
            cursor = await db.execute("SELECT building_type, level FROM country_buildings WHERE country_id = ?", (country_id,))
            buildings = await cursor.fetchall()
            businesses, _ = await get_country_businesses(db, country_id)
            await apply_business_upkeep(db, country_id)
            income_bonus = calculate_total_income_bonus(buildings, businesses)
            income_per_hour = calculate_country_income_hour(country[1], country[2], income_bonus)
            total_income = int(income_per_hour * hours_passed)
            business_income = calculate_business_income_for_period(businesses, hours_passed)
            total_income += business_income
            current_ts = now
            cursor = await db.execute("SELECT income_boost_percent, income_boost_until_ts FROM users WHERE id = ?", (uid,))
            boost_row = await cursor.fetchone()
            if boost_row and boost_row[0] > 0 and current_ts < boost_row[1]:
                total_income = int(total_income * (1 + boost_row[0]))
            title_bonuses = await calculate_title_bonuses(uid)
            income_bonus = title_bonuses.get('income', 0.0)
            total_income = int(total_income * (1 + income_bonus))
            world_effects = await get_world_event_effects()
            income_effect = world_effects.get('income', 0.0)
            total_income = int(total_income * (1 + income_effect))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total_income, uid))
            await db.execute("UPDATE countries SET last_tick = ? WHERE id = ?", (now, country_id))
            event_message = await check_random_events(db, country_id, uid)
            await db.commit()
            await check_and_award_titles(uid)
        return {
            "success": True,
            "total_income": total_income,
            "hours": hours_passed,
            "accumulated_seconds": collected_seconds,
            "event_message": event_message,
            "next_available": now + 24 * 3600
        }
    except Exception as e:
        logger.error(f"Ошибка collect_country_income_for_user: {e}")
        return {"success": False, "error": "Ошибка сбора дохода."}
@router.callback_query(F.data.startswith("collect_country_income_"))
async def collect_country_income_cb(cb: CallbackQuery):
    country_id = int(cb.data.split("_")[3])
    uid = cb.from_user.id
    result = await collect_country_income_for_user(uid, country_id)
    if not result["success"]:
        await cb.answer(result["error"], show_alert=True)
        return
    lines = [
        f"Income: {result['total_income']:,}",
        f"Accumulated: {format_duration(result['accumulated_seconds'])} (max 24 h)",
        f"Next collection: {format_timestamp(result['next_available'])}"
    ]
    response = "\n".join(lines)
    if result.get("event_message"):
        response += "\n\n" + result['event_message']
    await cb.answer(response, show_alert=True)
    text, reply_markup = await build_country_view(country_id, uid)
    if text:
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
async def build_tax_menu(country_id: int, uid: int):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT owner_user_id, tax_rate, stability FROM countries WHERE id = ?", (country_id,))
            row = await cursor.fetchone()
            if not row:
                return None, None, "not_found"
            if row[0] != uid:
                return None, None, "not_owner"
            tax_rate = row[1] or 0.1
            stability = row[2] or 0
        text = (
            "🌐 <b>Управление налогами</b>\n\n"
            f"Текущая ставка: {tax_rate * 100:.1f}%\n"
            f"Стабильность страны: {stability}%\n\n"
            "Высокие налоги усиливают доход, но снижают рост и стабильность."
        )
        keyboard = [
            [InlineKeyboardButton(text="0%", callback_data=f"set_tax_{country_id}_0")],
            [InlineKeyboardButton(text="5%", callback_data=f"set_tax_{country_id}_5")],
            [InlineKeyboardButton(text="10%", callback_data=f"set_tax_{country_id}_10")],
            [InlineKeyboardButton(text="15%", callback_data=f"set_tax_{country_id}_15")],
            [InlineKeyboardButton(text="20%", callback_data=f"set_tax_{country_id}_20")],
            [InlineKeyboardButton(text="🔙 К стране", callback_data=f"view_country_{country_id}")]
        ]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard), None
    except Exception as e:
        logger.error(f"Ошибка build_tax_menu: {e}")
        return None, None, "error"
@router.callback_query(F.data.startswith("tax_country_"))
async def tax_country_cb(cb: CallbackQuery):
    country_id = int(cb.data.split("_")[2])
    uid = cb.from_user.id
    text, reply_markup, err = await build_tax_menu(country_id, uid)
    if err == "not_owner":
        await cb.answer("в?? ђ?ђз ђ?ђш‘?ђш ‘?‘'‘?ђшђ?ђш", show_alert=True)
        return
    if err:
        await cb.answer("Ошибка управления налогами", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("set_tax_"))
async def set_tax_cb(cb: CallbackQuery):
    parts = cb.data.split("_")
    country_id = int(parts[2])
    tax_percent = int(parts[3])
    tax_rate = tax_percent / 100
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT owner_user_id FROM countries WHERE id = ?", (country_id,))
            owner = (await cursor.fetchone())[0]
            if owner != uid:
                await cb.answer("❌ Не ваша страна")
                return
            await db.execute("UPDATE countries SET tax_rate = ? WHERE id = ?", (tax_rate, country_id))
            await db.commit()
            await update_country_stats(country_id)
        await cb.answer(f"✅ Налог установлен: {tax_percent}%")
        await view_country_cb(cb)
    except Exception as e:
        logger.error(f"Ошибка set_tax_cb: {e}")
        await cb.answer("❌ Ошибка")
@router.callback_query(F.data == "show_clans")
async def show_clans_cb(cb: CallbackQuery):
    """Показать список кланов"""
    try:
        text, reply_markup = await build_clans_view()
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка show_clans_cb: {e}")
        await cb.answer("❌ Ошибка загрузки кланов")
@router.callback_query(F.data == "create_clan")
async def create_clan_cb(cb: CallbackQuery):
    """Создать клан"""
    creating_clan[cb.from_user.id] = True
    await cb.message.edit_text(
        "🏰 <b>СОЗДАНИЕ КЛАНА</b>\n\n"
        "Введите название клана (3-20 символов):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="show_clans")]
        ])
    )
    await cb.answer()
@router.callback_query(F.data.startswith("view_clan_"))
async def view_clan_cb(cb: CallbackQuery):
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка клана.", show_alert=True)
        return
    text, reply_markup = await build_clan_view(clan_id, cb.from_user.id)
    if not text:
        await cb.answer("Клан не найден.", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    try:
        await cb.answer()
    except TelegramBadRequest:
        pass
@router.callback_query(F.data.startswith("join_clan_"))
async def join_clan_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка клана.", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT id, is_open FROM clans WHERE id = ?", (clan_id,))
            clan = await cursor.fetchone()
            if not clan:
                await db.rollback()
                await cb.answer("Клан не найден.", show_alert=True)
                return
            if not clan["is_open"]:
                await db.rollback()
                await cb.answer("Клан закрыт, отправьте заявку.", show_alert=True)
                return
            cursor = await db.execute("SELECT 1 FROM clan_members WHERE user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Вы уже в клане.", show_alert=True)
                return
            await db.execute(
                "INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_at) "
                "VALUES (?, ?, 'member', ?)",
                (clan_id, uid, int(time.time()))
            )
            await db.execute(
                "DELETE FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                (clan_id, uid)
            )
            await db.commit()
        await cb.answer("Вы вступили в клан.", show_alert=True)
        text, reply_markup = await build_clan_view(clan_id, uid)
        if text:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка join_clan_cb: {e}")
        await cb.answer("Ошибка вступления в клан.", show_alert=True)


@router.callback_query(F.data.startswith("request_clan_"))
async def request_clan_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка клана.", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT id, is_open FROM clans WHERE id = ?", (clan_id,))
            clan = await cursor.fetchone()
            if not clan:
                await db.rollback()
                await cb.answer("Клан не найден.", show_alert=True)
                return
            if clan["is_open"]:
                await db.rollback()
                await cb.answer("Клан открыт, вступайте напрямую.", show_alert=True)
                return
            cursor = await db.execute("SELECT 1 FROM clan_members WHERE user_id = ?", (uid,))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Вы уже в клане.", show_alert=True)
                return
            cursor = await db.execute(
                "SELECT 1 FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                (clan_id, uid)
            )
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Заявка уже отправлена.", show_alert=True)
                return
            await db.execute(
                "INSERT INTO clan_join_requests (clan_id, user_id, created_at) VALUES (?, ?, ?)",
                (clan_id, uid, int(time.time()))
            )
            await db.commit()
        await cb.answer("Заявка отправлена.", show_alert=True)
        text, reply_markup = await build_clan_view(clan_id, uid)
        if text:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка request_clan_cb: {e}")
        await cb.answer("Ошибка отправки заявки.", show_alert=True)
@router.callback_query(F.data.startswith("clan_delete_"))
async def clan_delete_cb(cb: CallbackQuery):
    if cb.data.startswith("clan_delete_confirm_"):
        raise SkipHandler
    try:
        parts = cb.data.split("_")
        if len(parts) < 3:
            await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u043a\u043b\u0430\u043d\u0430.", show_alert=True)
            return
        clan_id = int(parts[2])
        uid = cb.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT owner_user_id FROM clans WHERE id = ?", (clan_id,))
            row = await cursor.fetchone()
            if not row:
                await cb.answer("\u041a\u043b\u0430\u043d \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.", show_alert=True)
                return
            if row[0] != uid:
                await cb.answer("\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446 \u043c\u043e\u0436\u0435\u0442 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u043a\u043b\u0430\u043d.", show_alert=True)
                return
        text = "\u26a0\ufe0f <b>\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043a\u043b\u0430\u043d?</b>\n\n\u042d\u0442\u043e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043d\u0435\u043e\u0431\u0440\u0430\u0442\u0438\u043c\u043e."
        keyboard = [
            [InlineKeyboardButton(text="\u2705 \u0414\u0430, \u0443\u0434\u0430\u043b\u0438\u0442\u044c", callback_data=f"clan_delete_confirm_{clan_id}")],
            [InlineKeyboardButton(text="\ud83d\udd19 \u041e\u0442\u043c\u0435\u043d\u0430", callback_data=f"view_clan_{clan_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except TelegramBadRequest:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer()
    except Exception as e:
        logger.error(f"Ошибка clan_delete_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f \u0443\u0434\u0430\u043b\u0435\u043d\u0438\u044f.", show_alert=True)
@router.callback_query(F.data.startswith("clan_delete_confirm_"))
async def clan_delete_confirm_cb(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u043a\u043b\u0430\u043d\u0430.", show_alert=True)
        return
    clan_id = int(parts[3])
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id FROM clans WHERE id = ?", (clan_id,))
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                await cb.answer("\u041a\u043b\u0430\u043d \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.", show_alert=True)
                return
            if row[0] != uid:
                await db.rollback()
                await cb.answer("\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446 \u043c\u043e\u0436\u0435\u0442 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u043a\u043b\u0430\u043d.", show_alert=True)
                return
            # clan_boss_rewards_claimed does not have clan_id; clean it via related hits
            await db.execute(
                """
                DELETE FROM clan_boss_rewards_claimed
                WHERE boss_id IN (
                    SELECT boss_id FROM clan_boss_hits WHERE clan_id = ?
                )
                """,
                (clan_id,)
            )
            for table in (
                "clan_join_requests",
                "clan_members",
                "clan_logs",
                "clan_boss_hits",
            ):
                await db.execute(f"DELETE FROM {table} WHERE clan_id = ?", (clan_id,))
            await db.execute("DELETE FROM clans WHERE id = ?", (clan_id,))
            await db.commit()
        text, reply_markup = await build_clans_view()
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except TelegramBadRequest:
            await cb.message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer("\u041a\u043b\u0430\u043d \u0443\u0434\u0430\u043b\u0435\u043d.")
    except Exception as e:
        logger.error(f"Ошибка clan_delete_confirm_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u0443\u0434\u0430\u043b\u0435\u043d\u0438\u044f \u043a\u043b\u0430\u043d\u0430.", show_alert=True)
@router.callback_query(F.data.startswith("clan_toggle_"))
async def clan_toggle_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка клана.", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT owner_user_id, is_open FROM clans WHERE id = ?",
                (clan_id,)
            )
            row = await cursor.fetchone()
            if not row or row[0] != uid:
                await db.rollback()
                await cb.answer("Нет прав.", show_alert=True)
                return
            new_state = 0 if int(row[1] or 0) == 1 else 1
            await db.execute("UPDATE clans SET is_open = ? WHERE id = ?", (new_state, clan_id))
            await db.commit()
        text, reply_markup = await build_clan_view(clan_id, uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        await cb.answer("Статус изменен.")
    except Exception as e:
        logger.error(f"Ошибка clan_toggle_cb: {e}")
        await cb.answer("Ошибка настроек.", show_alert=True)
@router.callback_query(F.data.startswith("clan_requests_"))
async def clan_requests_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка клана.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT owner_user_id FROM clans WHERE id = ?", (clan_id,))
        row = await cursor.fetchone()
        if not row or row["owner_user_id"] != uid:
            await cb.answer("Нет прав.", show_alert=True)
            return
        cursor = await db.execute("""
            SELECT r.user_id, u.username, r.created_at
            FROM clan_join_requests r
            LEFT JOIN users u ON u.id = r.user_id
            WHERE r.clan_id = ?
            ORDER BY r.created_at ASC
            LIMIT 10
        """, (clan_id,))
        reqs = await cursor.fetchall()
    text = "📨 <b>Заявки в клан</b>\n\n"
    keyboard = []
    if not reqs:
        text += "Заявок нет."
    else:
        for row in reqs:
            uname = row["username"] or str(row["user_id"])
            text += f"• {uname}\n"
            keyboard.append([
                InlineKeyboardButton(text="✅ Принять", callback_data=f"clan_accept_{clan_id}_{row['user_id']}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"clan_reject_{clan_id}_{row['user_id']}")
            ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_clan_{clan_id}")])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await cb.answer()
@router.callback_query(F.data.startswith("clan_accept_"))
async def clan_accept_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("Ошибка.", show_alert=True)
        return
    clan_id = int(parts[2])
    target_id = int(parts[3])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id FROM clans WHERE id = ?", (clan_id,))
            row = await cursor.fetchone()
            if not row or row[0] != uid:
                await db.rollback()
                await cb.answer("Нет прав.", show_alert=True)
                return
            cursor = await db.execute(
                "SELECT 1 FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                (clan_id, target_id)
            )
            if not await cursor.fetchone():
                await db.rollback()
                await cb.answer("Заявка не найдена.", show_alert=True)
                return
            cursor = await db.execute("SELECT 1 FROM clan_members WHERE user_id = ?", (target_id,))
            if await cursor.fetchone():
                await db.execute(
                    "DELETE FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                    (clan_id, target_id)
                )
                await db.commit()
                await cb.answer("Уже в клане.", show_alert=True)
                return
            now = int(time.time())
            await db.execute(
                "INSERT INTO clan_members (clan_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)",
                (clan_id, target_id, now)
            )
            await db.execute(
                "DELETE FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                (clan_id, target_id)
            )
            await db.commit()
        await clan_requests_cb(cb)
    except Exception as e:
        logger.error(f"Ошибка clan_accept_cb: {e}")
        await cb.answer("Ошибка.", show_alert=True)
@router.callback_query(F.data.startswith("clan_reject_"))
async def clan_reject_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("Ошибка.", show_alert=True)
        return
    clan_id = int(parts[2])
    target_id = int(parts[3])
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT owner_user_id FROM clans WHERE id = ?", (clan_id,))
            row = await cursor.fetchone()
            if not row or row[0] != uid:
                await db.rollback()
                await cb.answer("Нет прав.", show_alert=True)
                return
            await db.execute(
                "DELETE FROM clan_join_requests WHERE clan_id = ? AND user_id = ?",
                (clan_id, target_id)
            )
            await db.commit()
        await clan_requests_cb(cb)
    except Exception as e:
        logger.error(f"Ошибка clan_reject_cb: {e}")
        await cb.answer("Ошибка.", show_alert=True)
@router.callback_query(F.data.startswith("clan_leave_"))
async def clan_leave_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        clan_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("������ �����.", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT owner_user_id FROM clans WHERE id = ?",
                (clan_id,)
            )
            clan = await cursor.fetchone()
            if not clan:
                await db.rollback()
                await cb.answer("���� �� ������.", show_alert=True)
                return
            if clan["owner_user_id"] == uid:
                await db.rollback()
                await cb.answer("�������� �� ����� �����. ������� ��������� ���� ��� ������� ���.", show_alert=True)
                return
            cursor = await db.execute(
                "SELECT 1 FROM clan_members WHERE clan_id = ? AND user_id = ?",
                (clan_id, uid)
            )
            if not await cursor.fetchone():
                await db.rollback()
                await cb.answer("�� �� �������� � ���� �����.", show_alert=True)
                return
            await db.execute(
                "DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?",
                (clan_id, uid)
            )
            await db.commit()
        await cb.answer("�� �������� ����.", show_alert=True)
        text, reply_markup = await build_clans_view()
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"������ clan_leave_cb: {e}")
        await cb.answer("������ ������ �� �����.", show_alert=True)
@router.callback_query(F.data == "show_wars")
async def show_wars_cb(cb: CallbackQuery):
    """Показать войны"""
    text, reply_markup = await build_wars_view(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "view_war")
async def view_war_cb(cb: CallbackQuery):
    """Показать активную войну"""
    text, reply_markup = await build_war_view(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("war_attack_"))
async def war_attack_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await process_credit_defaults(db, uid)
            if await has_defaulted_credit(db, uid):
                await cb.answer("\u0423 \u0432\u0430\u0441 \u0434\u0435\u0444\u043e\u043b\u0442 \u043f\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0443. \u0412\u043e\u0439\u043d\u044b \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u044b.", show_alert=True)
                return
    except Exception as e:
        logger.error(f"Ошибка проверки дефолта по кредиту в war_attack_cb: {e}")
    try:
        defender_country_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка цели.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        attacker_country_id = await get_user_country_id(db, uid)
        if not attacker_country_id:
            await cb.answer("У вас нет страны.", show_alert=True)
            return
    token = hashlib.md5(f"{uid}:{defender_country_id}:{time.time()}".encode()).hexdigest()[:6].upper()
    war_challenges[uid] = {
        "token": token,
        "attacker_country_id": attacker_country_id,
        "defender_country_id": defender_country_id,
        "expires_at": int(time.time()) + 300
    }
    text = (
        "⚔️ <b>Подтверждение войны</b>\n\n"
        "Чтобы начать войну, отправьте:\n"
        f"<code>подтверждаю {token}</code>\n"
        "или просто <code>ДА</code> (в течение 5 минут)."
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к войнам", callback_data="show_wars")]
        ])
    )
    await cb.answer()
@router.callback_query(F.data == "show_bosses")
async def show_bosses_cb(cb: CallbackQuery):
    """Показать боссов"""
    text, reply_markup = await build_bosses_panel(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("view_boss_"))
async def view_boss_cb(cb: CallbackQuery):
    try:
        boss_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Ошибка босса.", show_alert=True)
        return
    text, reply_markup = await build_boss_view(cb.from_user.id, boss_id)
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await cb.answer()
@router.callback_query(F.data.startswith("attack_boss_"))
async def attack_boss_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        boss_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Некорректный босс.", show_alert=True)
        return
    cb_id = str(cb.id)
    if await is_callback_processed(cb_id):
        await cb.answer("Уже обработано.", show_alert=False)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT 1 FROM processed_callbacks WHERE id = ?", (cb_id,))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Уже обработано.", show_alert=False)
                return
            cursor = await db.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
            boss = await cursor.fetchone()
            if not boss or boss["status"] != "active":
                await db.rollback()
                await cb.answer("Босс не активен.", show_alert=True)
                return
            clan_id = await get_user_clan_id(db, uid)
            if not clan_id:
                await db.rollback()
                await cb.answer("Нужно состоять в клане.", show_alert=True)
                return
            country_id = await get_user_country_id(db, uid)
            if not country_id:
                await db.rollback()
                await cb.answer("Нужна страна.", show_alert=True)
                return
            cursor = await db.execute(
                "SELECT damage, ts FROM boss_hits WHERE boss_id = ? AND user_id = ?",
                (boss_id, uid)
            )
            existing_hit = await cursor.fetchone()
            now = int(time.time())
            if existing_hit and now - int(existing_hit["ts"]) < BOSS_COOLDOWN:
                await db.rollback()
                await cb.answer("КД ещё не закончился.", show_alert=True)
                return
            damage = await calculate_boss_damage(db, uid, country_id)
            if boss["tier"] == 6 and boss["hp"] <= boss["max_hp"] * 0.5:
                damage = int(damage * 0.9)
            new_hp = max(0, boss["hp"] - damage)
            new_phase = boss["phase"]
            if boss["tier"] == 6 and new_hp <= boss["max_hp"] * 0.5:
                new_phase = 2
            if existing_hit:
                await db.execute("""
                    UPDATE boss_hits
                    SET damage = damage + ?, ts = ?, clan_id = ?, country_id = ?
                    WHERE boss_id = ? AND user_id = ?
                """, (damage, now, clan_id, country_id, boss_id, uid))
            else:
                await db.execute("""
                    INSERT INTO boss_hits (boss_id, clan_id, user_id, country_id, damage, ts)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (boss_id, clan_id, uid, country_id, damage, now))
            if new_hp <= 0:
                await db.execute("""
                    UPDATE bosses SET hp = ?, status = 'defeated', phase = ?, ends_at = ?
                    WHERE id = ?
                """, (new_hp, new_phase, now, boss_id))
            else:
                await db.execute("""
                    UPDATE bosses SET hp = ?, phase = ?
                    WHERE id = ?
                """, (new_hp, new_phase, boss_id))
            await db.execute("INSERT INTO processed_callbacks (id, ts) VALUES (?, ?)", (cb_id, now))
            await db.commit()
        await cb.answer(f"Урон: {damage:,}!", show_alert=True)
        text, reply_markup = await build_boss_view(uid, boss_id)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    except Exception as e:
        logger.error(f"Ошибка атаки босса: {e}")
        await cb.answer("Атака не удалась.", show_alert=True)
@router.callback_query(F.data.startswith("claim_boss_"))
async def claim_boss_rewards_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        boss_id = int(cb.data.split("_")[2])
    except Exception:
        await cb.answer("Некорректный босс.", show_alert=True)
        return
    cb_id = str(cb.id)
    if await is_callback_processed(cb_id):
        await cb.answer("Уже обработано.", show_alert=False)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT 1 FROM processed_callbacks WHERE id = ?", (cb_id,))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Уже обработано.", show_alert=False)
                return
            cursor = await db.execute("SELECT * FROM bosses WHERE id = ?", (boss_id,))
            boss = await cursor.fetchone()
            if not boss or boss["status"] != "defeated":
                await db.rollback()
                await cb.answer("Босс ещё не побеждён.", show_alert=True)
                return
            cursor = await db.execute("SELECT damage, country_id FROM boss_hits WHERE boss_id = ? AND user_id = ?", (boss_id, uid))
            hit = await cursor.fetchone()
            if not hit or hit["damage"] <= 0:
                await db.rollback()
                await cb.answer("Вы не участвовали.", show_alert=True)
                return
            cursor = await db.execute("SELECT 1 FROM boss_rewards_claimed WHERE boss_id = ? AND user_id = ?", (boss_id, uid))
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("Награда уже получена.", show_alert=True)
                return
            tier = boss["tier"]
            reward = BOSS_REWARD_CONFIG.get(tier, {"money": 0, "plasma": 0, "unique_chance": 0})
            participation_money = scale_income(int(min(50_000, hit["damage"] * 5) * BOSS_REWARD_MULTIPLIER))
            total_money = participation_money + reward["money"] * BOSS_REWARD_MULTIPLIER
            plasma_reward = reward["plasma"] * BOSS_REWARD_MULTIPLIER
            await db.execute("""
                UPDATE users
                SET balance = balance + ?, plasma = plasma + ?
                WHERE id = ?
            """, (total_money, plasma_reward, uid))
            if tier >= 4:
                unlock_until = int(time.time()) + 7 * 24 * 60 * 60
                await db.execute("""
                    UPDATE users
                    SET weapons_shop_unlocked = 1,
                        weapons_shop_unlock_until = CASE
                            WHEN weapons_shop_unlock_until > ? THEN weapons_shop_unlock_until
                            ELSE ?
                        END
                    WHERE id = ?
                """, (unlock_until, unlock_until, uid))
            unique_item_id = await maybe_award_unique_item(db, hit["country_id"], tier)
            await db.execute("INSERT INTO boss_rewards_claimed (boss_id, user_id) VALUES (?, ?)", (boss_id, uid))
            await db.execute("INSERT INTO processed_callbacks (id, ts) VALUES (?, ?)", (cb_id, int(time.time())))
            await db.commit()
        msg = f"Награды: +{total_money:,} денег, +{plasma_reward} плазмы."
        if unique_item_id:
            msg += f" Уникальный предмет: {UNIQUE_ITEM_CONFIG[unique_item_id]['name']}."
        await cb.answer(msg, show_alert=True)
        text, reply_markup = await build_boss_view(uid, boss_id)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    except Exception as e:
        logger.error(f"Ошибка получения награды босса: {e}")
        await cb.answer("Не удалось забрать награду.", show_alert=True)
@router.callback_query(F.data.startswith("select_country_"))
async def select_country_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    country_code = cb.data.split("_")[2]
    # Проверяем, не выбрал ли уже страну
    if await check_user_has_country(uid):
        await cb.answer("Вы уже выбрали страну!", show_alert=True)
        return
    # Создаем страну
    success = await create_user_country(uid, country_code)
    if success:
        # Получаем данные страны
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT name FROM countries WHERE owner_user_id = ?", (uid,))
            row = await cursor.fetchone()
            country_name = row[0] if row else "Неизвестная"
        text = f"""
🏰 <b>СТРАНА ВЫБРАНА!</b>
🌍 <b>Вы стали правителем страны "{country_name}"!</b>
Теперь вы можете развивать свою страну, собирать налоги, строить здания и участвовать в войнах.
Используйте <code>моя страна</code> для управления.
Добро пожаловать в MURASAKI EMPIRE! 🎉
"""
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Моя страна", callback_data="show_my_country")],
            [InlineKeyboardButton(text="🎮 Начать игру", callback_data="back_to_menu")]
        ])
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await cb.answer("Страна создана! Добро пожаловать!")
    else:
        await cb.answer("Ошибка создания страны. Попробуйте еще раз.", show_alert=True)
# ========== SPACE HANDLERS ==========
def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours <= 0:
        return f"{minutes}\u043c"
    return f"{hours}\u0447 {minutes}\u043c"
async def build_space_menu(uid: int):
    access, country_id, station_level = await get_user_space_access(uid)
    if not access:
        return None, None, None
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT plasma, plutonium, artifacts, tech_data, space_prestige FROM users WHERE id = ?",
            (uid,)
        )
        user = await cursor.fetchone()
        cursor = await db.execute("SELECT COUNT(1) FROM space_discoveries WHERE user_id = ?", (uid,))
        discoveries = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(1) FROM space_colonies WHERE owner_user_id = ?", (uid,))
        colonies = (await cursor.fetchone())[0]
        cursor = await db.execute(
            "SELECT COUNT(1) FROM space_expeditions WHERE user_id = ? AND status = 'active'",
            (uid,)
        )
        active = (await cursor.fetchone())[0]
        techs = await get_user_space_techs(db, uid)
        max_active = get_max_active_expeditions(station_level, techs)
    text = (
        f"\U0001F30C \u041a\u043e\u0441\u043c\u043e\u0441\\n\\n"
        f"\u0421\u0442\u0430\u043d\u0446\u0438\u044f: \u0443\u0440. {station_level}\\n"
        f"\u042d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0438: {active}/{max_active}\\n"
        f"\u041e\u0442\u043a\u0440\u044b\u0442\u0438\u044f: {discoveries}\\n"
        f"\u041a\u043e\u043b\u043e\u043d\u0438\u0438: {colonies}\\n\\n"
        f"\u0420\u0435\u0441\u0443\u0440\u0441\u044b:\\n"
        f"- \u041f\u043b\u0430\u0437\u043c\u0430: {user['plasma']}\\n"
        f"- \u041f\u043b\u0443\u0442\u043e\u043d\u0438\u0439: {user['plutonium']}\\n"
        f"- \u0410\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u044b: {user['artifacts']}\\n"
        f"- \u0422\u0435\u0445\u043d\u043e\u0434\u0430\u043d\u043d\u044b\u0435: {user['tech_data']}\\n"
        f"\u041f\u0440\u0435\u0441\u0442\u0438\u0436: {user['space_prestige']}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F680 \u042d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0438", callback_data="space_expeditions")],
        [InlineKeyboardButton(text="\u23F3 \u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u043f\u043e\u043b\u0451\u0442\u044b", callback_data="space_active")],
        [InlineKeyboardButton(text="\U0001F52D \u041e\u0442\u043a\u0440\u044b\u0442\u0438\u044f", callback_data="space_discoveries")],
        [InlineKeyboardButton(text="\U0001F3D7 \u041a\u043e\u043b\u043e\u043d\u0438\u0438", callback_data="space_colonies")],
        [InlineKeyboardButton(text="\U0001F4DA \u0422\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u0438", callback_data="space_tech")],
    ])
    return text, keyboard, country_id
async def show_space_menu_msg(msg: Message):
    text, reply_markup, _ = await build_space_menu(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u0431\u0435\u0437 \u043a\u043e\u0441\u043c\u043e\u0441\u0442\u0430\u043d\u0446\u0438\u0438.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().strip() == "\u043a\u043e\u0441\u043c\u043e\u0441")
async def space_text_cmd(msg: Message):
    await show_space_menu_msg(msg)
@router.message(F.text.lower().strip() == "\u044d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0438")
async def space_expeditions_text_cmd(msg: Message):
    await space_expeditions_msg(msg)
@router.message(F.text.lower().strip() == "\u043a\u043e\u043b\u043e\u043d\u0438\u0438")
async def space_colonies_text_cmd(msg: Message):
    await space_colonies_msg(msg)
@router.message(F.text.lower().strip() == "\u0442\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u0438")
async def space_tech_text_cmd(msg: Message):
    await space_tech_msg(msg)
@router.message(F.text.lower().strip() == "\u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f")
async def space_discoveries_text_cmd(msg: Message):
    await space_discoveries_msg(msg)
@router.callback_query(F.data == "space_menu")
async def space_menu_cb(cb: CallbackQuery):
    text, reply_markup, _ = await build_space_menu(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def space_expeditions_msg(msg: Message):
    text, reply_markup = await build_space_expeditions_view(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u0431\u0435\u0437 \u043a\u043e\u0441\u043c\u043e\u0441\u0442\u0430\u043d\u0446\u0438\u0438.")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "space_expeditions")
async def space_expeditions_cb(cb: CallbackQuery):
    text, reply_markup = await build_space_expeditions_view(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def build_space_expeditions_view(uid: int):
    access, country_id, station_level = await get_user_space_access(uid)
    if not access:
        return None, None
    async with aiosqlite.connect(DB_PATH) as db:
        techs = await get_user_space_techs(db, uid)
        max_active = get_max_active_expeditions(station_level, techs)
        cursor = await db.execute(
            "SELECT COUNT(1) FROM space_expeditions WHERE user_id = ? AND status = 'active'",
            (uid,)
        )
        active = (await cursor.fetchone())[0]
    text = (
        f"\U0001F680 \u042d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0438\\n"
        f"\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435: {active}/{max_active}\\n\\n"
        f"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u0438\u043f \u043f\u043e\u043b\u0435\u0442\u0430:\\n"
        f"- \u0434\u0435\u0448\u0451\u0432\u0430\u044f: 2\u0447\\n"
        f"- \u0441\u0440\u0435\u0434\u043d\u044f\u044f: 6\u0447\\n"
        f"- \u044d\u043b\u0438\u0442\u043d\u0430\u044f: 12-24\u0447\\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u0414\u0435\u0448\u0451\u0432\u0430\u044f", callback_data="start_space_expedition_cheap")],
        [InlineKeyboardButton(text="\u0421\u0440\u0435\u0434\u043d\u044f\u044f", callback_data="start_space_expedition_medium")],
        [InlineKeyboardButton(text="\u042d\u043b\u0438\u0442\u043d\u0430\u044f", callback_data="start_space_expedition_elite")],
        [InlineKeyboardButton(text="\u23F3 \u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u043f\u043e\u043b\u0451\u0442\u044b", callback_data="space_active")],
        [InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_menu")],
    ])
    return text, keyboard
@router.callback_query(F.data.startswith("start_space_expedition_"))
async def start_space_expedition_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    exp_type = cb.data.split("_")[-1]
    if exp_type not in SPACE_EXPEDITION_TYPES:
        await cb.answer("\u0422\u0438\u043f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d", show_alert=True)
        return
    access, country_id, station_level = await get_user_space_access(uid)
    if not access:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")
            techs = await get_user_space_techs(db, uid)
            max_active = get_max_active_expeditions(station_level, techs)
            cursor = await db.execute(
                "SELECT COUNT(1) FROM space_expeditions WHERE user_id = ? AND status = 'active'",
                (uid,)
            )
            active = (await cursor.fetchone())[0]
            if active >= max_active:
                await db.rollback()
                await cb.answer("\u041b\u0438\u043c\u0438\u0442 \u044d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0439", show_alert=True)
                return
            cfg = SPACE_EXPEDITION_TYPES[exp_type]
            hours = cfg["min_hours"] if cfg["min_hours"] == cfg["max_hours"] else random.randint(cfg["min_hours"], cfg["max_hours"])
            now = int(time.time())
            ends_at = now + hours * 3600
            await db.execute(
                "INSERT INTO space_expeditions (user_id, country_id, expedition_type, started_at, ends_at, status) VALUES (?, ?, ?, ?, ?, 'active')",
                (uid, country_id, exp_type, now, ends_at)
            )
            await db.commit()
        await cb.answer("\u042d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u044f \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0430", show_alert=False)
        text, reply_markup = await build_space_expeditions_view(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка запуска космоэкспедиции: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430", show_alert=True)
async def space_active_msg(msg: Message):
    text, reply_markup = await build_space_active_view(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "space_active")
async def space_active_cb(cb: CallbackQuery):
    text, reply_markup = await build_space_active_view(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def build_space_active_view(uid: int):
    access, _, _ = await get_user_space_access(uid)
    if not access:
        return None, None
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM space_expeditions WHERE user_id = ? ORDER BY id DESC LIMIT 10", (uid,))
        rows = await cursor.fetchall()
    text = "\u23F3 \u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u043f\u043e\u043b\u0451\u0442\u044b\\n\\n"
    keyboard = []
    if not rows:
        text += "\u041d\u0435\u0442 \u044d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0439."
    for exp in rows:
        exp_type = exp["expedition_type"]
        status = exp["status"]
        remain = exp["ends_at"] - now
        if status == "active" and remain > 0:
            text += f"ID {exp['id']} - {SPACE_EXPEDITION_TYPES[exp_type]['name']}: \u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {format_duration(remain)}\\n"
        else:
            text += f"ID {exp['id']} - {SPACE_EXPEDITION_TYPES[exp_type]['name']}: \u0433\u043e\u0442\u043e\u0432\u043e\\n"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"\u2705 \u0417\u0430\u0431\u0440\u0430\u0442\u044c ID {exp['id']}",
                    callback_data=f"claim_space_expedition_{exp['id']}"
                )
            ])
    keyboard.append([InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data.startswith("claim_space_expedition_"))
async def claim_space_expedition_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    exp_id = int(cb.data.split("_")[-1])
    now = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM space_expeditions WHERE id = ? AND user_id = ?", (exp_id, uid))
            exp = await cursor.fetchone()
            if not exp:
                await db.rollback()
                await cb.answer("\u042d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u044f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430", show_alert=True)
                return
            if exp["status"] == "active" and exp["ends_at"] > now:
                await db.rollback()
                await cb.answer("\u0420\u0430\u043d\u043e \u0437\u0430\u0431\u0438\u0440\u0430\u0442\u044c \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442", show_alert=True)
                return
            cursor = await db.execute("SELECT * FROM space_expedition_results WHERE expedition_id = ?", (exp_id,))
            result = await cursor.fetchone()
            if not result:
                techs = await get_user_space_techs(db, uid)
                station_level = await get_space_station_level(db, exp["country_id"])
                outcome_data = resolve_expedition_outcome(exp["expedition_type"], station_level, techs)
                outcome = outcome_data["outcome"]
                loot = outcome_data["loot"]
                discovery = outcome_data["discovery"]
                discovery_id = None
                if discovery:
                    desc = discovery.get("description")
                    if desc == "unknown":
                        desc = "\u0421\u0438\u0433\u043c\u0430-\u0430\u043d\u043e\u043c\u0430\u043b\u0438\u044f. \u041e\u0449\u0443\u0449\u0435\u043d\u0438\u0435 \u0443\u0433\u0440\u043e\u0437\u044b."
                    await db.execute(
                        "INSERT INTO space_discoveries (user_id, discovery_type, rarity, description, discovered_at, status) VALUES (?, ?, ?, ?, ?, 'new')",
                        (uid, discovery["type"], discovery["rarity"], desc, now)
                    )
                    cursor = await db.execute("SELECT last_insert_rowid()")
                    discovery_id = (await cursor.fetchone())[0]
                if outcome in ("success", "partial"):
                    await db.execute(
                        "UPDATE users SET plasma = plasma + ?, plutonium = plutonium + ?, artifacts = artifacts + ?, tech_data = tech_data + ? WHERE id = ?",
                        (loot["plasma"], loot["plutonium"], loot["artifacts"], loot["tech_data"], uid)
                    )
                    await db.execute(
                        "UPDATE users SET space_prestige = space_prestige + ? WHERE id = ?",
                        (2 if outcome == "success" else 1, uid)
                    )
                    if discovery_id:
                        await db.execute("UPDATE users SET space_prestige = space_prestige + 1 WHERE id = ?", (uid,))
                else:
                    await db.execute("UPDATE users SET space_prestige = space_prestige + 1 WHERE id = ?", (uid,))
                status = "finished" if outcome in ("success", "partial") else "failed"
                message = outcome
                await db.execute("UPDATE space_expeditions SET status = ? WHERE id = ?", (status, exp_id))
                await db.execute(
                    "INSERT INTO space_expedition_results (expedition_id, outcome, loot_plasma, loot_plutonium, loot_artifacts, loot_tech, discovery_id, message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (exp_id, outcome, loot["plasma"], loot["plutonium"], loot["artifacts"], loot["tech_data"], discovery_id, message, now)
                )
                await db.commit()
                result = {
                    "outcome": outcome,
                    "loot_plasma": loot["plasma"],
                    "loot_plutonium": loot["plutonium"],
                    "loot_artifacts": loot["artifacts"],
                    "loot_tech": loot["tech_data"],
                    "discovery_id": discovery_id
                }
            else:
                await db.commit()
        outcome = result["outcome"] if isinstance(result, dict) else result["outcome"]
        loot_plasma = result["loot_plasma"] if isinstance(result, dict) else result["loot_plasma"]
        loot_plutonium = result["loot_plutonium"] if isinstance(result, dict) else result["loot_plutonium"]
        loot_artifacts = result["loot_artifacts"] if isinstance(result, dict) else result["loot_artifacts"]
        loot_tech = result["loot_tech"] if isinstance(result, dict) else result["loot_tech"]
        discovery_id = result["discovery_id"] if isinstance(result, dict) else result["discovery_id"]
        outcome_text = {
            "success": "\u0423\u0441\u043f\u0435\u0445",
            "partial": "\u0427\u0430\u0441\u0442\u0438\u0447\u043d\u044b\u0439 \u0443\u0441\u043f\u0435\u0445",
            "ship_lost": "\u041f\u043e\u0442\u0435\u0440\u044f \u043a\u043e\u0440\u0430\u0431\u043b\u044f",
            "crew_dead": "\u0413\u0438\u0431\u0435\u043b\u044c \u044d\u043a\u0438\u043f\u0430\u0436\u0430",
            "threat": "\u041e\u0442\u043a\u0440\u044b\u0442\u0438\u0435 \u0443\u0433\u0440\u043e\u0437\u044b"
        }.get(outcome, outcome)
        text = (
            f"\u2705 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u044d\u043a\u0441\u043f\u0435\u0434\u0438\u0446\u0438\u0438\\n\\n"
            f"\u0418\u0442\u043e\u0433: {outcome_text}\\n"
            f"\u041b\u0443\u0442: \u043f\u043b\u0430\u0437\u043c\u0430 +{loot_plasma}, \u043f\u043b\u0443\u0442\u043e\u043d\u0438\u0439 +{loot_plutonium}, \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u044b +{loot_artifacts}, \u0442\u0435\u0445\u043d\u043e\u0434\u0430\u043d\u043d\u044b\u0435 +{loot_tech}\\n"
        )
        if discovery_id:
            text += f"\u041e\u0442\u043a\u0440\u044b\u0442\u0438\u0435 ID {discovery_id}\\n"
        await cb.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_active")]
            ])
        )
        await cb.answer()
        await check_and_award_titles(uid)
    except Exception as e:
        logger.error(f"Ошибка claim_space_expedition_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u0432\u044b\u0434\u0430\u0447\u0438", show_alert=True)
async def space_discoveries_msg(msg: Message):
    text, reply_markup = await build_space_discoveries_view(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "space_discoveries")
async def space_discoveries_cb(cb: CallbackQuery):
    text, reply_markup = await build_space_discoveries_view(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def build_space_discoveries_view(uid: int):
    access, _, _ = await get_user_space_access(uid)
    if not access:
        return None, None
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM space_discoveries WHERE user_id = ? ORDER BY id DESC LIMIT 10", (uid,))
        rows = await cursor.fetchall()
    text = "\u2728 \u041e\u0442\u043a\u0440\u044b\u0442\u0438\u044f\\n\\n"
    keyboard = []
    if not rows:
        text += "\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u0439."
    for d in rows:
        status = d["status"]
        text += f"ID {d['id']} - {d['discovery_type']} ({d['rarity']}) [{status}]\\n"
        keyboard.append([InlineKeyboardButton(text=f"ID {d['id']}", callback_data=f"space_discovery_{d['id']}")])
    keyboard.append([InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data.startswith("space_discovery_"))
async def space_discovery_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    disc_id = int(cb.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM space_discoveries WHERE id = ? AND user_id = ?", (disc_id, uid))
        d = await cursor.fetchone()
    if not d:
        await cb.answer("\u041e\u0442\u043a\u0440\u044b\u0442\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e", show_alert=True)
        return
    text = f"\u2728 ID {d['id']}\\n\\n{d['description']}\\n\\n\u0421\u0442\u0430\u0442\u0443\u0441: {d['status']}"
    keyboard = []
    if d["status"] == "new":
        if d["discovery_type"] == "planet":
            keyboard.append([InlineKeyboardButton(text="\U0001F50E \u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u044c", callback_data=f"space_discovery_action_{disc_id}_deep")])
            keyboard.append([InlineKeyboardButton(text="\U0001F4C4 \u0417\u0430\u0431\u0440\u0430\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435", callback_data=f"space_discovery_action_{disc_id}_data")])
            keyboard.append([InlineKeyboardButton(text="\U0001F6A7 \u041f\u043e\u043f\u044b\u0442\u0430\u0442\u044c\u0441\u044f \u043a\u043e\u043b\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c", callback_data=f"space_discovery_action_{disc_id}_colonize")])
        else:
            keyboard.append([InlineKeyboardButton(text="\U0001F50E \u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u044c", callback_data=f"space_discovery_action_{disc_id}_deep")])
            keyboard.append([InlineKeyboardButton(text="\U0001F4C4 \u0417\u0430\u0431\u0440\u0430\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435", callback_data=f"space_discovery_action_{disc_id}_data")])
    keyboard.append([InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_discoveries")])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await cb.answer()
@router.callback_query(F.data.startswith("space_discovery_action_"))
async def space_discovery_action_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    parts = cb.data.split("_")
    disc_id = int(parts[3])
    action = parts[4]
    now = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM space_discoveries WHERE id = ? AND user_id = ?", (disc_id, uid))
            d = await cursor.fetchone()
            if not d:
                await db.rollback()
                await cb.answer("\u041e\u0442\u043a\u0440\u044b\u0442\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e", show_alert=True)
                return
            if d["status"] != "new":
                await db.rollback()
                await cb.answer("\u0423\u0436\u0435 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u043d\u043e", show_alert=True)
                return
            message = ""
            if action == "data":
                gain = scale_income(random.randint(1, 3))
                await db.execute("UPDATE users SET tech_data = tech_data + ? WHERE id = ?", (gain, uid))
                message = f"\u0414\u0430\u043d\u043d\u044b\u0435 \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u044b: +{gain}"
            elif action == "deep":
                if random.random() < 0.3:
                    message = "\u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0432\u0430\u043b\u0438\u043b\u043e\u0441\u044c"
                else:
                    loot_plasma = scale_income(random.randint(1, 4))
                    loot_plutonium = scale_income(random.randint(0, 2))
                    loot_artifacts = scale_income(random.randint(0, 2))
                    await db.execute(
                        "UPDATE users SET plasma = plasma + ?, plutonium = plutonium + ?, artifacts = artifacts + ? WHERE id = ?",
                        (loot_plasma, loot_plutonium, loot_artifacts, uid)
                    )
                    message = f"\u0414\u043e\u0431\u044b\u0442\u043e: \u043f\u043b\u0430\u0437\u043c\u0430 +{loot_plasma}, \u043f\u043b\u0443\u0442\u043e\u043d\u0438\u0439 +{loot_plutonium}, \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u044b +{loot_artifacts}"
            elif action == "colonize":
                if d["discovery_type"] != "planet":
                    await db.rollback()
                    await cb.answer("\u041d\u0435\u043b\u044c\u0437\u044f \u043a\u043e\u043b\u043e\u043d\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c", show_alert=True)
                    return
                cursor = await db.execute("SELECT COUNT(1) FROM space_colonies WHERE owner_user_id = ?", (uid,))
                count = (await cursor.fetchone())[0]
                if count >= SPACE_MAX_COLONIES:
                    await db.rollback()
                    await cb.answer("\u041b\u0438\u043c\u0438\u0442 \u043a\u043e\u043b\u043e\u043d\u0438\u0439", show_alert=True)
                    return
                colony_type = random.choice(list(SPACE_COLONY_TYPES.keys()))
                stability = random.randint(60, 90)
                await db.execute(
                    "INSERT INTO space_colonies (owner_user_id, colony_type, stability, bonus_type, created_at, last_yield) VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, colony_type, stability, SPACE_COLONY_TYPES[colony_type]["bonus_type"], now, now)
                )
                await db.execute("UPDATE users SET space_prestige = space_prestige + 3 WHERE id = ?", (uid,))
                message = f"\u041a\u043e\u043b\u043e\u043d\u0438\u044f \u043e\u0441\u043d\u043e\u0432\u0430\u043d\u0430: {SPACE_COLONY_TYPES[colony_type]['name']}"
            else:
                await db.rollback()
                await cb.answer("\u041d\u0435\u0432\u0435\u0440\u043d\u043e\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435", show_alert=True)
                return
            await db.execute("UPDATE space_discoveries SET status = 'resolved', resolved_at = ? WHERE id = ?", (now, disc_id))
            await db.commit()
        await cb.answer(message, show_alert=True)
        await check_and_award_titles(uid)
        text, reply_markup = await build_space_discoveries_view(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка space_discovery_action_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
async def space_colonies_msg(msg: Message):
    text, reply_markup = await build_space_colonies_view(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "space_colonies")
async def space_colonies_cb(cb: CallbackQuery):
    text, reply_markup = await build_space_colonies_view(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def build_space_colonies_view(uid: int):
    access, _, _ = await get_user_space_access(uid)
    if not access:
        return None, None
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM space_colonies WHERE owner_user_id = ? ORDER BY id DESC", (uid,))
        rows = await cursor.fetchall()
    text = "\U0001F3E0 \u041a\u043e\u043b\u043e\u043d\u0438\u0438\\n\\n"
    keyboard = []
    if not rows:
        text += "\u041d\u0435\u0442 \u043a\u043e\u043b\u043e\u043d\u0438\u0439."
    for c in rows:
        name = SPACE_COLONY_TYPES.get(c["colony_type"], {}).get("name", c["colony_type"])
        text += f"ID {c['id']} - {name}, \u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0441\u0442\u044c {c['stability']}\\n"
        keyboard.append([InlineKeyboardButton(text=f"\U0001F4E6 \u0421\u0431\u043e\u0440 ID {c['id']}", callback_data=f"space_colony_collect_{c['id']}")])
    keyboard.append([InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data.startswith("space_colony_collect_"))
async def space_colony_collect_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    colony_id = int(cb.data.split("_")[-1])
    now = int(time.time())
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute("SELECT * FROM space_colonies WHERE id = ? AND owner_user_id = ?", (colony_id, uid))
            col = await cursor.fetchone()
            if not col:
                await db.rollback()
                await cb.answer("\u041a\u043e\u043b\u043e\u043d\u0438\u044f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430", show_alert=True)
                return
            elapsed = max(0, now - (col["last_yield"] or col["created_at"]))
            hours = min(24, elapsed // 3600)
            if hours <= 0:
                await db.rollback()
                await cb.answer("\u0420\u0430\u043d\u043e \u0441\u043e\u0431\u0438\u0440\u0430\u0442\u044c", show_alert=True)
                return
            base = SPACE_COLONY_TYPES.get(col["colony_type"])
            if not base:
                await db.rollback()
                await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430 \u043a\u043e\u043b\u043e\u043d\u0438\u0438", show_alert=True)
                return
            stability_factor = max(0.5, min(1.2, col["stability"] / 100))
            gain_plasma = int(base["yield_plasma"] * hours * stability_factor)
            gain_plutonium = int(base["yield_plutonium"] * hours * stability_factor)
            gain_artifacts = int(base["yield_artifacts"] * hours * stability_factor)
            gain_tech = int(base["yield_tech"] * hours * stability_factor)
            await db.execute(
                "UPDATE users SET plasma = plasma + ?, plutonium = plutonium + ?, artifacts = artifacts + ?, tech_data = tech_data + ? WHERE id = ?",
                (gain_plasma, gain_plutonium, gain_artifacts, gain_tech, uid)
            )
            await db.execute("UPDATE space_colonies SET last_yield = ? WHERE id = ?", (now, colony_id))
            if random.random() < 0.05:
                await db.execute("DELETE FROM space_colonies WHERE id = ?", (colony_id,))
                message = "\u041a\u043e\u043b\u043e\u043d\u0438\u044f \u043f\u043e\u0442\u0435\u0440\u044f\u043d\u0430 \u0438\u0437-\u0437\u0430 \u043a\u0430\u0442\u0430\u0441\u0442\u0440\u043e\u0444\u044b."
            else:
                new_stability = max(0, col["stability"] - random.randint(0, 2))
                await db.execute("UPDATE space_colonies SET stability = ? WHERE id = ?", (new_stability, colony_id))
                message = f"\u0421\u043e\u0431\u0440\u0430\u043d\u043e: \u043f\u043b\u0430\u0437\u043c\u0430 +{gain_plasma}, \u043f\u043b\u0443\u0442\u043e\u043d\u0438\u0439 +{gain_plutonium}, \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u044b +{gain_artifacts}, \u0442\u0435\u0445\u043d\u043e\u0434\u0430\u043d\u043d\u044b\u0435 +{gain_tech}"
            await db.commit()
        await cb.answer(message, show_alert=True)
        text, reply_markup = await build_space_colonies_view(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка space_colony_collect_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
async def space_tech_msg(msg: Message):
    text, reply_markup = await build_space_tech_view(msg.from_user.id)
    if not text:
        await msg.reply("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d")
        return
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "space_tech")
async def space_tech_cb(cb: CallbackQuery):
    text, reply_markup = await build_space_tech_view(cb.from_user.id)
    if not text:
        await cb.answer("\u041a\u043e\u0441\u043c\u043e\u0441 \u043d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d", show_alert=True)
        return
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
async def build_space_tech_view(uid: int):
    access, _, _ = await get_user_space_access(uid)
    if not access:
        return None, None
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT plasma, plutonium FROM users WHERE id = ?", (uid,))
        user = await cursor.fetchone()
        techs = await get_user_space_techs(db, uid)
    text = "\U0001F4D6 \u0422\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u0438\\n\\n"
    text += f"\u0420\u0435\u0441\u0443\u0440\u0441\u044b: \u043f\u043b\u0430\u0437\u043c\u0430 {user['plasma']}, \u043f\u043b\u0443\u0442\u043e\u043d\u0438\u0439 {user['plutonium']}\\n\\n"
    keyboard = []
    for tech in SPACE_TECH_CONFIG:
        status = "\u2705" if tech["tech_code"] in techs else "\u274C"
        text += f"{status} {tech['name']} - \u0446\u0435\u043d\u0430 {tech['cost_plasma']}\u043f + {tech['cost_plutonium']}\u043f\\n"
        if tech["tech_code"] not in techs:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"\u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u044c {tech['name']}",
                    callback_data=f"research_space_tech_{tech['tech_code']}"
                )
            ])
    keyboard.append([InlineKeyboardButton(text="\u2190 \u041d\u0430\u0437\u0430\u0434", callback_data="space_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data.startswith("research_space_tech_"))
async def research_space_tech_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    tech_code = cb.data.split("_")[-1]
    tech = next((t for t in SPACE_TECH_CONFIG if t["tech_code"] == tech_code), None)
    if not tech:
        await cb.answer("\u0422\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u044f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430", show_alert=True)
        return
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT researched FROM user_space_tech WHERE user_id = ? AND tech_code = ?",
                (uid, tech_code)
            )
            if await cursor.fetchone():
                await db.rollback()
                await cb.answer("\u0423\u0436\u0435 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u043e", show_alert=True)
                return
            cursor = await db.execute("SELECT plasma, plutonium FROM users WHERE id = ?", (uid,))
            user = await cursor.fetchone()
            if user["plasma"] < tech["cost_plasma"] or user["plutonium"] < tech["cost_plutonium"]:
                await db.rollback()
                await cb.answer("\u041d\u0435\u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u0440\u0435\u0441\u0443\u0440\u0441\u043e\u0432", show_alert=True)
                return
            await db.execute(
                "UPDATE users SET plasma = plasma - ?, plutonium = plutonium - ? WHERE id = ?",
                (tech["cost_plasma"], tech["cost_plutonium"], uid)
            )
            await db.execute(
                "INSERT OR REPLACE INTO user_space_tech (user_id, tech_code, researched) VALUES (?, ?, 1)",
                (uid, tech_code)
            )
            await db.commit()
        await cb.answer("\u0422\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u044f \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0430", show_alert=True)
        text, reply_markup = await build_space_tech_view(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка research_space_tech_cb: {e}")
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
def get_pickaxe_config(level: int):
    for pick in PICKAXE_CONFIG:
        if pick["level"] == level:
            return pick
    return None
async def build_mine_panel(uid: int):
    user = await get_user(uid)
    pickaxe_level = int(user.get("pickaxe_level", 0) or 0)
    pickaxe = get_pickaxe_config(pickaxe_level)
    pickaxe_name = pickaxe["name"] if pickaxe else "Нет кирки"
    now = int(time.time())
    last_ts = int(user.get("mine_last_ts", 0) or 0)
    cooldown_left = max(0, ORE_MINE_COOLDOWN - (now - last_ts)) if last_ts else 0
    if not pickaxe:
        cooldown_text = "Сначала купите кирку в магазине."
    elif cooldown_left > 0:
        cooldown_text = f"Копать можно через {format_duration(cooldown_left)}."
    else:
        cooldown_text = "Копать можно сейчас."
    ore_lines = []
    total_value = 0
    for key in ORE_KEYS:
        count = int(user.get(f"ore_{key}", 0) or 0)
        if count > 0:
            ore = ORE_CONFIG[key]
            ore_lines.append(f"• {ore['name']}: {count} шт.")
            total_value += count * ore["price"]
    text = "⛏️ <b>Шахта</b>\n\n"
    text += f"Кирка: <b>{pickaxe_name}</b>\n"
    text += f"{cooldown_text}\n\n"
    text += "<b>Руды:</b>\n"
    if ore_lines:
        text += "\n".join(ore_lines)
        text += f"\n\nИтого: {format_money(total_value)}"
    else:
        text += "Пока нет."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⛏️ Копать", callback_data="mine_dig"),
            InlineKeyboardButton(text="🛒 Магазин кирок", callback_data="mine_shop")
        ],
        [InlineKeyboardButton(text="💰 Продать руду", callback_data="mine_sell")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    return text, keyboard
async def build_mine_shop(uid: int):
    user = await get_user(uid)
    pickaxe_level = int(user.get("pickaxe_level", 0) or 0)
    next_pickaxe = get_pickaxe_config(pickaxe_level + 1)
    text = "🛒 <b>Магазин кирок</b>\n\n"
    for pick in PICKAXE_CONFIG:
        status = " ✅ текущая" if pick["level"] == pickaxe_level else ""
        text += f"{pick['name']} — {format_money(pick['price'])}{status}\n"
    keyboard = []
    if next_pickaxe:
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {next_pickaxe['name']} за {format_money(next_pickaxe['price'])}",
                callback_data=f"mine_buy_pickaxe_{next_pickaxe['level']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="mine_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_mine_sell_menu(uid: int):
    user = await get_user(uid)
    total_value = 0
    rows = []
    for key in ORE_KEYS:
        count = int(user.get(f"ore_{key}", 0) or 0)
        if count > 0:
            ore = ORE_CONFIG[key]
            total_value += count * ore["price"]
            rows.append((key, ore, count))
    text = "💰 <b>Продажа руды</b>\n\n"
    if not rows:
        text += "У вас нет руды."
        keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="mine_menu")]]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    for _, ore, count in rows:
        text += f"{ore['name']}: {count} шт. (цена {format_money(ore['price'])} за 1)\n"
    text += f"\nИтого: {format_money(total_value)}"
    keyboard = [[InlineKeyboardButton(text="Продать все руды", callback_data="mine_sell_all")]]
    for key, ore, _ in rows:
        keyboard.append([
            InlineKeyboardButton(text=f"Продать 1 {ore['name']}", callback_data=f"mine_sell_{key}_one"),
            InlineKeyboardButton(text=f"Продать все {ore['name']}", callback_data=f"mine_sell_{key}_all")
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="mine_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.message(Command("mine"))
@router.message(Command("шахта"))
async def mine_cmd(msg: Message):
    logger.info(f"CMD mine hit uid={msg.from_user.id} text={msg.text!r}")
    text, reply_markup = await build_mine_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.message(F.text.lower().startswith(("шахта", "mine", "/шахта", "/mine")))
async def mine_text_cmd(msg: Message):
    logger.info(f"CMD mine text hit uid={msg.from_user.id} text={msg.text!r}")
    text, reply_markup = await build_mine_panel(msg.from_user.id)
    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "mine_menu")
async def mine_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_mine_panel(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "mine_dig")
async def mine_dig_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    user = await get_user(uid)
    pickaxe_level = int(user.get("pickaxe_level", 0) or 0)
    if pickaxe_level <= 0:
        await cb.answer("Нужна кирка. Откройте магазин.", show_alert=True)
        return
    now = int(time.time())
    last_ts = int(user.get("mine_last_ts", 0) or 0)
    if last_ts and now - last_ts < ORE_MINE_COOLDOWN:
        remaining = ORE_MINE_COOLDOWN - (now - last_ts)
        await cb.answer(f"⏳ До следующего копания: {format_duration(remaining)}", show_alert=True)
        return
    pickaxe = get_pickaxe_config(pickaxe_level)
    ore_key = random.choices(ORE_KEYS, weights=pickaxe["weights"], k=1)[0]
    ore = ORE_CONFIG[ore_key]
    ore_field = f"ore_{ore_key}"
    max_qty = min(15, 3 + pickaxe_level * 3)
    qty = scale_mining_qty(random.randint(1, max_qty))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            f"UPDATE users SET {ore_field} = {ore_field} + ?, mine_last_ts = ? WHERE id = ?",
            (qty, now, uid)
        )
        await db.commit()
    await cb.answer(f"⛏️ Добыто: {ore['name']} (+{qty})", show_alert=True)
    text, reply_markup = await build_mine_panel(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "mine_shop")
async def mine_shop_cb(cb: CallbackQuery):
    text, reply_markup = await build_mine_shop(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("mine_buy_pickaxe_"))
async def mine_buy_pickaxe_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        level = int(cb.data.split("_")[3])
    except Exception:
        await cb.answer("Ошибка покупки кирки.", show_alert=True)
        return
    user = await get_user(uid)
    current_level = int(user.get("pickaxe_level", 0) or 0)
    if level != current_level + 1:
        await cb.answer("Можно купить только следующий уровень.", show_alert=True)
        return
    pickaxe = get_pickaxe_config(level)
    if not pickaxe:
        await cb.answer("Кирка не найдена.", show_alert=True)
        return
    if user.get("balance", 0) < pickaxe["price"]:
        await cb.answer("Недостаточно средств.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ?, pickaxe_level = ? WHERE id = ?",
            (pickaxe["price"], level, uid)
        )
        await db.commit()
    await cb.answer(f"Кирка куплена: {pickaxe['name']}", show_alert=True)
    text, reply_markup = await build_mine_shop(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "mine_sell")
async def mine_sell_cb(cb: CallbackQuery):
    text, reply_markup = await build_mine_sell_menu(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("mine_sell_"))
async def mine_sell_action_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    if cb.data == "mine_sell_all":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT " + ", ".join([f"ore_{k}" for k in ORE_KEYS]) + " FROM users WHERE id = ?",
                (uid,)
            )
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                await cb.answer("Ошибка продажи.", show_alert=True)
                return
            total_value = 0
            for k in ORE_KEYS:
                total_value += int(row[f"ore_{k}"] or 0) * ORE_CONFIG[k]["price"]
            if total_value <= 0:
                await db.rollback()
                await cb.answer("Нет руды для продажи.", show_alert=True)
                return
            set_clause = ", ".join([f"ore_{k} = 0" for k in ORE_KEYS])
            await db.execute(
                f"UPDATE users SET {set_clause}, balance = balance + ? WHERE id = ?",
                (total_value, uid)
            )
            await db.commit()
        await cb.answer(f"Продано на {format_money(total_value)}.", show_alert=True)
        text, reply_markup = await build_mine_sell_menu(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        return
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("Ошибка продажи.", show_alert=True)
        return
    ore_key = parts[2]
    mode = parts[3]
    if ore_key not in ORE_CONFIG or mode not in {"one", "all"}:
        await cb.answer("Ошибка продажи.", show_alert=True)
        return
    ore = ORE_CONFIG[ore_key]
    ore_field = f"ore_{ore_key}"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            f"SELECT {ore_field} FROM users WHERE id = ?",
            (uid,)
      )
        row = await cursor.fetchone()
        count = int(row[ore_field] or 0) if row else 0
        if count <= 0:
            await db.rollback()
            await cb.answer("Нет руды для продажи.", show_alert=True)
            return
    qty = 1 if mode == "one" else count
    value = qty * ore["price"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {ore_field} = {ore_field} - ?, balance = balance + ? WHERE id = ?",
            (qty, value, uid)
        )
        await db.commit()
    await cb.answer(f"Продано: {ore['name']} x{qty} за {format_money(value)}.", show_alert=True)
    text, reply_markup = await build_mine_sell_menu(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
def get_fishing_boat_config(level: int):
    for boat in FISHING_BOATS:
        if boat["level"] == level:
            return boat
    return None
def get_fishing_rod_config(level: int):
    for rod in FISHING_RODS:
        if rod["level"] == level:
            return rod
    return None
def get_fishing_tackle_config(level: int):
    for tackle in FISHING_TACKLE:
        if tackle["level"] == level:
            return tackle
    return None
def get_fishing_location(index: int):
    for loc in FISHING_LOCATIONS:
        if loc["index"] == index:
            return loc
    return None
def get_max_fishing_location(boat_level: int) -> int:
    max_index = 1
    for loc in FISHING_LOCATIONS:
        if boat_level >= loc["required_boat_level"]:
            max_index = max(max_index, loc["index"])
    return max_index
def get_fishing_level(exp: int) -> int:
    return max(1, exp // FISHING_EXP_PER_LEVEL + 1)
def get_fishing_catch_count(rod_level: int) -> int:
    base_weights = [70, 15, 8, 5, 2]
    bonus = max(0, min(rod_level, 10))
    weights = base_weights[:]
    for i in range(1, 5):
        weights[i] += bonus * 2
    weights[0] = max(10, weights[0] - bonus * 4)
    count = random.choices([1, 2, 3, 4, 5], weights=weights, k=1)[0]
    return max(1, int(round(count * INCOME_MULTIPLIER)))
def format_short_seconds(seconds: int) -> str:
    if seconds <= 0:
        return "0 сек."
    return f"{seconds} сек."
async def build_fishing_panel(uid: int):
    user = await get_user(uid)
    boat_level = int(user.get("fishing_boat_level", 0) or 0)
    rod_level = int(user.get("fishing_rod_level", 0) or 0)
    tackle_level = int(user.get("fishing_tackle_level", 0) or 0)
    boat = get_fishing_boat_config(boat_level)
    rod = get_fishing_rod_config(rod_level)
    tackle = get_fishing_tackle_config(tackle_level)
    location_index = int(user.get("fishing_location", 1) or 1)
    max_location = get_max_fishing_location(boat_level)
    if location_index > max_location:
        location_index = max_location
    location = get_fishing_location(location_index)
    exp = int(user.get("fishing_exp", 0) or 0)
    level = get_fishing_level(exp)
    exp_in_level = exp - (level - 1) * FISHING_EXP_PER_LEVEL
    now = int(time.time())
    last_ts = int(user.get("fishing_last_ts", 0) or 0)
    cooldown_left = max(0, FISHING_COOLDOWN - (now - last_ts)) if last_ts else 0
    total_value = 0
    total_count = 0
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT fish_code, count FROM user_fish WHERE user_id = ? AND count > 0",
            (uid,)
        )
        rows = await cursor.fetchall()
    for row in rows:
        fish = FISH_BY_CODE.get(row["fish_code"])
        if not fish:
            continue
        count = int(row["count"] or 0)
        total_count += count
        total_value += count * fish["price"]
    boat_name = boat["name"] if boat else "Нет лодки"
    rod_name = rod["name"] if rod else "Нет удочки"
    tackle_name = tackle["name"] if tackle else "Нет снастей"
    location_name = location["name"] if location and boat_level > 0 else "Недоступна"
    text = "🎣 <b>Рыбалка</b>\n\n"
    text += f"Лодка: <b>{boat_name}</b>\n"
    text += f"Удочка: <b>{rod_name}</b>\n"
    text += f"Снасти: <b>{tackle_name}</b>\n"
    text += f"Локация: <b>{location_name}</b>\n"
    text += f"Уровень рыбака: <b>{level}</b> ({exp_in_level}/{FISHING_EXP_PER_LEVEL})\n"
    text += f"Улов: <b>{total_count}</b> шт. ({format_money(total_value)})\n"
    if boat_level <= 0 or rod_level <= 0:
        text += "\nНужны лодка и удочка, чтобы ловить рыбу."
    elif cooldown_left > 0:
        text += f"\nДо следующей попытки: {format_short_seconds(cooldown_left)}."
    else:
        text += "\nМожно ловить рыбу."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎣 Ловить рыбу", callback_data="fishing_catch")],
        [
            InlineKeyboardButton(text="🛶 Магазин лодок", callback_data="fishing_shop_boats"),
            InlineKeyboardButton(text="🎣 Магазин удочек", callback_data="fishing_shop_rods")
        ],
        [
            InlineKeyboardButton(text="🧰 Магазин снастей", callback_data="fishing_shop_tackle"),
            InlineKeyboardButton(text="🗺 Локации", callback_data="fishing_locations")
        ],
        [InlineKeyboardButton(text="💰 Продать рыбу", callback_data="fishing_sell")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    return text, keyboard
async def build_fishing_boat_shop(uid: int):
    user = await get_user(uid)
    current_level = int(user.get("fishing_boat_level", 0) or 0)
    next_boat = get_fishing_boat_config(current_level + 1)
    text = "🛶 <b>Магазин лодок</b>\n\n"
    for boat in FISHING_BOATS:
        status = " ✅" if boat["level"] == current_level else ""
        text += f"{boat['name']} - {format_money(boat['price'])}{status}\n"
    keyboard = []
    if next_boat:
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {next_boat['name']} за {format_money(next_boat['price'])}",
                callback_data=f"fishing_buy_boat_{next_boat['level']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_fishing_rod_shop(uid: int):
    user = await get_user(uid)
    current_level = int(user.get("fishing_rod_level", 0) or 0)
    next_rod = get_fishing_rod_config(current_level + 1)
    text = "🎣 <b>Магазин удочек</b>\n\n"
    for rod in FISHING_RODS:
        status = " ✅" if rod["level"] == current_level else ""
        text += f"{rod['name']} - {format_money(rod['price'])}{status}\n"
    keyboard = []
    if next_rod:
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {next_rod['name']} за {format_money(next_rod['price'])}",
                callback_data=f"fishing_buy_rod_{next_rod['level']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_fishing_tackle_shop(uid: int):
    user = await get_user(uid)
    current_level = int(user.get("fishing_tackle_level", 0) or 0)
    next_tackle = get_fishing_tackle_config(current_level + 1)
    text = "🧰 <b>Магазин снастей</b>\n\n"
    for tackle in FISHING_TACKLE:
        status = " ✅" if tackle["level"] == current_level else ""
        text += f"{tackle['name']} - {format_money(tackle['price'])}{status}\n"
    keyboard = []
    if next_tackle:
        keyboard.append([
            InlineKeyboardButton(
                text=f"Купить {next_tackle['name']} за {format_money(next_tackle['price'])}",
                callback_data=f"fishing_buy_tackle_{next_tackle['level']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_fishing_locations(uid: int):
    user = await get_user(uid)
    boat_level = int(user.get("fishing_boat_level", 0) or 0)
    current_location = int(user.get("fishing_location", 1) or 1)
    text = "🗺 <b>Локации</b>\n\n"
    for loc in FISHING_LOCATIONS:
        locked = " 🔒" if boat_level < loc["required_boat_level"] else ""
        current = " ✅" if current_location == loc["index"] else ""
        text += f"{loc['name']} (лодка {loc['required_boat_level']}+) {current}{locked}\n"
    keyboard = []
    for loc in FISHING_LOCATIONS:
        if boat_level >= loc["required_boat_level"]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"Выбрать {loc['name']}",
                    callback_data=f"fishing_set_location_{loc['index']}"
                )
            ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
async def build_fishing_sell_menu(uid: int):
    total_value = 0
    rows = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT fish_code, count FROM user_fish WHERE user_id = ? AND count > 0",
            (uid,)
        )
        rows = await cursor.fetchall()
    text = "💰 <b>Продажа рыбы</b>\n\n"
    if not rows:
        text += "Нет рыбы для продажи."
        keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")]]
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    for row in rows:
        fish = FISH_BY_CODE.get(row["fish_code"])
        if not fish:
            continue
        count = int(row["count"] or 0)
        total_value += count * fish["price"]
        text += f"{fish['name']}: {count} шт. (цена {format_money(fish['price'])} за 1)\n"
    text += f"\nИтого: {format_money(total_value)}"
    keyboard = [[InlineKeyboardButton(text="Продать всю рыбу", callback_data="fishing_sell_all")]]
    for row in rows:
        fish = FISH_BY_CODE.get(row["fish_code"])
        if not fish:
            continue
        keyboard.append([
            InlineKeyboardButton(text=f"Продать 1 {fish['name']}", callback_data=f"fishing_sell_{fish['code']}_one"),
            InlineKeyboardButton(text=f"Продать всю {fish['name']}", callback_data=f"fishing_sell_{fish['code']}_all")
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_menu")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
@router.callback_query(F.data == "fishing_menu")
async def fishing_menu_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_panel(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "fishing_shop_boats")
async def fishing_shop_boats_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_boat_shop(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "fishing_shop_rods")
async def fishing_shop_rods_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_rod_shop(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data == "fishing_shop_tackle")
async def fishing_shop_tackle_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_tackle_shop(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("fishing_buy_boat_"))
async def fishing_buy_boat_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        level = int(cb.data.split("_")[3])
    except Exception:
        await cb.answer("Ошибка покупки лодки.", show_alert=True)
        return
    user = await get_user(uid)
    current_level = int(user.get("fishing_boat_level", 0) or 0)
    if level != current_level + 1:
        await cb.answer("Можно купить только следующую лодку.", show_alert=True)
        return
    boat = get_fishing_boat_config(level)
    if not boat:
        await cb.answer("Лодка не найдена.", show_alert=True)
        return
    if user.get("balance", 0) < boat["price"]:
        await cb.answer("Не хватает денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ?, fishing_boat_level = ? WHERE id = ?",
            (boat["price"], level, uid)
        )
        await db.commit()
    await cb.answer(f"Лодка куплена: {boat['name']}", show_alert=True)
    text, reply_markup = await build_fishing_boat_shop(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("fishing_buy_rod_"))
async def fishing_buy_rod_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        level = int(cb.data.split("_")[3])
    except Exception:
        await cb.answer("Ошибка покупки удочки.", show_alert=True)
        return
    user = await get_user(uid)
    current_level = int(user.get("fishing_rod_level", 0) or 0)
    if level != current_level + 1:
        await cb.answer("Можно купить только следующую удочку.", show_alert=True)
        return
    rod = get_fishing_rod_config(level)
    if not rod:
        await cb.answer("Удочка не найдена.", show_alert=True)
        return
    if user.get("balance", 0) < rod["price"]:
        await cb.answer("Не хватает денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ?, fishing_rod_level = ? WHERE id = ?",
            (rod["price"], level, uid)
        )
        await db.commit()
    await cb.answer(f"Удочка куплена: {rod['name']}", show_alert=True)
    text, reply_markup = await build_fishing_rod_shop(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data.startswith("fishing_buy_tackle_"))
async def fishing_buy_tackle_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        level = int(cb.data.split("_")[3])
    except Exception:
        await cb.answer("Ошибка покупки снастей.", show_alert=True)
        return
    user = await get_user(uid)
    current_level = int(user.get("fishing_tackle_level", 0) or 0)
    if level != current_level + 1:
        await cb.answer("Можно купить только следующие снасти.", show_alert=True)
        return
    tackle = get_fishing_tackle_config(level)
    if not tackle:
        await cb.answer("Снасти не найдены.", show_alert=True)
        return
    if user.get("balance", 0) < tackle["price"]:
        await cb.answer("Не хватает денег.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET balance = balance - ?, fishing_tackle_level = ? WHERE id = ?",
            (tackle["price"], level, uid)
        )
        await db.commit()
    await cb.answer(f"Снасти куплены: {tackle['name']}", show_alert=True)
    text, reply_markup = await build_fishing_tackle_shop(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "fishing_locations")
async def fishing_locations_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_locations(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("fishing_set_location_"))
async def fishing_set_location_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    try:
        location_index = int(cb.data.split("_")[3])
    except Exception:
        await cb.answer("Ошибка выбора локации.", show_alert=True)
        return
    location = get_fishing_location(location_index)
    if not location:
        await cb.answer("Локация не найдена.", show_alert=True)
        return
    user = await get_user(uid)
    boat_level = int(user.get("fishing_boat_level", 0) or 0)
    if boat_level < location["required_boat_level"]:
        await cb.answer("Локация недоступна для вашей лодки.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET fishing_location = ? WHERE id = ?",
            (location_index, uid)
        )
        await db.commit()
    await cb.answer(f"Локация выбрана: {location['name']}", show_alert=True)
    text, reply_markup = await build_fishing_locations(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "fishing_sell")
async def fishing_sell_cb(cb: CallbackQuery):
    text, reply_markup = await build_fishing_sell_menu(cb.from_user.id)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    await cb.answer()
@router.callback_query(F.data.startswith("fishing_sell_"))
async def fishing_sell_action_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    if cb.data == "fishing_sell_all":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT fish_code, count FROM user_fish WHERE user_id = ? AND count > 0",
                (uid,)
            )
            rows = await cursor.fetchall()
            total_value = 0
            for row in rows:
                fish = FISH_BY_CODE.get(row["fish_code"])
                if not fish:
                    continue
                count = int(row["count"] or 0)
                total_value += count * fish["price"]
            if total_value <= 0:
                await db.rollback()
                await cb.answer("Нет рыбы для продажи.", show_alert=True)
                return
            await db.execute("DELETE FROM user_fish WHERE user_id = ?", (uid,))
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total_value, uid))
            await db.commit()
        await cb.answer(f"Продано на {format_money(total_value)}.", show_alert=True)
        text, reply_markup = await build_fishing_sell_menu(uid)
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        return
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("Ошибка продажи.", show_alert=True)
        return
    mode = parts[-1]
    fish_code = "_".join(parts[2:-1])
    if fish_code not in FISH_BY_CODE or mode not in {"one", "all"}:
        await cb.answer("Ошибка продажи.", show_alert=True)
        return
    fish = FISH_BY_CODE[fish_code]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT count FROM user_fish WHERE user_id = ? AND fish_code = ?",
            (uid, fish_code)
        )
        row = await cursor.fetchone()
        count = int(row["count"] or 0) if row else 0
        if count <= 0:
            await db.rollback()
            await cb.answer("Нет рыбы для продажи.", show_alert=True)
            return
        qty = 1 if mode == "one" else count
        value = qty * fish["price"]
        if qty >= count:
            await db.execute(
                "DELETE FROM user_fish WHERE user_id = ? AND fish_code = ?",
                (uid, fish_code)
            )
        else:
            await db.execute(
                "UPDATE user_fish SET count = count - ? WHERE user_id = ? AND fish_code = ?",
                (qty, uid, fish_code)
            )
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (value, uid))
        await db.commit()
    await cb.answer(f"Продано {fish['name']} x{qty} за {format_money(value)}.", show_alert=True)
    text, reply_markup = await build_fishing_sell_menu(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
@router.callback_query(F.data == "fishing_catch")
async def fishing_catch_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    user = await get_user(uid)
    boat_level = int(user.get("fishing_boat_level", 0) or 0)
    rod_level = int(user.get("fishing_rod_level", 0) or 0)
    tackle_level = int(user.get("fishing_tackle_level", 0) or 0)
    if boat_level <= 0 or rod_level <= 0:
        await cb.answer("Нужны лодка и удочка.", show_alert=True)
        return
    now = int(time.time())
    last_ts = int(user.get("fishing_last_ts", 0) or 0)
    if last_ts and now - last_ts < FISHING_COOLDOWN:
        remaining = FISHING_COOLDOWN - (now - last_ts)
        await cb.answer(f"Подожди {format_short_seconds(remaining)}.", show_alert=True)
        return
    boat = get_fishing_boat_config(boat_level)
    rod = get_fishing_rod_config(rod_level)
    tackle = get_fishing_tackle_config(tackle_level)
    location_index = int(user.get("fishing_location", 1) or 1)
    max_location = get_max_fishing_location(boat_level)
    if location_index > max_location:
        location_index = max_location
    location = get_fishing_location(location_index) or FISHING_LOCATIONS[0]
    rarity_bonus = 0.0
    exp_bonus = 0.0
    if boat:
        rarity_bonus += boat["rarity_bonus"]
        exp_bonus += boat["exp_bonus"]
    if rod:
        exp_bonus += rod["exp_bonus"]
    if tackle:
        rarity_bonus += tackle["rarity_bonus"]
        exp_bonus += tackle["exp_bonus"]
    rarity_weights = location["rarity_weights"]
    weights = []
    for rarity in FISHING_RARITY_ORDER:
        weight = rarity_weights.get(rarity, 0)
        if rarity in {"rare", "epic", "legendary", "mythic"}:
            weight = int(round(weight * (1 + rarity_bonus)))
        weights.append(weight)
    if sum(weights) <= 0:
        weights = [1 if r == "common" else 0 for r in FISHING_RARITY_ORDER]
    rarity = random.choices(FISHING_RARITY_ORDER, weights=weights, k=1)[0]
    pool = [f for f in FISH_CONFIG if location_index in f["locations"]]
    candidates = [f for f in pool if f["rarity"] == rarity]
    if not candidates:
        candidates = pool if pool else FISH_CONFIG
    fish = random.choice(candidates)
    count = get_fishing_catch_count(rod_level)
    exp_gain = max(1, int(round(FISHING_EXP_BASE * (1 + exp_bonus)))) * count
    new_exp = int(user.get("fishing_exp", 0) or 0) + exp_gain
    old_level = int(user.get("fishing_level", 1) or 1)
    new_level = get_fishing_level(new_exp)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT count FROM user_fish WHERE user_id = ? AND fish_code = ?",
            (uid, fish["code"])
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE user_fish SET count = count + ? WHERE user_id = ? AND fish_code = ?",
                (count, uid, fish["code"])
            )
        else:
            await db.execute(
                "INSERT INTO user_fish (user_id, fish_code, count) VALUES (?, ?, ?)",
                (uid, fish["code"], count)
            )
        await db.execute(
            "UPDATE users SET fishing_last_ts = ?, fishing_exp = ?, fishing_level = ?, fish_caught_total = fish_caught_total + ?, fishing_location = ? WHERE id = ?",
            (now, new_exp, new_level, count, location_index, uid)
        )
        await db.commit()
    total_value = fish["price"] * count
    message = f"Поймано: {fish['name']} x{count} (+{format_money(total_value)})"
    if new_level > old_level:
        message += f"\nУровень рыбака повышен до {new_level}!"
    await cb.answer(message, show_alert=True)
    text, reply_markup = await build_fishing_panel(uid)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
if __name__ == "__main__":
    asyncio.run(main())
