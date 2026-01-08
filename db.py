import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    data_dir = "/data"
    if os.path.isdir(data_dir):
        return os.path.join(data_dir, "murasaki_NEW.db")
    if os.getenv("RAILWAY_ENVIRONMENT"):
        try:
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, "murasaki_NEW.db")
        except Exception:
            pass
    return "murasaki_NEW.db"


DB_PATH = get_db_path()


async def init_db() -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA busy_timeout = 5000")

            await db.execute(
                """
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
                    last_collected INTEGER DEFAULT 0,
                    plasma BIGINT DEFAULT 0,
                    plutonium BIGINT DEFAULT 0,
                    artifacts BIGINT DEFAULT 0,
                    tech_data BIGINT DEFAULT 0,
                    space_prestige INTEGER DEFAULT 0,
                    bitcoin REAL DEFAULT 0,
                    mining_gpu_count INTEGER DEFAULT 0,
                    mining_gpu_level INTEGER DEFAULT 1,
                    last_mining_claim INTEGER DEFAULT 0,
                    last_daily_claim INTEGER DEFAULT NULL,
                    daily_streak INTEGER DEFAULT 0,
                    last_game_time INTEGER DEFAULT 0,
                    weapons_shop_unlocked INTEGER DEFAULT 1,
                    weapons_shop_unlock_until INTEGER DEFAULT 0,
                    energy INTEGER DEFAULT 100,
                    energy_max INTEGER DEFAULT 100,
                    energy_last_ts INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    income_boost_percent REAL DEFAULT 0,
                    income_boost_until_ts INTEGER DEFAULT 0,
                    total_wagered_today BIGINT DEFAULT 0,
                    wagered_reset_ts INTEGER DEFAULT 0,
                    specialization TEXT DEFAULT NULL,
                    specialization_changed_ts INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_callbacks (
                    id TEXT PRIMARY KEY,
                    ts INTEGER
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS referral_progress (
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER PRIMARY KEY,
                    actions_count INTEGER DEFAULT 0,
                    actions_required INTEGER DEFAULT 20,
                    reward_remaining BIGINT DEFAULT 0,
                    rep_remaining INTEGER DEFAULT 0,
                    created_ts INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_items (
                    user_id INTEGER,
                    item_id TEXT,
                    amount INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_unique_items (
                    user_id INTEGER,
                    item_id TEXT,
                    obtained_at INTEGER,
                    PRIMARY KEY(user_id, item_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS country_unique_slots (
                    country_id INTEGER PRIMARY KEY,
                    core_item_id TEXT NULL,
                    support_item_id TEXT NULL,
                    relic_item_id TEXT NULL
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS boss_loot_rolls (
                    boss_id INTEGER,
                    user_id INTEGER,
                    rolled_at INTEGER,
                    PRIMARY KEY(boss_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS planets (
                    user_id INTEGER,
                    planet_id INTEGER,
                    last_collected INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, planet_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS investments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    investment_id INTEGER,
                    amount BIGINT,
                    end_time INTEGER,
                    successful BOOLEAN DEFAULT NULL
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS lottery_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticket_type INTEGER,
                    prize_amount BIGINT,
                    position INTEGER,
                    draw_date INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS countries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_user_id INTEGER NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    treasury INTEGER NOT NULL DEFAULT 0,
                    stability INTEGER NOT NULL DEFAULT 70,
                    tax_rate REAL NOT NULL DEFAULT 0.10,
                    last_tick INTEGER NOT NULL DEFAULT 0,
                    last_war_end_ts INTEGER NOT NULL DEFAULT 0,
                    population INTEGER DEFAULT 0,
                    army_people INTEGER DEFAULT 0,
                    population_cap INTEGER DEFAULT 100000,
                    jobs_available INTEGER DEFAULT 0,
                    employment_rate REAL DEFAULT 0.0,
                    literacy INTEGER DEFAULT 50,
                    crime INTEGER DEFAULT 20,
                    happiness INTEGER DEFAULT 70,
                    birth_rate REAL DEFAULT 0.003,
                    death_rate REAL DEFAULT 0.001,
                    last_population_tick INTEGER DEFAULT 0,
                    specialization TEXT DEFAULT NULL,
                    last_specialization_change INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS country_buildings (
                    country_id INTEGER NOT NULL,
                    building_type TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, building_type)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS business_defs (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_cost INTEGER NOT NULL,
                    max_level INTEGER NOT NULL,
                    income_bonus REAL NOT NULL,
                    jobs INTEGER NOT NULL,
                    upkeep_day INTEGER NOT NULL
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS country_businesses (
                    country_id INTEGER NOT NULL,
                    business_code TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 0,
                    last_upkeep_ts INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, business_code)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS country_limits (
                    country_id INTEGER PRIMARY KEY,
                    people_limit INTEGER DEFAULT 100,
                    tech_limit INTEGER DEFAULT 20
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clan_boss_hits (
                    boss_id INTEGER NOT NULL,
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    country_id INTEGER NOT NULL,
                    damage INTEGER NOT NULL,
                    ts INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clan_boss_rewards_claimed (
                    boss_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clan_members (
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    joined_at INTEGER NOT NULL,
                    PRIMARY KEY(clan_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clan_join_requests (
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(clan_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clan_id INTEGER NOT NULL,
                    actor_user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS armies (
                    country_id INTEGER NOT NULL,
                    unit_type TEXT NOT NULL,
                    amount INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(country_id, unit_type)
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS credit_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credit_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    paid_at INTEGER NOT NULL
                )
                """
            )

            await db.execute(
                """
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
                    ends_at INTEGER NOT NULL,
                    level INTEGER DEFAULT 1
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS boss_hits (
                    boss_id INTEGER NOT NULL,
                    clan_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    country_id INTEGER NOT NULL,
                    damage INTEGER NOT NULL,
                    ts INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS boss_rewards_claimed (
                    boss_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS titles (
                    id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    bonus_type TEXT,
                    bonus_value REAL,
                    permanent INTEGER
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_titles (
                    user_id INTEGER,
                    title_code TEXT,
                    obtained_at INTEGER,
                    PRIMARY KEY(user_id, title_code)
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS space_expeditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    country_id INTEGER,
                    expedition_type TEXT,
                    started_at INTEGER,
                    ends_at INTEGER,
                    status TEXT
                )
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
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
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS space_colonies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER,
                    colony_type TEXT,
                    stability INTEGER,
                    bonus_type TEXT,
                    created_at INTEGER,
                    last_yield INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS space_tech (
                    tech_code TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    cost_plasma INTEGER,
                    cost_plutonium INTEGER
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_space_tech (
                    user_id INTEGER,
                    tech_code TEXT,
                    researched INTEGER,
                    PRIMARY KEY (user_id, tech_code)
                )
                """
            )

            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_boss_hits_unique ON boss_hits (boss_id, user_id)"
            )

            await db.commit()
            logger.info("DB initialized")
    except Exception as e:
        logger.error(f"DB init error: {e}")
