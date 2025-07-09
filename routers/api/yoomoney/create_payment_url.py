from fastapi import APIRouter, Request

from database import req_login

router = APIRouter()


@router.post("/create_payment_url")
def create_payment_url(request: Request):
    username = req_login(request)
    ...
