from system_data import BOT_TOKEN

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, User
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    filters, MessageHandler
import db_tools
from filters import build_gen_keyboard, build_inst_keyboard, build_inst_type_keyboard
from filters import (filter_city, filter_age, filter_age_input, filter_city_input,
                     filter_menu, filter_entry, filter_menu_handler, finish_filters)
from database.user import User

name, age, city, genre, instruments, exp, descrip, photo = range(8)
filter_city, filter_age, filter_gens, filter_insts, filter_menu = range(8, 13)
IS_FORM_CREATE = False


# Функции для создания анкеты
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите /menu")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Просмотр анкет", callback_data="form")],
         [InlineKeyboardButton("Мероприятия", callback_data="events")],
        [InlineKeyboardButton("Лайки", callback_data="liked")],
         [InlineKeyboardButton("Моя анкета", callback_data="my_anketa")],
         [InlineKeyboardButton("О боте", callback_data="info")]
    ]
    if db_tools.check_user_in_db(update.effective_user.id):
        keyboard.insert(0, [InlineKeyboardButton('Пересоздать анкету', callback_data='recreate')])
    else:
        keyboard.insert(0, [InlineKeyboardButton('Создать анкету', callback_data='create')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.text
    await update.message.reply_text('Введите ваш возраст:')
    context.user_data['user'].name = user_name
    return age


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_age = update.message.text
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
    await update.message.reply_text("Фото успешно сохранено!")
    db_tools.save_user(context.user_data['user'])
    IS_FORM_CREATE = False
    return ConversationHandler.END


async def create_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IS_FORM_CREATE
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    context.user_data["selected_genres"] = set()
    context.user_data["selected_insts"] = set()
    user = User()
    ef_user = update.effective_user
    user.telegram_id = ef_user.id
    user.telegram_name = ef_user.username
    context.user_data['user'] = user
    IS_FORM_CREATE = True
    await context.bot.send_message(chat_id=chat_id, text='Отлично! Введите своё имя:')
    return name


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global IS_FORM_CREATE
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id  # получаем ID чата, откуда пришёл запрос
    selected_gen: set = context.user_data.get("selected_genres", set())
    selected_inst: set = context.user_data.get('selected_insts', set())
    if query.data == 'form' and not IS_FORM_CREATE:
        keyboard = [[InlineKeyboardButton("Город", callback_data='filter:city')],
                    [InlineKeyboardButton("Возраст", callback_data='filter:age')],
                    [InlineKeyboardButton("Жанры", callback_data='filter:genre')],
                    [InlineKeyboardButton("Инструменты", callback_data='filter:insts')]]
        await context.bot.send_message(chat_id=chat_id,
                                       text="Выберите параметры анкет, которые вы хотите уточнить для поиска нужной анкеты",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'recreate':
        await context.bot.send_message(chat_id=chat_id,
                                       text='Ваша старая анкета будет полностью удалена,'
                                                             ' вы уверены, что хотите продолжить?',
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Да', callback_data="create"),
                                                                           InlineKeyboardButton('Нет', callback_data="no")]]))
    elif query.data == 'no':
        await context.bot.send_message(chat_id=chat_id, text='Введите /menu')
    elif query.data == 'events' and not IS_FORM_CREATE:
        await context.bot.send_message(chat_id=chat_id, text='Я хз как тут подключить апишку')
    elif query.data == 'liked' and not IS_FORM_CREATE:
        await context.bot.send_message(chat_id=chat_id, text='Тут будут лайкнувшие тебя люди')
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
    elif query.data.startswith('inst_type'):
        inst_type = query.data.split(':')[1]
        await query.edit_message_text(inst_type, reply_markup=build_inst_keyboard(selected_inst, inst_type))

    elif query.data.startswith('inst_name'):
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
                CallbackQueryHandler(filter_menu_handler),
            ],
            filter_age: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_age_input),
                CallbackQueryHandler(filter_menu_handler),
            ],
        },
        fallbacks=[],
        per_message=False
    )
    app.add_handler(form)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(filter_conv)
    app.run_polling()
