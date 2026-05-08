from db import Base
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, mapped_column, Mapped

class ExamAttempt(Base):
    __tablename__ = 'examattempt'

    ID = Column(Integer, primary_key=True)
    studentID = Column(Integer, ForeignKey('student.StudentID'), nullable=False)
    examID = Column(Integer, ForeignKey('exam.ID'), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='active')  # in_progress, completed, etc.
    front_cam: Mapped[bool] = mapped_column(default=True)
    back_cam: Mapped[bool] = mapped_column(default=False)
    
    mcqAns_rship = relationship('MCQAns', back_populates='examAttempt_rship') #
    desAns_rship = relationship('DesAns', back_populates='examAttempt_rship')
    log_rship = relationship("StudentExamLog", back_populates="examAttempt_rship")
    
    audio_chunks_mcq_rship = relationship("StudentMCQExamAudioChunk", back_populates="examAttempt_rship")
    audio_chunks_des_rship = relationship("StudentDESCExamAudioChunk", back_populates="examAttempt_rship")