from lib.db_functions.locations import add_location, fetch_recent_locations
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status
from lib.middleware import login_required, login_required_websocket
from lib.responses import generate_response
from lib.websocket import ConnectionManager
from lib.functions import image_to_base64
from lib.initial import IMAGES_DIR
from pydantic import BaseModel
from lib.logger import logger
import os
class Location(BaseModel):
    longitude: float
    latitude: float
    speed: float | None = None


router = APIRouter()

connection_manager = ConnectionManager()


def build_locations_payload(locations, current_user_id=None, message="Fetched locations successfully", code=200):
    return {
        "result": {
            "action": "success" if 200 <= code < 300 else "error",
            "message": message,
            "code": code,
            "data": {
                "users": [
                    {
                        "me": user.id == current_user_id,
                        "image": image_to_base64(os.path.join(IMAGES_DIR, user.profile_picture)) if user.profile_picture else None,
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
            }
        }
    }

async def broadcast_recent_locations():
    locations = fetch_recent_locations()
    payload = build_locations_payload(locations)
    await connection_manager.broadcast_json(payload)


@router.websocket("/")
@login_required_websocket()
async def fetch_locations(websocket: WebSocket):
    await websocket.accept()
    await connection_manager.connect(websocket)

    try:
        locations = fetch_recent_locations()
        await websocket.send_json(build_locations_payload(locations, current_user_id=websocket.state.user.id))

        while True:
            event = await websocket.receive()
            if event["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(websocket)


@router.post("/update")
@login_required()
async def update_location(request: Request, location: Location):
    location = add_location(
        request.state.user.id, location.latitude, location.longitude, location.speed
    )
    if location:
        await broadcast_recent_locations()
        return generate_response(message="Location updated successfully.", code=200)
    return generate_response(message="User Location Update Failed", code=500)
