import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


DATABASE_URL = os.getenv("DB_URL", "sqlite:///./botcamp_medical.db")

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_all():
    Base.metadata.create_all(bind=engine)


