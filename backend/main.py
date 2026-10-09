from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import InternalUser, get_current_internal_user
from config import FRONTEND_ORIGIN

app = FastAPI(title="Test2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def read_root():
    return {"message": "FastAPI backend berjalan"}


@app.get("/api/auth/me", response_model=InternalUser)
async def read_current_user(
    current_user: InternalUser = Depends(get_current_internal_user),
):
    return current_user
