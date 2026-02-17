from sqlalchemy import UUID, Column
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    id = Column(UUID, primary_key=True)
    pass
