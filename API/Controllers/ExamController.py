from typing import List

from Schemas.SaveMcqAns import SaveMcqAns
from API.Models import (ExamAttempt, MCQOption, ExamDescQues, ExamMCQ, Exam, MCQAns)
# from Models import MCQOption
# from Models import ExamDescQues
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
# from Models.Exam import Exam
from API.Schemas.ExamCreate import ExamCreate
from API.Schemas.ExamMcqCreate import ExamMCQCreate, MCQOptionCreate
from API.Schemas.AttemptedExam import AttemptedExam
# from Models.ExamMCQ import ExamMCQ

class ExamController:
    @staticmethod
    def fetch_mcqs(db: Session, exam_id: int):
        '''Method to fetch the mcq's of the exam for a particular exam. '''
        
        rows = db.query(
            ExamMCQ.ID.label("mcqID"),
            ExamMCQ.DESCRIPTION.label("question"),
            MCQOption.ID.label("optionID"),
            MCQOption.OPTION_TEXT.label("optionText"),
            MCQOption.IS_CORRECT.label("isCorrect")
        ).join(
            MCQOption, ExamMCQ.ID == MCQOption.M_ID
        ).filter(
            ExamMCQ.E_ID == exam_id
        ).all()

        if not rows:
            return JSONResponse(content={"content": []}, status_code=404)

        mcq_map = {}

        for row in rows:
            if row.mcqID not in mcq_map:
                mcq_map[row.mcqID] = {
                    "mcqID": row.mcqID,
                    "question": row.question,
                    "options": []
                }

            mcq_map[row.mcqID]["options"].append({
                "optionID": row.optionID,
                "text": row.optionText,
                "isCorrect": row.isCorrect
            })

        return {
            "content": list(mcq_map.values())
        }
    
    
    @staticmethod
    def fetch_desc_questions(db: Session, exam_id: int):
        '''Method to fetch the descriptive questions of the exam for a particular exam. '''
        
        try:
            rows = db.query(
                ExamDescQues.ID.label('questionId'),
                ExamDescQues.DESCRIPTION.label("question")
            ).join(
                Exam, ExamDescQues.E_ID == Exam.ID
            ).filter(
                Exam.ID == exam_id
            ).all()
            
            if not rows:
                return {'error':  'no questions found for this exam.'}
            
            content = [ 
                    {
                        "questionId": q.questionId,
                        "question": q.question
                    }
                for q in rows ]
            
            return {"content": content}
        except Exception as e:
            return {'error': f'Database error: {e}'}

    @staticmethod
    def create_exam(data: ExamCreate, db: Session):
        new_exam = Exam(
            A_ID=data.A_ID,
            TITLE=data.TITLE,
            TOTAL_QUESTIONS=data.TOTAL_QUESTIONS,
            E_DATE=data.E_DATE,
            timeInMinutes=data.timeInMinutes,
            E_TYPE=data.E_TYPE,
            STATUS=data.STATUS
        )
        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)

        return {"success": f"{new_exam.ID}"}
    
    @staticmethod
    def add_mcqs(mcq_list: List[ExamMCQCreate], db: Session):
        added_mcqs = []
        try:
            for mcq_data in mcq_list:
                # Add MCQ
                new_mcq = ExamMCQ(
                    E_ID=mcq_data.E_ID,
                    DESCRIPTION=mcq_data.DESCRIPTION,
                    MARKS=mcq_data.MARKS
                )
                db.add(new_mcq)
                db.commit()
                db.refresh(new_mcq)

                for opt in mcq_data.options:
                    new_option = MCQOption(
                        M_ID=new_mcq.ID,
                        OPTION_TEXT=opt.OPTION_TEXT,
                        IS_CORRECT=opt.IS_CORRECT
                    )
                    db.add(new_option)
                db.commit()

                added_mcqs.append({
                    "mcq_id": new_mcq.ID,
                    "description": new_mcq.DESCRIPTION
                })

            return {"message": "MCQs added successfully", "added_mcqs": added_mcqs}

        except Exception as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}, 500
        
    @staticmethod
    def update_exam_details(exam_id: int, data: dict, db: Session):
        exam = db.query(Exam).filter(Exam.ID == exam_id).first()
        if not exam:
            return {"error": "Exam record not found"}
        if 'a_id' in data:
            exam.A_ID = data['a_id']
        if 'title' in data:
            exam.TITLE = data['title']
        if 'total_questions' in data:
            exam.TOTAL_QUESTIONS = data['total_questions']
        if 'e_date' in data:
            exam.E_DATE = data['e_date']
        if 'start_time' in data:
            exam.START_TIME = data['start_time']
        if 'end_time' in data:
            exam.END_TIME = data['end_time']
        if 'e_type' in data:
            exam.E_TYPE = data['e_type']
        if 'status' in data:
            exam.STATUS = data['status']
        try:
            db.commit()
            return {"message": "Exam updated successfully", "exam_id": exam_id}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}, 500

    @staticmethod
    def remove_exam(exam_id: int, db: Session):
        examMcq = db.query(ExamMCQ).filter(ExamMCQ.E_ID == exam_id).all()
        if examMcq: 
            try:
                for row in examMcq:
                    if row.option_rship:
                        for opt in row.option_rship:
                            db.delete(opt)
                    db.delete(row)
                db.commit()
            except Exception as e:
                return {"error": "Exam record not found in database"}, 404
            
        examDesc = db.query(ExamDescQues).filter(ExamDescQues.E_ID == exam_id).all()
        if examDesc:
            try:
                for row in examDesc:
                    db.delete(row)
                db.commit()
            except Exception as e:
                return {"error": "Exam record not found in database"}, 404
            
        exam = db.query(Exam).filter(Exam.ID == exam_id).first()

        if not exam:
            return {"error": "Exam record not found in database"}, 404
        try:
            db.delete(exam)
            db.commit()
            return {"message": f"Exam ID {exam_id} deleted successfully"}
        
        except Exception as e:
            return {"error": f"Cannot delete: {str(e)}"}, 500

    @staticmethod
    def addStudentExamEntry(data: AttemptedExam , db:Session):
        """This method is for adding the student entry for the exam in the examattempt table after joining the exam."""
        
        attemptRecord = ExamAttempt(
            studentID= data.s_id,
            examID = data.e_id
        )
        try:
            db.add(attemptRecord)
            db.commit()
            return {"success": True,'attempt_id': attemptRecord.ID}
        except Exception as e:
            db.rollback()
            return {"fail": f"{e}"}
        
    @staticmethod
    def ifExamAlreadyAttempt(data: AttemptedExam, db:Session):
        """method to check if student has already attempted his exam or not to prevent duplication"""
        # return {"success": False, 'attempt_id': 7101}
        try:
            print(f"student id: {data.s_id}")
            print(f"Exam id: {data.e_id}")
            
            record = db.query(ExamAttempt).filter(
                ExamAttempt.studentID == data.s_id,
                ExamAttempt.examID == data.e_id
            ).first()
            
            if record:
                print("success")
                return {"success": True, 'attempt_id': record.ID, 'status': record.status}
            else:
                new_record = ExamAttempt(
                    studentID = data.s_id,
                    examID = data.e_id
                )
                db.add(new_record)
                db.commit()
                print(f"false {new_record.ID}")
                return {"success": False, 'attempt_id': new_record.ID}
            
        except Exception as e:
            print(f"error: {e}")
            db.rollback()
            return {"error": "Database error. try again."}
    

    @staticmethod 
    def setExamStatusToComplete(exam_id: int, db: Session):
        '''This is the method to set the pending exam staus to completed.'''
        try:
            exam = db.query(Exam).filter(Exam.ID == exam_id).first()
            if not exam: 
                return {'error': 'no exam found for this exam id.'}
            else:
                exam.STATUS = 'completed'
                db.commit()
                return {'success': True}
        except Exception as e:
            db.rollback()
            return{'error': f'Database error {e}'}
        return
    
    @staticmethod
    def save_mcq_answers(data: List[SaveMcqAns], attempt_id: int, db: Session):
        """Method to save mcq answers of the student against his exam attempt."""
        
        try:
            isExamAttempted = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
            
            if isExamAttempted:
                
                for ans in data:
                    
                    new_ans = MCQAns(
                        M_ID = ans.mcqId,
                        O_ID = ans.optionId,
                        attemptID = attempt_id
                    )
                    
                    db.add(new_ans)
                    db.commit()
                    return {'success': f'exam attempt found, {len(data)} answers to save'}
            else:
                return {'error': 'no exam attempt found for this attempt id.'}
        
        except Exception as e:
            return {'error', f'db error {e}'}
       
        
        
        
    @staticmethod
    def checkBackCamera(attempt_id: int, db: Session):
        """Method to check if student has used back camera during the exam attempt."""
        try:
            attempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
            if not attempt:
                return {'error': 'no exam attempt found for this attempt id.'}
            else:
                return {'success': attempt.back_cam}
        except Exception as e:
            return {'error': f'Database error {e}'}
        
        
    @staticmethod
    def setBackCameraStatus(attempt_id: int, db: Session):
        """Method to set the back camera status to true if student has used back camera during the exam attempt."""
        try:
            attempt = db.query(ExamAttempt).filter(ExamAttempt.ID == attempt_id).first()
            if not attempt:
                return {'error': 'no exam attempt found for this attempt id.'}
            else:
                attempt.back_cam = True
                db.commit()
                return {'success': True}
        except Exception as e:
            return {'error': f'Database error {e}'}