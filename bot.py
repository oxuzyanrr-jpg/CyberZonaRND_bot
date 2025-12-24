# Импорты для работы с асинхронностью, логированием и датами
import asyncio          # Для запуска асинхронных функций
import logging          # Для логирования (записи ошибок и информации)
from datetime import datetime, timedelta  # Для работы с датами и временем

# Импорты из библиотеки aiogram для работы с Telegram Bot API
from aiogram import Bot, Dispatcher, F  # Bot - бот, Dispatcher - обработчик сообщений, F - фильтры
from aiogram.filters import CommandStart  # Фильтр для команды /start
from aiogram.fsm.context import FSMContext  # Контекст для FSM (машина состояний)
from aiogram.fsm.storage.memory import MemoryStorage  # Хранение состояний в памяти
from aiogram.types import (
    Message,              # Тип для обычных сообщений
    InlineKeyboardMarkup, # Клавиатура с inline кнопками (под сообщением)
    InlineKeyboardButton, # Кнопка inline клавиатуры
    CallbackQuery,        # Тип для нажатий на inline кнопки
    ReplyKeyboardMarkup,  # Клавиатура с кнопками (внизу экрана)
    KeyboardButton,      # Кнопка reply клавиатуры
)

# Импорты из наших модулей
from states import Booking, Support  # Состояния FSM для бронирования и поддержки
from db import init_db, add_booking, is_pc_available, get_last_booking, delete_booking, get_user_bookings, update_booking_api_id  # Функции для работы с БД
from api_client import ClubAPI  # Класс для работы с API приложения клуба
from config import API_BASE_URL, API_USERNAME, API_PASSWORD, API_BRANCH_ID, API_REGISTER_ID  # Настройки API

# Константы - настройки бота
TOKEN = "8276794506:AAEqmgZHNn8f-d33dki3XWhPCa0JXF7k3ck"  # Токен бота от @BotFather
ADMIN_ID = 7545686154  # ID администратора в Telegram (получает уведомления)

# Ссылки для раздела "Ссылки"
VK_GROUP_LINK = "https://vk.com/cyberzona_rnd"  # Ссылка на группу ВК
MOBILE_APP_LINK = "https://cyberzona.parazey.com/"  # Ссылка на мобильное приложение
TOURNAMENT_CHAT_LINK = "https://t.me/tournament_cz"  # Ссылка на чат турниров

# Создание экземпляра бота с токеном
bot = Bot(token=TOKEN)

# Создание диспетчера для обработки сообщений
# MemoryStorage - хранит состояния FSM в памяти (при перезапуске бота состояния теряются)
dp = Dispatcher(storage=MemoryStorage())

# Создание клиента для работы с API приложения клуба
# Используется для синхронизации бронирований между ботом и приложением
api_client = ClubAPI(
    base_url=API_BASE_URL,      # URL API (из config.py)
    username=API_USERNAME,      # Логин для API (из config.py)
    password=API_PASSWORD,      # Пароль для API (из config.py)
    branch_id=API_BRANCH_ID,    # ID филиала (опционально, из config.py)
    register_id=API_REGISTER_ID # ID регистра (опционально, из config.py)
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)  # Уровень логирования: INFO (показывает важную информацию)
logger = logging.getLogger(__name__)  # Создаем логгер для этого модуля


async def send_to_admin(text: str):
    """
    Отправляет сообщение администратору с обработкой ошибок.
    
    Используется для уведомления администратора о:
    - Создании новой брони
    - Отмене брони
    - Сообщениях в поддержку
    
    Args:
        text: Текст сообщения для отправки администратору
    """
    try:
        # Отправляем сообщение администратору по его ID
        await bot.send_message(ADMIN_ID, text)
        logger.info(f"Сообщение отправлено администратору (ID: {ADMIN_ID})")
    except Exception as e:
        # Если не удалось отправить (админ не запустил бота, неправильный ID и т.д.)
        logger.error(f"Ошибка при отправке сообщения администратору: {e}")
        print(f"⚠️ Не удалось отправить сообщение администратору: {e}")
        print("Проверьте, что администратор запустил бота (/start) и ID корректен.")


@dp.message(CommandStart())
async def start(message: Message):
    """
    Обработчик команды /start.
    
    Вызывается когда пользователь отправляет команду /start или запускает бота впервые.
    Показывает приветственное сообщение и главное меню с кнопками.
    
    Args:
        message: Объект сообщения от пользователя
    """
    await message.answer(
        "🎮 Добро пожаловать в компьютерный клуб!\n\nВыберите действие:",
        reply_markup=main_menu()  # Показываем главное меню с кнопками
    )


def main_menu():
    """
    Создает главное меню с кнопками.
    
    ReplyKeyboardMarkup - клавиатура с кнопками внизу экрана.
    Каждый список в keyboard - это ряд кнопок.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с главным меню
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            # Первый ряд: одна кнопка "Забронировать ПК"
            [KeyboardButton(text="🎮 Забронировать ПК")],
            # Второй ряд: две кнопки рядом
            [KeyboardButton(text="📋 Мои брони"), KeyboardButton(text="❌ Отменить бронь")],
            # Третий ряд: одна кнопка "Поддержка"
            [KeyboardButton(text="💬 Поддержка")],
            # Четвертый ряд: две кнопки рядом
            [KeyboardButton(text="ℹ️ Информация"), KeyboardButton(text="🔗 Ссылки")]
        ],
        resize_keyboard=True  # Кнопки автоматически подстраиваются под размер экрана
    )


def info_menu():
    """
    Создает меню раздела "Информация".
    
    Показывается когда пользователь нажимает "ℹ️ Информация".
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с меню информации
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Прайс-лист")],  # Кнопка для просмотра цен
            [KeyboardButton(text="🎁 Акции и бонусы")],  # Кнопка для акций
            [KeyboardButton(text="🏆 Расписание турниров")],  # Кнопка для турниров
            [KeyboardButton(text="📜 Правила клуба")],  # Кнопка для правил
            [KeyboardButton(text="⬅️ Главное меню")]  # Кнопка возврата в главное меню
        ],
        resize_keyboard=True
    )


def links_menu():
    """
    Создает меню со ссылками (inline кнопки).
    
    InlineKeyboardMarkup - кнопки под сообщением (не внизу экрана).
    При нажатии открывают ссылки в браузере.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура со ссылками
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Группа ВК", url=VK_GROUP_LINK)],  # Кнопка со ссылкой на ВК
        [InlineKeyboardButton(text="📱 Мобильное приложение", url=MOBILE_APP_LINK)],  # Кнопка со ссылкой на приложение
        [InlineKeyboardButton(text="🎮 Чат для турниров", url=TOURNAMENT_CHAT_LINK)]  # Кнопка со ссылкой на чат
    ])


def pc_keyboard():
    """
    Создает клавиатуру для выбора ПК (1-26).
    
    Кнопки располагаются по 3 в ряд для удобства.
    Например: [ПК 1] [ПК 2] [ПК 3]
             [ПК 4] [ПК 5] [ПК 6]
             ...
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками ПК 1-26
    """
    # Создаем список кнопок: ПК 1, ПК 2, ..., ПК 26
    buttons = [KeyboardButton(text=f"ПК {i}") for i in range(1, 27)]
    # Разбиваем кнопки на ряды по 3 штуки
    # [buttons[0:3], buttons[3:6], buttons[6:9], ...]
    keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def time_keyboard():
    """
    Создает клавиатуру для выбора времени.
    
    Время от 00:30 до 23:59 с шагом 30 минут.
    Кнопки располагаются по 3 в ряд.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с временными кнопками
    """
    # Список всех доступных времен (каждые 30 минут)
    times = [
        "00:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00", "04:30",
        "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
        "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
        "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
        "21:00", "21:30", "22:00", "22:30", "23:00", "23:30", "23:59"
    ]
    # Разбиваем времена на ряды по 3 штуки
    keyboard = [[KeyboardButton(text=t) for t in times[i:i + 3]] for i in range(0, len(times), 3)]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def duration_keyboard():
    """
    Создает клавиатуру для выбора длительности бронирования.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с вариантами длительности
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 час"), KeyboardButton(text="3 часа")],  # Первый ряд: 1 и 3 часа
            [KeyboardButton(text="5 часов")],  # Второй ряд: 5 часов
            [KeyboardButton(text="7 часов")],  # Третий ряд: 7 часов
            [KeyboardButton(text="10 часов")]  # Четвертый ряд: 10 часов
        ],
        resize_keyboard=True
    )


@dp.message(F.text == "❌ Отменить бронь")
async def cancel_booking(message: Message):
    """
    Обработчик отмены последней брони пользователя.
    
    Удаляет бронь из локальной БД и из API приложения клуба (если есть api_booking_id).
    Отправляет уведомление администратору.
    
    Args:
        message: Сообщение от пользователя с текстом "❌ Отменить бронь"
    """
    # Получаем последнюю бронь пользователя из локальной БД
    booking = await get_last_booking(message.from_user.id)

    # Если броней нет - сообщаем пользователю
    if not booking:
        await message.answer("❌ У вас нет активных броней")
        return

    # Распаковываем данные брони: id, номер ПК, дата, время начала, время конца, api_booking_id
    booking_id, pc, date, time_from, time_to, api_booking_id = booking

    # Если есть api_booking_id - удаляем бронь из API приложения клуба
    if api_booking_id:
        try:
            # Отправляем DELETE запрос в API
            success = await api_client.delete_booking(api_booking_id)
            if success:
                logger.info(f"Бронь {api_booking_id} удалена из API")
            else:
                logger.warning(f"Не удалось удалить бронь {api_booking_id} из API")
        except Exception as e:
            # Если ошибка при удалении из API - логируем, но продолжаем удаление из локальной БД
            logger.error(f"Ошибка при удалении брони из API: {e}")

    # Удаляем бронь из локальной БД
    await delete_booking(booking_id)

    # Сообщаем пользователю об успешной отмене
    await message.answer(
        "✅ Бронь отменена:\n\n"
        f"ПК: {pc}\n"
        f"Дата: {date}\n"
        f"Время: {time_from} – {time_to}",
        reply_markup=main_menu()  # Показываем главное меню
    )

    # Отправляем уведомление администратору об отмене брони
    await send_to_admin(
        "❌ Бронь отменена!\n\n"
        f"👤 Пользователь: @{message.from_user.username or message.from_user.full_name}\n"
        f"🖥 ПК: {pc}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time_from} – {time_to}"
    )


@dp.message(F.text == "🎮 Забронировать ПК")
async def booking_start(message: Message, state: FSMContext):
    """
    Начало процесса бронирования.
    
    Устанавливает состояние FSM в Booking.pc (выбор ПК).
    Показывает клавиатуру с ПК 1-26.
    
    Args:
        message: Сообщение от пользователя с текстом "🎮 Забронировать ПК"
        state: Контекст FSM для хранения состояния бронирования
    """
    # Устанавливаем состояние FSM: теперь бот ожидает выбор ПК
    await state.set_state(Booking.pc)
    # Показываем клавиатуру с ПК 1-26
    await message.answer("🎮 Выберите ПК:", reply_markup=pc_keyboard())


@dp.message(Booking.pc)
async def booking_pc(message: Message, state: FSMContext):
    """
    Обработчик выбора ПК.
    
    Вызывается когда пользователь находится в состоянии Booking.pc и отправляет сообщение.
    Проверяет, что выбрана кнопка ПК, сохраняет номер ПК и переходит к выбору даты.
    
    Args:
        message: Сообщение от пользователя (должно быть "ПК 1", "ПК 2" и т.д.)
        state: Контекст FSM для сохранения данных
    """
    # Проверяем, что пользователь выбрал ПК кнопкой (текст начинается с "ПК")
    if not message.text.startswith("ПК"):
        await message.answer("❌ Выберите ПК кнопкой")
        return

    # Извлекаем номер ПК из текста ("ПК 5" -> 5)
    pc_number = int(message.text.replace("ПК ", ""))
    # Сохраняем номер ПК в состояние FSM
    await state.update_data(pc=pc_number)
    # Переходим к следующему шагу - выбор даты
    await state.set_state(Booking.date)

    # Показываем клавиатуру с кнопкой "Сегодня" и просим ввести дату
    await message.answer(
        "Введите дату (например: 2025-01-10) или выберите бронь на сегодня",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Сегодня")]],  # Кнопка для быстрого выбора сегодняшней даты
            resize_keyboard=True
        )
    )


@dp.message(Booking.date)
async def booking_date(message: Message, state: FSMContext):
    """
    Обработчик выбора даты.
    
    Вызывается когда пользователь находится в состоянии Booking.date.
    Если выбрана кнопка "Сегодня" - использует текущую дату, иначе использует введенную дату.
    Переходит к выбору времени начала.
    
    Args:
        message: Сообщение от пользователя (дата или "Сегодня")
        state: Контекст FSM для сохранения данных
    """
    # Если выбрана кнопка "Сегодня" - используем текущую дату
    if message.text == "Сегодня":
        date = datetime.now().strftime("%Y-%m-%d")  # Формат: "2025-01-15"
    else:
        # Иначе используем введенную пользователем дату
        date = message.text

    # Сохраняем дату в состояние FSM
    await state.update_data(date=date)
    # Переходим к следующему шагу - выбор времени начала
    await state.set_state(Booking.time_from)

    # Показываем клавиатуру с временами для выбора
    await message.answer("Выберите время начала:", reply_markup=time_keyboard())


@dp.message(Booking.time_from)
async def booking_time_from(message: Message, state: FSMContext):
    """
    Обработчик выбора времени начала.
    
    Вызывается когда пользователь находится в состоянии Booking.time_from.
    Сохраняет выбранное время начала и переходит к выбору длительности.
    
    Args:
        message: Сообщение от пользователя с временем (например, "14:00")
        state: Контекст FSM для сохранения данных
    """
    # Сохраняем время начала в состояние FSM
    await state.update_data(time_from=message.text)
    # Переходим к следующему шагу - выбор длительности
    await state.set_state(Booking.time_to)

    # Показываем клавиатуру с вариантами длительности
    await message.answer("Выберите длительность:", reply_markup=duration_keyboard())


@dp.message(Booking.time_to)
async def booking_time_to(message: Message, state: FSMContext):
    """
    Обработчик выбора длительности.
    
    Вызывается когда пользователь находится в состоянии Booking.time_to.
    Вычисляет время окончания, проверяет доступность ПК, показывает подтверждение.
    
    Args:
        message: Сообщение от пользователя с длительностью (например, "3 часа")
        state: Контекст FSM для сохранения данных
    """
    # Получаем все сохраненные данные из состояния FSM
    data = await state.get_data()

    # Извлекаем количество часов из текста ("3 часа" -> 3)
    hours = int(message.text.split()[0])
    # Парсим время начала из сохраненных данных
    start = datetime.strptime(data["time_from"], "%H:%M")
    # Вычисляем время окончания: время начала + длительность
    end_time = (start + timedelta(hours=hours)).strftime("%H:%M")

    # Проверяем доступность ПК на выбранное время
    available = await is_pc_available(
        pc=data["pc"],           # Номер ПК
        date=data["date"],       # Дата
        time_from=data["time_from"],  # Время начала
        time_to=end_time         # Время окончания
    )

    # Если ПК занят - сообщаем пользователю и завершаем процесс
    if not available:
        await state.clear()  # Очищаем состояние FSM
        await message.answer("❌ ПК занят на это время", reply_markup=main_menu())
        return

    # Формируем текст подтверждения с деталями брони
    confirmation_text = (
        f"📋 Подтвердите бронирование:\n\n"
        f"🖥 ПК: {data['pc']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time_from']} – {end_time}\n\n"
        f"Подтвердить?"
    )

    # Создаем inline клавиатуру с кнопками подтверждения и отмены
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Кнопка подтверждения (callback_data содержит данные для идентификации)
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{data['pc']}_{data['date']}_{data['time_from']}_{end_time}")],
        # Кнопка отмены
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")]
    ])

    # Сохраняем время окончания в состояние FSM
    await state.update_data(time_to=end_time)
    # Показываем подтверждение с кнопками
    await message.answer(confirmation_text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения бронирования.
    
    Вызывается когда пользователь нажимает кнопку "✅ Подтвердить".
    Создает бронь в локальной БД, отправляет в API приложения клуба,
    синхронизирует ID и уведомляет администратора.
    
    Args:
        callback: Объект callback от нажатия inline кнопки
        state: Контекст FSM с данными бронирования
    """
    # Получаем все сохраненные данные из состояния FSM
    data = await state.get_data()

    # Шаг 1: Создаем бронь в локальной БД
    await add_booking(
        user_id=callback.from_user.id,  # ID пользователя в Telegram
        pc=data["pc"],                   # Номер ПК
        date=data["date"],               # Дата
        time_from=data["time_from"],     # Время начала
        time_to=data["time_to"]          # Время окончания
    )
    
    # Получаем ID только что созданной брони из локальной БД
    booking = await get_last_booking(callback.from_user.id)
    local_booking_id = booking[0] if booking else None

    # Шаг 2: Отправляем бронь в API приложения клуба
    api_result = None
    try:
        # Формируем email из username пользователя (если есть)
        contact_email = f"{callback.from_user.username}@telegram" if callback.from_user.username else ""
        
        # Отправляем POST запрос в API для создания брони
        api_result = await api_client.create_booking(
            telegram_user_id=callback.from_user.id,  # ID пользователя в Telegram
            pc_number=data["pc"],                     # Номер ПК
            date=data["date"],                        # Дата
            time_from=data["time_from"],              # Время начала
            time_to=data["time_to"],                  # Время окончания
            contact_phone="",                         # Телефон (не используется)
            contact_email=contact_email               # Email
        )
        
        # Шаг 3: Синхронизируем ID - сохраняем api_booking_id в локальной БД
        if api_result and local_booking_id:
            api_booking_id = api_result.get("id")  # Извлекаем ID из ответа API
            if api_booking_id:
                # Сохраняем api_booking_id для синхронизации (чтобы можно было удалить из API)
                await update_booking_api_id(local_booking_id, api_booking_id)
                logger.info(f"Бронь синхронизирована: local_id={local_booking_id}, api_id={api_booking_id}")
    except Exception as e:
        # Если ошибка при отправке в API - логируем, но продолжаем работу
        # Бронь уже создана в локальной БД, бот продолжает работать
        logger.error(f"Ошибка при отправке брони в API: {e}")

    # Шаг 4: Отправляем уведомление администратору о новой брони
    await send_to_admin(
        "📢 Новая бронь!\n\n"
        f"👤 Пользователь: @{callback.from_user.username or callback.from_user.full_name}\n"
        f"🖥 ПК: {data['pc']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['time_from']} – {data['time_to']}"
    )

    # Шаг 5: Очищаем состояние FSM (бронирование завершено)
    await state.clear()
    
    # Редактируем сообщение с подтверждением (убираем кнопки, показываем результат)
    await callback.message.edit_text(
        "✅ Бронь создана!\n\n"
        f"ПК: {data['pc']}\n"
        f"Дата: {data['date']}\n"
        f"Время: {data['time_from']} – {data['time_to']}"
    )
    # Показываем уведомление пользователю о подтверждении
    await callback.answer("Бронь подтверждена!")

    # Показываем главное меню
    await callback.message.answer("Выберите действие:", reply_markup=main_menu())


@dp.callback_query(F.data == "cancel_booking")
async def cancel_booking_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отмены бронирования на этапе подтверждения.
    
    Вызывается когда пользователь нажимает кнопку "❌ Отменить" при подтверждении.
    Отменяет процесс бронирования, не создавая бронь.
    
    Args:
        callback: Объект callback от нажатия inline кнопки
        state: Контекст FSM (очищается)
    """
    # Очищаем состояние FSM (отменяем процесс бронирования)
    await state.clear()
    # Редактируем сообщение - показываем что бронирование отменено
    await callback.message.edit_text("❌ Бронирование отменено")
    # Показываем уведомление пользователю
    await callback.answer("Отменено")

    # Показываем главное меню
    await callback.message.answer("Выберите действие:", reply_markup=main_menu())


@dp.message(F.text == "💬 Поддержка")
async def support_start(message: Message, state: FSMContext):
    """
    Начало процесса отправки сообщения в поддержку.
    
    Устанавливает состояние FSM в Support.message.
    Бот будет ожидать текстовое сообщение от пользователя.
    
    Args:
        message: Сообщение от пользователя с текстом "💬 Поддержка"
        state: Контекст FSM для хранения состояния
    """
    # Устанавливаем состояние FSM: теперь бот ожидает сообщение для поддержки
    await state.set_state(Support.message)
    # Показываем клавиатуру с кнопкой отмены
    await message.answer(
        "💬 Напишите ваш вопрос или сообщение для поддержки:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],  # Кнопка для отмены
            resize_keyboard=True
        )
    )


@dp.message(Support.message)
async def support_message(message: Message, state: FSMContext):
    """
    Обработчик сообщения в поддержку.
    
    Вызывается когда пользователь находится в состоянии Support.message и отправляет сообщение.
    Пересылает сообщение администратору.
    
    Args:
        message: Сообщение от пользователя (текст вопроса/проблемы)
        state: Контекст FSM
    """
    # Если пользователь нажал кнопку отмены - отменяем процесс
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return

    # Формируем информацию о пользователе для администратора
    # Используем username если есть, иначе имя и ID
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.full_name} (ID: {message.from_user.id})"

    # Отправляем сообщение администратору
    await send_to_admin(
        f"💬 Новое сообщение в поддержку\n\n"
        f"👤 От: {user_info}\n"
        f"📝 Сообщение:\n{message.text}"
    )

    # Очищаем состояние FSM
    await state.clear()
    # Сообщаем пользователю что сообщение отправлено
    await message.answer(
        "✅ Ваше сообщение отправлено администратору. Мы ответим в ближайшее время!",
        reply_markup=main_menu()
    )


@dp.message(F.text == "📋 Мои брони")
async def my_bookings(message: Message):
    """
    Обработчик просмотра броней пользователя.
    
    Получает все брони пользователя из локальной БД и показывает их списком.
    
    Args:
        message: Сообщение от пользователя с текстом "📋 Мои брони"
    """
    # Получаем все брони пользователя из локальной БД
    bookings = await get_user_bookings(message.from_user.id)

    # Если броней нет - сообщаем пользователю
    if not bookings:
        await message.answer("📋 У вас нет активных броней", reply_markup=main_menu())
        return

    # Формируем текст со списком броней
    text = "📋 Ваши брони:\n\n"
    for booking in bookings:
        # Распаковываем данные брони: id, номер ПК, дата, время начала, время конца, api_booking_id
        booking_id, pc, date, time_from, time_to, api_booking_id = booking
        # Добавляем информацию о брони в текст
        text += f"🖥 ПК {pc}\n"
        text += f"📅 {date}\n"
        text += f"⏰ {time_from} – {time_to}\n"
        text += "─" * 20 + "\n"  # Разделитель между бронями

    # Отправляем список броней пользователю
    await message.answer(text, reply_markup=main_menu())


@dp.message(F.text == "ℹ️ Информация")
async def info_menu_handler(message: Message):
    """
    Обработчик раздела "Информация".
    
    Показывает меню с подразделами информации (прайс, акции, турниры, правила).
    
    Args:
        message: Сообщение от пользователя с текстом "ℹ️ Информация"
    """
    await message.answer("ℹ️ Выберите раздел:", reply_markup=info_menu())


@dp.message(F.text == "💰 Прайс-лист")
async def price_list(message: Message):
    """
    Обработчик просмотра прайс-листа.
    
    Показывает цены на все зоны (Standart, Bootcamp, VIP, PlayStation)
    с разбивкой по будням/выходным и дню/ночи.
    
    Args:
        message: Сообщение от пользователя с текстом "💰 Прайс-лист"
    """
    # Словарь с ценами для всех зон и периодов
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

    # Иконки для каждой зоны
    zone_icons = {"Standart": "🖥", "Bootcamp": "💻", "VIP": "⭐", "PlayStation": "🎮"}

    # Начинаем формировать текст прайс-листа
    text = "💰 Прайс-лист\n\n"
    text += "⏰ День: 10:00-22:00 | Ночь: 22:00-10:00\n\n"

    # Проходим по всем зонам и формируем текст с ценами
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
    """
    Обработчик раздела "Акции и бонусы".
    
    Показывает информацию об акциях и бонусной программе клуба.
    
    Args:
        message: Сообщение от пользователя с текстом "🎁 Акции и бонусы"
    """
    text = "🎁 Акции и бонусы:\n\n"
    text += "🎉 Система лояльности, со временем скидка на вашем аккаунте увеличивается, отследить прогресс можно в нашем приложении\n"
    text += "🎮 Х2 при покупке времени в ваш день рождения"
    await message.answer(text)


@dp.message(F.text == "🏆 Расписание турниров")
async def tournament_schedule(message: Message):
    """
    Обработчик раздела "Расписание турниров".
    
    Показывает расписание турниров в клубе.
    
    Args:
        message: Сообщение от пользователя с текстом "🏆 Расписание турниров"
    """
    text = "🏆 Расписание турниров:\n\n"
    text += "📅 Понедельник: CS2 турнир (14:00)\n\n"
    text += "🔗 Для записи перейдите в раздел 'Ссылки'"
    await message.answer(text)


@dp.message(F.text == "📜 Правила клуба")
async def club_rules(message: Message):
    """
    Обработчик раздела "Правила клуба".
    
    Показывает правила поведения в клубе.
    
    Args:
        message: Сообщение от пользователя с текстом "📜 Правила клуба"
    """
    text = "📜 Правила клуба:\n\n"
    text += "1. Соблюдайте тишину и порядок\n"
    text += "2. Запрещено курение и распитие алкогольной продукции в помещении\n"
    text += "3. Бережно относитесь к оборудованию\n"
    text += "4. Бронь действительна 20 минут после начала времени\n"
    text += "5. При опоздании более 20 минут бронь аннулируется\n"
    await message.answer(text)


@dp.message(F.text == "⬅️ Главное меню")
async def back_to_main(message: Message):
    """
    Обработчик возврата в главное меню.
    
    Показывает главное меню с основными кнопками.
    
    Args:
        message: Сообщение от пользователя с текстом "⬅️ Главное меню"
    """
    await message.answer("Главное меню:", reply_markup=main_menu())


@dp.message(F.text == "🔗 Ссылки")
async def links_handler(message: Message):
    """
    Обработчик раздела "Ссылки".
    
    Показывает inline кнопки со ссылками на ВК, приложение и чат турниров.
    
    Args:
        message: Сообщение от пользователя с текстом "🔗 Ссылки"
    """
    await message.answer("🔗 Полезные ссылки:", reply_markup=links_menu())


@dp.message(F.text == "/admin_info")
async def admin_info(message: Message):
    """
    Команда для отладки - показывает информацию об администраторе.
    
    Полезно для проверки правильности ADMIN_ID.
    Показывает ID текущего пользователя и ID администратора.
    
    Args:
        message: Сообщение от пользователя с командой "/admin_info"
    """
    # Если пользователь - администратор
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            f"✅ Вы администратор!\n"
            f"Ваш ID: {ADMIN_ID}\n"
            f"Бот работает корректно."
        )
    else:
        # Если пользователь не администратор - показываем его ID и ID админа
        await message.answer(
            f"Ваш ID: {message.from_user.id}\n"
            f"ID администратора: {ADMIN_ID}"
        )


async def main():
    """
    Главная функция запуска бота.
    
    Инициализирует базу данных и запускает бота в режиме polling
    (бот постоянно проверяет новые сообщения от Telegram).
    """
    try:
        # Шаг 1: Инициализация базы данных
        print("🔄 Инициализация базы данных...")
        await init_db()  # Создает таблицы если их нет
        print("✅ База данных инициализирована")

        # Шаг 2: Запуск бота
        print("🚀 Запуск бота...")
        # start_polling - запускает бота в режиме polling (постоянный опрос серверов Telegram)
        # Бот будет работать до тех пор, пока не будет остановлен
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        # Если пользователь нажал Ctrl+C - корректно останавливаем бота
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        # Если произошла ошибка - выводим информацию и останавливаем бота
        print(f"❌ Ошибка при запуске бота: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()  # Выводим полный traceback для отладки
        raise
    finally:
        # Этот блок выполняется всегда, даже при ошибке
        # Закрываем API клиент при завершении (освобождаем ресурсы)
        await api_client.close()


if __name__ == "__main__":
    """
    Точка входа в программу.
    
    Выполняется только если файл запущен напрямую (не импортирован).
    Запускает главную функцию main() в асинхронном режиме.
    """
    try:
        # Запускаем главную функцию в асинхронном режиме
        # asyncio.run() создает event loop и запускает функцию
        asyncio.run(main())
    except KeyboardInterrupt:
        # Если пользователь нажал Ctrl+C - выводим прощальное сообщение
        print("\n👋 До свидания!")
    except Exception as e:
        # Если произошла критическая ошибка - выводим информацию
        print(f"❌ Критическая ошибка: {e}")
        # Ожидаем нажатия Enter перед выходом (чтобы пользователь увидел ошибку)
        input("Нажмите Enter для выхода...")