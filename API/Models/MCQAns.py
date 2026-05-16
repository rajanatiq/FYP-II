from API.db import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class MCQAns(Base):
    __tablename__ = 'mcqans' #

    ID = Column(Integer, primary_key=True, index=True)
    M_ID = Column(Integer, ForeignKey('exammcq.ID'))
    O_ID = Column(Integer,ForeignKey('mcqoption.ID'))
    attemptID = Column(Integer, ForeignKey('examattempt.ID'))

    # Relationships
    question_rship = relationship('ExamMCQ', back_populates='ans_rship')
    option_rship=relationship('MCQOption',back_populates='mcq_rship')
    
    examAttempt_rship = relationship('ExamAttempt', back_populates='mcqAns_rship') #