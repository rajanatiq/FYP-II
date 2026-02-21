from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime
from fastapi.responses import JSONResponse

# import Models
from Models import (Exam,CourseAllocation,CourseOffering, Course, Teacher, Users, Section, Department)



class TeacherController:
    
    @staticmethod
    def teacherAllocatedCourses(t_id: int, session: str ,db:Session):
        current_year = datetime.now().year
        try:
            result = db.query(
                CourseAllocation.ID.label('allocationID'), 
                CourseOffering.ID.label('offeringID'),
                Course.ID.label('courseID'),
                Section.ID.label('sectionID'),
                Section.name.label('section'),
                Department.name.label('depName'),
                Course.COURSE_CODE.label('courseCode'),
                Course.Title.label('courseTitle'),
                CourseOffering.Semester.label('semester'),
                func.year(CourseAllocation.AllocationDate)
            ).join(
                CourseOffering, CourseOffering.ID == CourseAllocation.ID
            ).join(
                Course, Course.ID == CourseOffering.CourseID
            ).join(
                Section, Section.ID == CourseAllocation.SECTION
            ).join(
                Teacher, Teacher.ID == CourseAllocation.TeacherID
            ).join(
                Department, Department.ID == CourseOffering.DEPARTMENT
            ).join(
                Users, Users.ID == Teacher.userID
            ).filter(
                Teacher.ID == t_id, 
                extract('year', CourseAllocation.AllocationDate) == current_year, 
                CourseOffering.SESSION == session
            ).all()
            
            if not result:
                return {'error': 'no courses found'}
            else:
                courses = [
                    {
                        'allocationID': row.allocationID,
                        'offeringID': row.offeringID,
                        'courseID': row.courseID, 
                        'sectionID': row.sectionID,
                        'department': row.depName,
                        'section': row.section,
                        'semester': row.semester,
                        'coruseCode': row.courseCode,
                        'courseTitle': row.courseTitle
                    }
                for row in result   
                ]
                return courses
        except Exception as e:
            return {'error': f"Database Error: {str(e)}"}
    
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

    @staticmethod
    def fetch_allocated_courses_exams(teacher_id: int , db:Session):
        db.query( Exam.ID.label("examID"),
                  Exam.TITLE.label('examTitle'),
                  Exam.STATUS.label('examStatus')
                 ).join(CourseAllocation, CourseAllocation.ID==Exam.A_ID
                 ).join(CourseOffering, CourseOffering.ID==CourseAllocation.OfferingID
                 ).join(Teacher, Teacher.ID==CourseAllocation.TeacherID
                 ).join(Course, Course.ID==CourseAllocation.CourseID
                 ).filter(
            Teacher.ID == teacher_id
        ).all()







# select CA.ID from CourseOffering CF
# JOIN CourseAllocation CA on CA.OfferingID = Cf.ID
# JOIN Course C on c.ID = CF.CourseID
# JOIN Teacher T on T.ID = CA.TeacherID
# JOIN Users U on T.userID = U.ID
# where C.ID = 1 and T.ID = 1