from lib.db_functions.locations import add_location
from lib.responses import generate_response
from lib.middleware import login_required
from fastapi import APIRouter, Request
from pydantic import BaseModel
from lib.logger import logger

class Location(BaseModel):
    longitude: float
    latitude: float
    speed: int | None = None    

router = APIRouter()

@router.post("/update")
@login_required()
async def update_location(request: Request, location: Location):
    add_location(request.state.user.id, location.latitude, location.longitude, location.speed)
    return generate_response(message="User Location Update Failed", code=500)