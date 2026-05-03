from db import Base
from datetime import datetime
from sqlalchemy import Integer, text, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column


class StudentMCQExamAudioChunk(Base):
    __tablename__ = "studentmcqexamaudiochunk"

    ID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attemptID: Mapped[int] = mapped_column(ForeignKey("examattempt.ID"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("exammcq.ID"), nullable=False)
    chunk_url: Mapped[str] = mapped_column(String(100), nullable=False)
    transcript: Mapped[str] = mapped_column(String, nullable=True)
    
    student_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    other_person: Mapped[bool] = mapped_column(Boolean, nullable=True)
    other_suspicous: Mapped[bool] = mapped_column(Boolean, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)


    examAttempt_rship = relationship("ExamAttempt", back_populates="audio_chunks_mcq_rship")
    exam_mcq_qst_rship = relationship('ExamMCQ', back_populates='audio_chunks_des_rship')