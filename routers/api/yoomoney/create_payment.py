from fastapi import APIRouter, Request

from data_control import req_authorization

router = APIRouter()


@router.post("/create_payment")
def create_payment(request: Request):
    username = req_authorization(request)
    ...
