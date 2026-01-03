from sqlalchemy import create_engine, String, Float, Column, Boolean, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from contextlib import contextmanager
from lib.initial import CONFIG_DIR
from lib.logger import logger
import secrets
import bcrypt
import os

ENGINE = create_engine(f'sqlite:///{os.path.join(CONFIG_DIR, "aurbit.db")}', echo=False, future=True)

SessionLocal = scoped_session(sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True, expire_on_commit=False))

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    displayName = Column(String, nullable=False)
    access = Column(Integer, default=0) # 0: superuser, # 1: normal user... ( to be expanded later )
    initialized = Column(Boolean, default=False)
    _password = Column("password", String, nullable=True)

    @hybrid_property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, raw_password):
        if raw_password is None:
            self._password = None
        else:
            hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
            self._password = hashed.decode("utf-8")

    def verify_password(self, raw_password):
        if not self._password or raw_password is None:
            return False
        return bcrypt.checkpw(raw_password.encode("utf-8"), self._password.encode("utf-8"))

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User", backref="sessions")

class RateLimit(Base):
    __tablename__ = "ratelimit"
    id = Column(Integer, primary_key=True, index=True)
    ip_addr = Column(String, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    seconds = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    url = Column(String, nullable=False)

class Locations(Base):
    __tablename__ = "locations"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now(), primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Integer, default=0) # defaults to m/s


def init_db():
    Base.metadata.create_all(bind=ENGINE)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
        SessionLocal.remove()