from fastapi import APIRouter, Request

from database import req_login

router = APIRouter()


@router.post("/create_payment")
def create_payment(request: Request):
    username = req_login(request)
    ...
