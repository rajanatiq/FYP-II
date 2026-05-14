from API.db import Base
from sqlalchemy import Column, Integer, String 
from sqlalchemy.orm import relationship

class Course(Base):
    __tablename__ = 'course'

    ID = Column(Integer, primary_key=True)
    COURSE_CODE = Column(String(9), nullable=False)
    CATEGORY = Column(String(20), nullable=False)
    CREDIT_HRS = Column(Integer, nullable=False)
    Title = Column(String(50))

    # One Course can have many Offerings
    offering_rship = relationship('CourseOffering', back_populates='course_rship')