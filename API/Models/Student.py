from db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship


class Student(Base):
    __tablename__ = 'student'

    StudentID = Column(Integer, primary_key=True)
    userID = Column(Integer, ForeignKey('users.ID'))
    CGPA = Column(Float)
    Section = Column(Integer, ForeignKey('section.ID'))
    Intake = Column(String(20))
    YEAR = Column(Integer)

    # Previous Relationships
    user_rship = relationship('Users', back_populates='student_rship')
    section_rship = relationship('Section', back_populates='student_rship')
    enrollment_rship = relationship('CourseEnrollment', back_populates='student_rship')

    # NEW Relationships (Exam & Proctoring)
    proctoring_rship = relationship('ProctoringEvent', back_populates='student_rship') #
    seatings_rship = relationship('StudentSeating', back_populates='student_rship')

    break_rship = relationship('StudentBreak', back_populates='student_rship')


    def to_dict(self):
        return {
            "StudentID": self.StudentID,
            "userID": self.userID,
            "CGPA": self.CGPA,
            "Intake": self.Intake,
            "YEAR": self.YEAR
        }
        
        
        
#  Query to calculate the current semseter of a student based on intake and year. 

# SELECT 
#     StudentID,
#     intake,
#     [YEAR],

#     (
#         (YEAR(GETDATE()) - [YEAR]) * 2
#         +
#         (
#             CASE 
#                 WHEN MONTH(GETDATE()) BETWEEN 1 AND 8 THEN 1   -- Spring
#                 WHEN MONTH(GETDATE()) BETWEEN 9 AND 12 THEN 2  -- Fall
#             END
#             -
#             CASE 
#                 WHEN intake = 'spring' THEN 1
#                 WHEN intake = 'fall' THEN 2
#             END
#         )
#         + 1
#     ) AS current_semester

# FROM Student