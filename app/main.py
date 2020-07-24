import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.database import db_connect, db_disconnect
from app.config import LISTEN_PORT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_event_handler("startup", db_connect)
app.add_event_handler("shutdown", db_disconnect)

app.include_router(router)

# Start server with uvicorn if this is the main module
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT)
