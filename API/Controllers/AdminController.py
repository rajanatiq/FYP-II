
from sqlalchemy.orm import Session
from fastapi import UploadFile 
from Models import (CourseAllocation, CourseEnrollment, CourseOffering, Course, Teacher, Users, Section)
from io import BytesIO
import pandas as pd
from datetime import datetime

class AdminController:
    @staticmethod
    async def offer_course(file: UploadFile, db: Session):
        import pandas as pd
        from io import BytesIO
        content = await file.read()

        excel_file = BytesIO(content)

        df = pd.read_excel(excel_file)

        for _, item in df.iterrows():
                new_offering = CourseOffering(
                    CourseID=item["CourseID"],
                    Semester=item["Semester"],
                    DEPARTMENT=item.get("DEPARTMENT"),  # optional column
                    Year=item["Year"],
                    SESSION=item.get("SESSION")          # optional column
                )
                try:
                    db.add(new_offering)
                    db.commit()
                except Exception as e:
                    db.rollback()  # rollback the failed insert
                    return {"error": f"Database error: {str(e)}"}, 500

        return {"message": "Data inserted successfully"}

    @staticmethod
    async def add_enrollment(file: UploadFile, db: Session):
        import pandas as pd
        from io import BytesIO
        content = await file.read()

        excel_file = BytesIO(content)

        df = pd.read_excel(excel_file)

        for _, item in df.iterrows():
            new_enrollment = CourseEnrollment(
                StudentID = item["StudentID"],
                OfferingID = item["OfferingID"], 
                EnrollmentDate = item["EnrollmentDate"],
                Status = item["Status"]
            )
            try:
                db.add(new_enrollment)
                db.commit()
            except Exception as e:
                return {"error": f"Database error: {str(e)}"}, 500

        return {"message": "Data inserted successfully"}

    @staticmethod
    async def TeacherAllocation(file: UploadFile, db: Session):
        
        content = await file.read()

        excel_file = BytesIO(content)
    
        if file.filename.split(".")[-1] == "xlsx": #type: ignore
            courseOffering =  AdminController.makeOffering(excel_file, db)
            
            print(f'Total {len(courseOffering)} has been added. ')
            return [
                {
                    'offeringId': course.ID,
                    'CourseId' : course.CourseID,
                    'Semester': course.Semester,
                    "Department":  course.DEPARTMENT,
                    "Year": course.Year,
                    "Session": course.SESSION
                }
                for course in courseOffering
            ]
    @staticmethod
    
    def makeOffering(excelFile: BytesIO, db:Session):
        
        df = pd.read_excel(excelFile)
        row, columns = df.shape
        
        fileContent = []
        offeringList = []
        allocationList = []
        
        offeringId = 0
        sectionId = 0
        
        for i in range(row):
            fileContent.append(df.iloc[i].to_dict())
        
        for i in fileContent:
            
            courseCode = i.get('Course Code')
            
            courseId = db.query(Course.ID).filter(Course.COURSE_CODE == courseCode).scalar()
            
            if not courseId:
                new_course = AdminController.addNewCourse(courseCode, i.get('Teacher Name'), db)
                courseId = new_course.ID
                
            courseExists = db.query(CourseOffering).filter(CourseOffering.CourseID == courseId).first() # type: ignore
        
            #  Checking if course has already been added in the Coures Offering or not. If not then add in Course Offering. 
            if not courseExists:
                
                new_off = CourseOffering()
                new_off.Year = AdminController.getCurrentYear()
                month = AdminController.getCurrentMonth()
                
                if 1<= month <=8:
                    new_off.SESSION = "Spring"
                else:
                    new_off.SESSION = "Fall"
                    
                section = i.get('Section')
                    
                part1, part2 = section.split('-')
                if part1.startswith('BAI'):
                    new_off.DEPARTMENT = 3  # type:ignore (1 for CS, 2 for SE, 3 for AI)
                    
                elif part1.startswith('BSCS'):
                    new_off.DEPARTMENT = 1  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                    
                elif part1.startswith('BSSE'):
                    new_off.DEPARTMENT = 2  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                    
                semester = part2[:-1]
                new_off.Semester = semester
                
                section = part2[-1]
                
                sectionId = db.query(Section.ID).filter(
                    Section.department == new_off.DEPARTMENT, 
                    Section.name == section
                ).first()[0] # type: ignore
                
                new_off.CourseID = courseId #type: ignore
                
                db.add(new_off)
                db.commit()
                db.refresh(new_off)
                
                offeringList.append(new_off)
                offeringId = new_off.ID
                
            else:
                print(f'Course {courseCode} already exists in course offering having Id: {courseExists.ID}')
            
            if offeringId == 0: #type: ignore
                offeringId = courseExists.ID # type: ignore
            
            teacherName = i.get('Teacher Name')
            teacherId = AdminController.fetchTeacherId(teacherName, db)
            
            if teacherId != 0:
                print(f'Teacher ID: {teacherId}')
                
                if sectionId == 0:
                    sectionId = AdminController.getSectionID(i.get('Section'), db)

                new_all = CourseAllocation(
                    TeacherID = teacherId,
                    OfferingID = offeringId,
                    SECTION = sectionId,
                    AllocationDate = AdminController.getCurrentDate(),
                    status = 'allocated'
                )
                
                allocationList.append(new_all)
                    
            else:
                print(f'No Teacher Id found against Teacher {teacherName}')
            
            offeringId = 0
            sectionId = 0
            
        print(f'----------------------------------------------------')
        print(f'----------------------------------------------------')
        for all in allocationList:
            print(f'offering Id: {all.OfferingID}, SectionId: {all.SECTION}, teacher ID: {all.TeacherID}')
            
        print(f'----------------------------------------------------')
        print(f'----------------------------------------------------')
        
        return offeringList
        # return fileContent
    
    @staticmethod
    def fetchTeacherId(teacherName: str, db):
        record = db.query(
            Teacher.ID
        ).join(
            Users, Teacher.userID == Users.ID
        ).filter(
            Users.Name == teacherName
        ).first()
        
        return record[0] if record else 0
        

    @staticmethod
    def getSectionID(section: str, db: Session):
        part1, part2 = section.split('-')
        section = part2[-1]
        
        dep = 3 if part1.startswith('BAI') else 1 if part1.startswith('BSCS') else 2
        
        return db.query(Section.ID).filter(
            Section.department == dep, 
            Section.name == section
        ).first()[0] # type: ignore
        
    @staticmethod
    def addNewCourse(courseCode: str, teacherName: str, db: Session): 
        new_course = Course(
                    COURSE_CODE = courseCode,
                    CATEGORY = 'Core',
                    CREDIT_HRS = '3', 
                    Title = teacherName
                )
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        
        return new_course 
    
    @staticmethod
    def getCurrentYear():
        return datetime.now().year
    
    @staticmethod
    def getCurrentMonth():
        return datetime.now().month
    
    @staticmethod
    def getCurrentDate():
        return datetime.now()