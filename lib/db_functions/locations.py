from lib.db_functions.users import fetch_user
from lib.db import Locations, session_scope
from datetime import datetime
import math

def calculate_speed(lat1, lon1, lat2, lon2, time_diff_seconds):
    print(type(lat1), type(lon1), type(lat2), type(lon2), type(time_diff_seconds))
    # radius of the Earth in meters
    R = 6371e3
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    if time_diff_seconds > 0:
        speed = distance / time_diff_seconds
    else:
        speed = 0

    return speed

def fetch_locations(user_id):
    user = fetch_user(id=user_id)
    with session_scope() as session:
        return session.query(Locations).filter(Locations.user_id == user.id).all()

def add_location(user_id, latitude, longitude, speed=None):
    if not speed:
        user_locations = fetch_locations(user_id)
        last_location = user_locations[-1] if len(user_locations) > 0 else None
        if last_location:
            time_diff = (datetime.utcnow() - last_location.timestamp).total_seconds()
            speed = calculate_speed(
                last_location.latitude, last_location.longitude,
                latitude, longitude, time_diff
            )

    with session_scope() as session:
        location = Locations(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            speed=speed
        )

        session.add(location)
        session.commit()
        return location