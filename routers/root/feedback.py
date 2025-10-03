from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from templates import templates

router = APIRouter()

FEEDBACK_LEAVE_FILE = Path("data/leave_feedback.log")
FEEDBACK_FILE = Path("data/feedback.log")


@router.get("/leave_feedback")
async def feedback_leave_form(request: Request):
    return templates.TemplateResponse("leave_feedback.html", {"request": request})


@router.post("/leave_feedback")
async def feedback_leave_submit(
    request: Request,
    name: str = Form(""),
    feedback: str = Form(...),
):
    FEEDBACK_LEAVE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with FEEDBACK_LEAVE_FILE.open("a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Name: {name.strip() or 'Anonymous'} | Feedback: {feedback.strip()}\n"
        )

    return RedirectResponse(url="/", status_code=303)


@router.get("/feedback")
async def feedback_form(request: Request):
    return templates.TemplateResponse("feedback.html", {"request": request})


@router.post("/feedback")
async def feedback_submit(
    request: Request,
    name: str = Form(""),
    feedback: str = Form(...),
):
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)

    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Name: {name.strip() or 'Anonymous'} | Feedback: {feedback.strip()}\n"
        )

    return RedirectResponse(url="/", status_code=303)
