# create nesscary folders
from lib import initial
initial.setup()

from routers import users, location, appstate
from lib import configs, db, middleware
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
import os

# setup
load_dotenv()

# varibles
CONFIG = configs.fetch_server_config()
app = FastAPI()

app.middleware("http")(middleware.path_validator)
app.middleware("http")(middleware.auth_validator(CONFIG["PWD"]))
app.middleware("http")(middleware.log_requests)

# routers
app.include_router(users.router, prefix="/users")
app.include_router(location.router, prefix="/location")
app.include_router(appstate.router, prefix="/app-state")

if __name__ == "__main__":
    db.init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=CONFIG["PORT"], reload=True if os.environ.get("dev") else False)