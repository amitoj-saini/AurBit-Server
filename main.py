# create nesscary folders
from lib import initial
initial.setup()

from lib import configs, db, middleware
from routers import users, location
from fastapi import FastAPI
import uvicorn

# varibles
CONFIG = configs.fetch_server_config()
app = FastAPI()

app.middleware("http")(middleware.path_validator)
app.middleware("http")(middleware.auth_validator(CONFIG["PWD"]))
app.middleware("http")(middleware.log_requests)

# routers
app.include_router(users.router, prefix="/users")
app.include_router(location.router, prefix="/location")

if __name__ == "__main__":
    db.init_db()
    uvicorn.run(app, host="127.0.0.1", port=CONFIG["PORT"])