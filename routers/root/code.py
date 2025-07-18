from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/code/{number}")
def code(number: int):
    if number >= 400:
        raise HTTPException(
            status_code=number, detail=f"Forced error with status {number}"
        )

    return RedirectResponse("/", status_code=302)
