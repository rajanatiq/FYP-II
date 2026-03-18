from db import Base
from datetime import datetime
from sqlalchemy import Integer,text, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship,Mapped, mapped_column

class StudentDESCExamAudioChunk(Base):
    __tablename__ = "studentdescexamaudiochunk"

    ID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attemptID: Mapped[int] = mapped_column(ForeignKey("examattempt.ID"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("examdescques.ID"), nullable=False)
    chunk_url: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    
    examAttempt_rship = relationship("ExamAttempt", back_populates="audio_chunks_des_rship")
    exam_desc_qst_rship = relationship('ExamDescQues', back_populates='audio_chunks_des_rship')