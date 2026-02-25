import asyncio, requests, os, re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
user_settings = {}

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
        return f"🌤 Погода: {desc}\n🌡 {temp}°C (ощущается {feels}°C)\n💧 Влажность: {humidity}%"
    except:
        return "❌ Ошибка погоды"

def get_currency():
    try:
        r = requests.get("https://www.deghest.md/curscentru", timeout=10)
        text = r.text

        def extract(code):
            try:
                block = text.split(code)[1]
                part = block.split("cumpăr")[1][:150]
                nums = re.findall(r'\d{1,2}[.,]\d{2}', part)
                nums = [n.replace(',', '.') for n in nums]
                if len(nums) >= 2:
                    return f"{nums[0]} / {nums[1]}"
                return "—"
            except:
                return "—"

        usd = extract("USD")
        eur = extract("EUR")
        ron = extract("RON")
        uah = extract("UAH")
        gbp = extract("GBP")

        return (
            f"💱 Курс валют (покупка / продажа MDL):\n"
            f"🇺🇸 Доллар США:   {usd}\n"
            f"🇪🇺 Евро:              {eur}\n"
            f"🇷🇴 Лей румынский: {ron}\n"
            f"🇺🇦 Гривна:           {uah}\n"
            f"🇬🇧 Фунт стерл.:    {gbp}"
        )
    except:
        return "❌ Ошибка курса валют"

def get_roads(city):
    return f"🚗 Дороги в {city}: данные недоступны в бесплатном режиме"

async def send_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet")
    text = (
        f"🌅 Доброе утро! Ситуация в городе {city}:\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_roads(city)}"
    )
    await bot.send_message(uid, text)

def reschedule(uid):
    job_id = f"report_{uid}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    hour = user_settings.get(uid, {}).get("hour", 7)
    minute = user_settings.get(uid, {}).get("minute", 0)
    scheduler.add_job(
        send_report, "cron",
        hour=hour, minute=minute,
        args=[uid], id=job_id
    )

@dp.message(Command("start"))
async def start(m: types.Message):
    uid = m.from_user.id
    user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    reschedule(uid)
    await m.answer(
        "✅ Бот активирован!\n\n"
        "Каждый день в 7:00 буду присылать сводку.\n\n"
        "Команды:\n"
        "/now — сводка прямо сейчас\n"
        "/setcity — сменить город\n"
        "/settime — сменить время оповещения\n"
        "/settings — текущие настройки"
    )

@dp.message(Command("settings"))
async def settings(m: types.Message):
    uid = m.from_user.id
    s = user_settings.get(uid, {"city": "Edinet", "hour": 7, "minute": 0})
    await m.answer(
        f"⚙️ Текущие настройки:\n"
        f"🏙 Город: {s.get('city', 'Edinet')}\n"
        f"⏰ Время: {s.get('hour', 7):02d}:{s.get('minute', 0):02d}"
    )

@dp.message(Command("now"))
async def now(m: types.Message):
    await send_report(m.from_user.id)

@dp.message(Command("setcity"))
async def setcity(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0}
    user_settings[uid]["waiting"] = "city"
    await m.answer("🏙 Введите название города на английском (например: Chisinau, Balti, Bucuresti):")

@dp.message(Command("settime"))
async def settime(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0}
    user_settings[uid]["waiting"] = "time"
    await m.answer("⏰ Введите время в формате ЧЧ:ММ (например: 07:00 или 08:30):")

@dp.message()
async def handle_input(m: types.Message):
    uid = m.from_user.id
    waiting = user_settings.get(uid, {}).get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        await m.answer(f"✅ Город изменён на: {m.text}")

    elif waiting == "time":
        try:
            parts = m.text.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                user_settings[uid]["hour"] = hour
                user_settings[uid]["minute"] = minute
                user_settings[uid]["waiting"] = None
                reschedule(uid)
                await m.answer(f"✅ Время изменено на: {hour:02d}:{minute:02d}")
            else:
                await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")
        except:
            await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")
    else:
        await m.answer(
            "Команды:\n"
            "/now — сводка прямо сейчас\n"
            "/setcity — сменить город\n"
            "/settime — сменить время\n"
            "/settings — текущие настройки"
        )

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
