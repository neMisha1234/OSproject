from database import db_session
from database.user import User
from database.styles import Genres
from database.instruments import Instruments

db_session.global_init("db/bot.sqlite")
db_sess = db_session.create_session()


def load_to_db(tg_id, name, age, city, inst, genres, description, exp):
    bot_user = User()
    bot_user.telegram_id = tg_id
    bot_user.name, bot_user.age = name, age
    bot_user.city = city
    res_inst = ''
    for el in inst:
        inst_num = db_sess.query(Instruments).filter(Instruments.name == el).first().id
        res_inst += str(inst_num) + ';'
    res_inst = res_inst[:-1]
    bot_user.inst = res_inst

    res_gens = ''
    for el in genres:
        genr_num = db_sess.query(Genres).filter(Genres.name == el).first().id
        res_gens += str(genr_num) + ';'
    res_gens = res_gens[:-1]
    bot_user.gens = res_gens
    bot_user.exp = exp

    db_sess.add(bot_user)
    db_sess.commit()


def delete_user(tg_id):
    user = db_sess.query(User).filter(User.telegram_id == tg_id).first()
    db_sess.delete(user)


def get_user(tg_id):
    return db_sess.query(User).filter(User.telegram_id == tg_id).first()


def get_liked_users(uid):
    lst = []
    main_user = db_sess.query(User).filter(User.id == uid).first()
    con = lambda x, y: (';' + x + ';') in y or (x + ';') in y or (';' + x) in y or x == y
    for user in db_sess.query(User).all():
        if user.favorite_users and con(str(uid), user.favorite_users) and not con(str(user.id), main_user.favorite_users):
            lst.append(user)
    return lst


def save_user(user):
    db_sess.add(user)
    db_sess.commit()

def get_genres():
    return list(map(lambda x: x.name, db_sess.query(Genres).all()))


def get_genre_id(gen):
    return db_sess.query(Genres).filter(Genres.name == gen).first().id


def get_genre_with_id(g_id):
    return db_sess.query(Genres).filter(Genres.id == g_id).first().name


def check_user_in_db(tg_id):
    lst = list(db_sess.query(User).filter(User.telegram_id == tg_id))
    if lst:
        return 1
    return 0


def delete_user(tg_id):
    user = db_sess.query(User).filter(User.telegram_id == tg_id).first()
    db_sess.delete(user)
    db_sess.commit()


def get_inst_type(name):
    return db_sess.query(Instruments).filter(Instruments.name == name).first().inst_type


def get_inst_with_id(i_id):
    return db_sess.query(Instruments).filter(Instruments.id == i_id).first().name


def get_instruments():
    dct = {}
    types = set(map(lambda x: x.inst_type, db_sess.query(Instruments).all()))
    for typ in types:
        insts = list(map(lambda x: x.name, db_sess.query(Instruments).filter(Instruments.inst_type == typ).all()))
        dct[typ] = insts
    return dct


def get_inst_id(inst):
    return db_sess.query(Instruments).filter(Instruments.name == inst).first().id


def build_anket(tg_id):
    user = db_sess.query(User).filter(User.telegram_id == tg_id).first()
    dct = {0: 'новичёк', 1: "любитель", 2: "профессионал"}
    gens = []
    if user.gens:
        for g in user.gens.split(';'):
            gens.append(get_genre_with_id(int(g)))
    insts = []
    if user.inst:
        for i in user.inst.split(';'):
            insts.append(get_inst_with_id(int(i)))
    text = (f"{user.name}, возраст: {user.age}, город: {user.city}\n"
            f"Жанры, в которых играю: {', '.join(gens)} \n"
            f"Инструменты, на которых играю: {', '.join(insts)} \n"
            f"Опыт в музыке: {dct[user.exp]} \n \n"
            f"{user.description}")
    return (text, user.photo)


def search_users(city='', age='', insts='', genres=''):
    users = db_sess.query(User).all()
    if city:
        users = list(filter(lambda x: x.city == city.capitalize(), users))
    if age:
        users = list(filter(lambda x: age[0] <= x.age <= age[1], users))
    if insts:
        for inst in insts.split(';'):
            users = list(filter(lambda x: inst in x.inst, users))
    if genres:
        for gen in genres.split(';'):
            users = list(filter(lambda x: gen in x.gens, users))
    return users