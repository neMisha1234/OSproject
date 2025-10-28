from database.instruments import Instruments
from database.styles import Genres
from database import db_session
from database.first_data.data import instruments_data, genres_data

db_session.global_init("db/bot.sqlite")
db_sess = db_session.create_session()

for el in instruments_data:
    for elem in instruments_data[el]:
        inst = Instruments()
        inst.name = elem
        inst.inst_type = el
        db_sess.add(inst)

for el in genres_data:
    gent = Genres()
    gent.name = el

db_sess.commit()
