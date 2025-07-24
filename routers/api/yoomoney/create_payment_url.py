from fastapi import APIRouter, Request

from data_control import req_authorization

router = APIRouter()


@router.post("/create_payment_url")
def create_payment_url(request: Request):
    username = req_authorization(request)
    ...
