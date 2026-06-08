from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user
from app.database import engine
from app.models import Base

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(user.router)

@app.get("/")
def root():
    return {"message": "Hello World"}
