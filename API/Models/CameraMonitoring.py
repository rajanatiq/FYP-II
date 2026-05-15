from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship


class CameraMonitoring(Base):
    __tablename__ = 'cameramonitoring' #

    ID = Column(Integer, primary_key=True)
    EventID = Column(Integer, ForeignKey('proctoringevent.ID'))
    IsStudentPresent = Column(Integer)
    description = Column(String)
    ImageEvidence = Column(String) # Maps to VARBINARY(MAX)

    # Relationship
    event_rship = relationship('ProctoringEvent', back_populates='camera_rship')

    def to_dict(self):
        return {
            "ID": self.ID,
            "IsStudentPresent": self.IsStudentPresent,
            "ImageEvidence": self.ImageEvidence.hex() if self.ImageEvidence else None
        }