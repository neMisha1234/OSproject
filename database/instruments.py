import sqlalchemy as sa
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Instruments(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'instruments'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String)
    inst_type = sa.Column(sa.String)

