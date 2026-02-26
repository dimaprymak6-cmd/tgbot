import asyncio, requests, os, re, random, json
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

# ------------------ ЗАГРУЗКА / СОХРАНЕНИЕ ------------------

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

# ------------------ КЛАВИАТУРА ------------------

def get_keyboard(uid=None):
    keyboard = [
        [KeyboardButton(text="📊 Сводка сейчас"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="🏙 Сменить город"), KeyboardButton(text="⏰ Сменить время")]
    ]

    if uid and int(uid) == ADMIN_ID:
        keyboard.append([KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="👥 Статистика")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ------------------ ДАННЫЕ ------------------

HOLIDAYS = {
    (1, 1): "🎊 Новый год",
    (3, 8): "🌸 Международный женский день",
    (5, 9): "🎖 День Победы",
    (8, 27): "🇲🇩 День независимости Молдовы",
    (12, 25): "🎄 Рождество (католическое)",
}

FACTS = [
    "💡 Молдова — один из крупнейших производителей вина.",
    "💡 Кишинёв — один из самых зелёных городов Европы.",
    "💡 В Молдове более 300 солнечных дней в году.",
]

UKRAINE_EVENTS = {
    (2, 24): "🇺🇦 2022: Началось полномасштабное вторжение РФ.",
    (8, 24): "🇺🇦 1991: Украина провозгласила независимость.",
}

def get_day_info():
    today = date.today()
    holiday = HOLIDAYS.get((today.month, today.day), "")
    text = today.strftime("📅 %d.%m.%Y")
    if holiday:
        text += f"\n{holiday}"
    event = UKRAINE_EVENTS.get((today.month, today.day), "")
    if event:
        text += f"\n{event}"
    return text

def get_weather(city):
    try:
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": WEATHER_API, "units": "metric", "lang": "ru"}
        ).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        feels = r['main']['feels_like']
        humidity = r['main']['humidity']
        return f"🌤 {desc}\n🌡 {temp}°C (ощущается {feels}°C)\n💧 Влажность: {humidity}%"
    except:
        return "❌ Ошибка погоды"

def get_currency():
    try:
        r = requests.get("https://www.deghest.md/curscentru", timeout=10)
        text = r.text

        def extract(code):
            try:
                block = text.split(code)[1]
                nums = re.findall(r'\d{1,2}[.,]\d{2,3}', block)
                nums = [n.replace(',', '.') for n in nums]
                if len(nums) >= 2:
                    return f"{nums[0]} / {nums[1]}"
                return "—"
            except:
                return "—"

        return (
            "💱 Курс валют:\n"
            f"USD: {extract('USD')}\n"
            f"EUR: {extract('EUR')}\n"
            f"RON: {extract('RON')}\n"
            f"UAH: {extract('UAH')}"
        )
    except:
        return "❌ Ошибка курса"

def get_fuel():
    try:
        r = requests.get(
            "https://point.md/ru/novosti/story/tsena-na-toplivo/",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        text = r.text
        benzin = re.findall(r'(?:A-95|А-95)[^0-9]*(\d{2}[.,]\d{2})', text)
        dizel = re.findall(r'(?:дизел)[^0-9]*(\d{2}[.,]\d{2})', text)
        result = "⛽ Топливо:\n"
        result += f"Бензин A95: {benzin[0] if benzin else '—'}\n"
        result += f"Дизель: {dizel[0] if dizel else '—'}"
        return result
    except:
        return "⛽ Данные недоступны"

def get_fact():
    return random.choice(FACTS)

# ------------------ ОТПРАВКА ------------------

async def send_report(uid):
    city = user_settings[str(uid)]["city"]
    text = (
        f"{get_day_info()}\n\n"
        f"🌍 Город: {city}\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_fuel()}\n\n"
        f"{get_fact()}"
    )
    await bot.send_message(uid, text)

async def broadcast(text):
    for uid in user_settings.keys():
        try:
            await bot.send_message(uid, text)
        except:
            pass

# ------------------ ПЛАНИРОВЩИК ------------------

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

# ------------------ КОМАНДЫ ------------------

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

    await m.answer("✅ Бот активирован!", reply_markup=get_keyboard(uid))

@dp.message(F.text == "📊 Сводка сейчас")
async def now(m: types.Message):
    await send_report(str(m.from_user.id))

@dp.message(F.text == "⚙️ Настройки")
async def settings(m: types.Message):
    uid = str(m.from_user.id)
    s = user_settings[uid]
    await m.answer(
        f"🏙 {s['city']}\n⏰ {s['hour']:02d}:{s['minute']:02d}",
        reply_markup=get_keyboard(uid)
    )

@dp.message(F.text == "🏙 Сменить город")
async def set_city(m: types.Message):
    uid = str(m.from_user.id)
    user_settings[uid]["waiting"] = "city"
    save_users()
    await m.answer("Введите город (пример: Chisinau,MD)")

@dp.message(F.text == "⏰ Сменить время")
async def set_time(m: types.Message):
    uid = str(m.from_user.id)
    user_settings[uid]["waiting"] = "time"
    save_users()
    await m.answer("Введите время 07:00")

@dp.message(F.text == "👥 Статистика")
async def stats_button(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(f"👥 Всего пользователей: {len(user_settings)}")

@dp.message(F.text == "📢 Рассылка")
async def broadcast_button(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    user_settings[str(m.from_user.id)]["waiting"] = "broadcast"
    await m.answer("Введите текст для рассылки:")

@dp.message()
async def handler(m: types.Message):
    uid = str(m.from_user.id)
    waiting = user_settings.get(uid, {}).get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        save_users()
        await m.answer("✅ Город обновлён", reply_markup=get_keyboard(uid))

    elif waiting == "time":
        try:
            hour, minute = map(int, m.text.split(":"))
            user_settings[uid]["hour"] = hour
            user_settings[uid]["minute"] = minute
            user_settings[uid]["waiting"] = None
            save_users()
            reschedule(uid)
            await m.answer("✅ Время обновлено", reply_markup=get_keyboard(uid))
        except:
            await m.answer("❌ Неверный формат")

    elif waiting == "broadcast" and m.from_user.id == ADMIN_ID:
        await broadcast(m.text)
        user_settings[uid]["waiting"] = None
        await m.answer("✅ Рассылка отправлена", reply_markup=get_keyboard(uid))

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
