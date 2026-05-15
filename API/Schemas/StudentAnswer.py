# Schemas/StudentAnswer.py
from pydantic import BaseModel
from typing import List
from Schemas.McqAnswer import McqAnswer

class StudentAnswer(BaseModel):
    attemptID: int
    M_ID: int
    O_ID: int