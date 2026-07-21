import telebot
import os
import sqlite3
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, redirect

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ====================
# БАЗОВЫЕ ССЫЛКИ
# ====================
BASE_URL = "https://health-bot-production-a524.up.railway.app"
LAVA_LINK = "https://nastavnikchen.lovable.app/"

# ====================
# ЛОГИРОВАНИЕ / СТАТИСТИКА (SQLite)
# ====================
# Путь к базе теперь указывает на примонтированный Railway Volume (/data),
# который не стирается при редеплоях. Можно переопределить через переменную
# окружения DB_PATH, если понадобится.
DB_PATH = os.environ.get('DB_PATH', '/data/bot_stats.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            event_type TEXT,
            event_value TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_event(chat_id, event_type, event_value=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            'INSERT INTO events (chat_id, event_type, event_value) VALUES (?, ?, ?)',
            (chat_id, event_type, str(event_value) if event_value is not None else None)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[log_event error] {e}")

init_db()

# ====================
# 8 ВОПРОСОВ
# ====================
questions = [
    {"text": "Вопрос 1. Как часто у вас бывают головные боли, чувство тяжести в голове или «туман» сознания?",
     "options": ["✅ Не замечаю этого в обычной жизни", "🟡 Бывает после нагрузки или к вечеру", "❌ Возвращается регулярно и уже мешает"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 2. Как часто вы испытываете боль, скованность или дискомфорт в коленях, локтях или запястьях?",
     "options": ["✅ Не замечаю дискомфорта в суставах", "🟡 Иногда чувствую после физической нагрузки", "❌ Регулярно мешает, особенно по утрам"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 3. Как часто у вас бывает вздутие, метеоризм или чувство тяжести после еды?",
     "options": ["✅ Пищеварение работает стабильно", "🟡 Бывает тяжесть после плотной еды", "❌ Почти после каждого приёма пищи"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 4. Часто ли вы чувствуете тяжесть в правом подреберье, горечь во рту?",
     "options": ["✅ Не замечаю такого за собой", "🟡 Иногда чувствую после жирной пищи", "❌ Регулярно ощущаю тяжесть и горечь"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 5. Как часто у вас возникают отеки (мешки под глазами, отечные ноги) или проблемы с мочеиспусканием?",
     "options": ["✅ Не сталкиваюсь с этим", "🟡 Бывает после солёного или к вечеру", "❌ Отёки появляются регулярно"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 6. Как вы справляетесь со стрессом и тревожными мыслями в течение дня?",
     "options": ["✅ Спокойно переключаюсь и отпускаю мысли", "🟡 Иногда накручиваю себя, но справляюсь", "❌ Тревога почти не отпускает"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 7. Чувствуете ли вы скованность, напряжение или хронические зажимы в области шеи, спины или плеч?",
     "options": ["✅ Тело лёгкое, зажимов не чувствую", "🟡 Иногда напрягаются шея и плечи", "❌ Постоянно чувствую скованность"],
     "scores": [3, 2, 1]},
    {"text": "Вопрос 8. Просыпаясь утром, вы чувствуете себя полностью отдохнувшим?",
     "options": ["✅ Просыпаюсь бодрым и отдохнувшим", "🟡 По-разному: бывает бодро, бывает не очень", "❌ Почти всегда встаю уставшим"],
     "scores": [3, 2, 1]}
]

user_sessions = {}

# ====================
# ССЫЛКИ НА ДОБАВКИ
# ====================
supplement_links = {
    "Омега-3": "https://market.yandex.ru/cc/A4Ysoe",
    "Коллаген": "https://market.yandex.ru/cc/9cupUG",
    "Пробиотики": "https://market.yandex.ru/cc/A4VmgL",
    "Витамины группы B": "https://market.yandex.ru/cc/A4Wjg6",
    "Кордицепс": "https://market.yandex.ru/cc/A4WQg2",
    "Пластырь для суставов": "https://market.yandex.ru/cc/A4WdRt",
    "Гриб Рейши": "https://market.yandex.ru/cc/A4XyPC",
    "Кальций D3": "https://market.yandex.ru/cc/A4YVq3",
    "Витамин C": "https://market.yandex.ru/cc/A4Yv29",
    "Витамин D": "https://market.yandex.ru/cc/A4Yyqc",
    "Магний хелат": "https://market.yandex.ru/cc/A4Z8Ky",
}

# ====================
# ПРИВЕТСТВИЕ С КНОПКОЙ "НАЧАТЬ"
# ====================
@bot.message_handler(commands=['start'])
def start_quiz(message):
    chat_id = message.chat.id
    log_event(chat_id, 'start')
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Начать", callback_data="start_test"))

    welcome_text = (
        "🌿 **На связи Наставник Чень.**\n\n"
        "Я подготовил **8 коротких вопросов**.\n"
        "Они помогут вам увидеть, в каком состоянии сейчас находится ваш организм и есть ли в нём накопленное напряжение.\n\n"
        "После них вы поймёте, где у вас уходит энергия и как начать мягко возвращать телу спокойствие и ощущение лёгкости.\n\n"
        "Ответьте на них сейчас — это займёт около минуты."
    )

    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode='Markdown')
    user_sessions[chat_id] = {'step': -1, 'total_score': 0}

@bot.callback_query_handler(func=lambda call: call.data == "start_test")
def start_test(call):
    chat_id = call.message.chat.id
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    if chat_id in user_sessions and user_sessions[chat_id]['step'] == -1:
        user_sessions[chat_id]['step'] = 0
        send_question(chat_id)
    else:
        user_sessions[chat_id] = {'step': 0, 'total_score': 0}
        send_question(chat_id)

# ====================
# ЛОГИКА ВОПРОСОВ
# ====================
def send_question(chat_id):
    step = user_sessions[chat_id]['step']
    q_data = questions[step]
    markup = InlineKeyboardMarkup()
    for index, option_text in enumerate(q_data['options']):
        markup.add(InlineKeyboardButton(option_text, callback_data=f"q{step}_{index}"))
    bot.send_message(chat_id, f"📋 *Этап {step+1} из {len(questions)}*\n\n{q_data['text']}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('q') and '_' in call.data and call.data.split('_')[0][1:].isdigit())
def handle_answer(call):
    chat_id = call.message.chat.id
    data = call.data.split('_')
    q_idx = int(data[0][1:])
    opt_idx = int(data[1])

    user_sessions[chat_id]['total_score'] += questions[q_idx]['scores'][opt_idx]
    user_sessions[chat_id]['step'] += 1
    log_event(chat_id, 'question_answered', q_idx + 1)
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    if user_sessions[chat_id]['step'] < len(questions):
        send_question(chat_id)
    else:
        final_score = user_sessions[chat_id]['total_score']
        log_event(chat_id, 'quiz_completed', final_score)
        give_result(chat_id, final_score)

# ====================
# ШАГ 1: ВЫДАЧА РЕЗУЛЬТАТА + КНОПКА
# ====================
def give_result(chat_id, score):
    max_score = 24

    if score >= 21:
        msg = (
            f"📊 **Ваш результат:** {score} из {max_score} баллов.\n\n"
            "🎉 **Это хороший показатель.**\n"
            "По вашим ответам видно, что организм пока хорошо справляется с ежедневной нагрузкой. Скорее всего, вы редко сталкиваетесь с выраженными проблемами и достаточно быстро восстанавливаетесь.\n\n"
            "Но именно на этом этапе многие перестают обращать внимание на первые сигналы организма. А ведь любые серьёзные проблемы начинаются не за один день.\n\n"
            "Если вовремя поддерживать организм, можно сохранить лёгкость, энергию и хорошее самочувствие на долгие годы."
        )
    elif score >= 16:
        msg = (
            f"📊 **Ваш результат:** {score} из {max_score} баллов.\n\n"
            "🟡 **Организм уже начинает работать с повышенной нагрузкой.**\n"
            "По вашим ответам видно, что некоторые системы уже не успевают полностью восстанавливаться.\n\n"
            "Возможно, вы замечаете, что:\n"
            "• утром стало сложнее просыпаться;\n"
            "• периодически появляется тяжесть после еды;\n"
            "• тело стало быстрее уставать или чаще напрягаться.\n\n"
            "По отдельности такие симптомы редко вызывают тревогу. Но когда они появляются одновременно, это обычно говорит о том, что организму уже требуется поддержка.\n\n"
            "Сейчас самое подходящее время вернуть баланс, пока ситуация не стала серьёзнее."
        )
    elif score >= 10:
        msg = (
            f"📊 **Ваш результат:** {score} из {max_score} баллов.\n\n"
            "🟠 **Организм уже подаёт достаточно много сигналов.**\n"
            "По вашим ответам видно, что сразу несколько систем работают с перегрузкой.\n\n"
            "Чаще всего это проявляется так:\n"
            "• энергии становится меньше;\n"
            "• пищеварение работает нестабильно;\n"
            "• появляются боли или ощущение скованности;\n"
            "• даже после сна не всегда удаётся полностью восстановиться.\n\n"
            "Большинство людей пытаются бороться с каждым симптомом отдельно. Но чаще всего все они связаны одной причиной, поэтому проблемы продолжают возвращаться."
        )
    else:
        msg = (
            f"📊 **Ваш результат:** {score} из {max_score} баллов.\n\n"
            "🔴 **По вашим ответам организм уже долго работает на пределе своих возможностей.**\n"
            "Когда одновременно страдают сон, пищеварение, уровень энергии и общее самочувствие, организм уже не справляется с нагрузкой так, как раньше.\n\n"
            "Многие привыкают жить в таком состоянии и считают его нормой. Но постоянная усталость, напряжение и дискомфорт — это не возраст и не особенность характера, а сигналы, что телу нужна помощь.\n\n"
            "Чем раньше начать восстанавливать организм, тем легче вернуть хорошее самочувствие."
        )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📖 Узнать, что делать дальше", callback_data="show_book"))

    bot.send_message(chat_id, msg, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=markup)

# ====================
# ШАГ 2: ПОКАЗ КНИГИ (ОДНО СООБЩЕНИЕ, КНОПКА ВЕДЁТ СРАЗУ НА LAVA ЧЕРЕЗ /go/book)
# ====================
def send_book_offer(chat_id):
    book_text = (
        "📖 Если вы узнали себя в этом тесте, значит вашему организму уже нужен не очередной рывок, а спокойный и последовательный способ выйти из состояния дисбаланса.\n\n"
        "🌿 Именно для этого в книге «Рецепты наставника Чень» я собрал пошаговые протоколы, которые помогают мягко вывести организм из накопленного напряжения, вернуть ощущение молодости, внутреннего спокойствия и лёгкости.\n\n"
        "✅ Вы получите готовые протоколы для поддержки каждой системы организма.\n\n"
        "Достаточно найти главу, которая соответствует вашей проблеме, и просто следовать инструкции — всё объяснено простым языком, легко и приятно."
    )

    book_url = f"{BASE_URL}/go/book?chat_id={chat_id}"
    book_markup = InlineKeyboardMarkup()
    book_markup.add(InlineKeyboardButton("📖 Получить доступ к книге", url=book_url))

    bot.send_photo(chat_id, photo=open('book_cover.jpg', 'rb'), caption=book_text, parse_mode='Markdown', reply_markup=book_markup)

    timer = threading.Timer(3600.0, send_book_reminder, args=[chat_id])
    timer.start()
    if chat_id in user_sessions:
        user_sessions[chat_id]['timer'] = timer
        user_sessions[chat_id].setdefault('clicked_link', False)

@bot.callback_query_handler(func=lambda call: call.data == "show_book")
def show_book(call):
    chat_id = call.message.chat.id
    log_event(chat_id, 'show_book_click')
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    send_book_offer(chat_id)

# ====================
# НАПОМИНАНИЕ ЧЕРЕЗ ЧАС (КНОПКА ВЕДЁТ СРАЗУ НА LAVA ЧЕРЕЗ /go/reminder)
# ====================
def send_book_reminder(chat_id):
    clicked_link = False
    if chat_id in user_sessions:
        clicked_link = user_sessions[chat_id].get('clicked_link', False)

    reminder_url = f"{BASE_URL}/go/reminder?chat_id={chat_id}"
    markup = InlineKeyboardMarkup()

    if clicked_link:
        # Уже открывал(а) ссылку на книгу, но не купил(а) — снимаем сомнения
        reminder_caption = (
            "💭 Вы уже смотрели книгу — возможно, просто не было подходящего момента, чтобы решиться.\n\n"
            "💬 Вот что написала Валентина о своих результатах.\n"
            "✨ Это только начало."
        )
        markup.add(InlineKeyboardButton("Перейти к книге", url=reminder_url))
    else:
        # Даже не открывал(а) книгу — приглашаем посмотреть заново
        reminder_caption = (
            "👀 Вы прошли тест, но пока не посмотрели, что мы для вас подготовили.\n\n"
            "💬 Вот что написала Валентина, когда начала применять советы из книги:\n"
            "✨ Это только начало."
        )
        markup.add(InlineKeyboardButton("Посмотреть книгу", url=reminder_url))

    bot.send_photo(chat_id, photo=open('review_screenshot.jpg', 'rb'), caption=reminder_caption, reply_markup=markup)

    if chat_id in user_sessions:
        del user_sessions[chat_id]

# ====================
# WEBHOOK
# ====================
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

# ====================
# ПРЯМЫЕ ПЕРЕХОДЫ НА LAVA (С ЛОГИРОВАНИЕМ И РЕДИРЕКТОМ)
# ====================
@app.route('/go/book', methods=['GET'])
def go_book():
    chat_id = request.args.get('chat_id')
    log_event(chat_id, 'get_book_link_click')
    if chat_id and chat_id.lstrip('-').isdigit():
        chat_id_int = int(chat_id)
        if chat_id_int in user_sessions:
            user_sessions[chat_id_int]['clicked_link'] = True
    return redirect(LAVA_LINK, code=302)

@app.route('/go/reminder', methods=['GET'])
def go_reminder():
    chat_id = request.args.get('chat_id')
    log_event(chat_id, 'reminder_book_click')
    return redirect(LAVA_LINK, code=302)

if __name__ == '__main__':
    WEBHOOK_URL = f"{BASE_URL}/"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
