import aiohttp
import ssl
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# URL API клубной программы
API_BASE_URL = "https://127.0.0.1:8443/api"
# TODO: Если требуется авторизация, добавьте токен
API_TOKEN = None  # или "your-api-token"

# Для локального HTTPS с самоподписанным сертификатом отключаем проверку SSL
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


class ClubAPI:
    def __init__(self, base_url: str = API_BASE_URL, token: Optional[str] = API_TOKEN):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def create_reservation(
        self,
        user_id: int,
        pc_number: int,
        date: str,
        time_from: str,
        time_to: str,
        username: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создает бронирование через API клубной программы
        Использует PUT /api/reservations
        
        Параметры:
        - user_id: ID пользователя (int64)
        - pc_number: Номер ПК (будет преобразован в Hosts)
        - date: Дата в формате YYYY-MM-DD
        - time_from: Время начала в формате HH:MM
        - time_to: Время окончания в формате HH:MM
        - username: Имя пользователя (опционально)
        - contact_phone: Контактный телефон (опционально)
        - contact_email: Контактный email (опционально)
        - note: Примечание к брони (опционально)
        """
        try:
            # Вычисляем длительность в минутах
            start_time = datetime.strptime(time_from, "%H:%M")
            end_time = datetime.strptime(time_to, "%H:%M")
            if end_time < start_time:
                # Если время окончания меньше времени начала, значит это следующий день
                end_time += timedelta(days=1)
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
            
            # Объединяем дату и время начала в формат date-time
            # Формат: YYYY-MM-DDTHH:MM:SS
            date_time_str = f"{date}T{time_from}:00"
            
            # Преобразуем pc_number в массив Hosts (обязательное поле)
            # Предполагаем, что pc_number - это ID хоста, преобразуем в строку
            hosts = [str(pc_number)]
            
            # Преобразуем user_id в массив Users
            users = [str(user_id)]
            
            # Формируем данные для API согласно Swagger документации
            reservation_data = {
                "UserId": user_id,  # integer (int64)
                "Date": date_time_str,  # string (date-time)
                "Duration": duration_minutes,  # integer (int32) - длительность в минутах
                "Hosts": hosts,  # array[string] - обязательное поле
                "Users": users,  # array[string]
            }
            
            # Добавляем опциональные поля, если они указаны
            if note:
                reservation_data["Note"] = note
            if contact_phone:
                reservation_data["ContactPhone"] = contact_phone
            if contact_email:
                reservation_data["ContactEmail"] = contact_email

            # Логируем отправляемые данные для отладки
            logger.info(f"Отправка запроса на создание брони: {reservation_data}")
            logger.info(f"URL: {self.base_url}/reservations")
            logger.info(f"Headers: {self.headers}")

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                async with session.put(
                    f"{self.base_url}/reservations",
                    json=reservation_data,
                    headers=self.headers
                ) as response:
                    response_text = await response.text()
                    logger.info(f"Ответ API: статус={response.status}, тело={response_text}")
                    
                    if response.status == 200 or response.status == 201:
                        # API может вернуть пустой объект {} при успехе
                        try:
                            result = await response.json() if response_text else {}
                            logger.info(f"Бронь создана через API. Ответ: {result}")
                            # Если ответ пустой, но статус 200, считаем успешным
                            return result if result else {"success": True, "status": response.status}
                        except Exception as json_error:
                            logger.warning(f"Не удалось распарсить JSON ответ: {json_error}. Текст ответа: {response_text}")
                            # Если статус 200, но не JSON, считаем успешным
                            return {"success": True, "status": response.status, "raw_response": response_text}
                    else:
                        # Пытаемся распарсить ошибку
                        try:
                            error_json = await response.json()
                            logger.error(f"Ошибка создания брони через API: {response.status} - {error_json}")
                        except:
                            logger.error(f"Ошибка создания брони через API: {response.status} - {response_text}")
                        return None
        except aiohttp.ClientConnectorError as e:
            logger.error(f"❌ Не удалось подключиться к API серверу: {e}")
            logger.error(f"Проверьте, что API сервер запущен и доступен по адресу: {self.base_url}")
            logger.error(f"Убедитесь, что сервер слушает на порту 8443")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при создании брони через API: {e}")
            return None
        except Exception as e:
            logger.error(f"Исключение при создании брони через API: {e}", exc_info=True)
            return None

    async def update_reservation(
        self,
        reservation_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет бронирование через API
        Использует POST /api/reservations
        """
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                async with session.post(
                    f"{self.base_url}/reservations",
                    json={"id": reservation_id, **kwargs},
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Бронь обновлена через API: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка обновления брони через API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Исключение при обновлении брони через API: {e}")
            return None

    async def delete_reservation_user(
        self,
        reservation_id: int,
        user_id: int
    ) -> bool:
        """
        Удаляет пользователя из бронирования через API
        Использует DELETE /api/reservations/{reservationId}/users/{userId}
        """
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                async with session.delete(
                    f"{self.base_url}/reservations/{reservation_id}/users/{user_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200 or response.status == 204:
                        logger.info(f"Пользователь удален из брони через API: reservation_id={reservation_id}, user_id={user_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка удаления пользователя из брони через API: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Исключение при удалении пользователя из брони через API: {e}")
            return False

    async def get_reservations(self, user_id: Optional[int] = None) -> Optional[list]:
        """
        Получает список бронирований через API
        Использует GET /api/reservations
        """
        try:
            url = f"{self.base_url}/reservations"
            if user_id:
                url += f"?userId={user_id}"

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Получены брони через API: {len(result) if isinstance(result, list) else 'N/A'}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения броней через API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Исключение при получении броней через API: {e}")
            return None

    async def get_reservation_by_id(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает бронирование по ID через API
        Использует GET /api/reservations/{reservationId}
        """
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                async with session.get(
                    f"{self.base_url}/reservations/{reservation_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Получена бронь через API: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения брони через API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Исключение при получении брони через API: {e}")
            return None


# Глобальный экземпляр клиента API
club_api = ClubAPI()

