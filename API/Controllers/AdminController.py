
from sqlalchemy.orm import Session
from fastapi import UploadFile 
from Models import (CourseAllocation, CourseEnrollment, CourseOffering, Course)
from io import BytesIO
import pandas as pd

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
            return AdminController.makeAllocation(excel_file, db)
    
    @staticmethod
    def makeAllocation(excelFile: BytesIO, db:Session):
        
        df = pd.read_excel(excelFile)
        row, columns = df.shape
        
        fileContent = []

        for i in range(row):
            fileContent.append(df.iloc[i].to_dict())
        
        for i in fileContent:
            
            new_all = CourseOffering()
            
            for key, values in i.items():
                if key == 'Section':
                    
                    part1, part2 = values.split('-')
                    if part1.startswith('BAI'):
                        semester = part2[:-1]
                        new_all.Semester = semester
                        new_all.DEPARTMENT = 3 # type: ignore
                        section = part2[-1]
                        
                        print(f"semester: {semester}, section: {section}")
                        
                if key == 'Course Code':
                    courseId = db.query(Course.ID).filter(Course.COURSE_CODE == values).first()
                    new_all.CourseID = courseId[0] #type: ignore
                    print(f"Fetched Course id: {courseId[0]} for course {values}") #type: ignore
                
        return fileContent
    