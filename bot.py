import asyncio, requests, os, re, random, sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date, datetime
import fcntl

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")
ADMIN_ID = 5200690387

lock_file = open("/tmp/bot.lock", "w")
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Другой процесс уже запущен. Выход.")
    sys.exit(0)

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
user_settings = {}
last_sent = {}

HOLIDAYS = {
    (1, 1): "🎊 Новый год",
    (1, 7): "🎄 Рождество Христово (православное)",
    (1, 8): "🎄 Рождество Христово (второй день)",
    (3, 8): "🌸 Международный женский день",
    (5, 1): "💼 День труда",
    (5, 9): "🎖 День Победы",
    (6, 1): "👶 День защиты детей",
    (8, 27): "🇲🇩 День независимости Молдовы",
    (8, 31): "🗣 День языка",
    (12, 25): "🎄 Рождество Христово (католическое)",
}

DAYS_RU = {
    0: "Понедельник", 1: "Вторник", 2: "Среда",
    3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
}

FACTS = [
    "💡 Факт дня: Единцы основаны в 1774 году и названы по реке Единец.",
    "💡 Факт дня: Молдова — один из крупнейших производителей вина в мире.",
    "💡 Факт дня: В Молдове находится самый большой в мире подземный винный погреб — Милештий Мичь.",
    "💡 Факт дня: Молдова — одна из самых маленьких стран Европы по площади.",
    "💡 Факт дня: В Молдове более 300 солнечных дней в году.",
    "💡 Факт дня: Молдова граничит только с двумя странами — Румынией и Украиной.",
    "💡 Факт дня: Кишинёв — один из самых зелёных городов Европы по числу деревьев.",
    "💡 Факт дня: В Молдове производят более 50 сортов местного вина.",
    "💡 Факт дня: Национальный язык Молдовы — румынский.",
    "💡 Факт дня: Средняя продолжительность жизни в Молдове — 72 года.",
]

UKRAINE_EVENTS = {
    (1, 1): "🇺🇦 2016: Украина перешла на безвизовый режим с Грузией.",
    (1, 22): "🇺🇦 1918: Провозглашена независимость Украинской Народной Республики.",
    (2, 20): "🇺🇦 2014: Самый кровавый день Майдана — погибли более 50 человек.",
    (2, 22): "🇺🇦 2014: Янукович бежал из Украины после революции Майдан.",
    (2, 24): "🇺🇦 2022: Россия начала полномасштабное вторжение в Украину.",
    (2, 26): "🇺🇦 2022: Украинские силы остановили колонну российских войск под Киевом.",
    (3, 16): "🇺🇦 2014: Незаконный референдум в Крыму организован Россией.",
    (3, 18): "🇺🇦 2014: Россия аннексировала Крым.",
    (4, 26): "🇺🇦 1986: Катастрофа на Чернобыльской АЭС.",
    (5, 9): "🇺🇦 1945: День победы над нацистской Германией.",
    (6, 28): "🇺🇦 1996: Принята Конституция Украины.",
    (8, 24): "🇺🇦 1991: Украина провозгласила независимость от СССР.",
    (9, 29): "🇺🇦 1941: Массовое убийство в Бабьем Яру под Киевом.",
    (10, 14): "🇺🇦 День защитника Украины — национальный праздник.",
    (11, 21): "🇺🇦 2013: Начало революции Евромайдан в Киеве.",
    (11, 22): "🇺🇦 2004: Начало Оранжевой революции в Украине.",
    (12, 1): "🇺🇦 1991: Референдум подтвердил независимость Украины — 90% за.",
    (12, 5): "🇺🇦 1994: Подписан Будапештский меморандум.",
}

def get_main_keyboard(uid=0):
    buttons = [
        [KeyboardButton(text="📊 Сводка сейчас"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="🏙 Сменить город"), KeyboardButton(text="⏰ Сменить время")],
    ]
    if uid == ADMIN_ID:
        buttons.append([KeyboardButton(text="📣 Рассылка"), KeyboardButton(text="👥 Пользователи")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_day_info():
    today = date.today()
    day_name = DAYS_RU[today.weekday()]
    date_str = today.strftime("%d.%m.%Y")
    week_num = today.isocalendar()[1]
    holiday = HOLIDAYS.get((today.month, today.day), "")
    result = f"📅 {day_name}, {date_str} | Неделя #{week_num}"
    if today.weekday() >= 5:
        result += " — 🎉 Выходной!"
    if holiday:
        result += f"\n{holiday}"
    return result

def get_ukraine_event():
    today = date.today()
    event = UKRAINE_EVENTS.get((today.month, today.day), "")
    if event:
        return f"\n{event}"
    return ""

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
                part = block.split("cumpăr")[1][:300]
                nums = re.findall(r'\d{1,2}[.,]\d{2,3}', part)
                nums = [n.replace(',', '.') for n in nums]
                if len(nums) >= 2:
                    return f"{nums[0]} / {nums[1]}"
                elif len(nums) == 1:
                    return f"{nums[0]}"
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
            f"🇺🇸 Доллар США:      {usd}\n"
            f"🇪🇺 Евро:               {eur}\n"
            f"🇷🇴 Лей румынский:  {ron}\n"
            f"🇺🇦 Гривна:            {uah}\n"
            f"🇬🇧 Фунт стерл.:     {gbp}"
        )
    except:
        return "❌ Ошибка курса валют"

def get_fuel():
    try:
        r = requests.get(
            "https://point.md/ru/novosti/story/tsena-na-toplivo/",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        text = r.text
        benzin = re.findall(r'(?:бензин|A-95|А-95)[^0-9]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        dizel = re.findall(r'(?:дизел|motorin)[^0-9]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        result = "⛽ Цены на топливо (MDL/л):\n"
        result += f"🟡 Бензин А-95: {benzin[0].replace(',', '.')}\n" if benzin else "🟡 Бензин А-95: —\n"
        result += f"🔵 Дизель: {dizel[0].replace(',', '.')}" if dizel else "🔵 Дизель: —"
        return result
    except:
        return "⛽ Цены на топливо: данные недоступны"

def get_fact():
    return random.choice(FACTS)

async def send_report(uid, scheduled=False):
    if scheduled:
        now = datetime.now()
        key = f"{uid}_{now.strftime('%Y%m%d%H%M')}"
        if key in last_sent:
            return
        last_sent[key] = True

    city = user_settings.get(uid, {}).get("city", "Edinet")
    ukraine_event = get_ukraine_event()
    text = (
        f"{get_day_info()}{ukraine_event}\n\n"
        f"🌅 Здравствуйте! Ситуация в городе {city}:\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_fuel()}\n\n"
        f"{get_fact()}"
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
        args=[uid, True], id=job_id,
        replace_existing=True
    )

@dp.message(Command("start"))
async def start(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    reschedule(uid)
    await m.answer(
        "✅ Бот активирован!\n\n"
        "Каждый день в 7:00 буду присылать сводку.\n\n"
        "Используй кнопки внизу 👇",
        reply_markup=get_main_keyboard(uid)
    )

@dp.message(F.text == "📊 Сводка сейчас")
async def btn_now(m: types.Message):
    uid = m.from_user.id
    key = f"now_{uid}"
    if key in last_sent:
        diff = (datetime.now() - last_sent[key]).total_seconds()
        if diff < 10:
            return
    last_sent[key] = datetime.now()
    await send_report(uid, scheduled=False)

@dp.message(F.text == "⚙️ Настройки")
async def btn_settings(m: types.Message):
    uid = m.from_user.id
    s = user_settings.get(uid, {"city": "Edinet", "hour": 7, "minute": 0})
    await m.answer(
        f"⚙️ Текущие настройки:\n"
        f"🏙 Город: {s.get('city', 'Edinet')}\n"
        f"⏰ Время: {s.get('hour', 7):02d}:{s.get('minute', 0):02d}",
        reply_markup=get_main_keyboard(uid)
    )

@dp.message(F.text == "🏙 Сменить город")
async def btn_setcity(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "city"
    await m.answer("🏙 Введите название города на английском (например: Chisinau, Balti, Bucuresti):")

@dp.message(F.text == "⏰ Сменить время")
async def btn_settime(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "time"
    await m.answer("⏰ Введите время в формате ЧЧ:ММ (например: 07:00 или 08:30):")

@dp.message(F.text == "👥 Пользователи")
async def btn_users(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    count = len(user_settings)
    ids = "\n".join([f"• {uid}" for uid in user_settings.keys()])
    await m.answer(
        f"👥 Всего пользователей: {count}\n\n{ids}",
        reply_markup=get_main_keyboard(m.from_user.id)
    )

@dp.message(F.text == "📣 Рассылка")
async def btn_broadcast(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    if m.from_user.id not in user_settings:
        user_settings[m.from_user.id] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[m.from_user.id]["waiting"] = "broadcast"
    await m.answer("📣 Введите текст для рассылки всем пользователям:")

@dp.message(Command("now"))
async def cmd_now(m: types.Message):
    uid = m.from_user.id
    key = f"now_{uid}"
    if key in last_sent:
        diff = (datetime.now() - last_sent[key]).total_seconds()
        if diff < 10:
            return
    last_sent[key] = datetime.now()
    await send_report(uid, scheduled=False)

@dp.message()
async def handle_input(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    waiting = user_settings[uid].get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        reschedule(uid)
        await m.answer(f"✅ Город изменён на: {m.text}", reply_markup=get_main_keyboard(uid))

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
                await m.answer(
                    f"✅ Время изменено на: {hour:02d}:{minute:02d}\nЗавтра пришлю сводку в это время!",
                    reply_markup=get_main_keyboard(uid)
                )
            else:
                await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")
        except:
            await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")

    elif waiting == "broadcast":
        if uid != ADMIN_ID:
            return
        user_settings[uid]["waiting"] = None
        count = 0
        for user_id in list(user_settings.keys()):
            try:
                await bot.send_message(user_id, f"📣 Сообщение от администратора:\n\n{m.text}")
                count += 1
                await asyncio.sleep(0.1)
            except:
                pass
        await m.answer(
            f"✅ Рассылка отправлена {count} пользователям!",
            reply_markup=get_main_keyboard(uid)
        )

    else:
        await m.answer("Используй кнопки внизу 👇", reply_markup=get_main_keyboard(uid))

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    scheduler.start()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
