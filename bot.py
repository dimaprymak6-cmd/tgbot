import asyncio, requests, os, re, random, sys, json
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

def save_users():
    try:
        data = {str(k): v for k, v in user_settings.items()}
        with open(USERS_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
            for k, v in data.items():
                user_settings[int(k)] = v
    except:
        pass

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

ENGLISH_PHRASES = [
    ("Good morning!", "Доброе утро!"),
    ("Have a nice day!", "Хорошего дня!"),
    ("How are you?", "Как дела?"),
    ("I'm fine, thank you.", "Я в порядке, спасибо."),
    ("What's the weather like?", "Какая погода?"),
    ("It's a beautiful day.", "Прекрасный день."),
    ("See you tomorrow!", "До завтра!"),
    ("Take care of yourself.", "Береги себя."),
    ("Everything will be fine.", "Всё будет хорошо."),
    ("Keep going, don't give up!", "Продолжай, не сдавайся!"),
    ("You can do it!", "Ты можешь это сделать!"),
    ("Step by step.", "Шаг за шагом."),
    ("Every day is a new chance.", "Каждый день — новый шанс."),
    ("Stay positive!", "Оставайся позитивным!"),
    ("Hard work pays off.", "Упорный труд окупается."),
    ("Believe in yourself.", "Верь в себя."),
    ("Actions speak louder than words.", "Дела говорят громче слов."),
    ("Time is money.", "Время — деньги."),
    ("Better late than never.", "Лучше поздно, чем никогда."),
    ("Live and learn.", "Живи и учись."),
    ("Practice makes perfect.", "Практика делает мастера."),
    ("Knowledge is power.", "Знание — сила."),
    ("Where there's a will, there's a way.", "Где есть желание, там есть путь."),
    ("Every cloud has a silver lining.", "Нет худа без добра."),
    ("Don't worry, be happy.", "Не переживай, будь счастлив."),
    ("Home is where the heart is.", "Дом там, где сердце."),
    ("The early bird catches the worm.", "Кто рано встаёт, тому Бог подаёт."),
    ("No pain, no gain.", "Без труда не вытащишь рыбку из пруда."),
    ("Look before you leap.", "Семь раз отмерь, один раз отрежь."),
    ("Two heads are better than one.", "Одна голова хорошо, а две лучше."),
    ("A friend in need is a friend indeed.", "Друг познаётся в беде."),
    ("All that glitters is not gold.", "Не всё то золото, что блестит."),
    ("The more, the merrier.", "Чем больше, тем веселее."),
    ("It takes two to tango.", "Для танго нужны двое."),
    ("Good things come to those who wait.", "Всё приходит к тому, кто умеет ждать."),
    ("You reap what you sow.", "Что посеешь, то и пожнёшь."),
    ("The pen is mightier than the sword.", "Перо сильнее меча."),
    ("Life is short, enjoy it.", "Жизнь коротка, наслаждайся ею."),
    ("Dream big, work hard.", "Мечтай смело, работай усердно."),
    ("Never stop learning.", "Никогда не переставай учиться."),
    ("Be kind to others.", "Будь добр к другим."),
    ("Smile and the world smiles with you.", "Улыбнись — и мир улыбнётся тебе."),
    ("Think before you speak.", "Думай прежде, чем говорить."),
    ("Make the most of every day.", "Используй каждый день по максимуму."),
    ("Small steps lead to big results.", "Маленькие шаги ведут к большим результатам."),
    ("Be the change you want to see.", "Будь тем изменением, которое хочешь видеть."),
    ("It's never too late to start.", "Никогда не поздно начать."),
    ("Happiness is a choice.", "Счастье — это выбор."),
    ("Do what you love.", "Делай то, что любишь."),
    ("Success is a journey, not a destination.", "Успех — это путь, а не пункт назначения."),
]

UKRAINE_EVENTS = {
    (1, 1): "🇺🇦 В этот день в 2016 году Украина перешла на безвизовый режим с Грузией.",
    (1, 9): "🇺🇦 В этот день в 1990 году в Киеве прошёл первый Съезд Руха.",
    (1, 22): "🇺🇦 В этот день в 1918 году провозглашена независимость Украинской Народной Республики.",
    (1, 28): "🇺🇦 В этот день в 1992 году Украина приняла государственный флаг — сине-жёлтый.",
    (2, 2): "🇺🇦 В этот день в 1918 году Центральная Рада подписала мир с Германией.",
    (2, 9): "🇺🇦 В этот день в 1918 году УНР подписала мирный договор в Брест-Литовске.",
    (2, 16): "🇺🇦 В этот день в 1992 году введена украинская валюта — купон-карбованец.",
    (2, 20): "🇺🇦 В этот день в 2014 году — самый кровавый день Майдана, погибли более 50 человек.",
    (2, 22): "🇺🇦 В этот день в 2014 году Янукович бежал из Украины.",
    (2, 24): "🇺🇦 В этот день в 2022 году Россия начала полномасштабное вторжение в Украину.",
    (2, 26): "🇺🇦 В этот день в 2022 году украинские силы остановили колонну войск под Киевом.",
    (2, 28): "🇺🇦 В этот день в 2022 году начались первые переговоры Украины и России на белорусской границе.",
    (3, 4): "🇺🇦 В этот день в 2022 году российские войска захватили Запорожскую АЭС.",
    (3, 9): "🇺🇦 В этот день в 1814 году родился Тарас Шевченко — великий украинский поэт.",
    (3, 16): "🇺🇦 В этот день в 2014 году прошёл незаконный референдум в Крыму.",
    (3, 18): "🇺🇦 В этот день в 2014 году Россия аннексировала Крым.",
    (3, 20): "🇺🇦 В этот день в 2022 году разрушен Драматический театр в Мариуполе.",
    (4, 5): "🇺🇦 В этот день в 2022 году стало известно о массовых убийствах мирных жителей в Буче.",
    (4, 26): "🇺🇦 В этот день в 1986 году произошла катастрофа на Чернобыльской АЭС.",
    (5, 2): "🇺🇦 В этот день в 2014 году трагедия в Одессе — столкновения унесли 48 жизней.",
    (5, 9): "🇺🇦 В этот день в 1945 году — победа над нацистской Германией.",
    (5, 16): "🇺🇦 В этот день в 2022 году защитники Азовстали сложили оружие после 82 дней обороны.",
    (5, 18): "🇺🇦 В этот день в 1944 году началась депортация крымских татар Сталиным.",
    (6, 1): "🇺🇦 В этот день в 2022 году Украина получила статус кандидата на вступление в ЕС.",
    (6, 28): "🇺🇦 В этот день в 1996 году принята Конституция Украины.",
    (7, 8): "🇺🇦 В этот день в 2022 году ракетный удар по Виннице унёс жизни 27 мирных жителей.",
    (7, 16): "🇺🇦 В этот день в 1990 году Верховная Рада приняла Декларацию о суверенитете.",
    (8, 24): "🇺🇦 В этот день в 1991 году Украина провозгласила независимость от СССР.",
    (8, 29): "🇺🇦 В этот день в 2022 году началось контрнаступление Украины на Херсонском направлении.",
    (9, 1): "🇺🇦 В этот день в 1939 году Германия напала на Польшу — начало Второй мировой войны.",
    (9, 6): "🇺🇦 В этот день в 2022 году началось Харьковское контрнаступление Украины.",
    (9, 11): "🇺🇦 В этот день в 2022 году Украина освободила Изюм от российских войск.",
    (9, 29): "🇺🇦 В этот день в 1941 году массовое убийство в Бабьем Яру — более 33 000 жертв.",
    (10, 8): "🇺🇦 В этот день в 2022 году взрыв на Керченском мосту — ключевая победа Украины.",
    (10, 10): "🇺🇦 В этот день в 2022 году Россия нанесла массированный ракетный удар по городам Украины.",
    (10, 14): "🇺🇦 День защитника Украины — национальный праздник.",
    (10, 28): "🇺🇦 В этот день в 1944 году вся территория Украины освобождена от нацистов.",
    (11, 11): "🇺🇦 В этот день в 2022 году Украина освободила Херсон от российской оккупации.",
    (11, 21): "🇺🇦 В этот день в 2013 году начался Евромайдан в Киеве.",
    (11, 22): "🇺🇦 В этот день в 2004 году началась Оранжевая революция на Украине.",
    (11, 28): "🇺🇦 День памяти жертв Голодомора — геноцида украинского народа в 1932-1933 годах.",
    (12, 1): "🇺🇦 В этот день в 1991 году референдум подтвердил независимость Украины — 90% за.",
    (12, 5): "🇺🇦 В этот день в 1994 году подписан Будапештский меморандум.",
    (12, 19): "🇺🇦 В этот день в 1991 году Украина вступила в СНГ.",
    (12, 25): "🇺🇦 В этот день в 1991 году СССР официально прекратил существование.",
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

def get_english_phrase():
    today = date.today()
    idx = today.timetuple().tm_yday % len(ENGLISH_PHRASES)
    phrase, translation = ENGLISH_PHRASES[idx]
    return f"🇬🇧 Фраза дня:\n_{phrase}_\n🔤 {translation}"

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
    today = date.today()
    idx = today.timetuple().tm_yday % len(FACTS)
    return f"💡 {FACTS[idx]}"

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
        f"{get_fact()}\n\n"
        f"{get_english_phrase()}"
    )
    await bot.send_message(uid, text, parse_mode="Markdown")

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
        save_users()
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
    await m.answer(
        f"👥 Всего пользователей: {count}",
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
        save_users()
    waiting = user_settings[uid].get("waiting")

    if waiting == "city":
        user_settings[uid]["city"] = m.text
        user_settings[uid]["waiting"] = None
        reschedule(uid)
        save_users()
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
                save_users()
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
    load_users()
    for uid in list(user_settings.keys()):
        reschedule(uid)
    await bot.delete_webhook(drop_pending_updates=True)
    scheduler.start()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
