import asyncio
import requests
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Часовой пояс Молдовы
timezone = pytz.timezone("Europe/Chisinau")
scheduler = AsyncIOScheduler(timezone=timezone)

user_settings = {}

# ================= ПОГОДА =================
def get_weather(city):
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": WEATHER_API,
                "units": "metric",
                "lang": "ru"
            },
            timeout=10
        ).json()

        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        feels = r['main']['feels_like']
        humidity = r['main']['humidity']

        return (
            f"🌤 Погода: {desc}\n"
            f"🌡 {temp}°C (ощущается {feels}°C)\n"
            f"💧 Влажность: {humidity}%"
        )
    except:
        return "❌ Ошибка получения погоды"

# ================= КУРС ВАЛЮТ =================
def get_currency():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/MDL", timeout=10)
        data = r.json()

        if data["result"] != "success":
            return "❌ Ошибка получения курса валют"

        rates = data["rates"]

        usd = round(1 / rates["USD"], 2)
        eur = round(1 / rates["EUR"], 2)
        ron = round(1 / rates["RON"], 2)
        uah = round(1 / rates["UAH"], 2)
        gbp = round(1 / rates["GBP"], 2)

        return (
            f"💱 Курс валют (1 ед. = MDL):\n"
            f"🇺🇸 Доллар США: {usd}\n"
            f"🇪🇺 Евро: {eur}\n"
            f"🇷🇴 Лей румынский: {ron}\n"
            f"🇺🇦 Гривна: {uah}\n"
            f"🇬🇧 Фунт стерлинг: {gbp}"
        )

    except:
        return "❌ Ошибка получения курса валют"

# ================= ДОРОГИ =================
def get_roads(city):
    return f"🚗 Дороги в {city}: данные недоступны"

# ================= ОТПРАВКА ОТЧЁТА =================
async def send_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet,MD")
