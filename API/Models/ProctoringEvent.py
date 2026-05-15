from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class ProctoringEvent(Base):
    __tablename__ = 'proctoringevent' #

    ID = Column(Integer, primary_key=True)
    EX_ID = Column(Integer, ForeignKey('exam.ID'))
    S_ID = Column(Integer, ForeignKey('student.StudentID'))
    EventType = Column(String(50), nullable=False)
    EventTime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    exam_rship = relationship('Exam', back_populates='proctoring_rship')
    student_rship = relationship('Student', back_populates='proctoring_rship')
    
    # Monitoring Data
    voice_rship = relationship('VoiceMonitoring', back_populates='event_rship') #
    screen_rship = relationship('ScreenMonitoring', back_populates='event_rship') #
    camera_rship = relationship('CameraMonitoring', back_populates='event_rship') #

    def to_dict(self):
        return {
            "ID": self.ID,
            "EventType": self.EventType,
            "EventTime": self.EventTime.isoformat() if self.EventTime else None
        }