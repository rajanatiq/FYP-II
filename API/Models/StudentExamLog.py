from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship

class StudentExamLog(Base):
    __tablename__ = 'studentexamlog'

    id = Column(Integer, primary_key=True, autoincrement=True)

    attempt_id = Column(Integer,ForeignKey("examattempt.ID"),nullable=False)

    position = Column(String(30))
    isPresent = Column(Boolean)

    TIMESTAMP = Column(DateTime)
    image_path = Column(String(None))

    examAttempt_rship = relationship("ExamAttempt", back_populates="log_rship")

