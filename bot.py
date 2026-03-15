import asyncio, requests, os, re, sys, json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date, datetime
import fcntl

TOKEN = os.environ.get("TOKEN")
WEATHER_API = os.environ.get("WEATHER_API")
ADMIN_ID = 5200690387
USERS_FILE = "/tmp/users.json"

lock_file = open("/tmp/bot.lock", "w")
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("Другой процесс уже запущен. Выход.")
    sys.exit(0)

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Chisinau")
user_settings = {}
last_sent = {}

WELCOME_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Flag_of_Moldova.svg/1200px-Flag_of_Moldova.svg.png"

def save_users():
    try:
        data = {str(k): v for k, v in user_settings.items()}
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Save error: {e}")

def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
            for k, v in data.items():
                user_settings[int(k)] = v
            print(f"Загружено пользователей: {len(user_settings)}")
    except Exception as e:
        print(f"Load error: {e}")

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
    "Единцы основаны в 1774 году и названы по реке Единец.",
    "Молдова — один из крупнейших производителей вина в мире.",
    "В Молдове находится самый большой подземный винный погреб — Милештий Мичь (55 км тоннелей).",
    "Молдова — одна из самых маленьких стран Европы, площадь всего 33 846 км².",
    "В Молдове более 300 солнечных дней в году.",
    "Молдова граничит только с двумя странами — Румынией и Украиной.",
    "Кишинёв — один из самых зелёных городов Европы по числу деревьев.",
    "В Молдове производят более 50 сортов местного вина.",
    "Национальный язык Молдовы — румынский.",
    "Средняя продолжительность жизни в Молдове — 72 года.",
    "Молдова занимает первое место в мире по потреблению вина на душу населения.",
    "В Молдове более 1000 рек и речушек.",
    "Единцкий район граничит с Украиной на севере.",
    "Население Молдовы около 2.6 миллиона человек.",
    "Кишинёв основан в 1436 году.",
    "В Молдове находится уникальный заповедник Кодры — дубовые леса.",
    "Молдова экспортирует около 70% произведённого вина.",
    "Средняя температура летом в Молдове +22°C.",
    "В Молдове выращивают лучшие в Европе грецкие орехи.",
    "В Молдове официально зарегистрировано более 140 виноградников.",
    "Молдова входит в топ-20 стран мира по производству подсолнечного масла.",
    "В Единцком районе находится несколько православных монастырей.",
    "Река Прут образует западную границу Молдовы с Румынией.",
    "В Молдове более 600 000 гектаров сельскохозяйственных угодий.",
]

UKRAINE_EVENTS = {
    (1, 1): "🇺🇦 В этот день в 2016 году Украина перешла на безвизовый режим с Грузией.",
    (1, 22): "🇺🇦 В этот день в 1918 году провозглашена независимость УНР.",
    (2, 20): "🇺🇦 В этот день в 2014 году — самый кровавый день Майдана.",
    (2, 22): "🇺🇦 В этот день в 2014 году Янукович бежал из Украины.",
    (2, 24): "🇺🇦 В этот день в 2022 году Россия начала полномасштабное вторжение в Украину.",
    (2, 26): "🇺🇦 В этот день в 2022 году украинские силы остановили колонну войск под Киевом.",
    (2, 28): "🇺🇦 В этот день в 2022 году начались первые переговоры Украины и России.",
    (3, 4): "🇺🇦 В этот день в 2022 году российские войска захватили Запорожскую АЭС.",
    (3, 9): "🇺🇦 В этот день в 1814 году родился Тарас Шевченко — великий украинский поэт.",
    (3, 15): "🇺🇦 В этот день в 2022 году Россия нанесла удары по Николаеву и Херсону.",
    (3, 16): "🇺🇦 В этот день в 2014 году прошёл незаконный референдум в Крыму.",
    (3, 18): "🇺🇦 В этот день в 2014 году Россия аннексировала Крым.",
    (4, 5): "🇺🇦 В этот день в 2022 году стало известно о массовых убийствах мирных жителей в Буче.",
    (4, 26): "🇺🇦 В этот день в 1986 году произошла катастрофа на Чернобыльской АЭС.",
    (5, 9): "🇺🇦 В этот день в 1945 году — победа над нацистской Германией.",
    (5, 16): "🇺🇦 В этот день в 2022 году защитники Азовстали сложили оружие после 82 дней обороны.",
    (5, 18): "🇺🇦 В этот день в 1944 году началась депортация крымских татар Сталиным.",
    (6, 28): "🇺🇦 В этот день в 1996 году принята Конституция Украины.",
    (7, 16): "🇺🇦 В этот день в 1990 году Верховная Рада приняла Декларацию о суверенитете.",
    (8, 24): "🇺🇦 В этот день в 1991 году Украина провозгласила независимость от СССР.",
    (9, 29): "🇺🇦 В этот день в 1941 году массовое убийство в Бабьем Яру — более 33 000 жертв.",
    (10, 8): "🇺🇦 В этот день в 2022 году взрыв на Керченском мосту.",
    (10, 14): "🇺🇦 День защитника Украины — национальный праздник.",
    (10, 28): "🇺🇦 В этот день в 1944 году вся территория Украины освобождена от нацистов.",
    (11, 11): "🇺🇦 В этот день в 2022 году Украина освободила Херсон.",
    (11, 21): "🇺🇦 В этот день в 2013 году начался Евромайдан в Киеве.",
    (11, 22): "🇺🇦 В этот день в 2004 году началась Оранжевая революция.",
    (11, 28): "🇺🇦 День памяти жертв Голодомора 1932-1933 годов.",
    (12, 1): "🇺🇦 В этот день в 1991 году референдум подтвердил независимость Украины.",
    (12, 5): "🇺🇦 В этот день в 1994 году подписан Будапештский меморандум.",
    (12, 25): "🇺🇦 В этот день в 1991 году СССР официально прекратил существование.",
}

DIV = "➖➖➖➖➖➖➖➖➖➖"

def get_main_keyboard(uid=0):
    buttons = [
        [KeyboardButton(text="📊 Сводка сейчас"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="🌤 Погода"), KeyboardButton(text="💱 Курс валют")],
        [KeyboardButton(text="⛽ Топливо"), KeyboardButton(text="📰 Новости")],
        [KeyboardButton(text="🏙 Сменить город"), KeyboardButton(text="⏰ Сменить время")],
        [KeyboardButton(text="🔔 Напоминание")],
    ]
    if uid == ADMIN_ID:
        buttons.append([KeyboardButton(text="📣 Рассылка"), KeyboardButton(text="👥 Пользователи")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_day_info():
    today = date.today()
    day_name = DAYS_RU[today.weekday()]
    date_str = today.strftime("%d.%m.%Y")
    week_num = today.isocalendar()[1]
    day_of_year = today.timetuple().tm_yday
    holiday = HOLIDAYS.get((today.month, today.day), "")
    result = f"📅 *{day_name}, {date_str}*\n"
    result += f"📆 Неделя #{week_num} | День #{day_of_year}"
    if today.weekday() >= 5:
        result += " | 🎉 *Выходной!*"
    if holiday:
        result += f"\n{holiday}"
    return result

def get_ukraine_event():
    today = date.today()
    event = UKRAINE_EVENTS.get((today.month, today.day), "")
    return f"\n{event}" if event else ""

def get_war_counter():
    start = date(2022, 2, 24)
    days = (date.today() - start).days
    return f"⚔️ *День войны в Украине: #{days}*"

def get_fact():
    idx = date.today().timetuple().tm_yday % len(FACTS)
    return f"💡 _{FACTS[idx]}_"

def get_weather(city):
    try:
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": WEATHER_API, "units": "metric", "lang": "ru"}
        ).json()
        desc = r['weather'][0]['description'].capitalize()
        temp = round(r['main']['temp'], 1)
        feels = round(r['main']['feels_like'], 1)
        humidity = r['main']['humidity']
        wind = round(r['wind']['speed'], 1)
        return (
            f"🌡 *{temp}°C* (ощущается *{feels}°C*)\n"
            f"☁️ {desc}\n"
            f"💧 Влажность: *{humidity}%* | 💨 Ветер: *{wind} м/с*"
        )
    except:
        return "❌ Ошибка погоды"

def get_forecast(city):
    try:
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast",
            params={"q": city, "appid": WEATHER_API, "units": "metric", "lang": "ru", "cnt": 24}
        ).json()
        seen = set()
        result = ""
        for item in r['list']:
            day = item['dt_txt'][:10]
            if day not in seen and day != str(date.today()):
                seen.add(day)
                d = datetime.strptime(day, "%Y-%m-%d")
                day_name = DAYS_RU[d.weekday()]
                temp = round(item['main']['temp'], 1)
                desc = item['weather'][0]['description']
                result += f"• *{day_name} {d.strftime('%d.%m')}:* {temp}°C, {desc}\n"
            if len(seen) >= 3:
                break
        return result.strip()
    except:
        return "❌ Ошибка прогноза"

def get_bitcoin():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
            timeout=10
        ).json()
        btc = r['bitcoin']['usd']
        eth = r['ethereum']['usd']
        return f"🟡 Bitcoin: *${btc:,.0f}*\n🔷 Ethereum: *${eth:,.0f}*"
    except:
        return "₿ Крипто: данные недоступны"

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
                    return f"*{nums[0]}* / *{nums[1]}*"
                elif len(nums) == 1:
                    return f"*{nums[0]}*"
                return "—"
            except:
                return "—"

        return (
            f"🇺🇸 Доллар США:      {extract('USD')}\n"
            f"🇪🇺 Евро:               {extract('EUR')}\n"
            f"🇷🇴 Лей румынский:  {extract('RON')}\n"
            f"🇺🇦 Гривна:            {extract('UAH')}\n"
            f"🇬🇧 Фунт стерл.:     {extract('GBP')}"
        )
    except:
        return "❌ Ошибка курса валют"

def get_fuel():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Источник 1: bemol.md
    # Страница после парсинга содержит текст:
    # "Premium\n98\n\n00.00\n\n29.95\nPremium\n95\n\n00.00\n\n26.22\nEuro\nDiesel\n\n00.00\n\n26.24\nLICHEFIAT\nGAZ\n\n00.00\n\n13.80"
    # Просто берём ВСЕ числа XX.XX со страницы, убираем 00.00, берём первые 4
    try:
        r = requests.get("https://bemol.md/ru/prices", timeout=10, headers=headers)
        text = r.text

        # Все числа формата XX.XX на странице
        all_nums = re.findall(r'\b\d{2}\.\d{2}\b', text)
        print(f"bemol all_nums: {all_nums}")

        # Фильтруем — убираем 00.00, берём числа > 10 (цены топлива)
        prices = [n for n in all_nums if n != "00.00" and float(n) > 10]
        print(f"bemol prices: {prices}")

        # Определяем какие виды топлива есть на странице
        has_98 = "Premium\n98" in text or "Premium 98" in text
        has_95 = "Premium\n95" in text or "Premium 95" in text
        has_diesel = "Diesel" in text
        has_gaz = "GAZ" in text or "LICHEFIAT" in text

        idx = 0
        b98 = b95 = diesel = lpg = None

        if has_98 and idx < len(prices):
            b98 = prices[idx]; idx += 1
        if has_95 and idx < len(prices):
            b95 = prices[idx]; idx += 1
        if has_diesel and idx < len(prices):
            diesel = prices[idx]; idx += 1
        if has_gaz and idx < len(prices):
            lpg = prices[idx]; idx += 1

        print(f"bemol result: 98={b98} 95={b95} diesel={diesel} lpg={lpg}")

        if any([b98, b95, diesel, lpg]):
            result = ""
            if b98:    result += f"🔴 Премиум 98: *{b98} MDL*\n"
            if b95:    result += f"🟡 Премиум 95: *{b95} MDL*\n"
            if diesel: result += f"🔵 Дизель Euro: *{diesel} MDL*\n"
            if lpg:    result += f"🟢 Газ LPG: *{lpg} MDL*\n"
            return result.strip()

    except Exception as e:
        print(f"Fuel bemol error: {e}")

    # Источник 2: realitatea.md
    try:
        r = requests.get("https://realitatea.md/", timeout=10, headers=headers)
        text = r.text
        b = re.findall(r'(?:benzin|COR.?95)[^\d]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        d = re.findall(r'(?:motorin|дизел)[^\d]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        if b or d:
            result = ""
            if b: result += f"🟡 Бензин А-95: *{b[0].replace(',','.')} MDL*\n"
            if d: result += f"🔵 Дизель: *{d[0].replace(',','.')} MDL*"
            return result.strip()
    except Exception as e:
        print(f"Fuel realitatea error: {e}")

    # Источник 3: nokta.md
    try:
        r = requests.get("https://nokta.md/ru/", timeout=10, headers=headers)
        text = r.text
        b = re.findall(r'(?:бензин|A-?95)[^\d]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        d = re.findall(r'(?:дизел|motorin)[^\d]*(\d{2}[.,]\d{2})', text, re.IGNORECASE)
        if b or d:
            result = ""
            if b: result += f"🟡 Бензин А-95: *{b[0].replace(',','.')} MDL*\n"
            if d: result += f"🔵 Дизель: *{d[0].replace(',','.')} MDL*"
            return result.strip()
    except Exception as e:
        print(f"Fuel nokta error: {e}")

    return "данные недоступны"

def get_moldova_news():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = requests.get("https://newsmaker.md/ru/", timeout=10, headers=headers)
        text = r.text
        headlines = re.findall(r'<a[^>]+href="https://newsmaker\.md/ru/[^"#]*"[^>]*>\s*([^<]{25,150})\s*</a>', text)
        headlines = [h.strip() for h in headlines if len(h.strip()) > 25]
        if len(headlines) >= 2:
            seen = set()
            result = ""
            count = 0
            for h in headlines:
                if h not in seen:
                    seen.add(h)
                    result += f"• {h}\n"
                    count += 1
                if count >= 4:
                    break
            if count >= 2:
                return result.strip()
    except Exception as e:
        print(f"News newsmaker error: {e}")

    try:
        r = requests.get("https://nokta.md/ru/", timeout=10, headers=headers)
        text = r.text
        headlines = re.findall(r'<h\d[^>]*>\s*<a[^>]*>([^<]{25,150})</a>', text)
        headlines = [h.strip() for h in headlines if len(h.strip()) > 25]
        if len(headlines) >= 2:
            seen = set()
            result = ""
            count = 0
            for h in headlines:
                if h not in seen:
                    seen.add(h)
                    result += f"• {h}\n"
                    count += 1
                if count >= 4:
                    break
            if count >= 2:
                return result.strip()
    except Exception as e:
        print(f"News nokta error: {e}")

    try:
        r = requests.get("https://realitatea.md/", timeout=10, headers=headers)
        text = r.text
        headlines = re.findall(r'<h\d[^>]*>\s*<a[^>]*>([^<]{25,150})</a>', text)
        headlines = [h.strip() for h in headlines if len(h.strip()) > 25]
        if len(headlines) >= 2:
            seen = set()
            result = ""
            count = 0
            for h in headlines:
                if h not in seen:
                    seen.add(h)
                    result += f"• {h}\n"
                    count += 1
                if count >= 4:
                    break
            if count >= 2:
                return result.strip()
    except Exception as e:
        print(f"News realitatea error: {e}")

    return "данные недоступны"

async def send_evening_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet")
    fuel = get_fuel()
    news = get_moldova_news()
    text = (
        f"🌙 *ВЕЧЕРНЯЯ СВОДКА*\n🏙 _{city}_\n{DIV}\n\n"
        f"🌤 *ПОГОДА*\n{get_weather(city)}\n\n{DIV}\n"
        f"💱 *КУРС ВАЛЮТ* _(покупка / продажа MDL)_\n{get_currency()}\n\n{DIV}\n"
        f"₿ *КРИПТО*\n{get_bitcoin()}\n\n{DIV}\n"
        f"⛽ *ТОПЛИВО BEMOL*\n{fuel}\n\n{DIV}\n"
        f"📰 *НОВОСТИ*\n{news}\n\n{DIV}\n"
        f"🌙 _Хорошего вечера!_"
    )
    await bot.send_message(uid, text, parse_mode="Markdown")

async def send_report(uid, scheduled=False):
    if scheduled:
        now = datetime.now()
        key = f"{uid}_{now.strftime('%Y%m%d%H%M')}"
        if key in last_sent:
            return
        last_sent[key] = True

    city = user_settings.get(uid, {}).get("city", "Edinet")
    ukraine_event = get_ukraine_event()
    fuel = get_fuel()
    news = get_moldova_news()

    text = (
        f"{get_day_info()}{ukraine_event}\n"
        f"{get_war_counter()}\n{DIV}\n\n"
        f"🌅 *ДОБРОЕ УТРО, {city.upper()}!*\n\n{DIV}\n"
        f"🌤 *ПОГОДА*\n{get_weather(city)}\n\n"
        f"📅 *ПРОГНОЗ НА 3 ДНЯ*\n{get_forecast(city)}\n\n{DIV}\n"
        f"💱 *КУРС ВАЛЮТ* _(покупка / продажа MDL)_\n{get_currency()}\n\n{DIV}\n"
        f"₿ *КРИПТО*\n{get_bitcoin()}\n\n{DIV}\n"
        f"⛽ *ТОПЛИВО BEMOL*\n{fuel}\n\n{DIV}\n"
        f"📰 *НОВОСТИ МОЛДОВЫ*\n{news}\n\n{DIV}\n"
        f"{get_fact()}"
    )
    await bot.send_message(uid, text, parse_mode="Markdown")

def reschedule(uid):
    s = user_settings.get(uid, {})
    hour = s.get("hour", 7)
    minute = s.get("minute", 0)

    job_id = f"report_{uid}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(send_report, "cron", hour=hour, minute=minute,
                      args=[uid, True], id=job_id, replace_existing=True)

    evening_job_id = f"evening_{uid}"
    if scheduler.get_job(evening_job_id):
        scheduler.remove_job(evening_job_id)
    scheduler.add_job(send_evening_report, "cron", hour=20, minute=0,
                      args=[uid], id=evening_job_id, replace_existing=True)

    rem_hour = s.get("reminder_hour")
    rem_minute = s.get("reminder_minute")
    rem_text = s.get("reminder_text")
    if rem_hour is not None and rem_text:
        rem_job_id = f"reminder_{uid}"
        if scheduler.get_job(rem_job_id):
            scheduler.remove_job(rem_job_id)
        async def make_reminder(u=uid, t=rem_text):
            await bot.send_message(u, f"🔔 *Напоминание!*\n\n{t}", parse_mode="Markdown")
        scheduler.add_job(make_reminder, "cron", hour=rem_hour, minute=rem_minute,
                          id=rem_job_id, replace_existing=True)

@dp.message(Command("start"))
async def start(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
        save_users()
    reschedule(uid)
    welcome_text = (
        "🇲🇩 *Добро пожаловать в бот Единцы!*\n\n"
        "Я буду присылать тебе каждый день:\n\n"
        "🌤 Погоду и прогноз\n"
        "💱 Курс валют\n"
        "₿ Курс крипты\n"
        "⛽ Цены на топливо BEMOL\n"
        "📰 Новости Молдовы\n"
        "💡 Факт о Молдове\n\n"
        "🕖 *Утренняя сводка:* 07:00\n"
        "🌙 *Вечерняя сводка:* 20:00\n\n"
        "Используй кнопки внизу 👇"
    )
    try:
        await bot.send_photo(uid, photo=WELCOME_IMAGE, caption=welcome_text,
                             parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
    except:
        await m.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "📊 Сводка сейчас")
async def btn_now(m: types.Message):
    uid = m.from_user.id
    key = f"now_{uid}"
    if key in last_sent:
        if (datetime.now() - last_sent[key]).total_seconds() < 10:
            return
    last_sent[key] = datetime.now()
    await send_report(uid, scheduled=False)

@dp.message(F.text == "🌤 Погода")
async def btn_weather(m: types.Message):
    uid = m.from_user.id
    city = user_settings.get(uid, {}).get("city", "Edinet")
    text = (f"🌤 *ПОГОДА — {city.upper()}*\n{DIV}\n"
            f"{get_weather(city)}\n\n📅 *ПРОГНОЗ НА 3 ДНЯ*\n{get_forecast(city)}")
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "💱 Курс валют")
async def btn_currency(m: types.Message):
    uid = m.from_user.id
    text = (f"💱 *КУРС ВАЛЮТ*\n_{date.today().strftime('%d.%m.%Y')} | покупка / продажа MDL_\n{DIV}\n"
            f"{get_currency()}\n\n{DIV}\n₿ *КРИПТО (USD)*\n{get_bitcoin()}")
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "⛽ Топливо")
async def btn_fuel(m: types.Message):
    uid = m.from_user.id
    text = (f"⛽ *ЦЕНЫ НА ТОПЛИВО*\n_BEMOL | {date.today().strftime('%d.%m.%Y')}_\n{DIV}\n{get_fuel()}")
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "📰 Новости")
async def btn_news(m: types.Message):
    uid = m.from_user.id
    text = (f"📰 *НОВОСТИ МОЛДОВЫ*\n_{date.today().strftime('%d.%m.%Y')}_\n{DIV}\n{get_moldova_news()}")
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "⚙️ Настройки")
async def btn_settings(m: types.Message):
    uid = m.from_user.id
    s = user_settings.get(uid, {"city": "Edinet", "hour": 7, "minute": 0})
    rem = ""
    if s.get("reminder_hour") is not None:
        rem = f"\n🔔 Напоминание: *{s.get('reminder_hour',0):02d}:{s.get('reminder_minute',0):02d}* — {s.get('reminder_text','')}"
    await m.answer(
        f"⚙️ *НАСТРОЙКИ*\n{DIV}\n"
        f"🏙 Город: *{s.get('city','Edinet')}*\n"
        f"⏰ Утренняя сводка: *{s.get('hour',7):02d}:{s.get('minute',0):02d}*\n"
        f"🌙 Вечерняя сводка: *20:00*{rem}",
        parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "🏙 Сменить город")
async def btn_setcity(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "city"
    await m.answer("🏙 Введите название города на английском\n_(например: Chisinau, Balti, Bucuresti)_:", parse_mode="Markdown")

@dp.message(F.text == "⏰ Сменить время")
async def btn_settime(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "time"
    await m.answer("⏰ Введите время утренней сводки\n_Формат: ЧЧ:ММ (например: 07:00)_:", parse_mode="Markdown")

@dp.message(F.text == "🔔 Напоминание")
async def btn_reminder(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "reminder_time"
    await m.answer("🔔 Введите время напоминания\n_Формат: ЧЧ:ММ (например: 09:00)_:", parse_mode="Markdown")

@dp.message(F.text == "👥 Пользователи")
async def btn_users(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    await m.answer(f"👥 *Всего пользователей: {len(user_settings)}*",
                   parse_mode="Markdown", reply_markup=get_main_keyboard(m.from_user.id))

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
        if (datetime.now() - last_sent[key]).total_seconds() < 10:
            return
    last_sent[key] = datetime.now()
    await send_report(uid, scheduled=False)

@dp.message()
async def handle_input(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
        save_users()
    waiting = user_settings[uid].get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text.strip()
        user_settings[uid]["waiting"] = None
        reschedule(uid)
        save_users()
        await m.answer(f"✅ Город изменён на: *{m.text.strip()}*",
                       parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

    elif waiting == "time":
        try:
            h, mi = int(m.text.strip().split(":")[0]), int(m.text.strip().split(":")[1])
            if 0 <= h <= 23 and 0 <= mi <= 59:
                user_settings[uid]["hour"] = h
                user_settings[uid]["minute"] = mi
                user_settings[uid]["waiting"] = None
                reschedule(uid)
                save_users()
                await m.answer(f"✅ Утренняя сводка изменена на: *{h:02d}:{mi:02d}*",
                               parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
            else:
                await m.answer("❌ Неверный формат! Введите как *07:00*", parse_mode="Markdown")
        except:
            await m.answer("❌ Неверный формат! Введите как *07:00*", parse_mode="Markdown")

    elif waiting == "reminder_time":
        try:
            h, mi = int(m.text.strip().split(":")[0]), int(m.text.strip().split(":")[1])
            if 0 <= h <= 23 and 0 <= mi <= 59:
                user_settings[uid]["reminder_hour"] = h
                user_settings[uid]["reminder_minute"] = mi
                user_settings[uid]["waiting"] = "reminder_text"
                save_users()
                await m.answer(f"✅ Время *{h:02d}:{mi:02d}* установлено!\nТеперь введите текст напоминания:",
                               parse_mode="Markdown")
            else:
                await m.answer("❌ Неверный формат! Введите как *09:00*", parse_mode="Markdown")
        except:
            await m.answer("❌ Неверный формат! Введите как *09:00*", parse_mode="Markdown")

    elif waiting == "reminder_text":
        user_settings[uid]["reminder_text"] = m.text.strip()
        user_settings[uid]["waiting"] = None
        reschedule(uid)
        save_users()
        rh = user_settings[uid].get("reminder_hour", 9)
        rm = user_settings[uid].get("reminder_minute", 0)
        await m.answer(f"✅ Напоминание установлено на *{rh:02d}:{rm:02d}*\n_{m.text.strip()}_",
                       parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

    elif waiting == "broadcast":
        if uid != ADMIN_ID:
            return
        user_settings[uid]["waiting"] = None
        count = 0
        for user_id in list(user_settings.keys()):
            try:
                await bot.send_message(user_id, f"📣 *Сообщение от администратора:*\n\n{m.text}",
                                       parse_mode="Markdown")
                count += 1
                await asyncio.sleep(0.1)
            except:
                pass
        await m.answer(f"✅ Рассылка отправлена *{count}* пользователям!",
                       parse_mode="Markdown", reply_markup=get_main_keyboard(uid))
    else:
        await m.answer("Используй кнопки внизу 👇", reply_markup=get_main_keyboard(uid))

async def main():
    load_users()
    for uid in list(user_settings.keys()):
        reschedule(uid)
    await bot.delete_webhook(drop_pending_updates=True)
    scheduler.start()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
