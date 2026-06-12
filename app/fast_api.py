import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import async_engine
from app.models import Base
from app.routers import user_router, auth_router, recipe_router, ai_router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables when the app starts."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(recipe_router)
app.include_router(ai_router)

@app.get("/")
def root():
    """Health check endpoint - returns a simple message."""
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run("client:app", host="127.0.0.1", port=8000, reload=True)