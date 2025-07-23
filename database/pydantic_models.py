from datetime import datetime

from pydantic import BaseModel


class TargetUserData(BaseModel):
    target: str


class LogRangeData(BaseModel):
    start_id: int
    end_id: int


class LogTimeRangeData(BaseModel):
    start_time: datetime
    end_time: datetime


class LoginData(BaseModel):
    username: str
    password: str


class AccessData(TargetUserData):
    access: int
