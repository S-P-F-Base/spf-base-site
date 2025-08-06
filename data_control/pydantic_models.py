from datetime import datetime

from pydantic import BaseModel


class BaseUUIDAPIData(BaseModel):
    uuid: str


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


class ServiceCreateAPIData(BaseModel):
    name: str
    description: str
    price_main: str
    limit: int | None = None
    sell_time_end: datetime | None = None

    discount: int = 0
    discount_time_end: datetime | None = None


class ServiceEditAPIData(BaseUUIDAPIData):
    name: str | None = None
    description: str | None = None
    price_main: str | None = None
    status: int | None = None
    limit: int | None = None
    sell_time_end: datetime | None = None

    discount: int | None = None
    discount_time_end: datetime | None = None


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
