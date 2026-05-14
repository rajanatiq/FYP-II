from db import Base
from datetime import datetime
from sqlalchemy import text, String, ForeignKey, Boolean, DateTime, func
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
    
    # TIMESTAMP: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # TIMESTAMP: Mapped[datetime] = mapped_column(
    #     DateTime,
    #     server_default=text("GETDATE()")
    # )   

    image_path: Mapped[str] = mapped_column(String(100))
    eye_gaze: Mapped[str] = mapped_column(String(10))
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    
    examAttempt_rship = relationship("ExamAttempt", back_populates="log_rship")

