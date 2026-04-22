from pydantic import BaseModel

class SaveMcqAns(BaseModel):
    mcqId: int
    optionId: int