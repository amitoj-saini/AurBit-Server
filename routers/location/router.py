from lib.db_functions.locations import add_location, fetch_recent_locations, fetch_location_history, fetch_last_location
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status, Query
from lib.middleware import login_required, login_required_websocket
from lib.functions import image_to_base64, distance_meters
from datetime import datetime, timedelta, timezone
from fastapi.encoders import jsonable_encoder
from lib.responses import generate_response
from lib.websocket import ConnectionManager
from lib.initial import IMAGES_DIR
from pydantic import BaseModel
from lib.logger import logger
from lib.db import Locations
from lib import configs
import traceback
import os

CONFIG = configs.fetch_server_config()
class Location(BaseModel):
    longitude: float
    latitude: float
    speed: float | None = None
    street: str
    street_number: str
    city: str
    region: str
    country: str
    
class HistoryQuery(BaseModel):
    user_id: int
    from_time: str | None = None
    to_time: str | None = None

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
    async with connection_manager._lock:
        connections = list(connection_manager.active_connections)
        for connection in connections:
            try:
                await connection.send_json(build_locations_payload(locations, current_user_id=connection.state.user.id))
            except Exception:
                await connection_manager.disconnect(connection)

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
        request.state.user.id, location.latitude, location.longitude, location.speed, location.street, location.street_number, location.city, location.region, location.country
    )
    if location:
        await broadcast_recent_locations()
        return generate_response(message="Location updated successfully.", code=200)
    return generate_response(message="User Location Update Failed", code=500)

@router.get("/history")
@login_required()
async def fetch_history(request: Request, params: HistoryQuery = Query()):
    try:
        now = datetime.now(timezone.utc)
        
        if not params.from_time:
            params.from_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if not params.to_time:
            params.to_time = now
        
        # unformatted db data sorted by timestamps
        locations = fetch_location_history(params.user_id, params.from_time, params.to_time)
        
        data = {
            "records": [],
            "current": {}
        }
        
        current_location = fetch_last_location(params.user_id)
        if current_location:
            data["current"] = {
                **{column.name: getattr(current_location, column.name) for column in Locations.__table__.columns},
                "timestamp": current_location.timestamp.isoformat(),
                "connected": True if current_location.timestamp > (now.replace(tzinfo=None) - timedelta(hours=5)) else False,
            }
        else:
            data["current"] = {
                **{column.name: None for column in Locations.__table__.columns},
                "timestamp": location.timestamp.isoformat(),
                "connected": False
            }
        
        for i in range(len(locations)):
            location = locations[i]
            if i > 0:
                previous_location = locations[i-1]
                
                distance = distance_meters(
                    location.latitude,
                    location.longitude,
                    previous_location.latitude,
                    previous_location.longitude
                )
                
                if distance < CONFIG["COMBINE_THRESHOLD"]:
                    # increase last record frequency 
                    data["records"][-1]["recorded"] += 1
                    data["records"][-1]["timestamps"].append(location.timestamp.isoformat())
                    continue
            
            data["records"].append({
                **{column.name: getattr(location, column.name) for column in Locations.__table__.columns},
                "timestamps": [location.timestamp.isoformat()],
                "recorded": 1
            })
        
        return generate_response(
            message="Fetched user history",
            data=jsonable_encoder(data),
            code=200,
        )
    except Exception as e:
        print(traceback.format_exc())
        logger.error(f"Unable to fetch user history for {params.user_id} {traceback.format_exc()}")
        
    return generate_response(message="Something went wrong", code=500)
