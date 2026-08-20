from lib.db import User, Locations, session_scope
from lib.db_functions.users import fetch_user
from sqlalchemy import select, func, and_
from datetime import datetime
import math

def calculate_speed(lat1, lon1, lat2, lon2, time_diff_seconds):
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

def add_location(user_id, latitude, longitude, speed, street, street_number, city, region, country):
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
            speed=speed,
            street=street,
            street_number=street_number,
            city=city,
            region=region,
            country=country
        )

        session.add(location)
        session.commit()
        return location
    
    return False

def fetch_recent_locations():
    with session_scope() as session:
        ranked_locations = (
            select(
                Locations.id.label("id"),
                Locations.user_id.label("user_id"),
                Locations.latitude.label("latitude"),
                Locations.longitude.label("longitude"),
                Locations.timestamp.label("timestamp"),
                Locations.timestamp.label("street"),
                Locations.timestamp.label("street_number"),
                Locations.timestamp.label("city"),
                Locations.timestamp.label("region"),
                Locations.timestamp.label("country"),
                func.row_number()
                .over(
                    partition_by=Locations.user_id,
                    order_by=[
                        Locations.timestamp.desc(),
                        Locations.id.desc()
                    ]
                )
                .label("rn")
            )
            .subquery()
        )

        query = (
            select(Locations, User)
            .join(
                ranked_locations,
                Locations.id == ranked_locations.c.id
            )
            .join(
                User,
                User.id == Locations.user_id
            )
            .where(ranked_locations.c.rn == 1)
        )

        return session.execute(query).all()
    
def fetch_last_location(user_id: int):
    with session_scope() as session:
        query = (
            select(Locations)
            .where(Locations.user_id == user_id)
            .order_by(
                Locations.timestamp.desc(),
                Locations.id.desc()
            )
            .limit(1)
        )

        return session.scalars(query).first()

def fetch_location_history(user_id, from_datetime, to_datetime):
    with session_scope() as session:
        locations = session.scalars(
            select(Locations)
            .where(
                Locations.user_id == user_id,
                Locations.timestamp >= from_datetime.replace(tzinfo=None),
                Locations.timestamp <= to_datetime.replace(tzinfo=None),
            )
            .order_by(Locations.timestamp.asc())
        ).all()
        
        return locations