from lib.db_functions.users import fetch_users, fetch_user_from_session
from fastapi import Request, Response, status
from lib import responses, functions
from lib.logger import logger
from functools import wraps
import inspect
import time

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    request_time = (time.time() - start_time) * 1000
    logger.http(
        f"{request.client.host} - {request.method} {request.url.path} {request.url.query}"
        f"{response.status_code} - {request_time:.2f}ms"
    )
    return response

# validate authentication from user
def auth_validator(pwd):
    async def middleware(request: Request, call_next):
        auth = request.headers.get("authorization").removeprefix("Bearer ").strip()
        if auth == pwd:
            return await call_next(request)
        else:
            
            logger.access(f"Unauthorized User, incorrect bearer token from IP: {request.client.host}")
            limit = functions.leaky_rate_limiter(unauthorized_attempts=5, within=300, penalty=20, url="*", ip_addr=request.client.host)
            if limit: return limit
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    return middleware

# middleware for validating paths based off of aurbit contexts
async def path_validator(request: Request, call_next):
    # if no users created ( setup )
    request.state.users_length = len(fetch_users())
    if request.state.users_length == 0 and (request.url.path.rstrip("/") != "/users/register" or request.method != "POST"):
        return responses.generate_response(
            message="AurBit hasn't been setup yet, create a user.",
            code=400
        )
    
    session_token = request.cookies.get("session")
    session_user = None
    if session_token:
        session_user = fetch_user_from_session(token=session_token)

    request.state.user = session_user

    return await call_next(request)

# function based middleware
def login_required(exception=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not request.state.user:
                if (type(exception) == bool and not exception) or (inspect.isfunction(exception) and not exception(request)):
                    return responses.generate_response(
                        message="Invalid AurBit Session ID",
                        code=401
                    )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator