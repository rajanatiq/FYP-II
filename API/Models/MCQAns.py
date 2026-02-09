from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class MCQAns(Base):
    __tablename__ = 'mcqans' #

    ID = Column(Integer, primary_key=True, index=True)
    M_ID = Column(Integer, ForeignKey('exammcq.ID'))
    S_ID = Column(Integer, ForeignKey('student.StudentID'))
    O_ID = Column(Integer,ForeignKey('mcqoption.ID'))

    # Relationships
    question_rship = relationship('ExamMCQ', back_populates='ans_rship')
    student_rship = relationship('Student', back_populates='mcq_ans_rship')
    option_rship=relationship('MCQOption',back_populates='mcq_rship')
    