from db import Base
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

class ExamAttempt(Base):
    __tablename__ = 'examattempt'

    ID = Column(Integer, primary_key=True)
    studentID = Column(Integer, ForeignKey('student.StudentID'), nullable=False)
    examID = Column(Integer, ForeignKey('exam.ID'), nullable=False)

    
    mcqAns_rship = relationship('MCQAns', back_populates='examAttempt_rship') #
    desAns_rship = relationship('DesAns', back_populates='examAttempt_rship')
    log_rship = relationship("StudentExamLog", back_populates="examAttempt_rship")