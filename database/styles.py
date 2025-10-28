from sqlalchemy import Column, Integer, String
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Genres(SqlAlchemyBase, SerializerMixin):
    __tablename__ = "genre_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

