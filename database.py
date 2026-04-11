import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Pega a URL do banco do Railway (ou usa sqlite para teste local)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./estoque.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência para as rotas usarem o banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
