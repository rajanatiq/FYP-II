# Models/room.py
from db import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

class Room(Base):
    __tablename__ = "room"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    RoomName = Column(String(7), nullable=False)
    TotalRows = Column(Integer, nullable=False)
    SeatsPerRow = Column(Integer, nullable=False)

    student_seatings = relationship('StudentSeating', back_populates='room_rship')

    examroom_rship = relationship('ExamRoom', back_populates='room_rship')
