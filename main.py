"""
Telegram-бот с регистрацией пользователей и получением погоды
Использует библиотеку pyTelegramBotAPI
"""

import telebot
import requests
import json
import os
from config import BOT_TOKEN, OPENWEATHER_API_KEY, OPENWEATHER_URL, USERS_DATA_FILE

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для временного хранения данных регистрации
user_registration_data = {}


# ============= РАБОТА С JSON-ФАЙЛОМ =============

def load_users_data():
    """
    Загружает данные пользователей из JSON-файла.
    Если файл не существует, возвращает пустой словарь.
    """
    if os.path.exists(USERS_DATA_FILE):
        try:
            with open(USERS_DATA_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}


def save_users_data(data):
    """
    Сохраняет данные пользователей в JSON-файл.
    """
    with open(USERS_DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ============= КОМАНДА /START =============

@bot.message_handler(commands=['start'])
def start_command(message):
    """
    Обработчик команды /start.
    Приветствует пользователя и предлагает зарегистрироваться.
    """
    user_id = str(message.from_user.id)
    users_data = load_users_data()
    
    welcome_text = f"👋 Привет, {message.from_user.first_name}!\n\n"
    
    if user_id in users_data:
        welcome_text += "Вы уже зарегистрированы!\n\n"
    else:
        welcome_text += "Вы еще не зарегистрированы.\n\n"
    
    welcome_text += "Доступные команды:\n"
    welcome_text += "/register - Зарегистрироваться\n"
    welcome_text += "/me - Посмотреть свои данные\n"
    welcome_text += "/weather - Узнать погоду"
    
    bot.send_message(message.chat.id, welcome_text)


# ============= РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ =============

@bot.message_handler(commands=['register'])
def register_start(message):
    """
    Начинает процесс регистрации пользователя.
    Спрашивает имя.
    """
    user_id = str(message.from_user.id)
    users_data = load_users_data()
    
    # Проверяем, зарегистрирован ли пользователь
    if user_id in users_data:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы! Используйте /me для просмотра данных.")
        return
    
    # Инициализируем временное хранилище для данных регистрации
    user_registration_data[user_id] = {}
    
    msg = bot.send_message(message.chat.id, "📝 Начинаем регистрацию!\n\nКак вас зовут?")
    bot.register_next_step_handler(msg, process_name_step)


def process_name_step(message):
    """
    Обрабатывает ввод имени и спрашивает возраст.
    """
    user_id = str(message.from_user.id)
    
    # Сохраняем имя
    user_registration_data[user_id]['name'] = message.text
    
    msg = bot.send_message(message.chat.id, "Отлично! Сколько вам лет?")
    bot.register_next_step_handler(msg, process_age_step)


def process_age_step(message):
    """
    Обрабатывает ввод возраста и спрашивает город.
    """
    user_id = str(message.from_user.id)
    
    # Проверяем, что возраст - это число
    try:
        age = int(message.text)
        if age <= 0 or age > 150:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректный возраст (число от 1 до 150):")
        bot.register_next_step_handler(msg, process_age_step)
        return
    
    # Сохраняем возраст
    user_registration_data[user_id]['age'] = age
    
    msg = bot.send_message(message.chat.id, "Хорошо! В каком городе вы живёте?")
    bot.register_next_step_handler(msg, process_city_step)


def process_city_step(message):
    """
    Обрабатывает ввод города и завершает регистрацию.
    Сохраняет все данные в JSON-файл.
    """
    user_id = str(message.from_user.id)
    
    # Сохраняем город
    user_registration_data[user_id]['city'] = message.text
    
    # Загружаем существующие данные и добавляем нового пользователя
    users_data = load_users_data()
    users_data[user_id] = user_registration_data[user_id]
    save_users_data(users_data)
    
    # Очищаем временные данные
    del user_registration_data[user_id]
    
    bot.send_message(
        message.chat.id,
        f"✅ Регистрация завершена!\n\n"
        f"Ваши данные:\n"
        f"👤 Имя: {users_data[user_id]['name']}\n"
        f"🎂 Возраст: {users_data[user_id]['age']}\n"
        f"🏙 Город: {users_data[user_id]['city']}\n\n"
        f"Используйте /me для просмотра данных или /weather для погоды."
    )


# ============= КОМАНДА /ME =============

@bot.message_handler(commands=['me'])
def show_user_data(message):
    """
    Показывает сохранённые данные пользователя.
    """
    user_id = str(message.from_user.id)
    users_data = load_users_data()
    
    if user_id not in users_data:
        bot.send_message(
            message.chat.id,
            "❌ Вы ещё не зарегистрированы!\n\nИспользуйте /register для регистрации."
        )
        return
    
    user_info = users_data[user_id]
    response = (
        f"📋 Ваши данные:\n\n"
        f"👤 Имя: {user_info['name']}\n"
        f"🎂 Возраст: {user_info['age']}\n"
        f"🏙 Город: {user_info['city']}"
    )
    
    bot.send_message(message.chat.id, response)


# ============= КОМАНДА /WEATHER =============

@bot.message_handler(commands=['weather'])
def weather_command(message):
    """
    Обработчик команды /weather.
    Запрашивает погоду для города пользователя или спрашивает город.
    """
    user_id = str(message.from_user.id)
    users_data = load_users_data()
    
    # Проверяем, есть ли сохранённый город у пользователя
    if user_id in users_data and 'city' in users_data[user_id]:
        city = users_data[user_id]['city']
        get_weather(message.chat.id, city)
    else:
        msg = bot.send_message(
            message.chat.id,
            "🌍 Для какого города показать погоду?\n\n(Вы можете зарегистрироваться через /register, чтобы сохранить свой город)"
        )
        bot.register_next_step_handler(msg, process_weather_city)


def process_weather_city(message):
    """
    Обрабатывает ввод города для получения погоды.
    """
    city = message.text
    get_weather(message.chat.id, city)


def get_weather(chat_id, city):
    """
    Получает данные о погоде из OpenWeather API и отправляет пользователю.
    
    Параметры:
        chat_id: ID чата для отправки сообщения
        city: Название города для запроса погоды
    """
    try:
        # Формируем параметры запроса
        params = {
            'q': city,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',  # Температура в Цельсиях
            'lang': 'ru'  # Описание погоды на русском
        }
        
        # Отправляем запрос к API
        response = requests.get(OPENWEATHER_URL, params=params, timeout=10)
        
        # Проверяем статус ответа
        if response.status_code == 404:
            bot.send_message(chat_id, f"❌ Город '{city}' не найден. Проверьте правильность написания.")
            return
        elif response.status_code == 401:
            bot.send_message(chat_id, "❌ Ошибка API-ключа. Проверьте настройки в config.py.")
            return
        elif response.status_code != 200:
            bot.send_message(chat_id, f"❌ Ошибка при получении данных: {response.status_code}")
            return
        
        # Парсим JSON-ответ
        data = response.json()
        
        # Извлекаем нужные данные
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        description = data['weather'][0]['description'].capitalize()
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        city_name = data['name']
        
        # Формируем красивое сообщение
        weather_message = (
            f"🌤 Погода в городе {city_name}:\n\n"
            f"🌡 Температура: {temp}°C\n"
            f"🤔 Ощущается как: {feels_like}°C\n"
            f"📝 Описание: {description}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Скорость ветра: {wind_speed} м/с"
        )
        
        bot.send_message(chat_id, weather_message)
        
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, "❌ Превышено время ожидания. Проверьте подключение к интернету.")
    except requests.exceptions.ConnectionError:
        bot.send_message(chat_id, "❌ Ошибка подключения к серверу. Проверьте интернет-соединение.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Произошла ошибка: {str(e)}")


# ============= ЗАПУСК БОТА =============

if __name__ == '__main__':
    print("🤖 Бот запущен и готов к работе!")
    # Запускаем бота в режиме polling (постоянное ожидание сообщений)
    bot.infinity_polling()
