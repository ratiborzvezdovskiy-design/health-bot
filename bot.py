import telebot, threading, os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request

TOKEN = '8766262206:AAEDRa3bnluKb4vQajFV7dnfMZ0_ahq_Pvs'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

questions = [
    {"text": "Вопрос 1. Как часто у вас бывают головные боли, чувство тяжести в голове или «туман» сознания?", "options": ["✅ Крайне редко (3)", "🟡 Пару раз в месяц (2)", "❌ Каждую неделю или чаще (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 2. Как часто вы испытываете боль, скованность или дискомфорт в коленях, локтях или запястьях?", "options": ["✅ Практически никогда (3)", "🟡 Иногда бывает дискомфорт (2)", "❌ Часто беспокоят боли (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 3. Как часто у вас бывает вздутие, метеоризм или чувство тяжести после еды?", "options": ["✅ Редко или никогда (3)", "🟡 Время от времени (2)", "❌ Практически постоянно (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 4. Часто ли вы чувствуете тяжесть в правом подреберье, горечь во рту?", "options": ["✅ Нет, всё отлично (3)", "🟡 Иногда замечаю (2)", "❌ Да, часто беспокоит (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 5. Как часто у вас возникают отеки (мешки под глазами, отечные ноги) или проблемы с мочеиспусканием?", "options": ["✅ Никогда (3)", "🟡 Редко, после соленого (2)", "❌ Часто беспокоит (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 6. Как вы справляетесь со стрессом и тревожными мыслями в течение дня?", "options": ["✅ Легко, я спокоен (3)", "🟡 Иногда напрягаюсь (2)", "❌ Постоянно в тревоге (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 7. Чувствуете ли вы скованность, напряжение или хронические зажимы в области шеи, спины или плеч?", "options": ["✅ Нет, тело гибкое и лёгкое (3)", "🟡 Бывают зажимы (2)", "❌ Постоянные боли и скованность (1)"], "scores": [3, 2, 1]},
    {"text": "Вопрос 8. Просыпаясь утром, вы чувствуете себя полностью отдохнувшим?", "options": ["✅ Да, всегда бодр (3)", "🟡 Часто, но бывают сбои (2)", "❌ Нет, встаю разбитым (1)"], "scores": [3, 2, 1]}
]
user_sessions = {}

@bot.message_handler(commands=['start'])
def start_quiz(message):
    chat_id = message.chat.id
    if chat_id in user_sessions and 'timer' in user_sessions[chat_id]:
        user_sessions[chat_id]['timer'].cancel()
    user_sessions[chat_id] = {'step': 0, 'total_score': 0}
    send_question(chat_id)

def send_question(chat_id):
    q_data = questions[user_sessions[chat_id]['step']]
    markup = InlineKeyboardMarkup()
    for idx, txt in enumerate(q_data['options']):
        markup.add(InlineKeyboardButton(txt, callback_data=f"q{user_sessions[chat_id]['step']}_{idx}"))
    bot.send_message(chat_id, f"📋 *Этап {user_sessions[chat_id]['step']+1} из {len(questions)}*\n\n{q_data['text']}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    chat_id = call.message.chat.id
    data = call.data.split('_')
    q_idx, opt_idx = int(data[0][1:]), int(data[1])
    user_sessions[chat_id]['total_score'] += questions[q_idx]['scores'][opt_idx]
    user_sessions[chat_id]['step'] += 1
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    if user_sessions[chat_id]['step'] < len(questions):
        send_question(chat_id)
    else:
        give_result(chat_id, user_sessions[chat_id]['total_score'])

def give_result(chat_id, score):
    book_link = "https://app.lava.top/products/a6f5fdec-4317-4181-8e32-fb9e8850d59d"
    msg = f"📊 **Ваш результат:** {score} из 24 баллов.\n\n🔬 Краткий анализ организма:\n"
    if score >= 21: msg += "Ваш организм работает слаженно...\n\n🥗 ...\n\nЕсли вы хотите умножить свой ресурс — попробуйте мои методы в книге «Рецепты наставника Чень».\n\n👉 [Перейти к книге]({book_link})"
    elif score >= 16: msg += "В целом нормально, но есть зоны напряжения...\n\n🥗 ...\n\nВы уже чувствуете дисбаланс — попробуйте мои методы в книге «Рецепты наставника Чень».\n\n👉 [Перейти к книге]({book_link})"
    elif score >= 10: msg += "Организм с перегрузкой. Дисбаланс печени, нервной системы...\n\n🥗 ...\n\nВам больше нельзя затягивать — книга даст пошаговую стратегию.\n\n👉 [Перейти к книге]({book_link})"
    else: msg += "Тело подаёт сигналы SOS. Высокий стресс, хронические боли...\n\nСостояние требует немедленных действий. Книга — ваш спасательный круг.\n\n👉 [Перейти к книге]({book_link})"
    bot.send_message(chat_id, msg, parse_mode='Markdown', disable_web_page_preview=True)
    timer = threading.Timer(3600.0, send_book_reminder, args=[chat_id])
    timer.start()
    user_sessions[chat_id]['timer'] = timer

def send_book_reminder(chat_id):
    bot.send_message(chat_id, "⏰ Напоминание: книга «Рецепты наставника Чень» уже ждёт вас! В ней 9 глав, ритуалы, акупрессура. Спеццена 300₽.\n\n👉 [Забрать программу](https://app.lava.top/products/a6f5fdec-4317-4181-8e32-fb9e8850d59d)", parse_mode='Markdown')
    if chat_id in user_sessions: del user_sessions[chat_id]

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook("https://health-bot-4ivh.onrender.com/")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
