
from sqlalchemy.orm import Session
from fastapi import UploadFile 
from Models import (CourseAllocation, CourseEnrollment, CourseOffering, Course, Teacher, Users, Section, Student, Department)
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
    async def StudentEnrollment(file: UploadFile, db: Session):
        content = await file.read()
        
        excel_file = BytesIO(content)

        if file.filename.split(".")[-1] == "xlsx": #type: ignore
            return AdminController.makeEnrollment(excel_file, db)
        

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
    def makeEnrollment(excelFile:BytesIO, db: Session):
        
        df = pd.read_excel(excelFile)
        rows, columns = df.shape
        
        error_list = []
        
        filecontent = []
        
        if rows == 0:
            return {'error': 'Excel file is empty'}
        
        for i in range(rows):
            
            row = df.iloc[i]
            
            if not row.isnull().all():
                filecontent.append(df.iloc[i].to_dict())
                
        try:
            for i in filecontent: 
                course_code = i.get('Course Code')
                enrollment_session = i.get('Session')
                arid_no = i.get('Arid No')
                year = i.get('Enrollment Year')
                
                courseId = db.query(Course.ID).filter(Course.COURSE_CODE == course_code).scalar()
                
                
                std_departmentId = db.query(Department.ID).join(
                    Section, Section.department == Department.ID    
                ).join(
                    Student, Student.Section == Section.ID
                ).join(
                    Users, Users.ID == Student.userID
                ).filter(
                    Users.identity_no == arid_no
                ).scalar()
                
                std_semester = db.query(Student.semester).join(
                    Users, Users.ID == Student.userID
                ).filter(
                    Users.identity_no == arid_no    
                ).scalar()
                
                stdId = db.query(Student.StudentID).join(
                    Users, Users.ID == Student.userID    
                ).filter(
                    Users.identity_no == arid_no
                ).scalar()
                
                if std_departmentId and std_semester and stdId:
                    # print(f'Student Id: {stdId}, Student dep ID: {std_departmentId}, Student Semester: {std_semester}, Course Id: {courseId}, year: {year}, session: {enrollment_session}')
                    
                    isCourseOffered = db.query(CourseOffering.ID).filter(
                        CourseOffering.DEPARTMENT == std_departmentId, 
                        CourseOffering.Semester == std_semester,
                        CourseOffering.CourseID == courseId,
                        CourseOffering.Year == year,
                        CourseOffering.SESSION == enrollment_session 
                    ).scalar()
                    
                    if isCourseOffered:
                        
                        offeringId = isCourseOffered
                        
                        isAlreadyEnrolled = db.query(CourseEnrollment.ID).filter(
                            CourseEnrollment.OfferingID == offeringId
                        ).scalar()
                        
                        if not isAlreadyEnrolled:
                            new_enrl = CourseEnrollment(
                                StudentID = stdId,
                                OfferingID = isCourseOffered, 
                                EnrollmentDate = AdminController.getCurrentDate()
                            )
                            
                            # db.add(new_enrl)
                            # db.commit()
                            # db.refresh(new_enrl)
                            
                            print(f'new enrollment added for course {course_code} against student {stdId} having enrollment id {new_enrl.ID}')
                        else:
                            error_list.append(f'Coures {course_code} already enrolled for studnet {stdId} with enrollment id {isAlreadyEnrolled}')
                            print(f'Coures {course_code} already enrolled for studnet {stdId} with enrollment id {isAlreadyEnrolled}')
                        
                else:
                    if not courseId:
                        error_list.append(f'No course found having coures code {course_code}')
                        
                    if not std_departmentId:
                        error_list.append(f'Student department or section mismatched')
                     
                    if not std_semester:
                        error_list.append(f'Student semseter not found')
                        
                    if not stdId:
                        error_list.append(f'No Student Id found for arid no {arid_no}')
                        
                    
        except Exception as e:
            return {"error": f"Database error: {str(e)}. Please upload file again."}
               
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
        
        # AdminController.setCourseAllocationStauts(db)
        
        try:
            for i in fileContent:
                
                courseCode = i.get('Course Code')
                
                courseId = db.query(Course.ID).filter(Course.COURSE_CODE == courseCode).scalar()
               
                section = i.get('Section')
                part1, part2 = section.split('-')
                semester = part2[:-1]
                
                
                department = 3 if part1.startswith('BAI') else 1 if part1.startswith('BSCS') else 2
                    
                courseOffered = db.query(CourseOffering).filter(
                    CourseOffering.CourseID == courseId, 
                    CourseOffering.Year == AdminController.getCurrentYear(),
                    CourseOffering.SESSION == session,
                    CourseOffering.Semester == semester,
                    CourseOffering.DEPARTMENT == department
                ).first() # type: ignore
            
                #  Checking if course has already been added in the Coures Offering or not. If not then add in Course Offering. 
                if not courseOffered:
                    
                    new_off = CourseOffering()
                    new_off.Year = AdminController.getCurrentYear()
                    month = AdminController.getCurrentMonth()
                    
                    if 1<= month <=8:
                        new_off.SESSION = "Spring"
                    else:
                        new_off.SESSION = "Fall"
                      
                    new_off.DEPARTMENT = department # type: ignore  
                    # if part1.startswith('BAI'):
                    #     new_off.DEPARTMENT = 3  # type:ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    # elif part1.startswith('BSCS'):
                    #     new_off.DEPARTMENT = 1  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    # elif part1.startswith('BSSE'):
                    #     new_off.DEPARTMENT = 2  # type: ignore (1 for CS, 2 for SE, 3 for AI)
                        
                    # semester = part2[:-1]
                    new_off.Semester = semester
                    
                    section = part2[-1]
                    
                    sectionId = db.query(Section.ID).filter(
                        Section.department == new_off.DEPARTMENT, 
                        Section.name == section
                    ).first()[0] # type: ignore
                    
                    new_off.CourseID = courseId #type: ignore
                    
                    # db.add(new_off)
                    # db.commit()
                    # db.refresh(new_off)
                    
                    offeringList.append(new_off)
                    offeringId = new_off.ID
                    
                    print(f'Course {courseCode} added in course offering with Id: {offeringId} for department {department}')
                    
                else:
                    print(f'Course {courseCode}, for department: {department} already exists in course offering having Id: {courseOffered.ID}')
                
                if offeringId == 0: #type: ignore
                    offeringId = courseOffered.ID # type: ignore
                
                
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
                        # # Add in DB
                        # db.add(new_all)
                        # db.commit()
                        # db.refresh(new_all)
                        
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
    def setCourseAllocationStauts(db: Session):
        db.query(CourseAllocation).update({CourseAllocation.status: 'completed'})
        return
    
    @staticmethod 
    def setCourseEnrollmentStatus(db: Session):
        db.query(CourseEnrollment).update({CourseEnrollment.Status: 'Completed'})
        
    @staticmethod
    def updateStudentSemester(db: Session):
        return