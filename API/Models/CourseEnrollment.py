from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from datetime import datetime  
from sqlalchemy.orm import relationship

class CourseEnrollment(Base):
    __tablename__ = 'courseenrollment'

    ID = Column(Integer, primary_key=True)
    StudentID = Column(Integer, ForeignKey('student.StudentID'), nullable=False)
    OfferingID = Column(Integer, ForeignKey('courseoffering.ID'), nullable=False)
    EnrollmentDate = Column(Date, default=datetime.utcnow)
    Status = Column(String(20), default='Enrolled')

    # Relationships
    student_rship = relationship('Student', back_populates='enrollment_rship')
    offering_rship = relationship('CourseOffering', back_populates='enrollment_rship')