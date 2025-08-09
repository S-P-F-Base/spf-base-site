from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from templates import templates

router = APIRouter()


@router.get("/pay/{uuid}", response_class=HTMLResponse)
def pay_page():
    pass
