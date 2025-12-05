from system_data import BOT_TOKEN

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, User
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    filters, MessageHandler
import db_tools
from filters import build_gen_keyboard, build_inst_keyboard, build_inst_type_keyboard
from filters import (filter_city, filter_age, filter_age_input, filter_city_input,
                     filter_menu, filter_entry, filter_menu_handler, menu, filter_entr, push_users)
from APIwork.get_event import get_info_event
from database.user import User
import LAST_PINNED

name, age, city, genre, instruments, exp, descrip, photo = range(8)
IS_FORM_CREATE = False

LAST_PINNED_DCT = LAST_PINNED.LAST_PINNED_DCT


async def start(update, context):
    chat_id = update.effective_chat.id

    if chat_id in LAST_PINNED_DCT:
        try:
            await context.bot.unpin_chat_message(
                chat_id=chat_id,
                message_id=LAST_PINNED_DCT[chat_id]
            )
        except Exception:
            pass

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Меню", callback_data="menu")]
    ])

    msg = await update.message.reply_text(
        "Вызвать меню:",
        reply_markup=keyboard
    )
    await context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)

    LAST_PINNED_DCT[chat_id] = msg.message_id
    with open("LAST_PINNED.py", mode='w') as f:
        f.write("LAST_PINNED_DCT = {}\n")
        f.write(f"LAST_PINNED_DCT[{chat_id}] = {msg.message_id}")


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.text
    await update.message.reply_text('Введите ваш возраст:')
    context.user_data['user'].name = user_name
    return age


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_age = update.message.text
    try:
        user_age = int(user_age)
    except Exception:
        await update.message.reply_text('Ошибка введите свой возраст ещё раз:')
        return age

    await update.message.reply_text('Введите название города, в котором вы проживаете:')
    context.user_data['user'].age = user_age
    return city


async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_city = update.message.text.capitalize()
    context.user_data['user'].city = user_city
    await update.message.reply_text("Выберите жанры, в которых вы играете", reply_markup=build_gen_keyboard(set()))
    return genre


async def get_descrip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_descrip = update.message.text
    context.user_data['user'].description = user_descrip
    await update.message.reply_text("Прикрепите фотографию, которую будут видеть другие пользователи в вашей анкете")
    return photo


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IS_FORM_CREATE
    user1 = update.effective_user.username
    # защита от ситуации, если пользователь прислал не фото
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте фотографию")
        return photo
    file_id = update.message.photo[-1].file_id
    telegram_file = await context.bot.get_file(file_id)
    await telegram_file.download_to_drive(f'images/{user1}.jpg')
    context.user_data['user'].photo = f'images/{user1}.jpg'
    await update.message.reply_text("Фото успешно сохранено! Введите /menu, чтобы продолжить")
    db_tools.save_user(context.user_data['user'])
    IS_FORM_CREATE = False
    return ConversationHandler.END


async def show_next_liked_anket(chat_id, context: ContextTypes.DEFAULT_TYPE, tg_id):
    ankets = context.user_data.get("liked_ankets", [])

    if not ankets:
        await context.bot.send_message(chat_id, "Анкеты закончились 🙃")
        return ConversationHandler.END

    cur_user = db_tools.get_user(tg_id)

    # берём первую
    user = ankets.pop(0)
    if int(user.telegram_id) == int(tg_id) or str(user.id) in cur_user.favorite_users:
        user = ankets.pop(0)
    context.user_data["current_anket"] = user
    context.user_data["liked_ankets"] = ankets

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


async def show_next_event(chat_id, context, txt, photo):
    keyboard = []
    if len(context.user_data["showed_events"]) == 0:
        keyboard.append([InlineKeyboardButton("➡️", callback_data='next_ev')])
    else:
        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data='previous_ev'),
            InlineKeyboardButton("➡️", callback_data='next_ev')
        ])

    # Если это первое событие → отправляем новое сообщение
    if "event_message_id" not in context.user_data:
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=txt,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["event_message_id"] = msg.message_id
        context.user_data["showed_events"].append((txt, photo))
        return

    # Если сообщение уже есть → редактируем
    await context.bot.edit_message_media(
        chat_id=chat_id,
        message_id=context.user_data["event_message_id"],
        media=InputMediaPhoto(photo, caption=txt),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data["showed_events"].append((txt, photo))



async def create_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IS_FORM_CREATE
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    context.user_data["selected_genres"] = set()
    context.user_data["selected_insts"] = set()
    user = User()
    ef_user = update.effective_user
    tg_id = ef_user.id
    if db_tools.check_user_in_db(tg_id):
        db_tools.delete_user(tg_id)
    user.telegram_id = tg_id
    user.telegram_name = ef_user.username
    context.user_data['user'] = user
    IS_FORM_CREATE = True
    await context.bot.send_message(chat_id=chat_id, text='Отлично! Введите своё имя:')
    return name


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IS_FORM_CREATE
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    tg_id = update.effective_user.id
    selected_gen: set = context.user_data.get("selected_genres", set())
    selected_inst: set = context.user_data.get('selected_insts', set())
    con = lambda x, y: (';' + x + ';') in y or (x + ';') in y or (';' + x) in y or x == y

    if query.data == 'recreate':
        await context.bot.send_message(chat_id=chat_id,
                                       text='Ваша старая анкета будет полностью удалена,'
                                                             ' вы уверены, что хотите продолжить?',
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Да', callback_data="create"),
                                                                           InlineKeyboardButton('Нет', callback_data="no")]]))
    elif query.data == 'no':
        await context.bot.send_message(chat_id=chat_id, text='Введите /menu')

    elif query.data == 'events' and not IS_FORM_CREATE:
        context.user_data["showed_events"] = []
        photo, txt = '', ''
        while not(photo and txt):
            try:
                photo, txt = get_info_event()
            except Exception:
                pass
        await show_next_event(chat_id, context, txt, photo)

    elif query.data == "next_ev":
        photo, txt = '', ''
        while not (photo and txt):
            try:
                photo, txt = get_info_event()
            except Exception:
                pass
        await show_next_event(chat_id, context, txt, photo)

    elif query.data == "previous_ev":
        txt, photo = context.user_data["showed_events"][-1]
        context.user_data["showed_events"] = context.user_data["showed_events"][:-1]
        await show_next_event(chat_id, context, txt, photo)

    elif query.data == 'liked' and not IS_FORM_CREATE:
        user = db_tools.get_user(tg_id)
        context.user_data["liked_ankets"] = db_tools.get_liked_users(user.id)
        await show_next_liked_anket(chat_id, context, tg_id)

    elif query.data == 'like':
        cur_anket = context.user_data.get('current_anket')
        other_user = db_tools.get_user(cur_anket.telegram_id)
        user = db_tools.get_user(tg_id)
        if con(str(other_user.id), user.favorite_users):
            await context.bot.send_message("Вы уже лайкнули эту анкету", chat_id=chat_id)
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

    elif query.data == 'skip':
        await show_next_liked_anket(chat_id, context, tg_id=tg_id)


    elif query.data == "back_to_menu":
        await menu(update, context)
        return ConversationHandler.END

    elif query.data == 'my_anketa' and not IS_FORM_CREATE:
        tg_id = update.effective_user.id
        if db_tools.check_user_in_db(tg_id):
            txt, photo = db_tools.build_anket(tg_id)
            await context.bot.send_photo(chat_id=chat_id, caption=txt, photo=open(photo, 'rb'))
        else:
            await context.bot.send_message(chat_id=chat_id, text="Для начала создайте анкету")
    elif query.data == 'info' and not IS_FORM_CREATE:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                'Разработкой, реализацией, пиаром, финансированием, внешним видом и успехом '
                'этого проекта занималась @uiopccv'
            )
        )

    elif query.data.startswith('genre'):
        gen = query.data.split(':', 1)[1]
        if gen in selected_gen:
            selected_gen.remove(gen)
        else:
            selected_gen.add(gen)
        context.user_data['selected_genres'] = selected_gen
        await query.edit_message_reply_markup(reply_markup=build_gen_keyboard(selected_gen))
    elif query.data == 'done_gen':
        user = context.user_data['user']
        temp = context.user_data.get('selected_genres', '')
        res = ''
        if temp:
            for gen in temp:
                res += str(db_tools.get_genre_id(gen))
                res += ';'
            res = res[:-1]
        user.gens = res
        context.user_data['user'] = user

        await query.edit_message_text(
            text="Жанры сохранены ✅\nТеперь укажите, на каких инструментах вы играете:",
            reply_markup=build_inst_type_keyboard()
        )
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
        user = context.user_data['user']
        temp = context.user_data.get('selected_insts', '')
        res = ''
        if temp:
            for inst in temp:
                res += str(db_tools.get_inst_id(inst))
                res += ';'
            res = res[:-1]
        user.inst = res
        context.user_data['user'] = user
        keyboard = [[InlineKeyboardButton('Новичёк', callback_data='exp:0'),
                     InlineKeyboardButton('Любитель', callback_data='exp:1'),
                     InlineKeyboardButton('Профессионал', callback_data='exp:2')]]
        await context.bot.send_message(chat_id=chat_id, text="Какой у вас опыт в музыке?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('exp'):
        context.user_data['user'].exp = int(query.data.split(':')[1])
        await context.bot.send_message(chat_id=chat_id, text='Придумайте своё описание? Что любите? Что нужно знать о вас? и т.д.')
        return descrip

    elif query.data == "menu":
        await menu(update, context)



# Основной блок запуска
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    form = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_button, pattern="^create$")],
        states={
            name: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            age: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            genre: [CallbackQueryHandler(button_handler)],
            instruments: [CallbackQueryHandler(button_handler)],
            exp: [CallbackQueryHandler(button_handler)],
            city: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            descrip: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_descrip)],
            photo: [MessageHandler(filters.PHOTO & ~filters.COMMAND, get_photo)],
        },
        fallbacks=[],
        per_message=False
    )

    filter_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(filter_entry, pattern="^form$")],
        states={
            filter_menu: [
                CallbackQueryHandler(filter_menu_handler)
            ],
            filter_city: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_city_input),
                CallbackQueryHandler(filter_menu_handler)
            ],
            filter_age: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_age_input),
                CallbackQueryHandler(filter_menu_handler)
            ],
            filter_entr: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_entry),
                CallbackQueryHandler(filter_menu_handler)],
        },
        fallbacks=[],
        per_message=False
    )
    app.add_handler(form)
    app.add_handler(filter_conv)
    # Меню кнопки
    app.add_handler(
        CallbackQueryHandler(button_handler, pattern="^(create|recreate|form|previous_ev|next_ev|events|liked|my_anketa|info|no|menu|like|skip|back_to_menu)$"))

    # Жанры
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(genre:.*|done_gen)$"))

    # Инструменты
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(it:.*|in:.*|done_inst|done_inst_type)$"))

    # Опыт
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^exp:.*$"))
    app.add_handler(CallbackQueryHandler(filter_menu_handler, pattern="^(filter_city|filter_age|filter_gen|filter_inst|filter_done|filter_entr|match_like|menu_handler)$"))

    app.run_polling()
