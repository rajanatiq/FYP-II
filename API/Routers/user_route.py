from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from db import get_db
from Controllers.UserController import UserController


router = APIRouter()

@router.get("/")
def welcome():
    return {"message": "welcome to FAST API "}

@router.get('/users')
def fetch_users(db: Session = Depends(get_db)):
    return UserController.get_all_users(db)

@router.post('/login')
async def login_users(file: UploadFile = File(...), id: str = Form(...), db: Session = Depends(get_db)):
    return await UserController.checkLogin(file, id, db)