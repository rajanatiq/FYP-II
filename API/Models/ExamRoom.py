from db import Base
from sqlalchemy import Column, Integer, ForeignKey, Date, Time
from sqlalchemy.orm import relationship

class ExamRoom(Base):
    __tablename__ = 'examroom'

    ID = Column(Integer, primary_key=True, autoincrement=True)
    ExamID = Column(Integer, ForeignKey('exam.ID'), nullable=False)
    RoomID = Column(Integer, ForeignKey('room.ID'), nullable=False)
    E_Date = Column(Date, nullable=False)
    E_Time = Column(Time, nullable=False)

    # Relationships
    exam_rship = relationship('Exam', back_populates='examroom_rship')
    room_rship = relationship('Room', back_populates='examroom_rship')
    teacher_assignments = relationship('TeacherRoomAssignment', back_populates='examroom_rship')
