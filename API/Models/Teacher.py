from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Teacher(Base):
    __tablename__ = 'teacher'

    ID = Column(Integer, primary_key = True)
    userID = Column(Integer, ForeignKey('users.ID'))

    
    Deignation = Column(String(30))
    experience_in_years = Column(Integer)
    qualification = Column(String(30))

    user_rship = relationship('Users', back_populates='teacher_rship')
    allocation_rship = relationship('CourseAllocation', back_populates='teacher_rship')
    # room_assignments_rship = relationship('TeacherRoomAssignment', back_populates='teacher_rship')

    break_rship = relationship('StudentBreak', back_populates='teacher_rship')
    teacherroom_rship = relationship('TeacherRoomAssignment', back_populates='teacher_rship')


