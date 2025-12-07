from pydantic import BaseModel

class Message(BaseModel):
    usermessage: str

class UserCreate(BaseModel):
    name: str
    surname: str
    login: str
    mail: str
    password: str

class LoginRequest(BaseModel):
    login: str
    password: str

class ConversationCreate(BaseModel):
    token: str

class HistoryRate(BaseModel):
    rate: bool

class RefreshRequest(BaseModel):
    refreshtoken: str