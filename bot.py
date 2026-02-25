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
        r = requests.get("https://api.exchangerate.host/latest?base=MDL", timeout=10)
        data = r.json()
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

def get_roads(city):
    return f"🚗 Дороги в {city}: данные недоступны"

# ================= ОТПРАВКА ОТЧЁТА =================
async def send_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet,MD")

    text = (
        f"🌅 Доброе утро! Ситуация в городе {city}:\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_roads(city)}"
    )

    await bot.send_message(uid, text)

# ================= ПЕРЕНАЗНАЧЕНИЕ ВРЕМЕНИ =================
def reschedule(uid):
    job_id = f"report_{uid}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    hour = user_settings[uid]["hour"]
    minute = user_settings[uid]["minute"]

    trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)

    scheduler.add_job(
        send_report,
        trigger,
        args=[uid],
        id=job_id
    )

# ================= КОМАНДЫ =================
@dp.message(Command("start"))
async def start(m: types.Message):
    uid = m.from_user.id

    user_settings[uid] = {
        "city": "Edinet,MD",
        "hour": 7,
        "minute": 0,
        "waiting": None
    }

    reschedule(uid)

    await m.answer(
        "✅ Бот активирован!\n\n"
        "Команды:\n"
        "/now — сводка сейчас\n"
        "/setcity — сменить город\n"
        "/settime — сменить время\n"
        "/settings — настройки"
    )

@dp.message(Command("settings"))
async def settings_cmd(m: types.Message):
    uid = m.from_user.id
    s = user_settings.get(uid)

    await m.answer(
        f"⚙️ Настройки:\n"
        f"🏙 Город: {s['city']}\n"
        f"⏰ Время: {s['hour']:02d}:{s['minute']:02d}"
    )

@dp.message(Command("now"))
async def now_cmd(m: types.Message):
    await send_report(m.from_user.id)

@dp.message(Command("setcity"))
async def setcity(m: types.Message):
    uid = m.from_user.id
    user_settings[uid]["waiting"] = "city"
    await m.answer("Введите город на английском:")

@dp.message(Command("settime"))
async def settime(m: types.Message):
    uid = m.from_user.id
    user_settings[uid]["waiting"] = "time"
    await m.answer("Введите время в формате ЧЧ:ММ (например 07:30):")

@dp.message()
async def handle_input(m: types.Message):
    uid = m.from_user.id
    waiting = user_settings.get(uid, {}).get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        await m.answer(f"✅ Город изменён на {m.text}")

    elif waiting == "time":
        try:
            hour, minute = map(int, m.text.split(":"))

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                user_settings[uid]["hour"] = hour
                user_settings[uid]["minute"] = minute
                user_settings[uid]["waiting"] = None
                reschedule(uid)
                await m.answer(f"✅ Время изменено на {hour:02d}:{minute:02d}")
            else:
                await m.answer("❌ Неверный формат")
        except:
            await m.answer("❌ Введите время как 07:30")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
