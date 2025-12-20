import aiosqlite

DB_NAME = "club.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pc_number INTEGER,
            date TEXT,
            time_from TEXT,
            time_to TEXT
        )
        """)
        await db.commit()


async def is_pc_available(pc, date, time_from, time_to):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT 1 FROM bookings
        WHERE pc_number = ?
          AND date = ?
          AND time_from < ?
          AND time_to > ?
        """, (pc, date, time_to, time_from))
        result = await cursor.fetchone()
        return result is None

async def add_booking(user_id, pc, date, time_from, time_to):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO bookings (user_id, pc_number, date, time_from, time_to) VALUES (?, ?, ?, ?, ?)",
            (user_id, pc, date, time_from, time_to)
        )
        await db.commit()

async def get_last_booking(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT id, pc_number, date, time_from, time_to
        FROM bookings
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """, (user_id,))
        return await cursor.fetchone()

async def delete_booking(booking_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        await db.commit()

async def get_user_bookings(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT id, pc_number, date, time_from, time_to
        FROM bookings
        WHERE user_id = ?
        ORDER BY date DESC, time_from DESC
        """, (user_id,))
        return await cursor.fetchall()