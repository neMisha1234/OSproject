from system_data import BOT_TOKEN

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, User
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    filters, MessageHandler
import db_tools
from database.user import User

filter_city, filter_age, filter_menu = range(8, 11)


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
        keyboard.append([InlineKeyboardButton(t1, callback_data=f"inst_type:{t1}"),
                         InlineKeyboardButton(t2, callback_data=f"inst_type:{t2}")])
    if last_type:
        keyboard.append([InlineKeyboardButton(last_type, callback_data=f"inst_type:{last_type}")])
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
                                              callback_data=f"inst_name:{i1}"),
                         InlineKeyboardButton(check(i2),
                                              callback_data=f"inst_name:{i2}")])
    if last_inst:
        keyboard.append(
            [InlineKeyboardButton(check(last_inst),
                                  callback_data=f"inst_name:{last_inst}:{inst_type}")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done_inst")])
    return InlineKeyboardMarkup(keyboard)


async def filter_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Город", callback_data='filter_city')],
        [InlineKeyboardButton("Возраст", callback_data='filter_age')],
        [InlineKeyboardButton("Жанры", callback_data='filter_gen')],
        [InlineKeyboardButton("Инструменты", callback_data='filter_inst')],
        [InlineKeyboardButton("Готово", callback_data='filter_done')]
    ]

    await query.message.reply_text(
        "Выберите параметры фильтра:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return filter_menu


async def filter_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def filter_age_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def filter_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cd = query.data

    if cd == "filter_city":
        await query.message.reply_text("Введите город:")
        return filter_city

    elif cd == "filter_age":
        await query.message.reply_text("Введите желаемый возраст:")
        return filter_age

    elif cd == "filter_gen":
        context.user_data["selected_filter_gen"] = set()
        await query.message.reply_text(
            "Выберите жанры:",
            reply_markup=build_gen_keyboard(set())
        )

    elif cd == "filter_inst":
        context.user_data["selected_filter_inst"] = set()
        await query.message.reply_text(
            "Выберите инструменты:",
            reply_markup=build_inst_type_keyboard()
        )

    elif cd == "filter_done":
        return await finish_filters(update, context)

    elif cd.startswith('genre'):
        gen = cd.split(':')[1]


async def finish_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    city = context.user_data.get("f_city")
    age = context.user_data.get("f_age")
    gens = context.user_data.get("selected_filter_gen", set())
    insts = context.user_data.get("selected_filter_inst", set())

    results = db_tools.search_users(city=city, age=age, genres=gens, insts=insts)

    if not results:
        await query.message.reply_text("Ничего не найдено.")
        return ConversationHandler.END

    # выводим найденные анкеты
    for user in results:
        txt, photo = db_tools.build_anket(user.telegram_id)
        await query.message.reply_photo(photo=open(photo, "rb"), caption=txt)

    return ConversationHandler.END
