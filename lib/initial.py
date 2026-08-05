from platformdirs import user_config_dir
import os

APP_NAME = "aurbit"
CONFIG_DIR = user_config_dir(APP_NAME)
UPLOADS_DIR = os.path.join(CONFIG_DIR, "uploads")
IMAGES_DIR = os.path.join(UPLOADS_DIR, "images")
DIRS = [
    CONFIG_DIR,
    UPLOADS_DIR,
    IMAGES_DIR
]


def setup():
    for DIR in DIRS:
        os.makedirs(DIR, exist_ok=True)