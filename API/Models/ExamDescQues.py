from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship

class ExamDescQues(Base):
    __tablename__ = 'examdescques' #

    ID = Column(Integer, primary_key=True)
    E_ID = Column(Integer, ForeignKey('exam.ID'))
    DESCRIPTION = Column(String)
    MARKS = Column(Integer)

    # Relationships
    exam_rship = relationship('Exam', back_populates='desc_ques_rship')
    ans_rship = relationship('DesAns', back_populates='question_rship') #
    audio_chunks_des_rship = relationship('StudentDESCExamAudioChunk', back_populates='exam_desc_qst_rship')