from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/player")
def player(request: Request):
    raise HTTPException(500, detail="refactoring code")
