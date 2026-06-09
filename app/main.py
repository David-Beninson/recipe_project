import uvicorn
from app.config import Settings as settings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base
from app.routers import user_router, auth_router, find_recipes
from contextlib import asynccontextmanager


# Lifespan context manager - runs on app startup to create all database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables when the app starts."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# Initialize FastAPI app with lifespan management
app = FastAPI(lifespan=lifespan)

# CORS configuration - allow all origins for frontend communication
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

# Include all API routers for user authentication and recipe search
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(find_recipes)


@app.get("/")
def root():
    """Health check endpoint - returns a simple message."""
    return {"message": "Hello World"}
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


if __name__ == "__main__":
    uvicorn.run("client:app", host="127.0.0.1", port=8000, reload=True)