from API.db import Base
from sqlalchemy import Column, Integer, ForeignKey, Date, String
from sqlalchemy.orm import relationship
from datetime import datetime

class CourseAllocation(Base):
    __tablename__ = 'courseallocation'

    ID = Column(Integer, primary_key=True)
    TeacherID = Column(Integer, ForeignKey('teacher.ID'), nullable=False)
    OfferingID = Column(Integer, ForeignKey('courseoffering.ID'), nullable=False)
    SECTION = Column(Integer, ForeignKey('section.ID'))
    AllocationDate = Column(Date, default=datetime.utcnow)
    status = Column(String(20))

    # Previous Relationships
    teacher_rship = relationship('Teacher', back_populates='allocation_rship')
    offering_rship = relationship('CourseOffering', back_populates='allocation_rship')
    section_rship = relationship('Section', back_populates='allocation_rship')

    # NEW Relationship
    # exam_rship = relationship('Exam', back_populates='allocation_rship') #