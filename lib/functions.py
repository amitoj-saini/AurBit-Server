from lib.db_functions.users import fetch_ratelimit, update_ratelimit
from datetime import datetime, timezone, timedelta
from fastapi import Response, status
from lib.logger import logger
from PIL import Image
from math import *
from lib import db
import pillow_heif
import base64
import io

pillow_heif.register_heif_opener()

def name_location(lat, lon, street, street_number, city, region, country):
    text = f"{lat}, {lon}"
    if street and street_number:
        text = f"{street_number} {street}"
    elif city and region:
        text = f"{city}, {region}"
    elif city and country:
        text = f"{city}, {country}"
    elif country:
        text = f"{country}"
    return text

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


def convert_to_jpeg(file_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(file_bytes))

    # JPEG doesn't support transparency
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    output = io.BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=90,
        optimize=True
    )

    return output.getvalue()

def image_to_base64(path, max_size: int=256, quality: int=75):
    try:
        img = Image.open(path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail((max_size, max_size))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(e)
        pass
    
    return None

def leaky_rate_limiter(unauthorized_attempts, within, penalty, **kwargs):
    resp = False
    user_ratelimit = fetch_ratelimit(**kwargs)
    user_ratelimit.last_updated = user_ratelimit.last_updated.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = abs(now - user_ratelimit.last_updated).total_seconds()
    
    if diff > within:
        user_ratelimit.attempts = 1
    else:
        user_ratelimit.attempts += 1

    if user_ratelimit.attempts > unauthorized_attempts:
        user_ratelimit.seconds += penalty

    if now > user_ratelimit.last_updated+timedelta(seconds=user_ratelimit.seconds):    
        user_ratelimit.seconds = 0
    else:
        # still within penalty not allowed
        logger.access(f"Unauthorized User, too many requests: {user_ratelimit.ip_addr}")
        resp = Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    update_ratelimit(user_ratelimit.id, attempts=user_ratelimit.attempts, seconds=user_ratelimit.seconds) 

    return resp