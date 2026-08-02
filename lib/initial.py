from platformdirs import user_config_dir
import os

APP_NAME = "aurbit"
CONFIG_DIR = user_config_dir(APP_NAME)
DIRS = [
    CONFIG_DIR,
    os.path.join(CONFIG_DIR, "uploads"),
    os.path.join(CONFIG_DIR, "uploads", "images")
]


def setup():
    for DIR in DIRS:
        os.makedirs(DIR, exist_ok=True)