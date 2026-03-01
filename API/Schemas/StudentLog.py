from pydantic import BaseModel

class StudentLog(BaseModel):
    std_id: int
    exam_id: int
    # startTime: str
    # endTime: str
    