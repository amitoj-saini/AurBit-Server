from lib.db_functions.users import fetch_users, fetch_user_from_session
from fastapi import Request, Response, WebSocket, status
from lib.responses import generate_response
from lib import responses, functions
from lib.logger import logger
from functools import wraps
from lib import configs
import inspect
import time

CONFIG = configs.fetch_server_config()

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
        auth_header = request.headers.get("authorization")
        auth = auth_header.removeprefix("Bearer ").strip() if auth_header and "Bearer" in auth_header else None
        # check if bearer token is correct
        if auth and auth == CONFIG["PWD"]:
            return await call_next(request)
        elif not auth_header or "Bearer" not in auth_header:
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
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
    
    if request.state.users_length == 0 and (request.url.path.rstrip("/") != "/users/register" or request.method != "POST") and request.url.path.rstrip("/") != "/app-state":
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

async def websocket_path_validator(websocket: WebSocket):
    websocket.state.users_length = len(fetch_users())

    if websocket.state.users_length == 0 and websocket.url.path.rstrip("/") not in ["/users/register", "/app-state"]:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    session_token = websocket.cookies.get("session") or websocket.query_params.get("session")
    websocket.state.user = fetch_user_from_session(token=session_token) if session_token else None

    return True

async def websocket_auth_validator(websocket: WebSocket):
    auth_header = websocket.headers.get("authorization") or websocket.query_params.get("authorization")
    auth = auth_header.removeprefix("Bearer ").strip() if auth_header and "Bearer" in auth_header else None
    if auth:
        return True
    elif not auth_header or "Bearer" not in auth_header:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    else:
        logger.access(f"Unauthorized User, incorrect bearer token from IP: {websocket.client.host}")
        limit = functions.leaky_rate_limiter(unauthorized_attempts=5, within=300, penalty=20, url="*", ip_addr=websocket.client.host)
        if limit:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

# function based middleware
def login_required(exception=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request | WebSocket, *args, **kwargs):
            if isinstance(request, WebSocket):
                if not await websocket_path_validator(request):
                    return
                if not await websocket_auth_validator(request):
                    return
                if not request.state.user:
                    if (type(exception) == bool and not exception) or (inspect.isfunction(exception) and not exception(request)):
                        await request.close(code=status.WS_1008_POLICY_VIOLATION)
                        return
            else:
                if not request.state.user:
                    if (type(exception) == bool and not exception) or (inspect.isfunction(exception) and not exception(request)):
                        return responses.generate_response(
                            message="Invalid AurBit Session ID",
                            code=401
                        )

            return await func(request, *args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)
        return wrapper
    return decorator


def login_required_websocket(exception=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(websocket: WebSocket, *args, **kwargs):
            if not await websocket_path_validator(websocket):
                return
            if not await websocket_auth_validator(websocket):
                return
            if not websocket.state.user:
                if (type(exception) == bool and not exception) or (inspect.isfunction(exception) and not exception(websocket)):
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
            return await func(websocket, *args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)
        return wrapper
    return decorator