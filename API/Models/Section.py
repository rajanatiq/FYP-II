from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Section(Base):
    __tablename__ = "section"
    ID = Column(Integer, primary_key=True)
    name = Column(String(7))
    department = Column(Integer, ForeignKey('department.ID'))

    student_rship = relationship('Student', back_populates='section_rship')
    department_rship = relationship('Department', back_populates='section_rship')
    allocation_rship = relationship('CourseAllocation', back_populates='section_rship')