# Models/teacherroomassignment.py
from db import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship


class TeacherRoomAssignment(Base):
    __tablename__ = 'teacherroomassignment'

    ID = Column(Integer, primary_key=True, autoincrement=True)
    TeacherID = Column(Integer, ForeignKey('teacher.ID'), nullable=False)
    ExamRoomID = Column(Integer, ForeignKey('examroom.ID'), nullable=False)

    # Relationships
    examroom_rship = relationship('ExamRoom', back_populates='teacher_assignments')
    teacher_rship = relationship('Teacher', back_populates='teacherroom_rship')
