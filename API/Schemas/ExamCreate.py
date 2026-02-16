from datetime import datetime
from pydantic import BaseModel

class ExamCreate(BaseModel):
    A_ID: int
    TITLE: str
    TOTAL_QUESTIONS: int
    E_DATE: datetime
    START_TIME: str
    END_TIME: str
    E_TYPE: str
    STATUS: str
