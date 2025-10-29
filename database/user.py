import sqlalchemy as sa
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class User(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'users'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    telegram_id = sa.Column(sa.String, nullable=False, unique=True)
    name = sa.Column(sa.String)
    age = sa.Column(sa.Integer)
    city = sa.Column(sa.String)
    inst = sa.Column(sa.String)
    gens = sa.Column(sa.String)
    exp = sa.Column(sa.String)
    description = sa.Column(sa.String)

