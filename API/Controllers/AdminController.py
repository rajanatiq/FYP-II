
from sqlalchemy.orm import Session
from fastapi import UploadFile 
from Models import (CourseAllocation, CourseEnrollment, CourseOffering, Course, Teacher, Users, Section)
from io import BytesIO
import pandas as pd
from datetime import datetime
from sqlalchemy import func, extract

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
    
        print(f'File received: {file.filename}')
        if file.filename.split(".")[-1] == "xlsx": #type: ignore
            return  AdminController.makeAllocation(excel_file, db)

        print("Unsupported file format")
        return {"error": "Unsupported file format. Please upload an Excel file with .xlsx extension."}
            
            
    @staticmethod
    def makeAllocation(excelFile: BytesIO, db:Session):
        
        df = pd.read_excel(excelFile)
        print(df)
        rows, columns = df.shape
        
        fileContent = []
        offeringList = []
        allocationList = []
        
        offeringId = 0
        sectionId = 0
        
        month = AdminController.getCurrentMonth()
        
        session = 'spring' if 1 <= month <=8 else "fall"
        
        # coursesAlreadyInOffering = AdminController.getAllCourseOfferingID(db, AdminController.getCurrentYear(), session)
        
        if rows == 0:
            print("excel is empty")
            return {'error': 'Excel file is empty'}
        
        
        for i in range(rows):
            
            row = df.iloc[i]
            
            if not row.isnull().all():
                fileContent.append(df.iloc[i].to_dict())
        
        # AdminController.setCourseAllocationStaut(db)
        
        try:
            for i in fileContent:
                
                courseCode = i.get('Course Code')
                
                courseId = db.query(Course.ID).filter(Course.COURSE_CODE == courseCode).scalar()
               
                section = i.get('Section')
                part1, part2 = section.split('-')
                semester = part2[:-1]
                
                if not courseId:
                    new_course = AdminController.addNewCourse(courseCode, i.get('Teacher Name'), db)
                    courseId = new_course.ID
                    
                courseExists = db.query(CourseOffering).filter(
                    CourseOffering.CourseID == courseId, 
                    CourseOffering.Year == AdminController.getCurrentYear(),
                    CourseOffering.SESSION == session,
                    CourseOffering.Semester == semester
                ).first() # type: ignore
            
                #  Checking if course has already been added in the Coures Offering or not. If not then add in Course Offering. 
                if not courseExists:
                    
                    new_off = CourseOffering()
                    new_off.Year = AdminController.getCurrentYear()
                    month = AdminController.getCurrentMonth()
                    
                    if 1<= month <=8:
                        new_off.SESSION = "Spring"
                    else:
                        new_off.SESSION = "Fall"
                        
                    if part1.startswith('BAI'):
                        new_off.DEPARTMENT = 3  # type:ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    elif part1.startswith('BSCS'):
                        new_off.DEPARTMENT = 1  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    elif part1.startswith('BSSE'):
                        new_off.DEPARTMENT = 2  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    # semester = part2[:-1]
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
                    
                    # print(f'Course {courseCode} added in course offering with Id: {offeringId}')
                    
                # else:
                #     print(f'Course {courseCode} already exists in course offering having Id: {courseExists.ID}')
                
                if offeringId == 0: #type: ignore
                    offeringId = courseExists.ID # type: ignore
                
                
                teacherName = i.get('Teacher Name')
                teacherId = AdminController.fetchTeacherId(teacherName, db)
                
                if teacherId != 0:
                    print(f'Teacher ID: {teacherId}')
                    
                    if sectionId == 0:
                        sectionId = AdminController.getSectionID(i.get('Section'), db)

                    courseAlreadyAllocated = db.query(CourseAllocation).filter(
                        CourseAllocation.OfferingID == offeringId, 
                        CourseAllocation.SECTION == sectionId,
                        CourseAllocation.TeacherID == teacherId, 
                        extract('year', CourseAllocation.AllocationDate) == AdminController.getCurrentYear(), 
                    ).first() # type: ignore
                    
                    if not courseAlreadyAllocated:
                         
                        new_all = CourseAllocation(
                            TeacherID = teacherId,
                            OfferingID = offeringId,
                            SECTION = sectionId,
                            AllocationDate = AdminController.getCurrentDate(),
                            status = 'allocated'
                        )
                        # Add in DB
                        db.add(new_all)
                        db.commit()
                        db.refresh(new_all)
                        
                        allocationList.append(new_all)
                            
                        # print(f'Teacher {teacherName} allocated to course {courseCode} in section {i.get("Section")} with offering Id: {offeringId} ')
                    # else:
                    #     db.query(CourseAllocation).filter(CourseAllocation.ID == courseAlreadyAllocated.ID).update({CourseAllocation.status: 'allocated'})
                    #     print(f'Teacher {teacherName} is already allocated to course {courseCode} in section {i.get("Section")} with offering Id: {offeringId}')
                        
                # else:
                #     print(f'No Teacher Id found against Teacher {teacherName}')
                
                offeringId = 0
                sectionId = 0
                
            print('new allocation added in the list.. ')
                
            print(f'----------------------------------------------------')
            print(f'----------------------------------------------------')
            for all in allocationList:
                print(f'offering Id: {all.OfferingID}, SectionId: {all.SECTION}, teacher ID: {all.TeacherID}')
                
            print(f'----------------------------------------------------')
            print(f'----------------------------------------------------')
        
        except Exception as e:
            db.rollback()
            
            return {"error": f"Database error: {str(e)}. Please upload file again."}
        
        return  { 'success' : f'Total {len(allocationList)} allocations have been made successfully.'}
        # return fileContent
    
    @staticmethod
    def fetchTeacherId(teacherName: str, db):
        record = db.query(
            Teacher.ID
        ).join(
            Users, Teacher.userID == Users.ID
        ).filter(
            Users.Name.like(f'%{teacherName}%')
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
    

    @staticmethod
    def getAllCourseOfferingID(db: Session, year: int, session: str):
        allcourses = db.query(CourseOffering.ID).filter(CourseOffering.Year == year, CourseOffering.SESSION == session).all()
        return [
            i[0] for i in allcourses
        ]
        
    @staticmethod
    def setCourseAllocationStaut(db: Session):
        db.query(CourseAllocation).update({CourseAllocation.status: 'completed'})
        return