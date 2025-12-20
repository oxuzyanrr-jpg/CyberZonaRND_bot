import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from states import Booking, Support
from db import init_db, add_booking, is_pc_available, get_last_booking, delete_booking, get_user_bookings, update_booking_api_id
from api_client import club_api

TOKEN = "8276794506:AAEqmgZHNn8f-d33dki3XWhPCa0JXF7k3ck"
ADMIN_ID = 7545686154  

VK_GROUP_LINK = "https://vk.com/cyberzona_rnd"
MOBILE_APP_LINK = "https://cyberzona.parazey.com/"
TOURNAMENT_CHAT_LINK = "https://t.me/tournament_cz"
# URL Mini App (для разработки используйте localhost, для продакшена - ваш домен)
MINI_APP_URL = "http://localhost:3000"  # Замените на https://your-domain.com для продакшена

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_to_admin(text: str):
    """Отправляет сообщение администратору с обработкой ошибок"""
    try:
        await bot.send_message(ADMIN_ID, text)
        logger.info(f"Сообщение отправлено администратору (ID: {ADMIN_ID})")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения администратору: {e}")
        print(f"⚠️ Не удалось отправить сообщение администратору: {e}")
        print("Проверьте, что администратор запустил бота (/start) и ID корректен.")


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 Добро пожаловать в компьютерный клуб!\n\nВыберите действие:",
        reply_markup=main_menu()
    )


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton(text="🎮 Забронировать ПК")],
            [KeyboardButton(text="📋 Мои брони"), KeyboardButton(text="❌ Отменить бронь")],
            [KeyboardButton(text="💬 Поддержка")],
            [KeyboardButton(text="ℹ️ Информация"), KeyboardButton(text="🔗 Ссылки")]
        ],
        resize_keyboard=True
    )


def info_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Прайс-лист")],
            [KeyboardButton(text="🎁 Акции и бонусы")],
            [KeyboardButton(text="🏆 Расписание турниров")],
            [KeyboardButton(text="📜 Правила клуба")],
            [KeyboardButton(text="⬅️ Главное меню")]
        ],
        resize_keyboard=True
    )


def links_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Группа ВК", url=VK_GROUP_LINK)],
        [InlineKeyboardButton(text="📱 Мобильное приложение", url=MOBILE_APP_LINK)],
        [InlineKeyboardButton(text="🎮 Чат для турниров", url=TOURNAMENT_CHAT_LINK)]
    ])


def pc_keyboard():
    buttons = [KeyboardButton(text=f"ПК {i}") for i in range(1, 27)]
    keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def time_keyboard():
    times = [
        "00:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00", "04:30",
        "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
        "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
        "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
        "21:00", "21:30", "22:00", "22:30", "23:00", "23:30", "23:59"
    ]
    keyboard = [[KeyboardButton(text=t) for t in times[i:i + 3]] for i in range(0, len(times), 3)]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def duration_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 час"), KeyboardButton(text="3 часа")],
            [KeyboardButton(text="5 часов")],
            [KeyboardButton(text="7 часов")],
            [KeyboardButton(text="10 часов")]
        ],
        resize_keyboard=True
    )


@dp.message(F.text == "❌ Отменить бронь")
async def cancel_booking(message: Message):
    booking = await get_last_booking(message.from_user.id)

    if not booking:
        await message.answer("❌ У вас нет активных броней")
        return

    booking_id, pc, date, time_from, time_to, api_reservation_id = booking

    # Удаляем из API, если есть api_reservation_id
    if api_reservation_id:
        success = await club_api.delete_reservation_user(api_reservation_id, message.from_user.id)
        if success:
            logger.info(f"Бронь удалена из API: reservation_id={api_reservation_id}, user_id={message.from_user.id}")
        else:
            logger.warning(f"Не удалось удалить бронь из API: reservation_id={api_reservation_id}")

    await delete_booking(booking_id)

    await message.answer(
        "✅ Бронь отменена:\n\n"
        f"ПК: {pc}\n"
        f"Дата: {date}\n"
        f"Время: {time_from} – {time_to}",
        reply_markup=main_menu()
    )

    await send_to_admin(
        "❌ Бронь отменена!\n\n"
        f"👤 Пользователь: @{message.from_user.username or message.from_user.full_name}\n"
        f"🖥 ПК: {pc}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time_from} – {time_to}"
    )


@dp.message(F.text == "🎮 Забронировать ПК")
async def booking_start(message: Message, state: FSMContext):
    await state.set_state(Booking.pc)
    await message.answer("🎮 Выберите ПК:", reply_markup=pc_keyboard())


@dp.message(Booking.pc)
async def booking_pc(message: Message, state: FSMContext):
    if not message.text.startswith("ПК"):
        await message.answer("❌ Выберите ПК кнопкой")
        return

    pc_number = int(message.text.replace("ПК ", ""))
    await state.update_data(pc=pc_number)
    await state.set_state(Booking.date)

    await message.answer(
        "Введите дату (например: 2025-01-10) или выберите бронь на сегодня",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Сегодня")]],
            resize_keyboard=True
        )
    )


@dp.message(Booking.date)
async def booking_date(message: Message, state: FSMContext):
    if message.text == "Сегодня":
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = message.text

    await state.update_data(date=date)
    await state.set_state(Booking.time_from)

    await message.answer("Выберите время начала:", reply_markup=time_keyboard())


@dp.message(Booking.time_from)
async def booking_time_from(message: Message, state: FSMContext):
    await state.update_data(time_from=message.text)
    await state.set_state(Booking.time_to)

    await message.answer("Выберите длительность:", reply_markup=duration_keyboard())


@dp.message(Booking.time_to)
async def booking_time_to(message: Message, state: FSMContext):
    data = await state.get_data()

    hours = int(message.text.split()[0])
    start = datetime.strptime(data["time_from"], "%H:%M")
    end_time = (start + timedelta(hours=hours)).strftime("%H:%M")

    available = await is_pc_available(
        pc=data["pc"],
        date=data["date"],
        time_from=data["time_from"],
        time_to=end_time
    )

    if not available:
        await state.clear()
        await message.answer("❌ ПК занят на это время", reply_markup=main_menu())
        return

    confirmation_text = (
        f"📋 Подтвердите бронирование:\n\n"
        f"🖥 ПК: {data['pc']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time_from']} – {end_time}\n\n"
        f"Подтвердить?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{data['pc']}_{data['date']}_{data['time_from']}_{end_time}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")]
    ])

    await state.update_data(time_to=end_time)
    await message.answer(confirmation_text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Сначала создаем бронь в локальной БД
    booking_id = await add_booking(
        user_id=callback.from_user.id,
        pc=data["pc"],
        date=data["date"],
        time_from=data["time_from"],
        time_to=data["time_to"]
    )

    # Затем отправляем в API клубной программы
    logger.info(f"Создание брони через API для пользователя {callback.from_user.id}")
    api_result = await club_api.create_reservation(
        user_id=callback.from_user.id,
        pc_number=data["pc"],
        date=data["date"],
        time_from=data["time_from"],
        time_to=data["time_to"],
        username=callback.from_user.username
    )

    # Обрабатываем ответ API
    if api_result:
        logger.info(f"API вернул результат: {api_result}")
        # Пытаемся извлечь ID из ответа API (может быть в разных форматах)
        api_reservation_id = None
        if isinstance(api_result, dict):
            # Проверяем различные возможные поля с ID
            api_reservation_id = (
                api_result.get("id") or 
                api_result.get("reservationId") or 
                api_result.get("reservation_id") or
                api_result.get("Id") or
                api_result.get("ReservationId")
            )
            # Если есть success: True, но нет ID, это тоже успех
            if api_result.get("success") and not api_reservation_id:
                logger.info("Бронь успешно создана в API (пустой ответ, но статус 200)")
        elif isinstance(api_result, (int, str)):
            api_reservation_id = api_result
        
        if api_reservation_id and booking_id:
            await update_booking_api_id(booking_id, api_reservation_id)
            logger.info(f"Бронь синхронизирована с API: booking_id={booking_id}, api_reservation_id={api_reservation_id}")
        elif not api_reservation_id:
            logger.warning(f"API не вернул ID брони, но запрос был успешным. Ответ: {api_result}")
            # Бронь может быть создана, но API не вернул ID - это нормально для некоторых API
    else:
        logger.error(f"API не вернул результат при создании брони. Проверьте логи выше для деталей.")

    await send_to_admin(
        "📢 Новая бронь!\n\n"
        f"👤 Пользователь: @{callback.from_user.username or callback.from_user.full_name}\n"
        f"🖥 ПК: {data['pc']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time_from']} – {data['time_to']}"
    )

    await state.clear()
    await callback.message.edit_text(
        "✅ Бронь создана!\n\n"
        f"ПК: {data['pc']}\n"
        f"Дата: {data['date']}\n"
        f"Время: {data['time_from']} – {data['time_to']}"
    )
    await callback.answer("Бронь подтверждена!")

    await callback.message.answer("Выберите действие:", reply_markup=main_menu())


@dp.callback_query(F.data == "cancel_booking")
async def cancel_booking_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Бронирование отменено")
    await callback.answer("Отменено")

    await callback.message.answer("Выберите действие:", reply_markup=main_menu())


@dp.message(F.text == "💬 Поддержка")
async def support_start(message: Message, state: FSMContext):
    await state.set_state(Support.message)
    await message.answer(
        "💬 Напишите ваш вопрос или сообщение для поддержки:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )


@dp.message(Support.message)
async def support_message(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return

    user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.full_name} (ID: {message.from_user.id})"

    await send_to_admin(
        f"💬 Новое сообщение в поддержку\n\n"
        f"👤 От: {user_info}\n"
        f"📝 Сообщение:\n{message.text}"
    )

    await state.clear()
    await message.answer(
        "✅ Ваше сообщение отправлено администратору. Мы ответим в ближайшее время!",
        reply_markup=main_menu()
    )


@dp.message(F.text == "📋 Мои брони")
async def my_bookings(message: Message):
    bookings = await get_user_bookings(message.from_user.id)

    if not bookings:
        await message.answer("📋 У вас нет активных броней", reply_markup=main_menu())
        return

    text = "📋 Ваши брони:\n\n"
    for booking in bookings:
        booking_id, pc, date, time_from, time_to, api_reservation_id = booking
        text += f"🖥 ПК {pc}\n"
        text += f"📅 {date}\n"
        text += f"⏰ {time_from} – {time_to}\n"
        text += "─" * 20 + "\n"

    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "ℹ️ Информация")
async def info_menu_handler(message: Message):
    await message.answer("ℹ️ Выберите раздел:", reply_markup=info_menu())


@dp.message(F.text == "💰 Прайс-лист")
async def price_list(message: Message):
    prices = {
        "Standart": {
            "будни": {
                "день": {"1 час": 110, "3 часа": 300, "5 часов": 470, "7 часов": 600, "утро": 260, "ночь": 500},
                "ночь": {"1 час": 120, "3 часа": 320, "5 часов": 510, "7 часов": 670, "утро": 260, "ночь": 500}
            },
            "выходные": {
                "день": {"1 час": 120, "3 часа": 320, "5 часов": 510, "7 часов": 670, "утро": 310, "ночь": 550},
                "ночь": {"1 час": 130, "3 часа": 350, "5 часов": 550, "7 часов": 730, "утро": 310, "ночь": 550}
            }
        },
        "Bootcamp": {
            "будни": {
                "день": {"1 час": 120, "3 часа": 320, "5 часов": 510, "7 часов": 670, "утро": 320, "ночь": 600},
                "ночь": {"1 час": 130, "3 часа": 350, "5 часов": 550, "7 часов": 730, "утро": 320, "ночь": 600}
            },
            "выходные": {
                "день": {"1 час": 130, "3 часа": 350, "5 часов": 550, "7 часов": 730, "утро": 370, "ночь": 650},
                "ночь": {"1 час": 140, "3 часа": 380, "5 часов": 590, "7 часов": 780, "утро": 370, "ночь": 650}
            }
        },
        "VIP": {
            "будни": {
                "день": {"1 час": 130, "3 часа": 350, "5 часов": 550, "7 часов": 730, "утро": 400, "ночь": 710},
                "ночь": {"1 час": 140, "3 часа": 380, "5 часов": 590, "7 часов": 780, "утро": 400, "ночь": 710}
            },
            "выходные": {
                "день": {"1 час": 140, "3 часа": 380, "5 часов": 590, "7 часов": 780, "утро": 450, "ночь": 760},
                "ночь": {"1 час": 150, "3 часа": 410, "5 часов": 640, "7 часов": 840, "утро": 450, "ночь": 760}
            }
        },
        "PlayStation": {
            "Standart": {"1 час": 250, "3 часа": 600, "5 часов": 900, "ночь": 1200},
            "VIP": {"1 час": 300, "3 часа": 750, "5 часов": 1100, "ночь": 1500}
        }
    }

    zone_icons = {"Standart": "🖥", "Bootcamp": "💻", "VIP": "⭐", "PlayStation": "🎮"}

    text = "💰 Прайс-лист\n\n"
    text += "⏰ День: 10:00-22:00 | Ночь: 22:00-10:00\n\n"

    for zone, periods in prices.items():
        icon = zone_icons[zone]
        text += f"{icon} {zone}\n"

        if zone == "PlayStation":
            text += "  🖥 Standart: "
            text += f"1ч-{periods['Standart']['1 час']}₽ | "
            text += f"3ч-{periods['Standart']['3 часа']}₽ | "
            text += f"5ч-{periods['Standart']['5 часов']}₽ | "
            text += f"ночь-{periods['Standart']['ночь']}₽\n"
            text += "  ⭐ VIP: "
            text += f"1ч-{periods['VIP']['1 час']}₽ | "
            text += f"3ч-{periods['VIP']['3 часа']}₽ | "
            text += f"5ч-{periods['VIP']['5 часов']}₽ | "
            text += f"ночь-{periods['VIP']['ночь']}₽\n\n"
        else:
            text += "  📅 Будни - День: "
            text += f"1ч-{periods['будни']['день']['1 час']}₽ | "
            text += f"3ч-{periods['будни']['день']['3 часа']}₽ | "
            text += f"5ч-{periods['будни']['день']['5 часов']}₽ | "
            text += f"7ч-{periods['будни']['день']['7 часов']}₽ | "
            text += f"утро-{periods['будни']['день']['утро']}₽ | "
            text += f"ночь-{periods['будни']['день']['ночь']}₽\n"
            text += "  📅 Будни - Ночь: "
            text += f"1ч-{periods['будни']['ночь']['1 час']}₽ | "
            text += f"3ч-{periods['будни']['ночь']['3 часа']}₽ | "
            text += f"5ч-{periods['будни']['ночь']['5 часов']}₽ | "
            text += f"7ч-{periods['будни']['ночь']['7 часов']}₽ | "
            text += f"утро-{periods['будни']['ночь']['утро']}₽ | "
            text += f"ночь-{periods['будни']['ночь']['ночь']}₽\n"
            text += "  📅 Выходные - День: "
            text += f"1ч-{periods['выходные']['день']['1 час']}₽ | "
            text += f"3ч-{periods['выходные']['день']['3 часа']}₽ | "
            text += f"5ч-{periods['выходные']['день']['5 часов']}₽ | "
            text += f"7ч-{periods['выходные']['день']['7 часов']}₽ | "
            text += f"утро-{periods['выходные']['день']['утро']}₽ | "
            text += f"ночь-{periods['выходные']['день']['ночь']}₽\n"
            text += "  📅 Выходные - Ночь: "
            text += f"1ч-{periods['выходные']['ночь']['1 час']}₽ | "
            text += f"3ч-{periods['выходные']['ночь']['3 часа']}₽ | "
            text += f"5ч-{periods['выходные']['ночь']['5 часов']}₽ | "
            text += f"7ч-{periods['выходные']['ночь']['7 часов']}₽ | "
            text += f"утро-{periods['выходные']['ночь']['утро']}₽ | "
            text += f"ночь-{periods['выходные']['ночь']['ночь']}₽\n\n"

    await message.answer(text)


@dp.message(F.text == "🎁 Акции и бонусы")
async def promotions(message: Message):
    text = "🎁 Акции и бонусы:\n\n"
    text += "🎉 Система лояльности, со временем скидка на вашем аккаунте увеличивается, отследить прогресс можно в нашем приложении\n"
    text += "🎮 Х2 при покупке времени в ваш день рождения"
    await message.answer(text)


@dp.message(F.text == "🏆 Расписание турниров")
async def tournament_schedule(message: Message):
    text = "🏆 Расписание турниров:\n\n"
    text += "📅 Понедельник: CS2 турнир (14:00)\n\n"
    text += "🔗 Для записи перейдите в раздел 'Ссылки'"
    await message.answer(text)


@dp.message(F.text == "📜 Правила клуба")
async def club_rules(message: Message):
    text = "📜 Правила клуба:\n\n"
    text += "1. Соблюдайте тишину и порядок\n"
    text += "2. Запрещено курение и распитие алкогольной продукции в помещении\n"
    text += "3. Бережно относитесь к оборудованию\n"
    text += "4. Бронь действительна 20 минут после начала времени\n"
    text += "5. При опоздании более 20 минут бронь аннулируется\n"
    await message.answer(text)


@dp.message(F.text == "⬅️ Главное меню")
async def back_to_main(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu())


@dp.message(F.text == "🔗 Ссылки")
async def links_handler(message: Message):
    await message.answer("🔗 Полезные ссылки:", reply_markup=links_menu())


@dp.message(F.text == "/admin_info")
async def admin_info(message: Message):
    """Показывает информацию об администраторе (для отладки)"""
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            f"✅ Вы администратор!\n"
            f"Ваш ID: {ADMIN_ID}\n"
            f"Бот работает корректно."
        )
    else:
        await message.answer(
            f"Ваш ID: {message.from_user.id}\n"
            f"ID администратора: {ADMIN_ID}"
        )


async def main():
    try:
        print("🔄 Инициализация базы данных...")
        await init_db()
        print("✅ База данных инициализирована")

        print("🚀 Запуск бота...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")