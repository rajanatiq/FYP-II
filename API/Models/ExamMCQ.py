from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship

class ExamMCQ(Base):
    __tablename__ = 'exammcq' #

    ID = Column(Integer, primary_key=True)
    E_ID = Column(Integer, ForeignKey('exam.ID'))
    DESCRIPTION = Column(String) # Maps to VARCHAR(MAX)
    MARKS = Column(Integer)

    # Relationships
    exam_rship = relationship('Exam', back_populates='mcq_rship')
    option_rship = relationship('MCQOption', back_populates='question_rship') #
    ans_rship = relationship('MCQAns', back_populates='question_rship') #
    audio_chunks_des_rship = relationship('StudentMCQExamAudioChunk', back_populates='exam_mcq_qst_rship')
    