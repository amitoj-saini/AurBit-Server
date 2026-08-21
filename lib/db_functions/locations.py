from lib.db import User, Locations, session_scope
from lib.db_functions.users import fetch_user
from sqlalchemy import select, func, and_
from datetime import datetime, timezone
from lib import configs
from math import *
import math

CONFIG = configs.fetch_server_config()

def distance_meters(lat1, lon1, lat2, lon2):
    R = 6_371_000

    lat1 = radians(lat1)
    lat2 = radians(lat2)
    dlat = lat2 - lat1
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

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
    
def fetch_last_location(user_id):
    with session_scope() as session:
            return session.query(Locations).filter(
                Locations.user_id == user_id,
            ).order_by(Locations.last_timestamp.desc()).first()
            
    return None


def add_location(user_id, latitude, longitude, speed, street, street_number, city, region, country):
    last_location = fetch_last_location(user_id)
    
    if last_location:
        distance = distance_meters(latitude, longitude, last_location.latitude, last_location.longitude)
        if distance < CONFIG["COMBINE_THRESHOLD"]:
            with session_scope() as session:
                last_location = session.merge(last_location)
                last_location.street = street
                last_location.street_number = street_number
                last_location.recorded += 1
                session.commit()
                return last_location
    
        if not speed:
            time_diff = (datetime.now(timezone.utc) - last_location.timestamp).total_seconds()
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
                Locations.last_timestamp >= from_datetime.replace(tzinfo=None),
                Locations.last_timestamp <= to_datetime.replace(tzinfo=None),
            )
            .order_by(Locations.last_timestamp.asc())
        ).all()
        
        return locations