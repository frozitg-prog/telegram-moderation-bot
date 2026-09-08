import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                chat_id INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (chat_id, key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ban_words (
                chat_id INTEGER,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mute_words (
                chat_id INTEGER,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                chat_id INTEGER,
                user_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS log_chat (
                chat_id INTEGER PRIMARY KEY,
                log_chat_id INTEGER
            )
        """)
        await db.commit()


async def get_setting(chat_id, key, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key)
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_setting(chat_id, key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, ?, ?)",
            (chat_id, key, str(value))
        )
        await db.commit()


async def get_ban_words(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM ban_words WHERE chat_id=?", (chat_id,)
        )
        return [row[0] for row in await cursor.fetchall()]


async def add_ban_word(chat_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO ban_words (chat_id, word) VALUES (?, ?)",
            (chat_id, word.lower())
        )
        await db.commit()


async def remove_ban_word(chat_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM ban_words WHERE chat_id=? AND word=?",
            (chat_id, word.lower())
        )
        await db.commit()


async def get_mute_words(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM mute_words WHERE chat_id=?", (chat_id,)
        )
        return [row[0] for row in await cursor.fetchall()]


async def add_mute_word(chat_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO mute_words (chat_id, word) VALUES (?, ?)",
            (chat_id, word.lower())
        )
        await db.commit()


async def remove_mute_word(chat_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM mute_words WHERE chat_id=? AND word=?",
            (chat_id, word.lower())
        )
        await db.commit()


async def get_warns(chat_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM warns WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def add_warn(chat_id, user_id):
    current = await get_warns(chat_id, user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)",
            (chat_id, user_id, current + 1)
        )
        await db.commit()
    return current + 1


async def reset_warns(chat_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warns WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        await db.commit()


async def set_log_chat(chat_id, log_chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO log_chat (chat_id, log_chat_id) VALUES (?, ?)",
            (chat_id, log_chat_id)
        )
        await db.commit()


async def get_log_chat(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT log_chat_id FROM log_chat WHERE chat_id=?", (chat_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
