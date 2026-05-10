from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db import Base  # adjust according to your project

class DetectedObjects(Base):
    __tablename__ = "detectedobjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    attemptID = Column(Integer, ForeignKey("examattempt.ID"), nullable=False)
    
    objects = Column(String(255), nullable=True)
    
    timestamp = Column(DateTime, nullable=False)
    
    image_path: Mapped[str] = mapped_column(String, nullable=True)

    # Optional relationship (recommended)
    exam_attempt = relationship("ExamAttempt", back_populates="detected_objects")