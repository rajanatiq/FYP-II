from db import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

class Department(Base):
    __tablename__ = "department"
    ID = Column(Integer, primary_key = True)
    name = Column(String(2))

    section_rship = relationship('Section', back_populates = 'department_rship')
    offering_rship = relationship('CourseOffering', back_populates='department_rship')
