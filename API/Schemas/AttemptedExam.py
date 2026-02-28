from pydantic import BaseModel

class AttemptedExam(BaseModel):
    s_id: int
    e_id: int
    
    
