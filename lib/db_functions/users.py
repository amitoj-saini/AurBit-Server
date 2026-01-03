from lib.db import User, Session, RateLimit, session_scope
from datetime import datetime, timedelta
from lib.logger import logger

def fetch_users():
    with session_scope() as session:
        return session.query(User).all()
    
def fetch_user(**kwargs):
    with session_scope() as session:
        return session.query(User).filter_by(**kwargs).first()
    
def fetch_ratelimit(**kwargs):
    with session_scope() as session:
        
        instance = session.query(RateLimit).filter_by(**kwargs).first()
        if instance: return instance
        instance = RateLimit(**kwargs, attempts=0, seconds=0)
        session.add(instance)
        session.flush()
        return instance
    
def update_ratelimit(id, **kwargs):
    with session_scope() as session:
        session.query(RateLimit).filter_by(id=id).update({**kwargs})

def fetch_user_from_session(**kwargs):
    with session_scope() as session:
        user_session = session.query(Session).filter_by(**kwargs).one_or_none()
        if user_session:
            return user_session.user
        else:
            return None
    
def create_new_user(**kwargs):
    try:
        with session_scope() as session:
            user = User(**kwargs)
            session.add(user)
            session.commit()
            return user
    except Exception as e:
        print(e)
        logger.error(e)
    return None

def edit_user(user_id, **kwargs):
    try:
        with session_scope() as session:
            user = session.query(User).filter_by(id=user_id).one_or_none()
            if user:
                for key, val in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, val)
                session.commit()
            return user
    except Exception as e:
        print(e)
        logger.error(e)
    return False

def delete_user_sessions(user_id):
    with session_scope() as session:
        for user_session in session.query(Session).filter(Session.user_id == user_id).all():
            session.delete(user_session)
            session.commit()

def create_user_session(user_id):
    with session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user_session = Session(
                user_id=user_id,
                expires_at=datetime.utcnow() + timedelta(days=365)
            )

            session.add(user_session)
            session.commit()
            session.refresh(user_session)

            return user_session
        return None