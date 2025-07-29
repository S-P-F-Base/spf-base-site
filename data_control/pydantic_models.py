from datetime import datetime

from pydantic import BaseModel


class TargetUserAPIData(BaseModel):
    target: str


class AccessAPIData(TargetUserAPIData):
    access: int


class LoginAPIData(BaseModel):
    username: str
    password: str


class PlayerAPIData(BaseModel):
    discord_name: str
    steam_url: str


# region LOGS DATA
class LogRangeAPIData(BaseModel):
    start_id: int
    end_id: int


class LogTimeRangeAPIData(BaseModel):
    start_time: datetime
    end_time: datetime


class LogTypeAPIData(BaseModel):
    log_type: int


# endregion
