from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
class MCQOption(Base):
    __tablename__ = 'mcqoption' #

    ID = Column(Integer, primary_key=True)
    M_ID = Column(Integer, ForeignKey('exammcq.ID'))
    OPTION_TEXT = Column(String)
    IS_CORRECT = Column(Boolean) # Maps to BIT

    # Relationship
    question_rship = relationship('ExamMCQ', back_populates='option_rship')
    mcq_rship=relationship('MCQAns',back_populates='option_rship')