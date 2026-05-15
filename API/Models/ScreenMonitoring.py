from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship

class ScreenMonitoring(Base):
    __tablename__ = 'screenmonitoring' #

    ID = Column(Integer, primary_key=True)
    EventID = Column(Integer, ForeignKey('proctoringevent.ID'))
    ActionType = Column(String(50))
    EvidanceImage = Column(LargeBinary) # Maps to VARBINARY(MAX)

    # Relationship
    event_rship = relationship('ProctoringEvent', back_populates='screen_rship')

    def to_dict(self):
        return {
            "ID": self.ID,
            "ActionType": self.ActionType,
            "EvidanceImage": self.EvidanceImage.hex() if self.EvidanceImage else None
        }
    