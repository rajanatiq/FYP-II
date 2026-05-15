from db import Base
from sqlalchemy import Column, Integer, String, Date, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

class VoiceMonitoring(Base):
    __tablename__ = 'VOICE_MONITORING' #

    ID = Column(Integer, primary_key=True)
    EventID = Column(Integer, ForeignKey('proctoringevent.ID'))
    Transcript = Column(String)

    # Relationship
    event_rship = relationship('ProctoringEvent', back_populates='voice_rship')
    