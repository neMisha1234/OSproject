from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, User
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    filters, MessageHandler
import db_tools
import random

filter_city, filter_age, filter_menu, filter_entr, match_like, menu_handler = range(8, 14)

KEYBOARD = [
    [InlineKeyboardButton("Город", callback_data='filter_city')],
    [InlineKeyboardButton("Возраст", callback_data='filter_age')],
    [InlineKeyboardButton("Жанры", callback_data='filter_gen')],
    [InlineKeyboardButton("Инструменты", callback_data='filter_inst')],
    [InlineKeyboardButton("Готово", callback_data='filter_done')]
]


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        chat_id = update.message.chat.id
    else:
        chat_id = update.callback_query.message.chat.id

    keyboard = [
        [InlineKeyboardButton("Просмотр анкет", callback_data="form")],
        [InlineKeyboardButton("Мероприятия", callback_data="events")],
        [InlineKeyboardButton("Лайки", callback_data="liked")],
        [InlineKeyboardButton("Моя анкета", callback_data="my_anketa")],
        [InlineKeyboardButton("О боте", callback_data="info")],
    ]

    if db_tools.check_user_in_db(update.effective_user.id):
        keyboard.insert(0, [InlineKeyboardButton('Пересоздать анкету', callback_data='recreate')])
    else:
        keyboard.insert(0, [InlineKeyboardButton('Создать анкету', callback_data='create')])
    context.user_data["showed_events"] = []
    await context.bot.send_message(
        chat_id=chat_id,
        text="Привет, этот бот является курсовым проектом,"
             " и сейчас находиться на стадии разработки, если ты нашел его случайно,"
             " то учти большинство его функций пока ограничено. Но буду рад, если ты создашь свою анкету - это поможет мне на защите курсовой. Выбери действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def build_gen_keyboard(selected):
    keyboard = []
    lst_gen = db_tools.get_genres()
    last_gen = None
    if len(lst_gen) % 2 == 1:
        last_gen = lst_gen[-1]
        lst_gen = lst_gen[:-1]

    check = lambda x: ("✅" if x in selected else "") + " " + x
    for i in range(1, len(lst_gen), 2):
        g1, g2 = lst_gen[i - 1], lst_gen[i]
        keyboard.append([InlineKeyboardButton(check(g1),
                                              callback_data=f"genre:{g1}"),
                         InlineKeyboardButton(check(g2),
                                              callback_data=f"genre:{g2}")])
    if last_gen:
        keyboard.append(
            [InlineKeyboardButton(check(last_gen),
                                  callback_data=f"genre:{last_gen}")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done_gen")])
    return InlineKeyboardMarkup(keyboard)


def build_inst_type_keyboard():
    keyboard = []
    lst_types = list(db_tools.get_instruments().keys())
    last_type = None
    if len(lst_types) % 2 == 1:
        last_type = lst_types[-1]
        lst_types = lst_types[:-1]
    for i in range(1, len(lst_types), 2):
        t1, t2 = lst_types[i - 1], lst_types[i]
        keyboard.append([InlineKeyboardButton(t1, callback_data=f"it:{t1}"),
                         InlineKeyboardButton(t2, callback_data=f"it:{t2}")])
    if last_type:
        keyboard.append([InlineKeyboardButton(last_type, callback_data=f"it:{last_type}")])
    keyboard.append([InlineKeyboardButton("✅ Завершить", callback_data='done_inst_type')])
    return InlineKeyboardMarkup(keyboard)


def build_inst_keyboard(selected, inst_type):
    keyboard = []
    lst_inst = db_tools.get_instruments()[inst_type]
    last_inst = None
    if len(lst_inst) % 2 == 1:
        last_inst = lst_inst[-1]
        lst_inst = lst_inst[:-1]

    check = lambda x: ("✅" if x in selected else "") + " " + x
    for i in range(1, len(lst_inst), 2):
        i1, i2 = lst_inst[i - 1], lst_inst[i]
        keyboard.append([InlineKeyboardButton(check(i1),
                                              callback_data=f"in:{i1}"),
                         InlineKeyboardButton(check(i2),
                                              callback_data=f"in:{i2}")])
    if last_inst:
        keyboard.append(
            [InlineKeyboardButton(check(last_inst),
                                  callback_data=f"in:{last_inst}")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done_inst")])
    return InlineKeyboardMarkup(keyboard)


async def filter_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    context.user_data["selected_genres"] = set()
    context.user_data["selected_insts"] = set()

    await context.bot.send_message(
        chat_id=chat_id,
        text="Выберите параметры фильтра:",
        reply_markup=InlineKeyboardMarkup(KEYBOARD)
    )

    return filter_menu


async def filter_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f_city = update.message.text
    context.user_data['f_city'] = f_city
    await update.message.reply_text("Выберите параметры фильтра:",
                                    reply_markup=InlineKeyboardMarkup(KEYBOARD))


async def filter_age_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f_age = update.message.text.split()
    try:
        f_age = sorted(list(map(int, f_age)))
    except Exception:
        await update.message.reply_text("Ошибка формата, повторите ввод:")
        return filter_age

    if not (f_age[0] == f_age[1] == 0):
        context.user_data['f_age'] = f_age
        await update.message.reply_text("Выберите параметры фильтра:",
                                        reply_markup=InlineKeyboardMarkup(KEYBOARD))


async def show_next_anket(chat_id, context, tg_id):
    ankets = context.user_data.get("ankets", [])

    if not ankets:
        await context.bot.send_message(chat_id, "Анкеты закончились 🙃")
        return ConversationHandler.END

    cur_user = db_tools.get_user(tg_id)

    # берём первую
    user = ankets.pop(0)
    if int(user.telegram_id) == int(tg_id) or (cur_user.favorite_users and str(user.id) in cur_user.favorite_users):
        user = ankets.pop(0)
    context.user_data["current_anket"] = user
    context.user_data["ankets"] = ankets

    txt, photo = db_tools.build_anket(user.telegram_id)

    keyboard = [
        [InlineKeyboardButton("❤️", callback_data="like"),
         InlineKeyboardButton("💤", callback_data="skip"),
         InlineKeyboardButton("🚩", callback_data="report")],
        [InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]
    ]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=open(photo, 'rb'),
        caption=txt,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return filter_entr  # или ваше состояние


async def push_users(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=0, other_user_id=0):
    cur_user = db_tools.get_user(user_id)
    other_user = db_tools.get_user(other_user_id)
    txt_cur, photo_cur = db_tools.build_anket(cur_user.telegram_id)
    txt_other, photo_other = db_tools.build_anket(other_user.telegram_id)
    await context.bot.send_message(chat_id=other_user.telegram_id,
                                   text=f"Ваша анкета понравилась: @{cur_user.telegram_name}")
    await context.bot.send_photo(chat_id=other_user.telegram_id, photo=open(photo_cur, 'rb'), caption=txt_cur)

    await context.bot.send_message(chat_id=cur_user.telegram_id,
                                   text=f"Ваша анкета понравилась: @{other_user.telegram_name}")
    await context.bot.send_photo(chat_id=cur_user.telegram_id, photo=open(photo_other, 'rb'), caption=txt_other)


async def filter_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_gen: set = context.user_data.get("selected_genres", set())
    selected_inst: set = context.user_data.get('selected_insts', set())
    chat_id = query.message.chat.id
    tg_id = update.effective_user.id
    con = lambda x, y: (';' + x + ';') in y or (x + ';') in y or (';' + x) in y or x == y

    cd = query.data

    if cd == "filter_city":
        await query.message.reply_text("Введите город:")
        return filter_city

    elif cd == "filter_age":
        await query.message.reply_text("Введите от какого и до какого возраста"
                                       " людей вы хотите видеть в анкетах в формате 'число1 число2'."
                                       " Например, если вы хотите видеть анкеты от 17 до 19 лет введите сообщение '17 19'. "
                                       "Если вам не важен возраст введите '0 0':")
        return filter_age

    elif cd == "filter_gen":
        await query.message.reply_text(
            "Выберите жанры:",
            reply_markup=build_gen_keyboard(set())
        )

    elif cd == "filter_inst":
        await query.message.reply_text(
            "Выберите инструменты:",
            reply_markup=build_inst_type_keyboard()
        )

    elif cd == "filter_done":
        return await finish_filters(update, context)

    elif query.data.startswith('genre'):
        gen = query.data.split(':', 1)[1]
        if gen in selected_gen:
            selected_gen.remove(gen)
        else:
            selected_gen.add(gen)
        context.user_data['selected_genres'] = selected_gen
        await query.edit_message_reply_markup(reply_markup=build_gen_keyboard(selected_gen))

    elif query.data == 'done_gen':
        temp = context.user_data.get('selected_genres', '')
        res = ''
        if temp:
            for gen in temp:
                res += str(db_tools.get_genre_id(gen))
                res += ';'
            res = res[:-1]
        context.user_data['gens'] = res
        await query.edit_message_text("Выберите параметры фильтра:",
                                      reply_markup=InlineKeyboardMarkup(KEYBOARD))

    elif query.data.startswith('it'):
        inst_type = query.data.split(':')[1]
        await query.edit_message_text(inst_type, reply_markup=build_inst_keyboard(selected_inst, inst_type))

    elif query.data.startswith('in'):
        inst_name = query.data.split(':')[1]
        inst_type = db_tools.get_inst_type(inst_name)
        if inst_name in selected_inst:
            selected_inst.remove(inst_name)
        else:
            selected_inst.add(inst_name)
        context.user_data['selected_insts'] = selected_inst
        await query.edit_message_reply_markup(reply_markup=build_inst_keyboard(selected_inst, inst_type))

    elif query.data == 'done_inst':
        await query.edit_message_text("Виды инструментов:", reply_markup=build_inst_type_keyboard())

    elif query.data == 'done_inst_type':
        temp = context.user_data.get('selected_insts', '')
        res = ''
        if temp:
            for inst in temp:
                res += str(db_tools.get_inst_id(inst))
                res += ';'
            res = res[:-1]
            context.user_data['insts'] = res
        await query.edit_message_text("Выберите параметры фильтра:",
                                      reply_markup=InlineKeyboardMarkup(KEYBOARD))

    # Логика анкеты
    elif cd == 'like':
        cur_anket = context.user_data.get('current_anket')
        other_user = db_tools.get_user(cur_anket.telegram_id)
        user = db_tools.get_user(tg_id)
        if con(str(other_user.id), user.favorite_users):
            await context.bot.send_message(text="Вы уже лайкнули эту анкету", chat_id=chat_id)
        else:
            if user.favorite_users:
                if not(con(str(other_user.id), user.favorite_users)):
                    user.favorite_users += f";{other_user.id}"
            else:
                user.favorite_users = other_user.id
            db_tools.save_user(user)
            if other_user.favorite_users:
                if con(str(user.id), other_user.favorite_users):
                    await push_users(update, context, user_id=user.telegram_id, other_user_id=other_user.telegram_id)

    elif cd == 'skip':
        await show_next_anket(chat_id, context, tg_id=tg_id)


    elif cd == "back_to_menu":
        await menu(update, context)
        return ConversationHandler.END


async def finish_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    tg_id = update.effective_user.id

    # поиск пользователей
    results = db_tools.search_users(
        city=context.user_data.get("f_city"),
        age=context.user_data.get("f_age"),
        genres=context.user_data.get("gens"),
        insts=context.user_data.get("insts")
    )

    if not results:
        await query.message.reply_text("Ничего не найдено.")
        context.user_data['f_city'] = ""
        context.user_data['f_age'] = ''
        context.user_data["gens"] = ''
        context.user_data["insts"] = ''
        return ConversationHandler.END

    # сохраняем список
    context.user_data["ankets"] = results
    return await show_next_anket(chat_id, context, tg_id=tg_id)
