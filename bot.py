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
    ("Good things come to those who wait.", "Всё приходит к тому, кто умеет ждать."),
    ("You reap what you sow.", "Что посеешь, то и пожнёшь."),
    ("Life is short, enjoy it.", "Жизнь коротка, наслаждайся ею."),
    ("Dream big, work hard.", "Мечтай смело, работай усердно."),
    ("Never stop learning.", "Никогда не переставай учиться."),
    ("Be kind to others.", "Будь добр к другим."),
    ("Smile and the world smiles with you.", "Улыбнись — и мир улыбнётся тебе."),
    ("Think before you speak.", "Думай прежде, чем говорить."),
    ("Make the most of every day.", "Используй каждый день по максимуму."),
    ("Small steps lead to big results.", "Маленькие шаги ведут к большим результатам."),
    ("It's never too late to start.", "Никогда не поздно начать."),
    ("Happiness is a choice.", "Счастье — это выбор."),
    ("Do what you love.", "Делай то, что любишь."),
    ("Success is a journey, not a destination.", "Успех — это путь, а не пункт назначения."),
]

QUOTES = [
    ("Наполеон Бонапарт", "Невозможное — это слово из словаря глупцов."),
    ("Альберт Эйнштейн", "Воображение важнее знания."),
    ("Стив Джобс", "Единственный способ делать великую работу — любить то, что делаешь."),
    ("Конфуций", "Не важно, как медленно ты идёшь, главное — не останавливаться."),
    ("Уинстон Черчилль", "Успех — это умение идти от одной неудачи к другой, не теряя энтузиазма."),
    ("Лев Толстой", "Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему."),
    ("Антон Чехов", "Краткость — сестра таланта."),
    ("Мартин Лютер Кинг", "Если ты не можешь летать — беги. Если не можешь бежать — иди. Если не можешь идти — ползи. Но двигайся вперёд."),
    ("Сократ", "Я знаю, что ничего не знаю."),
    ("Билл Гейтс", "Жизнь несправедлива — привыкайте к этому."),
    ("Авраам Линкольн", "Дайте мне шесть часов, чтобы срубить дерево, и я потрачу первые четыре на заточку топора."),
    ("Марк Твен", "Секрет успеха в том, чтобы начать."),
    ("Оскар Уайльд", "Будь собой — все остальные роли уже заняты."),
    ("Фридрих Ницше", "Всё, что нас не убивает, делает нас сильнее."),
    ("Махатма Ганди", "Будь тем изменением, которое хочешь видеть в мире."),
    ("Стивен Хокинг", "Жизнь была бы трагедией, если бы не была такой смешной."),
    ("Альберт Эйнштейн", "Есть только два бесконечных явления: Вселенная и человеческая глупость."),
    ("Достоевский", "Красота спасёт мир."),
    ("Булгаков", "Трусость — это самый страшный грех."),
    ("Черчилль", "Если вы идёте через ад — продолжайте идти."),
]

JOKES = [
    "— Доктор, я буду жить?\n— А смысл?",
    "Оптимист учит английский. Пессимист учит китайский. Реалист учит автомат Калашникова.",
    "— Как ты себя чувствуешь?\n— Как понедельник в пятничном теле.",
    "Я встаю в 6 утра, чтобы всё успеть. Успеваю лечь в 4 утра.",
    "— Почему ты опоздал?\n— Будильник не зазвонил.\n— Почему?\n— Я его не заводил.\n— Почему?\n— Зачем заводить то, что не хочешь слышать?",
    "Мой мозг: надо спать. Я: ок. Мой мозг: а помнишь тот стыд из 2009 года?",
    "Диета — это когда смотришь на еду и говоришь: нет. Потом: ладно, немного. Потом: всё.",
    "Понедельник — это такой маленький год.",
    "Человек, который улыбается когда всё идёт не так, уже придумал на кого свалить вину.",
    "— Папа, что такое WiFi?\n— Это невидимая штука, без которой жить невозможно. Как мама.",
    "Я не толстый, просто у меня много запасных частей.",
    "Кофе — потому что злым людям нельзя давать оружие.",
    "— Ты спишь?\n— Нет, я считаю деньги которых у меня нет.",
    "Жизнь как зебра: если сейчас чёрная полоса — скоро будет белая. Если белая — держись, скоро чёрная.",
    "— Сколько времени?\n— Уже поздно.\n— А точнее?\n— Надо было раньше думать.",
]

RECIPES = [
    ("🥘 Мамалыга", "Вскипятить воду с солью, постепенно всыпать кукурузную муку, варить 20 минут помешивая. Подавать с брынзой и сметаной."),
    ("🥗 Зама", "Сварить курицу, добавить овощи, заправить яйцом с лимонным соком и сметаной. Традиционный молдавский суп."),
    ("🍖 Мититеи", "Смешать фарш говядина+свинина, чеснок, тмин, соду. Сформировать колбаски и жарить на гриле."),
    ("🥧 Плацинда с брынзой", "Раскатать тесто, положить начинку из брынзы с укропом, сложить конвертом и жарить на масле."),
    ("🍲 Чорба де бурта", "Говяжий рубец отварить до мягкости, добавить морковь, заправить яйцом со сметаной и уксусом."),
    ("🥩 Токана", "Обжарить лук, добавить мясо кусочками, тушить с помидорами и чесноком 1.5 часа. Подавать с мамалыгой."),
    ("🍅 Гивеч", "Нарезать баклажаны, перец, помидоры, картофель. Запечь в духовке с чесноком и зеленью."),
    ("🥐 Вертута", "Раскатать тонкое тесто, смазать маслом, посыпать сыром или яблоками с сахаром, свернуть рулетом и запечь."),
    ("🍷 Глинтвейн по-молдавски", "Красное вино подогреть с корицей, гвоздикой, апельсиновой цедрой и мёдом. Не кипятить!"),
    ("🫕 Фасоле ку чиолан", "Фасоль замочить на ночь, варить с копчёной рулькой, добавить лук, морковь и томатную пасту."),
]

DAILY_QUESTIONS = [
    ("Какая столица Австралии?", ["Сидней", "Мельбурн", "Канберра", "Брисбен"], "Канберра"),
    ("Сколько планет в Солнечной системе?", ["7", "8", "9", "10"], "8"),
    ("Кто написал 'Войну и мир'?", ["Достоевский", "Чехов", "Толстой", "Пушкин"], "Толстой"),
    ("Какая самая длинная река в мире?", ["Амазонка", "Нил", "Янцзы", "Миссисипи"], "Нил"),
    ("В каком году высадились на Луну?", ["1967", "1968", "1969", "1970"], "1969"),
    ("Какая самая высокая гора?", ["К2", "Эверест", "Килиманджаро", "Монблан"], "Эверест"),
    ("Столица Молдовы?", ["Бельцы", "Тирасполь", "Кишинёв", "Единцы"], "Кишинёв"),
    ("Сколько континентов на Земле?", ["5", "6", "7", "8"], "7"),
    ("Какой язык самый распространённый в мире?", ["Английский", "Китайский", "Испанский", "Хинди"], "Китайский"),
    ("Кто написал 'Гамлета'?", ["Байрон", "Шекспир", "Диккенс", "Твен"], "Шекспир"),
    ("Какой металл самый лёгкий?", ["Железо", "Алюминий", "Литий", "Титан"], "Литий"),
    ("В каком году началась Вторая мировая война?", ["1937", "1938", "1939", "1940"], "1939"),
    ("Столица Франции?", ["Лион", "Марсель", "Париж", "Бордо"], "Париж"),
    ("Сколько букв в русском алфавите?", ["30", "32", "33", "35"], "33"),
    ("Какая самая большая страна в мире?", ["Китай", "США", "Канада", "Россия"], "Россия"),
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
        [KeyboardButton(text="🌤 Погода"), KeyboardButton(text="💱 Курс валют")],
        [KeyboardButton(text="⛽ Топливо"), KeyboardButton(text="❓ Вопрос дня")],
        [KeyboardButton(text="🏙 Сменить город"), KeyboardButton(text="⏰ Сменить время")],
        [KeyboardButton(text="⏰ Напоминание")],
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
    result = f"📅 {day_name}, {date_str} | Неделя #{week_num} | День #{day_of_year}"
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

def get_war_counter():
    start = date(2022, 2, 24)
    days = (date.today() - start).days
    return f"⚔️ День войны в Украине: #{days}"

def get_english_phrase():
    today = date.today()
    idx = today.timetuple().tm_yday % len(ENGLISH_PHRASES)
    phrase, translation = ENGLISH_PHRASES[idx]
    return f"🇬🇧 *Фраза дня:*\n_{phrase}_\n🔤 {translation}"

def get_quote():
    today = date.today()
    idx = today.timetuple().tm_yday % len(QUOTES)
    author, quote = QUOTES[idx]
    return f"💬 *Цитата дня:*\n_{quote}_\n— {author}"

def get_joke():
    today = date.today()
    idx = today.timetuple().tm_yday % len(JOKES)
    return f"😄 *Анекдот дня:*\n{JOKES[idx]}"

def get_recipe():
    today = date.today()
    idx = today.timetuple().tm_yday % len(RECIPES)
    name, recipe = RECIPES[idx]
    return f"🍽 *Рецепт дня — {name}:*\n{recipe}"

def get_fact():
    today = date.today()
    idx = today.timetuple().tm_yday % len(FACTS)
    return f"💡 {FACTS[idx]}"

def get_daily_question():
    today = date.today()
    idx = today.timetuple().tm_yday % len(DAILY_QUESTIONS)
    question, options, answer = DAILY_QUESTIONS[idx]
    opts = "\n".join([f"{i+1}. {o}" for i, o in enumerate(options)])
    return f"❓ *Вопрос дня:*\n{question}\n\n{opts}\n\n||Ответ: {answer}||"

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
        wind = r['wind']['speed']
        return (
            f"🌤 *Погода в {city}:*\n"
            f"🌡 {temp}°C (ощущается {feels}°C)\n"
            f"☁️ {desc}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind} м/с"
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
        result = "📅 *Прогноз на 3 дня:*\n"
        for item in r['list']:
            day = item['dt_txt'][:10]
            if day not in seen and day != str(date.today()):
                seen.add(day)
                d = datetime.strptime(day, "%Y-%m-%d")
                day_name = DAYS_RU[d.weekday()]
                temp = item['main']['temp']
                desc = item['weather'][0]['description']
                result += f"• {day_name} {d.strftime('%d.%m')}: {temp}°C, {desc}\n"
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
        return (
            f"₿ *Крипто курс (USD):*\n"
            f"🟡 Bitcoin: ${btc:,.0f}\n"
            f"🔷 Ethereum: ${eth:,.0f}"
        )
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
            f"💱 *Курс валют (покупка / продажа MDL):*\n"
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
        result = "⛽ *Цены на топливо (MDL/л):*\n"
        result += f"🟡 Бензин А-95: {benzin[0].replace(',', '.')}\n" if benzin else "🟡 Бензин А-95: —\n"
        result += f"🔵 Дизель: {dizel[0].replace(',', '.')}" if dizel else "🔵 Дизель: —"
        return result
    except:
        return "⛽ Цены на топливо: данные недоступны"

def get_moldova_news():
    try:
        r = requests.get(
            "https://noi.md/ru/",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        text = r.text
        headlines = re.findall(r'<h\d[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', text)
        if not headlines:
            headlines = re.findall(r'<a[^>]*class="[^"]*title[^"]*"[^>]*>([^<]{20,100})</a>', text)
        if headlines:
            result = "📰 *Новости Молдовы:*\n"
            for h in headlines[:4]:
                result += f"• {h.strip()}\n"
            return result.strip()
        return "📰 Новости: данные недоступны"
    except:
        return "📰 Новости: данные недоступны"

async def send_evening_report(uid):
    city = user_settings.get(uid, {}).get("city", "Edinet")
    text = (
        f"🌙 *Вечерняя сводка — {city}*\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_fuel()}\n\n"
        f"{get_bitcoin()}\n\n"
        f"Хорошего вечера! 😊"
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
    text = (
        f"{get_day_info()}{ukraine_event}\n"
        f"{get_war_counter()}\n\n"
        f"🌅 Здравствуйте! Ситуация в городе {city}:\n\n"
        f"{get_weather(city)}\n\n"
        f"{get_forecast(city)}\n\n"
        f"{get_currency()}\n\n"
        f"{get_bitcoin()}\n\n"
        f"{get_fuel()}\n\n"
        f"{get_moldova_news()}\n\n"
        f"{get_fact()}\n\n"
        f"{get_english_phrase()}\n\n"
        f"{get_quote()}\n\n"
        f"{get_joke()}\n\n"
        f"{get_recipe()}\n\n"
        f"{get_daily_question()}"
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
    evening_job_id = f"evening_{uid}"
    if scheduler.get_job(evening_job_id):
        scheduler.remove_job(evening_job_id)
    scheduler.add_job(
        send_evening_report, "cron",
        hour=20, minute=0,
        args=[uid], id=evening_job_id,
        replace_existing=True
    )

def schedule_reminder(uid, hour, minute, text):
    job_id = f"reminder_{uid}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    async def send_reminder():
        await bot.send_message(uid, f"⏰ Напоминание:\n\n{text}")
    scheduler.add_job(
        send_reminder, "cron",
        hour=hour, minute=minute,
        id=job_id, replace_existing=True
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
        "Каждый день в 7:00 — утренняя сводка.\n"
        "Каждый день в 20:00 — вечерняя сводка.\n\n"
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

@dp.message(F.text == "🌤 Погода")
async def btn_weather(m: types.Message):
    uid = m.from_user.id
    city = user_settings.get(uid, {}).get("city", "Edinet")
    text = f"{get_weather(city)}\n\n{get_forecast(city)}"
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "💱 Курс валют")
async def btn_currency(m: types.Message):
    uid = m.from_user.id
    text = f"{get_currency()}\n\n{get_bitcoin()}"
    await m.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "⛽ Топливо")
async def btn_fuel(m: types.Message):
    uid = m.from_user.id
    await m.answer(get_fuel(), parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "❓ Вопрос дня")
async def btn_question(m: types.Message):
    uid = m.from_user.id
    await m.answer(get_daily_question(), parse_mode="Markdown", reply_markup=get_main_keyboard(uid))

@dp.message(F.text == "⚙️ Настройки")
async def btn_settings(m: types.Message):
    uid = m.from_user.id
    s = user_settings.get(uid, {"city": "Edinet", "hour": 7, "minute": 0})
    await m.answer(
        f"⚙️ Текущие настройки:\n"
        f"🏙 Город: {s.get('city', 'Edinet')}\n"
        f"⏰ Утренняя сводка: {s.get('hour', 7):02d}:{s.get('minute', 0):02d}\n"
        f"🌙 Вечерняя сводка: 20:00",
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
    await m.answer("⏰ Введите время утренней сводки в формате ЧЧ:ММ (например: 07:00 или 08:30):")

@dp.message(F.text == "⏰ Напоминание")
async def btn_reminder(m: types.Message):
    uid = m.from_user.id
    if uid not in user_settings:
        user_settings[uid] = {"city": "Edinet", "hour": 7, "minute": 0, "waiting": None}
    user_settings[uid]["waiting"] = "reminder_time"
    await m.answer("⏰ Введите время напоминания в формате ЧЧ:ММ (например: 09:00):")

@dp.message(F.text == "👥 Пользователи")
async def btn_users(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    count = len(user_settings)
    await m.answer(f"👥 Всего пользователей: {count}", reply_markup=get_main_keyboard(m.from_user.id))

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
                    f"✅ Время изменено на: {hour:02d}:{minute:02d}",
                    reply_markup=get_main_keyboard(uid)
                )
            else:
                await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")
        except:
            await m.answer("❌ Неверный формат! Введите как 07:00 или 08:30")

    elif waiting == "reminder_time":
        try:
            parts = m.text.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                user_settings[uid]["reminder_hour"] = hour
                user_settings[uid]["reminder_minute"] = minute
                user_settings[uid]["waiting"] = "reminder_text"
                await m.answer(f"✅ Время {hour:02d}:{minute:02d} установлено!\nТеперь введите текст напоминания:")
            else:
                await m.answer("❌ Неверный формат! Введите как 09:00")
        except:
            await m.answer("❌ Неверный формат! Введите как 09:00")

    elif waiting == "reminder_text":
        rh = user_settings[uid].get("reminder_hour", 9)
        rm = user_settings[uid].get("reminder_minute", 0)
        user_settings[uid]["waiting"] = None
        save_users()
        schedule_reminder(uid, rh, rm, m.text)
        await m.answer(
            f"✅ Напоминание установлено на {rh:02d}:{rm:02d}\nТекст: {m.text}",
            reply_markup=get_main_keyboard(uid)
        )

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
