from sqlalchemy import Column, Integer, String
from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    neon_user_id = Column(String(255), unique=True, index=True)  # From Neon Auth
    username = Column(String(80))
