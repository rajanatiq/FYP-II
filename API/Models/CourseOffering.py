from API.db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column


class CourseOffering(Base):
    __tablename__ = 'courseoffering'

    ID = Column(Integer, primary_key=True)
    CourseID = Column(Integer, ForeignKey('course.ID'), nullable=False)
    Semester = Column(Integer, nullable=False)
    DEPARTMENT = Column(Integer, ForeignKey('department.ID'))
    Year: Mapped[int] = mapped_column()
    SESSION : Mapped[str] = mapped_column(String())

    # Relationships
    course_rship = relationship('Course', back_populates='offering_rship')
    department_rship = relationship('Department', back_populates='offering_rship')
    
    # Downstream relationships (Enrollments/Allocations)
    enrollment_rship = relationship('CourseEnrollment', back_populates='offering_rship')
    allocation_rship = relationship('CourseAllocation', back_populates='offering_rship')