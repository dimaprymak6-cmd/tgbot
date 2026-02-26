import asyncio, requests, os, re, random, sys, json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date, datetime

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")

ADMIN_ID = 5200690387

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

DATA_FILE = "users.json"

# ---------- ЗАГРУЗКА / СОХРАНЕНИЕ ----------

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(user_settings, f)

user_settings = load_users()
last_sent = {}

# ---------- КЛАВИАТУРА ----------

def get_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Сводка сейчас"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🏙 Сменить город"), KeyboardButton(text="⏰ Сменить время")],
        ],
        resize_keyboard=True
    )

# ---------- ДАННЫЕ ----------

def get_day_info():
    today = date.today()
    return today.strftime("📅 %d.%m.%Y")

def get_weather(city):
    try:
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": WEATHER_API, "units": "metric", "lang": "ru"}
        ).json()
        return f"🌡 {r['main']['temp']}°C\n💧 {r['main']['humidity']}%"
    except:
        return "❌ Ошибка погоды"

# ---------- ОТПРАВКА ----------

async def send_report(uid):
    city = user_settings[str(uid)]["city"]
    text = (
        f"{get_day_info()}\n\n"
        f"🌍 Город: {city}\n\n"
        f"{get_weather(city)}"
    )
    await bot.send_message(uid, text)

async def broadcast(text):
    for uid in user_settings.keys():
        try:
            await bot.send_message(uid, text)
        except:
            pass

# ---------- ПЛАНИРОВЩИК ----------

def reschedule(uid):
    job_id = f"report_{uid}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    hour = user_settings[str(uid)]["hour"]
    minute = user_settings[str(uid)]["minute"]

    scheduler.add_job(
        send_report,
        "cron",
        hour=hour,
        minute=minute,
        args=[uid],
        id=job_id,
        replace_existing=True
    )

# ---------- КОМАНДЫ ----------

@dp.message(Command("start"))
async def start(m: types.Message):
    uid = str(m.from_user.id)

    if uid not in user_settings:
        user_settings[uid] = {
            "city": "Edinet,MD",
            "hour": 7,
            "minute": 0,
            "waiting": None
        }
        save_users()

    reschedule(uid)

    await m.answer(
        "✅ Бот активирован!",
        reply_markup=get_keyboard()
    )

@dp.message(Command("stats"))
async def stats(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(f"👥 Пользователей: {len(user_settings)}")

@dp.message(Command("send"))
async def admin_send(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return

    text = m.text.replace("/send ", "")
    await broadcast(text)
    await m.answer("✅ Рассылка отправлена")

@dp.message(F.text == "📊 Сводка сейчас")
async def now(m: types.Message):
    await send_report(str(m.from_user.id))

@dp.message(F.text == "⚙️ Настройки")
async def settings(m: types.Message):
    uid = str(m.from_user.id)
    s = user_settings.get(uid)
    await m.answer(
        f"🏙 Город: {s['city']}\n⏰ {s['hour']:02d}:{s['minute']:02d}",
        reply_markup=get_keyboard()
    )

@dp.message(F.text == "🏙 Сменить город")
async def set_city(m: types.Message):
    uid = str(m.from_user.id)
    user_settings[uid]["waiting"] = "city"
    save_users()
    await m.answer("Введите город (например: Chisinau,MD)")

@dp.message(F.text == "⏰ Сменить время")
async def set_time(m: types.Message):
    uid = str(m.from_user.id)
    user_settings[uid]["waiting"] = "time"
    save_users()
    await m.answer("Введите время в формате 07:00")

@dp.message()
async def input_handler(m: types.Message):
    uid = str(m.from_user.id)
    waiting = user_settings.get(uid, {}).get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        save_users()
        await m.answer("✅ Город изменён", reply_markup=get_keyboard())

    elif waiting == "time":
        try:
            hour, minute = map(int, m.text.split(":"))
            user_settings[uid]["hour"] = hour
            user_settings[uid]["minute"] = minute
            user_settings[uid]["waiting"] = None
            save_users()
            reschedule(uid)
            await m.answer("✅ Время изменено", reply_markup=get_keyboard())
        except:
            await m.answer("❌ Неверный формат")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
