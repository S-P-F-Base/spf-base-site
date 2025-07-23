from datetime import datetime

from pydantic import BaseModel


class TargetUserData(BaseModel):
    target: str


class LoginData(BaseModel):
    username: str
    password: str


class AccessData(TargetUserData):
    access: int


# region LOGS DATA
class LogRangeData(BaseModel):
    start_id: int
    end_id: int


class LogTimeRangeData(BaseModel):
    start_time: datetime
    end_time: datetime


class LogTypeData(BaseModel):
    log_type: int


# endregion
