from app.config import settings

print("DATABASE_HOSTNAME =", settings.database_hostname)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)

app.mount("/static", StaticFiles(directory="frontend/client"), name="static")

@app.get("/login")
def login_page():
    return FileResponse("frontend/client/loggingin.html")

@app.post("/register")
def register_page():
    return FileResponse("frontend/client/register.html")

@app.get("/home")
def home_page():
    return FileResponse("frontend/client/home.html")
