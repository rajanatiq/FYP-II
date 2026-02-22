from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship

class DesAns(Base):
    __tablename__ = 'desans' #

    ID = Column(Integer, primary_key=True)
    Q_ID = Column(Integer, ForeignKey('examdescques.ID'))
    ANSWERS = Column(String)
    attemptID = Column(Integer, ForeignKey('examattempt.ID'))

    # Relationships
    question_rship = relationship('ExamDescQues', back_populates='ans_rship')
    examAttempt_rship = relationship('ExamAttempt', back_populates='desAns_rship')