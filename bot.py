import asyncio, requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
user_settings = {}

def get_weather(city):
    try:
        r = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=ru").json()
        return f"🌤 {r['weather'][0]['description']} {r['main']['temp']}°C"
    except:
        return "Ошибка погоды"

def get_currency():
    try:
        data = requests.get("https://www.bnm.md/ro/official_exchange_rates?get_xml=1").text
        eur = data.split('EUR')[1].split('value="')[1].split('"')[0]
        usd = data.split('USD')[1].split('value="')[1].split('"')[0]
        return f"💱 EUR:{eur} USD:{usd} MDL:1.00"
    except:
        return "Ошибка курса"

def get_roads(): return "🚗 Пробки: средние"

async def send_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet")
    txt = f"📍 {city}\n{get_weather(city)}\n{get_currency()}\n{get_roads()}"
    await bot.send_message(uid, txt)

@dp.message(Command("start"))
async def start(m: types.Message):
    user_settings[m.from_user.id] = {"city": "Edinet"}
    await m.answer("✅ Бот активирован!\n/now — отчёт сейчас\n/setcity — сменить город")

@dp.message(Command("setcity"))
async def setcity(m: types.Message):
    await m.answer("Введите название города:")

@dp.message(Command("now"))
async def now(m: types.Message):
    await send_report(m.from_user.id)

@dp.message()
async def save(m: types.Message):
    user_settings[m.from_user.id] = {"city": m.text}
    await m.answer(f"✅ Город изменён на: {m.text}")

async def main():
    scheduler.add_job(
        lambda: [asyncio.create_task(send_report(uid)) for uid in user_settings.keys()],
        "cron", hour=6, minute=0
    )
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
