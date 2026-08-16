from lib.db_functions.users import (
    create_new_user,
    create_user_session,
    delete_user_sessions,
    fetch_user,
    edit_user,
)
from fastapi import APIRouter, Request, UploadFile, File, Form
from pydantic import BaseModel, EmailStr, ValidationError
from lib.functions import image_to_base64, convert_to_jpeg
from lib.responses import generate_response
from lib.middleware import login_required
from lib.initial import IMAGES_DIR
from lib.logger import logger
from PIL import Image
import traceback
import random
import string
import os

class CreateUser(BaseModel):
    displayName: str
    email: EmailStr
    access: int | None = None  # inital user creation doesn't require
    password: str | None = None  # initial user creation require


class LoginUser(BaseModel):
    email: EmailStr
    password: str


class UserStatus(BaseModel):
    email: EmailStr
    
class UserDetails(BaseModel):
    displayName: str
    email: EmailStr


ALLOWED_IMAGE_FILES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif"
}

router = APIRouter()


@router.post("/register")
@login_required(exception=lambda req: req.state.users_length == 0)
async def create_user(request: Request, user: CreateUser):
    # if no previous users ( allow super user creation )
    if not request.state.user and request.state.users_length == 0 and user.password:
        created_user = create_new_user(
            displayName=user.displayName,
            email=user.email,
            password=user.password,
            initialized=True,
            access=0,
        )
        if created_user:
            created_session = create_user_session(created_user.id)
            return generate_response(
                data={"access_token": created_session.token}, code=200
            )
    else:
        # if super user then create user template
        if request.state.users_length == 0 and not user.password:
            return generate_response(message="Missing field password", code=400)
        elif request.state.user and request.state.user.access == 0:
            created_user = create_new_user(
                displayName=user.displayName,
                email=user.email,
                initialized=False,
                access=(user.access or 1),
            )
            if created_user:
                return generate_response(
                    message="User creation was successful", code=200
                )
            else:
                return generate_response(
                    message="Unable to create user, email most likely already exists.",
                    code=500,
                )
        else:
            return generate_response(
                message="Only superusers can create users", code=401
            )

    logger.warning(f"User creation failed for {user.email}, ( check DB )")

    return generate_response(message="User Creation Failed", code=500)


@router.post("/user-status")
async def user_status(request: Request, user: UserStatus):
    db_user = fetch_user(email=user.email)
    if not db_user:
        return generate_response(message="The email does not exist", code=401)

    return generate_response(
        message="Fetched status", data={"initialized": db_user.initialized}, code=200
    )


# allows normal login and also creates the password for user templates
@router.post("/login")
async def login_user(request: Request, user: LoginUser):
    db_user = fetch_user(email=user.email)
    if db_user and (
        (not db_user.initialized)
        or (db_user.initialized and db_user.verify_password(user.password))
    ):
        if not db_user.initialized:
            db_user = edit_user(
                db_user.id, password=user.password, initialized=True, access=1
            )
        delete_user_sessions(db_user.id)  # delete all previous user sessions
        created_session = create_user_session(db_user.id)
        return generate_response(data={"access_token": created_session.token}, code=200)
    else:
        logger.access(f"Failed credentials for {user.email}")

    return generate_response(message="Unable to login user", code=500)


@router.get("/user-details")
@login_required()
async def user_details(request: Request):
    user = fetch_user(email=request.state.user.email)
    if not user:
        return generate_response(message="Something went wrong", code=500)

    return generate_response(
        message="Fetched data",
        data={        
            "image": (
                image_to_base64(os.path.join(IMAGES_DIR, user.profile_picture))
                if user.profile_picture
                else None
            ),
            "email": user.email,
            "displayName": user.displayName    
        },
        
        code=200
    )
    
@router.post("/edit-details")
@login_required()
async def edit_details(request: Request, file: UploadFile | None = File(None), data: str = Form(...)):
    try:
        user_details = UserDetails.model_validate_json(data)
        filename = None
        
        if file is not None:
            if file.content_type not in ALLOWED_IMAGE_FILES:
                return generate_response(message="Invalid file type.", code=422)

            contents = await file.read()
            jpeg_bytes = convert_to_jpeg(contents)
            filename = f"{''.join(random.choices(string.ascii_letters, k=12))}.jpg"

            with open(os.path.join(IMAGES_DIR, filename), 'wb') as f:
                f.write(jpeg_bytes)

            try:
                old_profile = getattr(request.state.user, 'profile_picture', None)
                if old_profile:
                    old_file_path = os.path.join(IMAGES_DIR, old_profile)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
            except Exception:
                # don't fail the whole request if cleanup fails
                pass

        # prepare kwargs for edit_user
        edit_kwargs = {
            'displayName': user_details.displayName,
            'email': user_details.email,
        }
        if filename:
            edit_kwargs['profile_picture'] = filename

        # call edit_user with keyword args
        res = edit_user(request.state.user.id, **edit_kwargs)

        if res:
            return generate_response(message="User details edited successfully.", code=200)
    
    except ValidationError as e:
        return generate_response(message="Parse failed", data={"errors": e.errors()}, code=422)
    except Exception as e:
        logger.error(f"Unable to edit user detail {traceback.format_exc()}")
    
    return generate_response(message="Edit details failed", code=500)