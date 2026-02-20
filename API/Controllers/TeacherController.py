from sqlalchemy.orm import Session
# import Models
from Models import (CourseAllocation,CourseOffering, Course, Teacher, Users)


class TeacherController:
    
    @staticmethod
    def course_allocation_id(course_id: int, teacher_id: int, db: Session):
        try:
            allocation = db.query(
                CourseAllocation.ID.label("ID")
            ).join(CourseOffering, CourseOffering.ID == CourseAllocation.OfferingID).\
                join(Course, Course.ID == CourseOffering.CourseID).\
                join(Teacher, Teacher.ID == CourseAllocation.TeacherID).\
                join(Users, Users.ID == Teacher.userID).\
                filter(Course.ID == course_id, Teacher.ID == teacher_id).first()

            if allocation:
                return {"CourseAllocationID": allocation[0]}
            else:
                return {"message": "No allocation found for this course and teacher"}

        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500


# select CA.ID from CourseOffering CF
# JOIN CourseAllocation CA on CA.OfferingID = Cf.ID
# JOIN Course C on c.ID = CF.CourseID
# JOIN Teacher T on T.ID = CA.TeacherID
# JOIN Users U on T.userID = U.ID
# where C.ID = 1 and T.ID = 1