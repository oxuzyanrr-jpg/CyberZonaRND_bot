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
            time_to TEXT,
            api_reservation_id INTEGER
        )
        """)
        # Миграция: добавляем поле api_reservation_id если его нет
        try:
            await db.execute("ALTER TABLE bookings ADD COLUMN api_reservation_id INTEGER")
            await db.commit()
        except Exception:
            # Поле уже существует или другая ошибка, игнорируем
            pass
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

async def add_booking(user_id, pc, date, time_from, time_to, api_reservation_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO bookings (user_id, pc_number, date, time_from, time_to, api_reservation_id) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, pc, date, time_from, time_to, api_reservation_id)
        )
        await db.commit()
        # Возвращаем ID созданной записи
        cursor = await db.execute("SELECT last_insert_rowid()")
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_last_booking(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT id, pc_number, date, time_from, time_to, api_reservation_id
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
        SELECT id, pc_number, date, time_from, time_to, api_reservation_id
        FROM bookings
        WHERE user_id = ?
        ORDER BY date DESC, time_from DESC
        """, (user_id,))
        return await cursor.fetchall()

async def update_booking_api_id(booking_id, api_reservation_id):
    """Обновляет api_reservation_id для существующей брони"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE bookings SET api_reservation_id = ? WHERE id = ?",
            (api_reservation_id, booking_id)
        )
        await db.commit()

async def get_booking_by_id(booking_id):
    """Получает бронь по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT id, user_id, pc_number, date, time_from, time_to, api_reservation_id
        FROM bookings
        WHERE id = ?
        """, (booking_id,))
        return await cursor.fetchone()