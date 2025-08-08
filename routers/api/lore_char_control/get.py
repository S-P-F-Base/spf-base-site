from fastapi import APIRouter

from .base_func import load_data

router = APIRouter()


@router.get("/get")
def get_all_characters():
    return load_data()
