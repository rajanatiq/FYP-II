# Models/studentbreak.py
from db import Base
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class StudentBreak(Base):
    __tablename__ = "studentbreak"

    breakid = Column(Integer, primary_key=True, autoincrement=True)
    studentid = Column(Integer, ForeignKey('student.StudentID'), nullable=False)
    examid = Column(Integer, ForeignKey('exam.ID'), nullable=False)
    teacherid = Column(Integer, ForeignKey('teacher.ID'), nullable=False)
    breakstarttime = Column(DateTime, nullable=False, default=datetime.utcnow)
    breakendtime = Column(DateTime, nullable=True)
    breaktype = Column(String(20), nullable=True)

    student_rship = relationship('Student', back_populates='break_rship')
    exam_rship = relationship('Exam', back_populates='break_rship')
    teacher_rship = relationship('Teacher', back_populates='break_rship')
