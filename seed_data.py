import hashlib
import json
import datetime
from database import SessionLocal, engine, Base
import models

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Users
        users = [
            models.User(
                name="Rahul Kumar",
                role="STUDENT",
                identifier="23CSE101",
                email="rahul@vignan.ac.in",
                hashed_password=hash_pw("password123"),
                department="CSE",
                year="2nd Year",
                section="A",
                college="Vignan University",
                skills="C, Java, Python, Data Structures"
            ),
            models.User(
                name="Priya Sharma",
                role="STUDENT",
                identifier="23ECE204",
                email="priya@vignan.ac.in",
                hashed_password=hash_pw("password123"),
                department="ECE",
                year="3rd Year",
                section="B",
                college="Vignan University",
                skills="Python, C++, Verilog, Embedded Systems"
            ),
            models.User(
                name="Dr. Naveen Kumar",
                role="FACULTY",
                identifier="FAC701",
                email="dr.kumar@vignan.ac.in",
                hashed_password=hash_pw("password123"),
                department="CSE",
                year="Faculty",
                section="All",
                college="Vignan University",
                skills="Algorithms, Data Structures, Machine Learning"
            ),
            models.User(
                name="Prof. Anitha Rao",
                role="REMEDIAL_COORDINATOR",
                identifier="RC402",
                email="coord.anitha@vignan.ac.in",
                hashed_password=hash_pw("password123"),
                department="CSE & ECE",
                year="Coordinator",
                section="Remedial Cell",
                college="Vignan University",
                skills="Remedial Pedagogy, Student Learning Analytics"
            ),
            models.User(
                name="Central Library Admin",
                role="LIBRARY",
                identifier="LIB108",
                email="library@vignan.ac.in",
                hashed_password=hash_pw("password123"),
                department="Central Library",
                year="Staff",
                section="Digital & Physical Repositories",
                college="Vignan University",
                skills="Library Science, Digital Archiving, Resource Cataloging"
            )
        ]
        db.add_all(users)
        db.commit()

        # 2. Resources
        resources = [
            models.Resource(
                title="Binary Tree Inorder, Preorder & Postorder Recursive Traces",
                subject="Data Structures",
                topic="Binary Trees",
                description="Comprehensive lecture by Prof. Naveen Garg showing recursive call stack unwinding, activation records, and visual node traversal.",
                resource_type="Video",
                url="https://www.youtube.com/watch?v=9GMxdZ6U244",
                tags="Trees, Recursion, Traversal, NPTEL",
                difficulty="Beginner",
                duration_mins=15,
                platform="NPTEL / IIT Delhi (Prof. Naveen Garg)",
                faculty_endorsed=True,
                created_by_name="Dr. Naveen Kumar"
            ),
            models.Resource(
                title="Tree Traversal Visualization Lab",
                subject="Data Structures",
                topic="Binary Trees",
                description="Interactive visualizer and step-through lab for animated binary tree depth-first and breadth-first traversals with custom test nodes.",
                resource_type="Practice Material",
                url="https://visualgo.net/en/bst",
                tags="Trees, Visualization, Interactive Lab",
                difficulty="Intermediate",
                duration_mins=10,
                platform="VisuAlgo Interactive Lab",
                faculty_endorsed=True,
                created_by_name="Prof. Ravi"
            ),
            models.Resource(
                title="Recursion & Call Stack Prerequisite Refresh",
                subject="Data Structures",
                topic="Recursion",
                description="Concise faculty notes detailing stack frame allocation, base conditions, and common pitfalls in recursive algorithm design.",
                resource_type="Notes",
                url="https://vignan.ac.in/resources/recursion-basics.pdf",
                tags="Recursion, Stack, Basics",
                difficulty="Beginner",
                duration_mins=10,
                platform="Vignan Faculty Repository",
                faculty_endorsed=True,
                created_by_name="Prof. Anitha Rao"
            ),
            models.Resource(
                title="Graph BFS / DFS Adjacency Track",
                subject="Data Structures",
                topic="Graphs",
                description="In-depth coverage of graph representations, breadth-first search with FIFO queue, and depth-first search with recursion.",
                resource_type="Video",
                url="https://swayam.gov.in/explorer?searchText=graphs",
                tags="Graphs, BFS, DFS, Algorithms",
                difficulty="Intermediate",
                duration_mins=40,
                platform="SWAYAM / IIT Kharagpur",
                faculty_endorsed=True,
                created_by_name="Dr. Naveen Kumar"
            ),
            models.Resource(
                title="Binary Search Trees – Insertion, Deletion & Search",
                subject="Data Structures",
                topic="Binary Search Trees",
                description="Step-by-step algorithms for maintaining the BST invariant with O(h) complexity proofs.",
                resource_type="Article",
                url="https://geeksforgeeks.org/binary-search-tree-data-structure/",
                tags="BST, Search, Deletion",
                difficulty="Intermediate",
                duration_mins=25,
                platform="GeeksforGeeks Curated",
                faculty_endorsed=False,
                created_by_name="Dr. Naveen Kumar"
            ),
            models.Resource(
                title="DBMS Relational Algebra & Normalization Cheatsheet",
                subject="DBMS",
                topic="Normalization",
                description="1NF, 2NF, 3NF, and BCNF decomposition rules with worked examples from previous semester exams.",
                resource_type="PDF",
                url="https://vignan.ac.in/resources/dbms-normalization.pdf",
                tags="DBMS, Normalization, SQL",
                difficulty="Intermediate",
                duration_mins=30,
                platform="Vignan Department Notes",
                faculty_endorsed=True,
                created_by_name="Prof. Anitha Rao"
            )
        ]
        db.add_all(resources)
        db.commit()

        # 3. Exam
        exam = models.Exam(
            title="Data Structures – Unit 2 Quiz",
            subject="Data Structures",
            unit_topic="Trees & Traversals",
            description="Mid-term assessment testing binary trees, recursive traversals, and complexity analysis.",
            date="2026-09-12",
            start_time="10:00 AM",
            end_time="10:30 AM",
            duration_mins=30,
            total_marks=20,
            pass_percentage=50,
            instructions="Time limit is 30 minutes. Auto-submission will trigger when time expires. Do not navigate away.",
            status="Live",
            created_by_name="Dr. Naveen Kumar"
        )
        db.add(exam)
        db.commit()

        questions = [
            models.Question(
                exam_id=exam.id,
                question_text="What is the time complexity of binary search on a sorted array of size n?",
                question_type="MCQ",
                marks=2,
                options_json=json.dumps(["A. O(n)", "B. O(log n)", "C. O(n²)", "D. O(1)"]),
                correct_answer="B",
                explanation="Binary search repeatedly divides the search space in half, giving logarithmic time complexity O(log n).",
                topic_tag="Binary Search",
                order_num=1
            ),
            models.Question(
                exam_id=exam.id,
                question_text="In a binary tree, which traversal visits the root node LAST?",
                question_type="MCQ",
                marks=2,
                options_json=json.dumps(["A. Preorder", "B. Inorder", "C. Postorder", "D. Level-order"]),
                correct_answer="C",
                explanation="Postorder traversal recursively visits the Left subtree, Right subtree, and then the Root node (L-R-Root).",
                topic_tag="Binary Trees",
                order_num=2
            ),
            models.Question(
                exam_id=exam.id,
                question_text="A Binary Search Tree (BST) guarantees that all values in the left subtree are strictly smaller than the root value.",
                question_type="TRUE_FALSE",
                marks=2,
                options_json=json.dumps(["True", "False"]),
                correct_answer="True",
                explanation="By BST property definition: for any node, all keys in the left subtree are smaller and all keys in the right subtree are greater.",
                topic_tag="Binary Search Trees",
                order_num=3
            ),
            models.Question(
                exam_id=exam.id,
                question_text="Explain the role of the call stack in recursive binary tree traversals.",
                question_type="SHORT_ANSWER",
                marks=4,
                options_json="[]",
                correct_answer="The call stack preserves activation records containing local variables, return addresses, and node references as execution recurses through subtrees, unwinding back to the parent once base cases are reached.",
                explanation="Requires explaining activation records, preservation of state across parent nodes, and unwinding back from base cases.",
                topic_tag="Binary Trees",
                order_num=4
            ),
            models.Question(
                exam_id=exam.id,
                question_text="What is the maximum number of nodes in a binary tree of height h (where a root-only tree has height 0)?",
                question_type="MCQ",
                marks=2,
                options_json=json.dumps(["A. 2^h", "B. 2^(h+1) - 1", "C. 2^h - 1", "D. h²"]),
                correct_answer="B",
                explanation="The sum of nodes at all levels 0 to h is 2^0 + 2^1 + ... + 2^h = 2^(h+1) - 1.",
                topic_tag="Binary Trees",
                order_num=5
            ),
            models.Question(
                exam_id=exam.id,
                question_text="Which data structure is fundamentally utilized to perform Breadth-First Search (BFS) / Level-Order traversal?",
                question_type="MCQ",
                marks=2,
                options_json=json.dumps(["A. Stack", "B. Queue", "C. Priority Queue", "D. Hash Map"]),
                correct_answer="B",
                explanation="Breadth-First Search processes nodes in First-In-First-Out sequence using a Queue data structure.",
                topic_tag="Graphs",
                order_num=6
            ),
            models.Question(
                exam_id=exam.id,
                question_text="Why is recursive postorder traversal particularly suitable for deleting or freeing an entire binary tree?",
                question_type="SHORT_ANSWER",
                marks=4,
                options_json="[]",
                correct_answer="Postorder traversal visits and deletes both left and right child subtrees before deleting the root node itself, preventing dangling pointer references and memory leaks.",
                explanation="Children must be deallocated before deleting parent pointers to avoid losing memory addresses.",
                topic_tag="Binary Trees",
                order_num=7
            ),
            models.Question(
                exam_id=exam.id,
                question_text="In a full/strictly binary tree, every non-leaf node has exactly two children.",
                question_type="TRUE_FALSE",
                marks=2,
                options_json=json.dumps(["True", "False"]),
                correct_answer="True",
                explanation="A strictly or full binary tree is defined such that every node has either 0 or 2 children.",
                topic_tag="Binary Trees",
                order_num=8
            )
        ]
        db.add_all(questions)
        db.commit()

        # 4. Exam Submissions
        eval_sample_rahul = [
            {"questionId": 1, "studentAnswer": "B", "correctAnswer": "B", "marksObtained": 2, "maxMarks": 2, "feedback": "Correct."},
            {"questionId": 2, "studentAnswer": "C", "correctAnswer": "C", "marksObtained": 2, "maxMarks": 2, "feedback": "Correct."},
            {"questionId": 3, "studentAnswer": "True", "correctAnswer": "True", "marksObtained": 2, "maxMarks": 2, "feedback": "Correct."},
            {"questionId": 4, "studentAnswer": "The call stack stores activation records for each recursive call so execution can return to the parent node after traversing left and right children.", "correctAnswer": questions[3].correct_answer, "marksObtained": 3.5, "maxMarks": 4, "feedback": "Good answer covering core concepts of activation records."},
            {"questionId": 5, "studentAnswer": "B", "correctAnswer": "B", "marksObtained": 2, "maxMarks": 2, "feedback": "Correct."},
            {"questionId": 6, "studentAnswer": "B", "correctAnswer": "B", "marksObtained": 2, "maxMarks": 2, "feedback": "Correct."},
            {"questionId": 7, "studentAnswer": "Postorder deletes left and right child nodes first before the parent node, ensuring no memory leak or dangling reference.", "correctAnswer": questions[6].correct_answer, "marksObtained": 3.5, "maxMarks": 4, "feedback": "Accurate explanation of bottom-up memory deallocation."},
            {"questionId": 8, "studentAnswer": "False", "correctAnswer": "True", "marksObtained": 0, "maxMarks": 2, "feedback": "Incorrect. Full binary trees have 0 or 2 children per node."}
        ]
        sub1 = models.ExamSubmission(
            exam_id=exam.id,
            student_id=users[0].id,
            student_name="Rahul Kumar",
            student_identifier="23CSE101",
            score=17.0,
            total_marks=20,
            percentage=85.0,
            passed=True,
            total_correct=7,
            total_wrong=1,
            time_taken="24m 32s",
            answers_json=json.dumps({"1": "B", "2": "C", "3": "True", "4": "Stack stores activation frames", "5": "B", "6": "B", "7": "Deletes children before root", "8": "False"}),
            evaluation_json=json.dumps(eval_sample_rahul)
        )
        sub2 = models.ExamSubmission(
            exam_id=exam.id,
            student_id=users[1].id,
            student_name="Priya Sharma",
            student_identifier="23ECE204",
            score=12.0,
            total_marks=20,
            percentage=60.0,
            passed=True,
            total_correct=5,
            total_wrong=3,
            time_taken="27m 41s",
            answers_json=json.dumps({"1": "B", "2": "A", "3": "True", "4": "Saves state in memory", "5": "B", "6": "B", "7": "Order matters", "8": "True"}),
            evaluation_json=json.dumps([])
        )
        sub3 = models.ExamSubmission(
            exam_id=exam.id,
            student_id=None,
            student_name="Kiran Varma",
            student_identifier="23CSE118",
            score=7.0,
            total_marks=20,
            percentage=35.0,
            passed=False,
            total_correct=3,
            total_wrong=5,
            time_taken="29m 52s",
            answers_json=json.dumps({"1": "A", "2": "A", "3": "False", "4": "", "5": "B", "6": "A", "7": "", "8": "True"}),
            evaluation_json=json.dumps([])
        )
        sub4 = models.ExamSubmission(
            exam_id=exam.id,
            student_id=None,
            student_name="Suresh Reddy",
            student_identifier="23CSE142",
            score=16.0,
            total_marks=20,
            percentage=80.0,
            passed=True,
            total_correct=6,
            total_wrong=2,
            time_taken="22m 10s",
            answers_json=json.dumps({}),
            evaluation_json=json.dumps([])
        )
        db.add_all([sub1, sub2, sub3, sub4])
        db.commit()

        # 5. Student Gap Profiles
        gaps = [
            models.StudentGapProfile(
                student_id=users[0].id,
                student_name="Rahul Kumar",
                department="CSE",
                subject="Data Structures",
                topic="Binary Trees",
                accuracy_pct=32,
                skill_level="Weak",
                gap_severity="High",
                initial_score=32,
                current_score=78,
                prerequisites="Recursion, Call Stack, Pointers",
                weakness_reason="Recursive call stack frame unwinding in Postorder and Preorder traversals"
            ),
            models.StudentGapProfile(
                student_id=users[0].id,
                student_name="Rahul Kumar",
                department="CSE",
                subject="Data Structures",
                topic="Graphs",
                accuracy_pct=20,
                skill_level="Critical Gap",
                gap_severity="Critical",
                initial_score=20,
                current_score=45,
                prerequisites="Queue, Stack, Adjacency Matrix",
                weakness_reason="BFS queue state management and cycle detection in directed graphs"
            ),
            models.StudentGapProfile(
                student_id=users[0].id,
                student_name="Rahul Kumar",
                department="CSE",
                subject="Data Structures",
                topic="Linked Lists",
                accuracy_pct=48,
                skill_level="Needs Improvement",
                gap_severity="Medium",
                initial_score=48,
                current_score=84,
                prerequisites="Pointers, Dynamic Memory",
                weakness_reason="Doubly linked list pointer swapping and boundary head/tail conditions"
            ),
            models.StudentGapProfile(
                student_id=users[0].id,
                student_name="Rahul Kumar",
                department="CSE",
                subject="Data Structures",
                topic="Arrays",
                accuracy_pct=90,
                skill_level="Strong",
                gap_severity="Low",
                initial_score=90,
                current_score=94,
                prerequisites="Basic Programming",
                weakness_reason="None (Mastered)"
            ),
            models.StudentGapProfile(
                student_id=users[1].id,
                student_name="Priya Sharma",
                department="ECE",
                subject="Data Structures",
                topic="Binary Trees",
                accuracy_pct=38,
                skill_level="Weak",
                gap_severity="High",
                initial_score=38,
                current_score=44,
                prerequisites="Recursion",
                weakness_reason="Binary tree height calculation and recursive base termination"
            ),
            models.StudentGapProfile(
                student_id=None,
                student_name="Kiran Varma",
                department="CSE",
                subject="Data Structures",
                topic="Binary Trees",
                accuracy_pct=30,
                skill_level="Critical Gap",
                gap_severity="High",
                initial_score=30,
                current_score=55,
                prerequisites="Recursion, Stacks",
                weakness_reason="Call stack unwinding and tree traversal logic"
            )
        ]
        db.add_all(gaps)
        db.commit()

        # 6. Books
        books = [
            models.Book(
                name="Data Structures and Algorithms in C++",
                author="Robert Lafore",
                isbn="978-0672324536",
                subject="Data Structures",
                department="CSE",
                category="Algorithms & Data Structures",
                publisher="Pearson / Sams Publishing",
                edition="4th Edition",
                total_copies=5,
                available_copies=3,
                issued_copies=2,
                shelf_number="CS-Rack-3A",
                softcopy_available=True,
                softcopy_url="https://raw.githubusercontent.com/kalya/sample/main/lafore_dsa.pdf",
                cover_image="https://images.unsplash.com/photo-1532012164546-f432f2e3edd4?w=400"
            ),
            models.Book(
                name="Operating System Concepts",
                author="Abraham Silberschatz, Peter B. Galvin, Greg Gagne",
                isbn="978-1118063330",
                subject="Operating Systems",
                department="CSE",
                category="Systems Architecture",
                publisher="John Wiley & Sons",
                edition="10th Edition",
                total_copies=4,
                available_copies=0,
                issued_copies=4,
                shelf_number="CS-Rack-1B",
                softcopy_available=True,
                softcopy_url="https://raw.githubusercontent.com/kalya/sample/main/silberschatz_os.pdf",
                cover_image="https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400"
            ),
            models.Book(
                name="Computer Networks",
                author="Andrew S. Tanenbaum, David J. Wetherall",
                isbn="978-0132126953",
                subject="Networking",
                department="CSE / ECE",
                category="Computer Networks",
                publisher="Pearson Higher Ed",
                edition="5th Edition",
                total_copies=3,
                available_copies=1,
                issued_copies=2,
                shelf_number="CS-Rack-2C",
                softcopy_available=False,
                softcopy_url=None,
                cover_image="https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400"
            ),
            models.Book(
                name="Introduction to Algorithms (CLRS)",
                author="Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein",
                isbn="978-0262033848",
                subject="Algorithms",
                department="CSE",
                category="Core Computer Science",
                publisher="MIT Press",
                edition="3rd Edition",
                total_copies=6,
                available_copies=4,
                issued_copies=2,
                shelf_number="CS-Rack-3B",
                softcopy_available=True,
                softcopy_url="https://raw.githubusercontent.com/kalya/sample/main/clrs_algo.pdf",
                cover_image="https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400"
            ),
            models.Book(
                name="Database System Concepts",
                author="Abraham Silberschatz, Henry F. Korth, S. Sudarshan",
                isbn="978-0073523323",
                subject="Database Management",
                department="CSE / IT",
                category="Databases",
                publisher="McGraw-Hill",
                edition="7th Edition",
                total_copies=4,
                available_copies=2,
                issued_copies=2,
                shelf_number="CS-Rack-4A",
                softcopy_available=True,
                softcopy_url="https://raw.githubusercontent.com/kalya/sample/main/korth_dbms.pdf",
                cover_image="https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400"
            ),
            models.Book(
                name="Signals and Systems",
                author="Alan V. Oppenheim, Alan S. Willsky, S. Hamid Nawab",
                isbn="978-0138147570",
                subject="Signals & Systems",
                department="ECE",
                category="Electronics & Communication",
                publisher="Prentice Hall",
                edition="2nd Edition",
                total_copies=3,
                available_copies=2,
                issued_copies=1,
                shelf_number="EC-Rack-2A",
                softcopy_available=True,
                softcopy_url="https://raw.githubusercontent.com/kalya/sample/main/signals_oppenheim.pdf",
                cover_image="https://images.unsplash.com/photo-1532012164546-f432f2e3edd4?w=400"
            )
        ]
        db.add_all(books)
        db.commit()

        # 7. AI Insights
        insights = [
            models.AIInsight(
                category="LEARNING_GAP",
                title="Critical Topic Struggle: Binary Tree Traversal",
                insight_text="21 students showed difficulty with Binary Tree Traversal and recursive stack unwinding in recent diagnostic checks.",
                recommended_action="Assign prerequisite learning resource 'VisuAlgo Traversal Lab' and auto-generate a 5-question practice quiz.",
                approved_by_faculty=False,
                related_topic="Binary Trees",
                target_count=21
            ),
            models.AIInsight(
                category="EXAM_ANALYSIS",
                title="Question 7 High Error Rate",
                insight_text="Question 7 (Recursive Deletion & Memory Freeing) had the highest incorrect response rate (65% incorrect).",
                recommended_action="Schedule brief 10-minute remediation session and recommend Prof. Naveen Garg's memory trace lecture.",
                approved_by_faculty=True,
                related_topic="Binary Trees",
                target_count=34
            ),
            models.AIInsight(
                category="REMEDIAL_RECOMMENDATION",
                title="Graph BFS/DFS Class-Wide Gap",
                insight_text="38 students struggling with Graph BFS/DFS Adjacency implementations. Prerequisite queues and arrays are strong, indicating conceptual gap in graph state exploration.",
                recommended_action="Conduct targeted remedial workshop and release interactive BFS adjacency tracker module.",
                approved_by_faculty=False,
                related_topic="Graphs",
                target_count=38
            )
        ]
        db.add_all(insights)
        db.commit()

        # 8. Doubts
        doubts = [
            models.Doubt(
                student_name="Rahul Kumar",
                student_identifier="23CSE101",
                faculty_name="Dr. Naveen Kumar",
                subject="Data Structures",
                topic="AVL Trees Rotation",
                question="Sir, during double rotation (LR rotation), why do we rotate the left child left first before rotating the root right? Could you explain the balance factor changes?",
                status="Answered",
                answer="In LR rotation, the imbalance is caused by a node inserted into the right subtree of the left child. To fix this, we first rotate the left child left so that the deepest nodes align in a single left-heavy line (LL case). Then, a single right rotation at the root restores balance. Balance factors of the affected nodes are recalculated to 0 or ±1 depending on where the insertion occurred.",
                answered_by="Dr. Naveen Kumar",
                answered_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            ),
            models.Doubt(
                student_name="Rahul Kumar",
                student_identifier="23CSE101",
                faculty_name="Dr. Naveen Kumar",
                subject="Data Structures",
                topic="Graph Cycle Detection in Directed Graphs",
                question="How does cycle detection differ between undirected graphs and directed graphs using DFS? Do we need a recursion call stack array in directed graphs?",
                status="Pending",
                answer=None,
                answered_by=None,
                answered_at=None
            ),
            models.Doubt(
                student_name="Priya Sharma",
                student_identifier="23ECE204",
                faculty_name="Dr. Naveen Kumar",
                subject="Data Structures",
                topic="Dynamic Programming vs Memoization",
                question="When should we prefer bottom-up tabulation over top-down memoization in recursive DAG problems?",
                status="Pending",
                answer=None,
                answered_by=None,
                answered_at=None
            )
        ]
        db.add_all(doubts)
        db.commit()

        # 9. Live Sessions
        live_sessions = [
            models.LiveSession(
                faculty_name="Dr. Naveen Kumar",
                faculty_id="FAC701",
                subject="Data Structures",
                topic="Live Code Lab: AVL Tree Balancing & Red-Black Invariants",
                scheduled_time="Live Now (Started 10 mins ago)",
                duration_mins=45,
                meeting_link="https://meet.google.com/gap-grow-vignan",
                status="Live",
                joined_count=28
            ),
            models.LiveSession(
                faculty_name="Dr. Naveen Kumar",
                faculty_id="FAC701",
                subject="Data Structures",
                topic="Mastering Dynamic Programming & Bellman-Ford",
                scheduled_time="Tomorrow at 4:30 PM",
                duration_mins=60,
                meeting_link="https://meet.google.com/daa-algo-vignan",
                status="Scheduled",
                joined_count=0
            )
        ]
        db.add_all(live_sessions)
        db.commit()

        # 10. Faculty PDFs
        faculty_pdfs = [
            models.FacultyPdf(
                faculty_name="Dr. Naveen Kumar",
                subject="Data Structures",
                title="Unit 3: Self-Balancing Search Trees & B-Trees Comprehensive Notes",
                unit="Unit 3",
                description="Faculty authored handwritten & typed lecture notes covering AVL rotations, Splay Trees, and 2-3-4 tree splitting mechanisms with exam problems.",
                file_url="https://raw.githubusercontent.com/kalya/sample/main/avl_notes.pdf",
                file_name="Data_Structures_Unit3_Notes.pdf",
                file_size="3.2 MB",
                downloads_count=42
            ),
            models.FacultyPdf(
                faculty_name="Dr. Naveen Kumar",
                subject="Data Structures",
                title="Unit 4: Graph Theory, Dijkstra & Minimum Spanning Trees",
                unit="Unit 4",
                description="Official Vignan syllabus compilation containing adjacency lists, Prim's and Kruskal's algorithms with step-by-step trace tables.",
                file_url="https://raw.githubusercontent.com/kalya/sample/main/graph_notes.pdf",
                file_name="Graph_Algorithms_Unit4.pdf",
                file_size="4.1 MB",
                downloads_count=67
            )
        ]
        db.add_all(faculty_pdfs)
        db.commit()

        print("Database seeded successfully with all roles, resources, exams, submissions, books, doubts, live sessions, and PDFs!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()

