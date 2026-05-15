# Models/studentseating.py
from db import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

class StudentSeating(Base):
    __tablename__ = "studentseating"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    studentid = Column(Integer, ForeignKey('student.StudentID'), nullable=False)
    roomid = Column(Integer, ForeignKey('room.ID'), nullable=False)
    examid = Column(Integer, ForeignKey('exam.ID'), nullable=False)
    rownumber = Column(Integer, nullable=False)
    seatnumber = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint('roomid', 'examid', 'rownumber', 'seatnumber', name='uq_room_exam_row_seat'),)

    student_rship = relationship('Student', back_populates='seatings_rship')
    room_rship = relationship('Room', back_populates='student_seatings')
    exam_rship = relationship('Exam', back_populates='student_seatings')
