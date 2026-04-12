from lib.db_functions.users import fetch_ratelimit, update_ratelimit
from datetime import datetime, timezone, timedelta
from fastapi import Response, status
from lib.logger import logger
from lib import db

def leaky_rate_limiter(unauthorized_attempts, within, penalty, **kwargs):
    resp = False
    user_ratelimit = fetch_ratelimit(**kwargs)
    user_ratelimit.last_updated = user_ratelimit.last_updated.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = abs(now - user_ratelimit.last_updated).total_seconds()
    
    if diff > within:
        user_ratelimit.attempts = 1
    else:
        user_ratelimit.attempts += 1

    if user_ratelimit.attempts > unauthorized_attempts:
        user_ratelimit.seconds += penalty

    if now > user_ratelimit.last_updated+timedelta(seconds=user_ratelimit.seconds):    
        user_ratelimit.seconds = 0
    else:
        # still within penalty not allowed
        logger.access(f"Unauthorized User, too many requests: {user_ratelimit.ip_addr}")
        resp = Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    update_ratelimit(user_ratelimit.id, attempts=user_ratelimit.attempts, seconds=user_ratelimit.seconds) 

    return resp