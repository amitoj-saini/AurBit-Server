from lib.responses import generate_response
from lib.middleware import login_required
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/")
async def app_state(request: Request):
    return generate_response(message="Everything looks good.", data={
        "authenticated": True,
        "initalized": False if request.state.users_length == 0 else True,
        "loggedin": True if request.state.user else False
    }, code=200)