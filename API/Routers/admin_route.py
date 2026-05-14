from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from API.db import get_db
from API.Controllers.AdminController import AdminController
router = APIRouter()

@router.post("/upload-course-enrollment/")
async def upload_course(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload Excel file for course enrollment.
    """
    return await AdminController.add_enrollment(file, db)

@router.post("/upload-course-offering/")
async def upload_course_offering(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await AdminController.offer_course(file, db)

@router.post('/uploadAllocation')
async def TeacherAllocation(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await AdminController.TeacherAllocation(file, db)
    
@router.post('/uploadEnrollment')
async def StudentEnrollment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await AdminController.StudentEnrollment(file, db)
    
  