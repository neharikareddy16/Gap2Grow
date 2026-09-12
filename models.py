import datetime
import json
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False)  # STUDENT, FACULTY, REMEDIAL_COORDINATOR, LIBRARY
    identifier = Column(String(50), unique=True, index=True, nullable=False)  # Register No / Faculty ID / Library ID
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    department = Column(String(50), default="CSE")
    year = Column(String(20), default="2nd Year")
    section = Column(String(10), default="A")
    college = Column(String(100), default="Vignan University")
    skills = Column(Text, default="C, Java, Python, Data Structures")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "identifier": self.identifier,
            "email": self.email,
            "department": self.department,
            "year": self.year,
            "section": self.section,
            "college": self.college,
            "skills": [s.strip() for s in (self.skills or "").split(",") if s.strip()],
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), default="Data Structures")
    topic = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(String(50), default="Video")  # PDF, Video, Article, Website, Notes, Practice Material, Quiz
    url = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)
    tags = Column(String(200), default="")
    difficulty = Column(String(30), default="Beginner")  # Beginner, Intermediate, Advanced
    duration_mins = Column(Integer, default=30)
    platform = Column(String(100), default="NPTEL / IIT Delhi")
    faculty_endorsed = Column(Boolean, default=False)
    created_by_name = Column(String(100), default="Prof. Naveen Garg")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "subject": self.subject,
            "topic": self.topic,
            "description": self.description,
            "resourceType": self.resource_type,
            "url": self.url,
            "filePath": self.file_path,
            "tags": [t.strip() for t in (self.tags or "").split(",") if t.strip()],
            "difficulty": self.difficulty,
            "durationMins": self.duration_mins,
            "platform": self.platform,
            "facultyEndorsed": self.faculty_endorsed,
            "createdByName": self.created_by_name,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), default="Data Structures")
    unit_topic = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(String(30), default="2026-09-12")
    start_time = Column(String(20), default="10:00 AM")
    end_time = Column(String(20), default="11:00 AM")
    duration_mins = Column(Integer, default=30)
    total_marks = Column(Integer, default=20)
    pass_percentage = Column(Integer, default=50)
    instructions = Column(Text, default="Answer all questions carefully. Time limit applies.")
    status = Column(String(30), default="Draft")  # Draft, Published, Live, Completed, Archived
    created_by_name = Column(String(100), default="Dr. Naveen Kumar")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    submissions = relationship("ExamSubmission", back_populates="exam", cascade="all, delete-orphan")

    def to_dict(self, include_questions=False, hide_answers_for_student=False):
        data = {
            "id": self.id,
            "title": self.title,
            "subject": self.subject,
            "unitTopic": self.unit_topic,
            "description": self.description,
            "date": self.date,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "durationMins": self.duration_mins,
            "totalMarks": self.total_marks,
            "passPercentage": self.pass_percentage,
            "instructions": self.instructions,
            "status": self.status,
            "createdByName": self.created_by_name,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "questionCount": len(self.questions) if self.questions else 0
        }
        if include_questions and self.questions:
            sorted_q = sorted(self.questions, key=lambda q: q.order_num)
            data["questions"] = [q.to_dict(hide_answer=hide_answers_for_student) for q in sorted_q]
        return data

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), default="MCQ")  # MCQ, TRUE_FALSE, SHORT_ANSWER
    marks = Column(Integer, default=1)
    options_json = Column(Text, default="[]")  # JSON list of string options
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, default="")
    topic_tag = Column(String(100), default="Binary Trees")
    order_num = Column(Integer, default=1)

    exam = relationship("Exam", back_populates="questions")

    def to_dict(self, hide_answer=False):
        opts = []
        try:
            opts = json.loads(self.options_json or "[]")
        except Exception:
            opts = []

        data = {
            "id": self.id,
            "examId": self.exam_id,
            "questionText": self.question_text,
            "questionType": self.question_type,
            "marks": self.marks,
            "options": opts,
            "topicTag": self.topic_tag,
            "orderNum": self.order_num
        }
        if not hide_answer:
            data["correctAnswer"] = self.correct_answer
            data["explanation"] = self.explanation
        return data

class ExamSubmission(Base):
    __tablename__ = "exam_submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_name = Column(String(100), nullable=False)
    student_identifier = Column(String(50), nullable=False)
    score = Column(Float, default=0.0)
    total_marks = Column(Integer, default=20)
    percentage = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)
    time_taken = Column(String(30), default="15m 30s")
    answers_json = Column(Text, default="{}")  # student answers map
    evaluation_json = Column(Text, default="[]")  # detailed Q-by-Q evaluation
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    exam = relationship("Exam", back_populates="submissions")

    def to_dict(self):
        try:
            answers = json.loads(self.answers_json or "{}")
        except Exception:
            answers = {}
        try:
            eval_data = json.loads(self.evaluation_json or "[]")
        except Exception:
            eval_data = []

        return {
            "id": self.id,
            "examId": self.exam_id,
            "examTitle": self.exam.title if self.exam else "Exam",
            "studentId": self.student_id,
            "studentName": self.student_name,
            "studentIdentifier": self.student_identifier,
            "score": self.score,
            "totalMarks": self.total_marks,
            "percentage": self.percentage,
            "passed": self.passed,
            "totalCorrect": self.total_correct,
            "totalWrong": self.total_wrong,
            "timeTaken": self.time_taken,
            "answers": answers,
            "evaluation": eval_data,
            "submittedAt": self.submitted_at.isoformat() if self.submitted_at else None
        }

class StudentGapProfile(Base):
    __tablename__ = "student_gap_profiles"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student_name = Column(String(100), nullable=False)
    department = Column(String(50), default="CSE")
    subject = Column(String(100), default="Data Structures")
    topic = Column(String(100), nullable=False)
    accuracy_pct = Column(Integer, default=32)
    skill_level = Column(String(50), default="Weak")  # Strong, Needs Improvement, Weak, Critical Gap
    gap_severity = Column(String(30), default="High")  # Low, Medium, High, Critical
    initial_score = Column(Integer, default=32)
    current_score = Column(Integer, default=78)
    prerequisites = Column(String(200), default="Recursion, Pointers")
    weakness_reason = Column(Text, default="Recursive call stack frame unwinding in Postorder and Preorder traversals")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "studentId": self.student_id,
            "studentName": self.student_name,
            "department": self.department,
            "subject": self.subject,
            "topic": self.topic,
            "accuracyPct": self.accuracy_pct,
            "skillLevel": self.skill_level,
            "gapSeverity": self.gap_severity,
            "initialScore": self.initial_score,
            "currentScore": self.current_score,
            "improvement": self.current_score - self.initial_score,
            "prerequisites": [p.strip() for p in (self.prerequisites or "").split(",") if p.strip()],
            "weaknessReason": self.weakness_reason,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(250), nullable=False)
    author = Column(String(150), nullable=False)
    isbn = Column(String(50), nullable=False, unique=True, index=True)
    subject = Column(String(100), default="Computer Science")
    department = Column(String(50), default="CSE")
    category = Column(String(100), default="Algorithms & Data Structures")
    publisher = Column(String(150), default="Pearson / McGraw-Hill")
    edition = Column(String(50), default="4th Edition")
    total_copies = Column(Integer, default=5)
    available_copies = Column(Integer, default=3)
    issued_copies = Column(Integer, default=2)
    shelf_number = Column(String(50), default="CS-Rack-3A")
    softcopy_available = Column(Boolean, default=True)
    softcopy_url = Column(String(500), nullable=True)
    cover_image = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        status = "Available at Library"
        if self.available_copies <= 0:
            status = "Currently Issued" if self.issued_copies > 0 else "Not Available"

        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "isbn": self.isbn,
            "subject": self.subject,
            "department": self.department,
            "category": self.category,
            "publisher": self.publisher,
            "edition": self.edition,
            "totalCopies": self.total_copies,
            "availableCopies": self.available_copies,
            "issuedCopies": self.issued_copies,
            "shelfNumber": self.shelf_number,
            "availabilityStatus": status,
            "softcopyAvailable": self.softcopy_available,
            "softcopyUrl": self.softcopy_url,
            "coverImage": self.cover_image,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), default="LEARNING_GAP")  # LEARNING_GAP, EXAM_ANALYSIS, REMEDIAL_RECOMMENDATION
    title = Column(String(200), nullable=False)
    insight_text = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    approved_by_faculty = Column(Boolean, default=False)
    related_topic = Column(String(100), default="Binary Trees")
    target_count = Column(Integer, default=21)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "insightText": self.insight_text,
            "recommendedAction": self.recommended_action,
            "approvedByFaculty": self.approved_by_faculty,
            "relatedTopic": self.related_topic,
            "targetCount": self.target_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class Doubt(Base):
    __tablename__ = "doubts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=True)
    student_name = Column(String(100), nullable=False)
    student_identifier = Column(String(50), nullable=True)
    faculty_name = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=False)
    topic = Column(String(200), nullable=False)
    question = Column(Text, nullable=False)
    status = Column(String(30), default="Pending")  # Pending, Answered
    answer = Column(Text, nullable=True)
    answered_by = Column(String(100), nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "studentId": self.student_id,
            "studentName": self.student_name,
            "studentIdentifier": self.student_identifier,
            "facultyName": self.faculty_name,
            "subject": self.subject,
            "topic": self.topic,
            "question": self.question,
            "status": self.status,
            "answer": self.answer,
            "answeredBy": self.answered_by,
            "answeredAt": self.answered_at.isoformat() if self.answered_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class LiveSession(Base):
    __tablename__ = "live_sessions"

    id = Column(Integer, primary_key=True, index=True)
    faculty_name = Column(String(100), nullable=False)
    faculty_id = Column(String(50), nullable=True)
    subject = Column(String(100), nullable=False)
    topic = Column(String(200), nullable=False)
    scheduled_time = Column(String(50), nullable=False)
    duration_mins = Column(Integer, default=45)
    meeting_link = Column(String(500), nullable=False)
    status = Column(String(30), default="Live")  # Live, Scheduled, Completed
    joined_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "facultyName": self.faculty_name,
            "facultyId": self.faculty_id,
            "subject": self.subject,
            "topic": self.topic,
            "scheduledTime": self.scheduled_time,
            "durationMins": self.duration_mins,
            "meetingLink": self.meeting_link,
            "status": self.status,
            "joinedCount": self.joined_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

class FacultyPdf(Base):
    __tablename__ = "faculty_pdfs"

    id = Column(Integer, primary_key=True, index=True)
    faculty_name = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    unit = Column(String(50), default="Unit 1")
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=False)
    file_size = Column(String(50), default="2.4 MB")
    downloads_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "facultyName": self.faculty_name,
            "subject": self.subject,
            "title": self.title,
            "unit": self.unit,
            "description": self.description,
            "fileUrl": self.file_url,
            "fileName": self.file_name,
            "fileSize": self.file_size,
            "downloadsCount": self.downloads_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }

