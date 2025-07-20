from pydantic import BaseModel


class TargetUserData(BaseModel):
    target: str


class LoginData(BaseModel):
    username: str
    password: str
