from db import Base
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship,Mapped, mapped_column

class StudentExamLog(Base):
    __tablename__ = 'studentexamlog'

    # id = Column(Integer, primary_key=True, autoincrement=True)
    # attempt_id = Column(Integer,ForeignKey("examattempt.ID"),nullable=False)
    # position = Column(String(30))
    # isPresent = Column(Boolean)
    # TIMESTAMP = Column(DateTime)
    # image_path = Column(String(None))

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("examattempt.ID"), 
        nullable=False
    )

    position: Mapped[str] = mapped_column(String)

    isPresent: Mapped[bool] = mapped_column(Boolean)

    TIMESTAMP: Mapped[datetime] = mapped_column(DateTime)

    image_path: Mapped[str] = mapped_column(String(100))
    
    examAttempt_rship = relationship("ExamAttempt", back_populates="log_rship")

