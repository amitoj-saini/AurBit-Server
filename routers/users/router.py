from lib.db_functions.users import create_new_user, create_user_session, delete_user_sessions, fetch_user, edit_user
from lib.responses import generate_response
from lib.middleware import login_required
from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
from lib.logger import logger

class CreateUser(BaseModel):
    displayName: str
    email: EmailStr
    access: int | None = None # inital user creation doesn't require
    password: str | None = None # initial user creation require
class LoginUser(BaseModel):
    email: EmailStr
    password: str


router = APIRouter()

@router.post("/register")
@login_required(exception=lambda req: req.state.users_length == 0)
async def create_user(request: Request, user: CreateUser):
    # if no previous users ( allow super user creation )
    
    if not request.state.user and request.state.users_length == 0 and user.password:
        created_user = create_new_user(displayName=user.displayName, email=user.email, password=user.password, initialized=True, access=0)
        if created_user:
            created_session = create_user_session(created_user.id)
            return generate_response(data={
                "access_token": created_session.token
            }, code=200)
    else:
        if request.state.user.access == 0:
            created_user = create_new_user(displayName=user.displayName, email=user.email, initialized=False, access=1)
            if created_user:
                return generate_response(message="User creation was successful", code=200)
            else:
                return generate_response(message="Unable to create user, email most likely already exists.", code=500)
        else:
            return generate_response(message="Only superusers can create users", code=401)
    
    logger.warning(f"User creation failed for {user.email}, ( check DB )")

    return generate_response(message="User Creation Failed", code=500)

@router.post("/login")
async def login_user(request: Request, user: LoginUser):
    db_user = fetch_user(email=user.email)
    if db_user and ((not db_user.initialized) or (db_user.initialized and db_user.verify_password(user.password))):
        if not db_user.initialized:
            db_user = edit_user(db_user.id, password=user.password, initialized=True, access=1)
        delete_user_sessions(db_user.id) # delete all previous user sessions
        created_session = create_user_session(db_user.id)
        return generate_response(data={
            "access_token": created_session.token
        }, code=200)
    else:
        logger.access(f"Failed credentials for {user.email}")
    
    return generate_response(message="Unable to login user", code=500)