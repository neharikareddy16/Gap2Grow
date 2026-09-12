import os
import json
import hashlib
import datetime
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, Query, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from database import engine, get_db, Base
import models
from ai_service import ai_service

# Auto-create newly defined tables (doubts, live_sessions, faculty_pdfs, etc.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gap2Grow API", description="AI Learning Resource Agent API for Vignan University", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

# ----------------- PYDANTIC SCHEMAS -----------------

class RegisterRequest(BaseModel):
    name: str
    role: str  # STUDENT, FACULTY, REMEDIAL_COORDINATOR, LIBRARY
    identifier: str  # Register No, Faculty ID, Library ID
    email: str
    password: str
    department: Optional[str] = "CSE"
    year: Optional[str] = "2nd Year"
    branch: Optional[str] = "CSE"
    section: Optional[str] = "A"
    college: Optional[str] = "Vignan University"
    skills: Optional[str] = "C, Java, Python"

class LoginRequest(BaseModel):
    role: str
    identifier: str
    password: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    skills: Optional[str] = None

class CreateExamRequest(BaseModel):
    title: str
    subject: str
    department: Optional[str] = "CSE"
    year: Optional[str] = "2nd Year"
    section: Optional[str] = "A"
    examType: Optional[str] = "Diagnostic"  # Diagnostic, Quiz, Mid-Term, Assignment
    durationMinutes: Optional[int] = 30
    totalMarks: Optional[int] = 20
    passingMarks: Optional[int] = 10
    instructions: Optional[str] = "Read all questions carefully."
    questions: List[Dict[str, Any]]
    facultyName: Optional[str] = "Faculty Member"
    facultyId: Optional[str] = "FAC001"
    isPublished: Optional[bool] = False

class ResourceCreateRequest(BaseModel):
    title: str
    type: str  # textbook, nptel, faculty_notes, video, code_repo
    subject: str
    topic: str
    url: Optional[str] = ""
    filePath: Optional[str] = ""
    description: Optional[str] = ""
    uploadedBy: Optional[str] = "Faculty"
    department: Optional[str] = "CSE"
    year: Optional[str] = "2nd Year"

class BookCreateRequest(BaseModel):
    name: str
    author: str
    isbn: Optional[str] = ""
    subject: str
    department: Optional[str] = "CSE"
    category: Optional[str] = "Core"
    publisher: Optional[str] = ""
    edition: Optional[str] = "1st Edition"
    totalCopies: int = 5

class ExamSubmissionRequest(BaseModel):
    studentId: Optional[int] = None
    studentName: str
    studentIdentifier: str
    timeTaken: Optional[str] = "15m"
    answers: Dict[str, str]

class ChatRequest(BaseModel):
    message: str
    userContext: Optional[Dict[str, Any]] = {}
    sessionId: Optional[str] = "default"
    history: Optional[List[Dict[str, str]]] = []


class SimplifyRequest(BaseModel):
    type: str  # youtube, nptel, pdf, notes, text, topic
    content: str
    title: Optional[str] = ""
    topic: Optional[str] = ""

# ----------------- AUTH ROUTES -----------------

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Gap2Grow Learning Resource Agent", "time": datetime.datetime.utcnow().isoformat()}

@app.get("/api/auth/demo-users")
def get_demo_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [u.to_dict() for u in users]

@app.post("/api/auth/register")
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check duplicate email or identifier
    existing_email = db.query(models.User).filter(models.User.email == req.email.strip().lower()).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email ID is already registered.")

    existing_id = db.query(models.User).filter(models.User.identifier == req.identifier.strip()).first()
    if existing_id:
        raise HTTPException(status_code=400, detail="Register Number / ID is already registered.")

    dept = req.branch if req.role == "STUDENT" and req.branch else req.department
    year_str = f"{req.year} Year" if req.role == "STUDENT" and req.year and not req.year.endswith("Year") else (req.year or "2nd Year")

    new_user = models.User(
        name=req.name.strip(),
        role=req.role.strip().upper(),
        identifier=req.identifier.strip(),
        email=req.email.strip().lower(),
        hashed_password=hash_pw(req.password),
        department=dept or "CSE",
        year=year_str,
        section=req.section or "A",
        college=req.college or "Vignan University",
        skills=req.skills or "C, Java, Python"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If student, create initial gap profile
    if new_user.role == "STUDENT":
        initial_gaps = [
            models.StudentGapProfile(
                student_id=new_user.id,
                student_name=new_user.name,
                department=new_user.department,
                subject="Data Structures",
                topic="Binary Trees",
                accuracy_pct=32,
                skill_level="Weak",
                gap_severity="High",
                initial_score=32,
                current_score=78,
                prerequisites="Recursion, Pointers",
                weakness_reason="Recursive call stack frame unwinding in Postorder and Preorder traversals"
            ),
            models.StudentGapProfile(
                student_id=new_user.id,
                student_name=new_user.name,
                department=new_user.department,
                subject="Data Structures",
                topic="Graphs",
                accuracy_pct=20,
                skill_level="Critical Gap",
                gap_severity="Critical",
                initial_score=20,
                current_score=45,
                prerequisites="Queue, Stack",
                weakness_reason="BFS queue state management"
            )
        ]
        db.add_all(initial_gaps)
        db.commit()

    return {
        "success": True,
        "message": "Registration Successful",
        "user": new_user.to_dict()
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    ident = req.identifier.strip()
    target_role = req.role.strip().upper()

    user = db.query(models.User).filter(
        and_(
            models.User.role == target_role,
            or_(
                models.User.email == ident.lower(),
                models.User.identifier == ident
            )
        )
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid Credentials. Account not found for selected role.")

    if user.hashed_password != hash_pw(req.password):
        raise HTTPException(status_code=401, detail="Invalid Credentials. Password does not match.")

    return {
        "success": True,
        "message": "Login Successful",
        "token": f"gap2grow_token_{user.id}_{int(datetime.datetime.utcnow().timestamp())}",
        "user": user.to_dict()
    }

# ----------------- STUDENT ROUTES -----------------

@app.get("/api/student/topic-gaps")
def get_student_topic_gaps(student_name: Optional[str] = "Rahul Kumar", db: Session = Depends(get_db)):
    profiles = db.query(models.StudentGapProfile).filter(models.StudentGapProfile.student_name == student_name).all()
    if not profiles:
        # Fallback to general data
        profiles = db.query(models.StudentGapProfile).limit(4).all()
    return [p.to_dict() for p in profiles]

@app.get("/api/student/learning-path")
def get_student_learning_path(student_name: Optional[str] = "Rahul Kumar", gap_topic: Optional[str] = "Binary Trees"):
    return ai_service.generate_smart_path(student_name, gap_topic)

@app.post("/api/student/diagnostic/submit")
def submit_diagnostic(data: Dict[str, Any] = Body(...)):
    responses = data.get("responses", [])
    analysis = ai_service.analyze_diagnostic(responses)
    return analysis

@app.post("/api/student/practice/submit")
def submit_practice(data: Dict[str, Any] = Body(...)):
    score = data.get("score", 4)
    total = data.get("total", 5)
    pct = round((score / max(total, 1)) * 100)

    # Adaptive feedback
    if pct >= 80:
        feedback = "Great! This gap is nearly closed. Moving you to the next concept (Binary Search Trees & AVL Trees)."
        status_msg = "Gap Closed"
    elif pct >= 60:
        feedback = "Good progress! Concept comprehension has improved significantly. One more practice session recommended."
        status_msg = "Gap Narrowed"
    else:
        feedback = "Your understanding is still developing. Let's revise the prerequisite concept (Recursion & Call Stack Basics)."
        status_msg = "Needs Prerequisite Revision"

    return {
        "score": score,
        "total": total,
        "percentage": pct,
        "beforeAccuracy": 32,
        "afterAccuracy": pct,
        "gapReduction": max(0, pct - 32),
        "feedback": feedback,
        "status": status_msg
    }

@app.get("/api/student/before-after")
def get_before_after_data():
    return {
        "summary": {
            "beforeAvg": 35,
            "afterAvg": 79,
            "overallGain": 44
        },
        "topics": [
            {"topic": "Trees", "before": 32, "after": 81, "gain": 49},
            {"topic": "Graphs", "before": 25, "after": 72, "gain": 47},
            {"topic": "Linked Lists", "before": 48, "after": 84, "gain": 36},
            {"topic": "Stacks & Queues", "before": 58, "after": 88, "gain": 30},
            {"topic": "Recursion", "before": 42, "after": 80, "gain": 38}
        ]
    }

@app.get("/api/student/exams")
def get_student_available_exams(db: Session = Depends(get_db)):
    exams = db.query(models.Exam).filter(models.Exam.status.in_(["Published", "Live"])).all()
    return [e.to_dict(include_questions=True, hide_answers_for_student=True) for e in exams]

@app.post("/api/student/exams/{exam_id}/submit")
def submit_student_exam(exam_id: int, req: ExamSubmissionRequest, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    total_marks = 0
    obtained_marks = 0.0
    correct_count = 0
    wrong_count = 0
    eval_breakdown = []

    for q in exam.questions:
        q_marks = q.marks
        total_marks += q_marks
        ans = req.answers.get(str(q.id), req.answers.get(f"q_{q.id}", "")).strip()

        if q.question_type in ["MCQ", "TRUE_FALSE"]:
            is_correct = (ans.upper() == q.correct_answer.strip().upper())
            score_earned = float(q_marks) if is_correct else 0.0
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            eval_breakdown.append({
                "questionId": q.id,
                "questionText": q.question_text,
                "questionType": q.question_type,
                "studentAnswer": ans,
                "correctAnswer": q.correct_answer,
                "marksObtained": score_earned,
                "maxMarks": q_marks,
                "explanation": q.explanation,
                "feedback": "Correct answer." if is_correct else "Incorrect answer choice."
            })
            obtained_marks += score_earned
        else:
            # Short answer - Evaluate via AI Service
            ai_res = ai_service.evaluate_short_answer(
                question_text=q.question_text,
                expected_answer=q.correct_answer,
                student_answer=ans,
                max_marks=q_marks
            )
            score_earned = ai_res["marksObtained"]
            if score_earned >= (q_marks * 0.5):
                correct_count += 1
            else:
                wrong_count += 1

            eval_breakdown.append({
                "questionId": q.id,
                "questionText": q.question_text,
                "questionType": q.question_type,
                "studentAnswer": ans,
                "correctAnswer": q.correct_answer,
                "marksObtained": score_earned,
                "maxMarks": q_marks,
                "explanation": q.explanation,
                "feedback": ai_res["feedback"],
                "keywordsMatched": ai_res.get("keywordsMatched", []),
                "missingConcepts": ai_res.get("missingConcepts", [])
            })
            obtained_marks += score_earned

    final_pct = round((obtained_marks / max(total_marks, 1)) * 100, 1)
    passed = final_pct >= exam.pass_percentage

    sub = models.ExamSubmission(
        exam_id=exam.id,
        student_id=req.studentId,
        student_name=req.studentName,
        student_identifier=req.studentIdentifier,
        score=round(obtained_marks, 1),
        total_marks=total_marks,
        percentage=final_pct,
        passed=passed,
        total_correct=correct_count,
        total_wrong=wrong_count,
        time_taken=req.timeTaken or "20m",
        answers_json=json.dumps(req.answers),
        evaluation_json=json.dumps(eval_breakdown)
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return sub.to_dict()

# ----------------- FACULTY ROUTES -----------------

@app.get("/api/faculty/dashboard-stats")
def get_faculty_stats(db: Session = Depends(get_db)):
    active_exams = db.query(models.Exam).filter(models.Exam.status.in_(["Live", "Published"])).count()
    submissions = db.query(models.ExamSubmission).all()
    tested_count = len(submissions)
    avg_score = round(sum(s.percentage for s in submissions) / max(tested_count, 1), 1) if submissions else 76.0
    need_support = sum(1 for s in submissions if not s.passed or s.percentage < 50)
    resource_count = db.query(models.Resource).count()

    return {
        "activeExams": active_exams,
        "studentsTested": max(tested_count, 52),
        "averagePerformance": avg_score,
        "studentsNeedingSupport": max(need_support, 11),
        "learningResources": resource_count
    }

@app.get("/api/faculty/exams")
def get_faculty_exams(db: Session = Depends(get_db)):
    exams = db.query(models.Exam).order_by(desc(models.Exam.created_at)).all()
    return [e.to_dict(include_questions=True, hide_answers_for_student=False) for e in exams]

@app.post("/api/faculty/exams")
def create_faculty_exam(req: ExamCreateRequest, db: Session = Depends(get_db)):
    exam = models.Exam(
        title=req.title.strip(),
        subject=req.subject.strip(),
        unit_topic=req.unitTopic.strip(),
        description=req.description,
        date=req.date or "2026-09-12",
        start_time=req.startTime or "10:00 AM",
        end_time=req.endTime or "10:30 AM",
        duration_mins=req.durationMins,
        total_marks=req.totalMarks,
        pass_percentage=req.passPercentage,
        instructions=req.instructions,
        status=req.status or "Draft",
        created_by_name="Dr. Naveen Kumar"
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # Add questions
    calc_total_marks = 0
    for idx, q_data in enumerate(req.questions, start=1):
        q_marks = int(q_data.get("marks", 1))
        calc_total_marks += q_marks
        q_obj = models.Question(
            exam_id=exam.id,
            question_text=q_data.get("questionText", "Question"),
            question_type=q_data.get("questionType", "MCQ"),
            marks=q_marks,
            options_json=json.dumps(q_data.get("options", [])),
            correct_answer=q_data.get("correctAnswer", ""),
            explanation=q_data.get("explanation", ""),
            topic_tag=q_data.get("topicTag", exam.unit_topic),
            order_num=idx
        )
        db.add(q_obj)

    if calc_total_marks > 0:
        exam.total_marks = calc_total_marks

    db.commit()
    db.refresh(exam)
    return exam.to_dict(include_questions=True, hide_answers_for_student=False)

@app.put("/api/faculty/exams/{exam_id}")
def update_faculty_exam(exam_id: int, req: ExamCreateRequest, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    exam.title = req.title.strip()
    exam.subject = req.subject.strip()
    exam.unit_topic = req.unitTopic.strip()
    exam.description = req.description
    exam.duration_mins = req.durationMins
    exam.total_marks = req.totalMarks
    exam.pass_percentage = req.passPercentage
    exam.instructions = req.instructions
    exam.status = req.status or exam.status

    # Delete existing questions and replace
    db.query(models.Question).filter(models.Question.exam_id == exam_id).delete()
    for idx, q_data in enumerate(req.questions, start=1):
        q_obj = models.Question(
            exam_id=exam.id,
            question_text=q_data.get("questionText", "Question"),
            question_type=q_data.get("questionType", "MCQ"),
            marks=int(q_data.get("marks", 1)),
            options_json=json.dumps(q_data.get("options", [])),
            correct_answer=q_data.get("correctAnswer", ""),
            explanation=q_data.get("explanation", ""),
            topic_tag=q_data.get("topicTag", exam.unit_topic),
            order_num=idx
        )
        db.add(q_obj)

    db.commit()
    db.refresh(exam)
    return exam.to_dict(include_questions=True, hide_answers_for_student=False)

@app.post("/api/faculty/exams/{exam_id}/publish")
def publish_faculty_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    exam.status = "Live"
    db.commit()
    return {"success": True, "message": f"Exam '{exam.title}' is now Live for students.", "status": "Live"}

@app.delete("/api/faculty/exams/{exam_id}")
def delete_faculty_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    db.delete(exam)
    db.commit()
    return {"success": True, "message": "Exam deleted successfully."}

@app.get("/api/faculty/exams/{exam_id}/results")
def get_faculty_exam_results(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    submissions = db.query(models.ExamSubmission).filter(models.ExamSubmission.exam_id == exam_id).all()
    total_students = 60
    submitted = len(submissions)
    not_submitted = max(0, total_students - submitted)
    passed_count = sum(1 for s in submissions if s.passed)
    failed_count = sum(1 for s in submissions if not s.passed)

    percentages = [s.percentage for s in submissions] or [0]
    avg_score = round(sum(percentages) / max(len(percentages), 1), 1)
    highest = max(percentages) if percentages else 0
    lowest = min(percentages) if percentages else 0

    return {
        "exam": exam.to_dict(),
        "stats": {
            "totalStudents": total_students,
            "submitted": submitted,
            "notSubmitted": not_submitted,
            "passed": passed_count,
            "failed": failed_count,
            "averageScore": avg_score,
            "highestScore": highest,
            "lowestScore": lowest
        },
        "scoreDistribution": [
            {"range": "0-40%", "count": sum(1 for p in percentages if p < 40)},
            {"range": "40-60%", "count": sum(1 for p in percentages if 40 <= p < 60)},
            {"range": "60-80%", "count": sum(1 for p in percentages if 60 <= p < 80)},
            {"range": "80-100%", "count": sum(1 for p in percentages if p >= 80)}
        ],
        "submissions": [s.to_dict() for s in submissions]
    }

@app.get("/api/faculty/ai-insights")
def get_faculty_ai_insights(db: Session = Depends(get_db)):
    insights = db.query(models.AIInsight).all()
    return [i.to_dict() for i in insights]

@app.post("/api/faculty/ai-insights/{insight_id}/approve")
def approve_ai_insight(insight_id: int, db: Session = Depends(get_db)):
    insight = db.query(models.AIInsight).filter(models.AIInsight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.approved_by_faculty = True
    db.commit()
    return {"success": True, "message": "AI recommendation approved! It will now be assigned to students."}

# ----------------- RESOURCE CRUD -----------------

@app.get("/api/resources")
def get_resources(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    resource_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Resource)
    if subject:
        query = query.filter(models.Resource.subject.ilike(f"%{subject}%"))
    if topic:
        query = query.filter(models.Resource.topic.ilike(f"%{topic}%"))
    if resource_type:
        query = query.filter(models.Resource.resource_type == resource_type)
    if difficulty:
        query = query.filter(models.Resource.difficulty == difficulty)
    if search:
        query = query.filter(
            or_(
                models.Resource.title.ilike(f"%{search}%"),
                models.Resource.topic.ilike(f"%{search}%"),
                models.Resource.description.ilike(f"%{search}%")
            )
        )
    resources = query.all()
    return [r.to_dict() for r in resources]

@app.post("/api/resources")
def add_resource(req: ResourceCreateRequest, db: Session = Depends(get_db)):
    res = models.Resource(
        title=req.title.strip(),
        subject=req.subject.strip(),
        topic=req.topic.strip(),
        description=req.description,
        resource_type=req.resourceType,
        url=req.url,
        file_path=req.filePath,
        tags=req.tags,
        difficulty=req.difficulty,
        duration_mins=req.durationMins,
        platform=req.platform,
        faculty_endorsed=req.facultyEndorsed,
        created_by_name="Dr. Naveen Kumar"
    )
    db.add(res)
    db.commit()
    db.refresh(res)
    return res.to_dict()

@app.put("/api/resources/{resource_id}")
def edit_resource(resource_id: int, req: ResourceCreateRequest, db: Session = Depends(get_db)):
    res = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")
    res.title = req.title.strip()
    res.subject = req.subject.strip()
    res.topic = req.topic.strip()
    res.description = req.description
    res.resource_type = req.resourceType
    res.url = req.url
    res.file_path = req.filePath
    res.tags = req.tags
    res.difficulty = req.difficulty
    res.duration_mins = req.durationMins
    res.platform = req.platform
    res.faculty_endorsed = req.facultyEndorsed
    db.commit()
    db.refresh(res)
    return res.to_dict()

@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    res = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(res)
    db.commit()
    return {"success": True, "message": "Resource deleted successfully"}

# ----------------- REMEDIAL COORDINATOR ROUTES -----------------

@app.get("/api/remedial/dashboard-stats")
def get_remedial_stats(db: Session = Depends(get_db)):
    total_students = 250
    students_with_gaps = 48
    immediate_support = 17
    avg_perf = 74
    assessments_completed = 18
    resources_count = db.query(models.Resource).count()

    return {
        "totalStudents": total_students,
        "studentsWithGaps": students_with_gaps,
        "immediateSupport": immediate_support,
        "averagePerformance": avg_perf,
        "assessmentsCompleted": assessments_completed,
        "availableResources": max(resources_count, 86)
    }

@app.get("/api/remedial/students")
def get_remedial_students(
    search: Optional[str] = None,
    gap_level: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    student_list = [
        {
            "id": 1,
            "name": "Rahul Kumar",
            "studentId": "23CSE101",
            "department": "CSE",
            "year": "2nd Year",
            "section": "A",
            "overallScore": 68,
            "weakSubjects": "Data Structures",
            "primaryGap": "Binary Trees (32%)",
            "gapLevel": "High",
            "status": "Improving",
            "recentScores": [72, 65, 58, 68]
        },
        {
            "id": 2,
            "name": "Priya Sharma",
            "studentId": "23ECE204",
            "department": "ECE",
            "year": "3rd Year",
            "section": "B",
            "overallScore": 54,
            "weakSubjects": "Data Structures, DBMS",
            "primaryGap": "Trees (38%), Graphs (34%)",
            "gapLevel": "High",
            "status": "Needs Support",
            "recentScores": [58, 52, 49, 54]
        },
        {
            "id": 3,
            "name": "Kiran Varma",
            "studentId": "23CSE118",
            "department": "CSE",
            "year": "2nd Year",
            "section": "A",
            "overallScore": 42,
            "weakSubjects": "Data Structures, Mathematics",
            "primaryGap": "Tree Traversal (30%)",
            "gapLevel": "High",
            "status": "Immediate Support",
            "recentScores": [45, 38, 35, 42]
        },
        {
            "id": 4,
            "name": "Suresh Reddy",
            "studentId": "23CSE142",
            "department": "CSE",
            "year": "2nd Year",
            "section": "B",
            "overallScore": 82,
            "weakSubjects": "None",
            "primaryGap": "Sorting Algorithms (72%)",
            "gapLevel": "Low",
            "status": "Improving",
            "recentScores": [78, 80, 81, 82]
        },
        {
            "id": 5,
            "name": "Deepika Nair",
            "studentId": "23AIML105",
            "department": "AIML",
            "year": "1st Year",
            "section": "A",
            "overallScore": 89,
            "weakSubjects": "None",
            "primaryGap": "Recursion (78%)",
            "gapLevel": "Low",
            "status": "Strong",
            "recentScores": [85, 87, 88, 89]
        }
    ]

    filtered = student_list
    if search:
        s_lower = search.lower()
        filtered = [s for s in filtered if s_lower in s["name"].lower() or s_lower in s["studentId"].lower() or s_lower in s["department"].lower() or s_lower in s["weakSubjects"].lower()]
    if gap_level:
        filtered = [s for s in filtered if s["gapLevel"].lower() == gap_level.lower()]
    if department:
        filtered = [s for s in filtered if s["department"].lower() == department.lower()]

    return filtered

@app.get("/api/remedial/students/{student_id}/profile")
def get_remedial_student_profile(student_id: int, db: Session = Depends(get_db)):
    # Student detail overview
    return {
        "student": {
            "id": student_id,
            "name": "Rahul Kumar" if student_id == 1 else "Priya Sharma",
            "studentId": "23CSE101" if student_id == 1 else "23ECE204",
            "department": "CSE" if student_id == 1 else "ECE",
            "year": "2nd Year",
            "section": "A",
            "overallScore": 68
        },
        "performanceTrend": [
            {"assessment": "Assessment 1", "score": 72, "date": "Aug 10"},
            {"assessment": "Assessment 2", "score": 65, "date": "Aug 20"},
            {"assessment": "Assessment 3", "score": 58, "date": "Aug 30"},
            {"assessment": "Assessment 4", "score": 68, "date": "Sep 08"}
        ],
        "subjectPerformance": [
            {"subject": "Data Structures", "averageScore": 52, "performance": "Weak", "gap": "High"},
            {"subject": "DBMS", "averageScore": 64, "performance": "Average", "gap": "Medium"},
            {"subject": "Java", "averageScore": 82, "performance": "Strong", "gap": "Low"},
            {"subject": "Mathematics", "averageScore": 48, "performance": "Weak", "gap": "High"}
        ],
        "topicGaps": [
            {"topic": "Arrays", "score": 84, "level": "Low"},
            {"topic": "Linked Lists", "score": 71, "level": "Low"},
            {"topic": "Stacks", "score": 62, "level": "Medium"},
            {"topic": "Queues", "score": 58, "level": "Medium"},
            {"topic": "Trees", "score": 39, "level": "High"},
            {"topic": "Graphs", "score": 34, "level": "High"}
        ],
        "aiAnalysis": {
            "observations": [
                "The student is consistently performing below 50% in Tree Traversal and Graph Algorithms across three assessments.",
                "The student appears to have difficulty understanding recursive call stack unwinding."
            ],
            "identifiedGaps": ["Tree Traversal (High)", "Graph Algorithms (High)", "Recursion (Medium)"],
            "recommendedSteps": [
                "1. Review Tree Traversal fundamentals and call stack mechanics",
                "2. Study the teacher-uploaded Tree Traversal notes by Prof. Ravi",
                "3. Watch the recommended NPTEL learning video by Prof. Naveen Garg",
                "4. Attempt a 5-question adaptive practice quiz",
                "5. Reassess after completing the resources"
            ]
        },
        "matchedTeacherResources": [
            {"title": "Tree Traversal Fundamentals & Visual Notes", "teacher": "Prof. Ravi", "type": "Notes", "topic": "Binary Trees"},
            {"title": "Binary Tree Inorder, Preorder & Postorder Recursive Traces", "teacher": "Dr. Naveen Kumar", "type": "Video", "topic": "Binary Trees"},
            {"title": "Tree Traversal Visualization Lab", "teacher": "Prof. Ravi", "type": "Interactive Lab", "topic": "Binary Trees"}
        ]
    }

@app.get("/api/remedial/class-gaps")
def get_class_gaps():
    return {
        "commonGaps": [
            {"topic": "Graph Algorithms", "studentsAffected": 42, "severity": "High"},
            {"topic": "Tree Traversal", "studentsAffected": 38, "severity": "High"},
            {"topic": "Recursion", "studentsAffected": 31, "severity": "Medium"},
            {"topic": "Normalization", "studentsAffected": 18, "severity": "Medium"},
            {"topic": "SQL Joins", "studentsAffected": 14, "severity": "Low"}
        ],
        "aiInsight": {
            "text": "Data Structures is currently the largest learning-gap area. 38 students are struggling with Tree Traversal and 42 students are struggling with Graph Algorithms.",
            "actions": [
                "Share existing Tree Traversal resources to all affected students",
                "Conduct a remedial session on Graph BFS/DFS",
                "Assign an adaptive 5-question practice quiz",
                "Reassess students after resource completion"
            ]
        }
    }

@app.get("/api/remedial/progress")
def get_remedial_progress():
    return [
        {"student": "Rahul Kumar", "initialScore": 42, "currentScore": 68, "improvement": 26, "status": "Improving"},
        {"student": "Priya Sharma", "initialScore": 38, "currentScore": 44, "improvement": 6, "status": "Needs Support"},
        {"student": "Kiran Varma", "initialScore": 55, "currentScore": 72, "improvement": 17, "status": "Improving"},
        {"student": "Suresh Reddy", "initialScore": 60, "currentScore": 82, "improvement": 22, "status": "Strong"}
    ]

# ----------------- LIBRARY ROUTES -----------------

@app.get("/api/library/stats")
def get_library_stats(db: Session = Depends(get_db)):
    books = db.query(models.Book).all()
    total_books = len(books)
    avail_copies = sum(b.available_copies for b in books)
    issued_copies = sum(b.issued_copies for b in books)
    with_softcopy = sum(1 for b in books if b.softcopy_available)
    without_softcopy = total_books - with_softcopy

    return {
        "totalBooks": total_books,
        "availableCopies": avail_copies,
        "issuedCopies": issued_copies,
        "withSoftcopy": with_softcopy,
        "withoutSoftcopy": without_softcopy,
        "recentlyAdded": total_books
    }

@app.get("/api/library/books")
def get_library_books(
    search: Optional[str] = None,
    available_only: Optional[bool] = False,
    softcopy_only: Optional[bool] = False,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Book)
    if search:
        s = search.strip()
        query = query.filter(
            or_(
                models.Book.name.ilike(f"%{s}%"),
                models.Book.author.ilike(f"%{s}%"),
                models.Book.subject.ilike(f"%{s}%"),
                models.Book.isbn.ilike(f"%{s}%")
            )
        )
    if available_only:
        query = query.filter(models.Book.available_copies > 0)
    if softcopy_only:
        query = query.filter(models.Book.softcopy_available == True)
    if department:
        query = query.filter(models.Book.department.ilike(f"%{department}%"))

    books = query.all()
    return [b.to_dict() for b in books]

@app.post("/api/library/books")
def add_library_book(req: BookCreateRequest, db: Session = Depends(get_db)):
    book = models.Book(
        name=req.name.strip(),
        author=req.author.strip(),
        isbn=req.isbn.strip(),
        subject=req.subject or "Computer Science",
        department=req.department or "CSE",
        category=req.category or "Core",
        publisher=req.publisher or "",
        edition=req.edition or "1st Edition",
        total_copies=req.totalCopies,
        available_copies=req.totalCopies,
        issued_copies=0,
        shelf_number=req.shelfNumber or "CS-1A",
        softcopy_available=req.softcopyAvailable,
        softcopy_url=req.softcopyUrl if req.softcopyAvailable else None,
        cover_image=req.coverImage
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book.to_dict()

@app.put("/api/library/books/{book_id}")
def edit_library_book(book_id: int, req: BookCreateRequest, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.name = req.name.strip()
    book.author = req.author.strip()
    book.isbn = req.isbn.strip()
    book.subject = req.subject
    book.department = req.department
    book.category = req.category
    book.publisher = req.publisher
    book.edition = req.edition
    book.total_copies = req.totalCopies
    # Adjust available copies if total changed
    book.available_copies = max(0, req.totalCopies - book.issued_copies)
    book.shelf_number = req.shelfNumber
    book.softcopy_available = req.softcopyAvailable
    book.softcopy_url = req.softcopyUrl if req.softcopyAvailable else None
    if req.coverImage:
        book.cover_image = req.coverImage
    db.commit()
    db.refresh(book)
    return book.to_dict()

@app.delete("/api/library/books/{book_id}")
def delete_library_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"success": True, "message": "Book removed from library catalogue"}

@app.post("/api/library/books/{book_id}/issue")
def issue_book_copy(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="All physical copies are currently issued.")
    book.available_copies -= 1
    book.issued_copies += 1
    db.commit()
    db.refresh(book)
    return book.to_dict()

@app.post("/api/library/books/{book_id}/return")
def return_book_copy(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.issued_copies <= 0:
        raise HTTPException(status_code=400, detail="No issued copies to return.")
    book.available_copies += 1
    book.issued_copies -= 1
    db.commit()
    db.refresh(book)
    return book.to_dict()

# ----------------- AI CHAT & RESOURCE SIMPLIFIER ROUTES -----------------

@app.post("/api/ai/chat")
def chat_with_assistant(req: ChatRequest):
    return ai_service.chat_assistant(req.message, req.userContext or {}, session_id=req.sessionId or "default")


@app.post("/api/ai/simplify")
def simplify_resource_endpoint(req: SimplifyRequest):
    return ai_service.simplify_resource(
        content_type=req.type,
        content=req.content,
        title=req.title or "",
        topic_hint=req.topic or ""
    )

@app.post("/api/ai/simplify-file")
async def simplify_file_endpoint(file: UploadFile = File(...), topic: Optional[str] = Form(None)):
    filename = file.filename or "Uploaded Document"
    content_bytes = await file.read()
    extracted_text = ""
    
    if filename.lower().endswith(".pdf"):
        try:
            import io
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages_text = [p.extract_text() for p in reader.pages if p.extract_text()]
            extracted_text = "\n".join(pages_text)
        except Exception as e:
            extracted_text = content_bytes.decode("utf-8", errors="ignore")
    else:
        extracted_text = content_bytes.decode("utf-8", errors="ignore")
    
    return ai_service.simplify_resource(
        content_type="pdf" if filename.lower().endswith(".pdf") else "notes",
        content=extracted_text,
        title=filename,
        topic_hint=topic or filename
    )

@app.get("/api/student/topic-hierarchy")
def get_topic_hierarchy_endpoint(topic_id: str = "trees"):
    return ai_service.get_topic_hierarchy(topic_id)

@app.get("/api/student/important-notes")
def get_important_notes_endpoint(department: str = "CSE", year: str = "2"):
    return ai_service.get_default_important_notes(department, year)

# ----------------- DOUBTS & LIVE SESSIONS & FACULTY PDF SCHEMAS -----------------

class AskDoubtRequest(BaseModel):
    studentId: Optional[int] = None
    studentName: str
    studentIdentifier: Optional[str] = "23CSE101"
    facultyName: str
    subject: str
    topic: str
    question: str

class AnswerDoubtRequest(BaseModel):
    answer: str
    answeredBy: str

class CreateLiveSessionRequest(BaseModel):
    facultyName: str
    facultyId: Optional[str] = "FAC701"
    subject: str
    topic: str
    scheduledTime: Optional[str] = "Now (Live)"
    durationMins: Optional[int] = 45
    meetingLink: Optional[str] = ""
    status: Optional[str] = "Live"

class UploadFacultyPdfRequest(BaseModel):
    facultyName: str
    subject: str
    title: str
    unit: Optional[str] = "Unit 1"
    description: Optional[str] = ""
    fileUrl: str
    fileName: str
    fileSize: Optional[str] = "2.4 MB"

# ----------------- DOUBTS ENDPOINTS -----------------

@app.get("/api/doubts")
def get_doubts(
    student_identifier: Optional[str] = None,
    faculty_name: Optional[str] = None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Doubt)
    if student_identifier:
        query = query.filter(models.Doubt.student_identifier == student_identifier)
    if faculty_name:
        query = query.filter(models.Doubt.faculty_name.ilike(f"%{faculty_name}%"))
    if subject:
        query = query.filter(models.Doubt.subject.ilike(f"%{subject}%"))
    if status:
        query = query.filter(models.Doubt.status == status)
    
    doubts = query.order_by(desc(models.Doubt.created_at)).all()
    return [d.to_dict() for d in doubts]

@app.post("/api/doubts")
def ask_doubt(req: AskDoubtRequest, db: Session = Depends(get_db)):
    new_doubt = models.Doubt(
        student_id=req.studentId,
        student_name=req.studentName,
        student_identifier=req.studentIdentifier,
        faculty_name=req.facultyName,
        subject=req.subject,
        topic=req.topic,
        question=req.question,
        status="Pending",
        created_at=datetime.datetime.utcnow()
    )
    db.add(new_doubt)
    db.commit()
    db.refresh(new_doubt)
    return new_doubt.to_dict()

@app.post("/api/doubts/{doubt_id}/answer")
def answer_doubt(doubt_id: int, req: AnswerDoubtRequest, db: Session = Depends(get_db)):
    doubt = db.query(models.Doubt).filter(models.Doubt.id == doubt_id).first()
    if not doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
    
    doubt.status = "Answered"
    doubt.answer = req.answer
    doubt.answered_by = req.answeredBy
    doubt.answered_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(doubt)
    return doubt.to_dict()

# ----------------- FACULTY LIVE SESSIONS ENDPOINTS -----------------

@app.get("/api/faculty/live-sessions")
def get_live_sessions(faculty_name: Optional[str] = None, subject: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.LiveSession)
    if faculty_name:
        query = query.filter(models.LiveSession.faculty_name.ilike(f"%{faculty_name}%"))
    if subject:
        query = query.filter(models.LiveSession.subject.ilike(f"%{subject}%"))
    sessions = query.order_by(desc(models.LiveSession.created_at)).all()
    return [s.to_dict() for s in sessions]

@app.post("/api/faculty/live-sessions")
def create_live_session(req: CreateLiveSessionRequest, db: Session = Depends(get_db)):
    link = req.meetingLink.strip() if req.meetingLink else f"https://meet.google.com/{hashlib.md5(req.topic.encode()).hexdigest()[:3]}-{hashlib.md5(req.topic.encode()).hexdigest()[3:7]}-{hashlib.md5(req.topic.encode()).hexdigest()[7:10]}"
    session = models.LiveSession(
        faculty_name=req.facultyName,
        faculty_id=req.facultyId,
        subject=req.subject,
        topic=req.topic,
        scheduled_time=req.scheduledTime or "Now (Live)",
        duration_mins=req.durationMins or 45,
        meeting_link=link,
        status=req.status or "Live",
        joined_count=1,
        created_at=datetime.datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.to_dict()

@app.post("/api/faculty/live-sessions/{session_id}/end")
def end_live_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.LiveSession).filter(models.LiveSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "Completed"
    db.commit()
    db.refresh(session)
    return session.to_dict()

# ----------------- FACULTY SUBJECT PDF ENDPOINTS -----------------

@app.get("/api/faculty/pdfs")
def get_faculty_pdfs(faculty_name: Optional[str] = None, subject: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.FacultyPdf)
    if faculty_name:
        query = query.filter(models.FacultyPdf.faculty_name.ilike(f"%{faculty_name}%"))
    if subject:
        query = query.filter(models.FacultyPdf.subject.ilike(f"%{subject}%"))
    pdfs = query.order_by(desc(models.FacultyPdf.created_at)).all()
    return [p.to_dict() for p in pdfs]

@app.post("/api/faculty/upload-pdf")
def upload_faculty_pdf(req: UploadFacultyPdfRequest, db: Session = Depends(get_db)):
    pdf = models.FacultyPdf(
        faculty_name=req.facultyName,
        subject=req.subject,
        title=req.title,
        unit=req.unit or "Unit 1",
        description=req.description or "",
        file_url=req.fileUrl,
        file_name=req.fileName,
        file_size=req.fileSize or "2.4 MB",
        downloads_count=0,
        created_at=datetime.datetime.utcnow()
    )
    db.add(pdf)
    db.commit()
    db.refresh(pdf)
    return pdf.to_dict()

# ----------------- AI CHAT & RESOURCE SIMPLIFICATION ENDPOINTS -----------------

@app.post("/api/ai/chat")
def ai_chat(req: ChatRequest):
    return ai_service.chat_assistant(req.message, req.userContext or {}, session_id=req.sessionId or "default")


@app.post("/api/ai/simplify")
def ai_simplify(req: SimplifyRequest):
    return ai_service.simplify_resource(req.type, req.content, req.title or "", req.topic or "")

@app.post("/api/ai/simplify-file")
async def ai_simplify_file(file: UploadFile = File(...)):
    content = ""
    try:
        data = await file.read()
        if file.filename.lower().endswith(".pdf"):
            import pypdf, io
            reader = pypdf.PdfReader(io.BytesIO(data))
            for page in reader.pages[:10]:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        else:
            content = data.decode("utf-8", errors="ignore")
    except Exception as e:
        content = f"Uploaded file: {file.filename}"
    return ai_service.simplify_resource("pdf", content, file.filename, "Uploaded Document")



