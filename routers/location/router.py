from lib.db_functions.locations import add_location, fetch_recent_locations
from lib.responses import generate_response
from lib.middleware import login_required
from lib.functions import image_to_base64
from fastapi import APIRouter, Request
from lib.initial import CONFIG_DIR
from pydantic import BaseModel
from lib.logger import logger
import os
class Location(BaseModel):
    longitude: float
    latitude: float
    speed: int | None = None


router = APIRouter()


@router.get("/")
@login_required()
async def fetch_locations(request: Request):
    locations = fetch_recent_locations()
    if locations:
        return generate_response(
            message="Fetched locations sucessfully",
            code=200,
            data={
                "users": [
                    {
                        "me": user.id == request.state.user.id,
                        "image": image_to_base64(os.path.join(CONFIG_DIR, user.profile_picture)) if user.profile_picture else None,
                        "userid": location.user_id,
                        "user": user.displayName,
                        "timestamp": location.timestamp.isoformat(),
                        "longitude": location.longitude,
                        "latitude": location.latitude,
                        "speed": location.speed if location.speed > 0 else 0,
                    }
                    for location, user in locations
                ],
                "region": []
            },
        )
    return generate_response(message="Fetch location failed", code=500)


@router.post("/update")
@login_required()
async def update_location(request: Request, location: Location):
    location = add_location(
        request.state.user.id, location.latitude, location.longitude, location.speed
    )
    if location:
        return generate_response(message="Location updated successfully.", code=200)
    return generate_response(message="User Location Update Failed", code=500)
