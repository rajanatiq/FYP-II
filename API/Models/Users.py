from db import Base
from sqlalchemy import Column, Integer, String, Date, LargeBinary
from sqlalchemy.orm import relationship

class Users(Base):
    __tablename__ = 'users'

    ID = Column(Integer, primary_key=True)
    Name = Column(String(100), nullable=False)
    Gender = Column(String(20), nullable=False)
    DateOfBirth = Column(Date, nullable=False)
    Email = Column(String(150), unique=True, nullable=False)
    PhoneNumber = Column(String(20), nullable=False)
    Role = Column(String(50), nullable=False)
    profile_image = Column(String, nullable=False)  # Maps to VARBINARY(MAX)
    image_embedding = Column(LargeBinary, nullable=False)  # Maps to VARBINARY(MAX)
    identity_no = Column(String(10), nullable=False)

    # Relationship: User <-> Student
    # uselist=False implies a One-to-One relationship (One User has One Student Profile)
    student_rship = relationship('Student', back_populates='user_rship', uselist=False)
    teacher_rship = relationship('Teacher', back_populates='user_rship',  uselist=False)

    def to_dict(user):
        return {
            "ID": user.ID,
            "Name": user.Name,
            "Gender": user.Gender,
            "DateOfBirth": user.DateOfBirth.isoformat() if user.DateOfBirth else None,
            "Email": user.Email,
            "PhoneNumber": user.PhoneNumber,
            "Role": user.Role,
           }