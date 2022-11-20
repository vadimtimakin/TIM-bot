# -*- coding: utf-8 -*-

import os
import json
import random
import logging

from aiogram import Bot, Dispatcher, executor, types
from generate import generate_file, generate_canvas, pad, generate_pptx

from Crypto.Cipher import DES

# Set an API_TOKEN.
API_TOKEN = '5948098907:AAGNyGlR_m3afJXM070vmDlKsQzC_Y1T_c0'

# Configure the logging.
logging.basicConfig(level=logging.INFO)

# Initialize a bot and a dispatcher.
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Initialize encriptor.
key = b'abcdefgh'
des = DES.new(key, DES.MODE_ECB)

# Initialize users' data.
ud = dict()
# The list of questions.
with open('questions.json', 'r') as f: questions = json.load(f) 
# The list of questions' types (expects text / photo as an answer).
with open('questions_types.json', 'r') as f: questions_types = json.load(f)
# The list of tags of questions.
with open('tags.json', 'r') as f: tags = json.load(f)
# The list of people with access to the admin panel (managers).
with open('admins.json', 'r') as f: admins = json.load(f)
# The list of blocked users.
with open('blacklist.json', 'r') as f: blacklist = json.load(f)
# Сontacts to whom applications are sent (analysts).
with open('contacts.json', 'r') as f: contacts = json.load(f)  
# Statistics.
with open('stats.json', 'r') as f: stats = json.load(f)

# Bot's functions.

@dp.message_handler(commands=['cancel'])
async def start(message: types.Message):
    """Initializes a dialog."""
    global ud
    uid = message.from_id

    # Reset the current state.
    ud[uid] = dict()
    ud[uid]["state"] = 0
    ud[uid]["flag"] = False
    ud[uid]["answers"] = {}
    ud[uid]["image_count"] = 0

    # Create a keyboard.
    res = types.ReplyKeyboardMarkup(resize_keyboard=True)
    res.add(types.KeyboardButton(text="✅ Начать!"))
    res.add(types.KeyboardButton(text="📜 Просмотреть список вопросов"))

    # Reply to the user.
    await message.answer(text="Добро пожаловать! 👋"
                            "\n\nДанный бот создан с целью автоматизировать и "
                            "упростить процесс отправки и проверки заявок "
                            "на получение инвестиций из фонда Транспортных "
                            " Инноваций Москвы."
                            "\n\nПодробнее о нашем фонде и акселераторе можно прочитать"
                            " по ссылке: https://ftim.ru/."
                            "\n\nЧтобы оставить заявку, "
                            " необходимо ответить на следующие вопросы."
                            " Для возврата к предыдущему вопросу или пропуска "
                            "текущего вы можете пользоваться соответсвующими кнопками."
                            " Чтобы начать, нажмите кнопку ниже.", reply_markup=res)


@dp.message_handler(content_types=['photo'])
async def photo_processing(message):
    """
    Triggeres when the user sends an image and starts its proccessing.
    """
    global ud, tags
    uid = message.from_id
    
    ud[uid]["image_count"] += 1
    ud[uid]["flag"] = False

    if not os.path.exists(f'users/{uid}'):
        os.mkdir(f'users/{uid}')

    await message.photo[-1].download(f'users/{uid}/{tags[ud[uid]["state"]]}_{ud[uid]["image_count"]}.jpg')


@dp.message_handler()
async def processing(message: types.Message):
    """Determines type of user."""
    uid = message.from_id

    if uid in admins:
        await handle_admin_message(message)
    else:
        await handle_user_message(message)


@dp.callback_query_handler()
async def handle_analytic_message(callback_query: types.CallbackQuery):
    """Handles messages from an analytic."""
    global blacklist, stats
    text = callback_query.data
    uid = text.split(";")[1]
    answer = text.split(";")[0]
    if answer == "блокировать":
        blacklist.append(uid)
    else:
        if answer == "принять":
            answer = "Ваша заявка принята на рассмотрение."
            stats["принято"] += 1 
        else:
            answer = "Ваша заявка отклонена."
            stats["отклонено"] += 1
        await bot.send_message(uid, answer)


async def handle_admin_message(message: types.Message):
    """Handles messages from an admin."""
    global ud, questions, tags, contacts, admins, stats
    uid = message.from_id
    text = message.text

    res = types.ReplyKeyboardMarkup(resize_keyboard=True)
    res.add(types.KeyboardButton(text="📜 Просмотреть список текущих вопросов"))
    res.add(types.KeyboardButton(text="📝 Изменить вопрос"))
    res.add(types.KeyboardButton(text="➕ Добавить новый вопрос"))
    res.add(types.KeyboardButton(text="👤 Изменить список контактов аналитиков"))
    res.add(types.KeyboardButton(text="📊 Просмотреть статистику"))
    res.add(types.KeyboardButton(text="🚪 Покинуть админ-панель"))
        
    if text == "🚪 Покинуть админ-панель":
        await message.answer('Вы вернулись в обычный режим.')
        admins.remove(uid)
        await start(message)

    elif ud[uid]["state"] == "contacts":
        contacts = [text.split('\n')]
        ud[uid]["state"] = 0
        await message.answer(text="Роли аналитиков успешно обновлены.", reply_markup=res)

    elif text == "📜 Просмотреть список текущих вопросов":
        questions_list = '\n'.join([f'{i + 1}. {q}' for i, q in enumerate(questions)])
        # Reply to the user.
        for x in range(0, len(questions_list), 4096):
            await message.answer(text=questions_list[x:x+4096], reply_markup=res)

    elif text == "👤 Изменить список контактов аналитиков":
        await message.answer(text="Введите в столбец id пользователей, "
                                  "которым вы хотите дать роль аналитика.")
        ud[uid]["state"] = "contacts"

    elif text == "📊 Просмотреть статистику":
        await message.answer(text=f'Всего заявок {stats["принято"] + stats["отклонено"]}'
                                    f'\nПринято {stats["принято"]}'
                                    f'\nОтклонено {stats["отклонено"]}',
                     reply_markup=res)


async def handle_user_message(message: types.Message):
    """Handles messages from an average user."""
    global ud, questions, tags, contacts, admins, blacklist
    uid = message.from_id
    text = message.text

    if des.encrypt(pad(str.encode(text))) == b'\x05\x97\xfd\x8a\xa4/Sb\x03Q\x10L\x06\xee&z':  
        admins.append(uid)
        res = types.ReplyKeyboardMarkup(resize_keyboard=True)
        res.add(types.KeyboardButton(text="📜 Просмотреть список текущих вопросов"))
        res.add(types.KeyboardButton(text="📝 Изменить вопрос"))
        res.add(types.KeyboardButton(text="➕ Добавить новый вопрос"))
        res.add(types.KeyboardButton(text="👤 Изменить список контактов аналитиков"))
        res.add(types.KeyboardButton(text="📊 Просмотреть статистику"))
        res.add(types.KeyboardButton(text="🚪 Покинуть админ-панель"))

        await message.answer('Добро пожаловать в админ-панель! Выберите опцию.',
                            reply_markup=res)
        return

    if text == "📜 Просмотреть список вопросов":
        res = types.ReplyKeyboardMarkup(resize_keyboard=True)
        res.add(types.KeyboardButton(text="✅ Начать!"))
        questions_list = '\n'.join([f'{i + 1}. {q}' for i, q in enumerate(questions)])
        # Reply to the user.
        for x in range(0, len(questions_list), 4096):
            await message.answer(text=questions_list[x:x+4096], reply_markup=res)
        return

    # Initialize a dialog.
    if (uid not in ud) or (text == "🔄 Заполнить еще одну анкету"):
        await start(message)
        return
    
    # Stop collecting images and go the next question.
    elif (text == "✅ Сохранить изображения" and not ud[uid]["flag"]):
        ud[uid]["image_count"] = 0
        ud[uid]["state"] += 1
        ud[uid]["flag"] = True

    elif text == "🔙 Вернуться назад":
        ud[uid]["state"] -= 2

    # Finish the dialog and send the respond to the analytics.
    if ud[uid]["flag"]:
        ud[uid]["state"] += 1

    if ud[uid]["state"] >= len(questions):
        
        if text == "⏩ Пропустить вопрос":
            ud[uid]["answers"][tags[ud[uid]["state"] - 1]] = "Ответ отсутствует"
        else:
            ud[uid]["answers"][tags[ud[uid]["state"] - 1]] = text

        if uid in blacklist: return

        path = f'users/{uid}/'
        if not os.path.exists(path):
            os.mkdir(path) 

        json_answers = {t: a for t, a in ud[uid]["answers"].items()}
        json_answers["path"] = path

        generate_canvas(json_answers)
        generate_file(json_answers)
        generate_pptx(json_answers)

        contact = random.choice(contacts)
        
        await bot.send_message(contact, "Поступила новая заявка!")

        await bot.send_document(contact, open(f'{path}slides.pptx', 'rb'))
        await bot.send_document(contact, open(f'{path}CANVASresult.docx', 'rb'))
        await bot.send_document(contact, open(f'{path}MEMOresult.docx', 'rb'))

        res = types.InlineKeyboardMarkup(resize_keyboard=True)
        res.add(types.InlineKeyboardButton(text="✅ Принять заявку",
                                callback_data=f"принять;{uid}"))
        res.add(types.InlineKeyboardButton(text="❌ Отклонить заявку", 
                                callback_data=f"отклонить;{uid}"))
        res.add(types.InlineKeyboardButton(text="⛔ Заблокировать пользователя", 
                                callback_data=f"блокировать;{uid}"))

        await bot.send_message(chat_id=contact, text="Принять заявку?", reply_markup=res)
    
        res = types.ReplyKeyboardMarkup(resize_keyboard=True)
        res.add(types.KeyboardButton(text="🔄 Заполнить еще одну анкету"))

        await message.answer(text="Анкета отправлена!"
                                    " После того, как аналитик  ознакомится с твоей анкетой,"
                                    " вам придет уведомление."
                                    , reply_markup=res)
        return
    
    # Handling question type.
    if questions_types[ud[uid]["state"]] == "text":
        res = types.ReplyKeyboardMarkup(resize_keyboard=True)
        res.add(types.KeyboardButton(text="🔙 Вернуться назад"))
        res.add(types.KeyboardButton(text="⏩ Пропустить вопрос"))

        await message.answer(text=questions[ud[uid]["state"]], reply_markup=res) 
    else:
        res = types.ReplyKeyboardMarkup(resize_keyboard=True)
        res.add(types.KeyboardButton(text="✅ Сохранить изображения"))
        res.add(types.KeyboardButton(text="🔙 Вернуться назад"))
        res.add(types.KeyboardButton(text="⏩ Пропустить вопрос"))

        await message.answer(text=questions[ud[uid]["state"]], reply_markup=res) 

    if ud[uid]["flag"]:
        if text == "⏩ Пропустить вопрос":
            ud[uid]["answers"][tags[ud[uid]["state"] - 1]] = "Ответ отсутствует"
        else:
            ud[uid]["answers"][tags[ud[uid]["state"] - 1]] = text

    ud[uid]["flag"] = True

    
if __name__ == '__main__':
    # Launch the bot.
    executor.start_polling(dp, skip_updates=True)  
