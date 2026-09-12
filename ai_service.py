import os
import re
import json
import difflib
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
load_dotenv()

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class AIService:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.api_key = self.gemini_key or self.groq_key or self.openai_key
        self.mode = "LLM_ENABLED" if self.api_key else "INTELLIGENT_SYNTHESIS"

    # =========================================================================
    # 1. SHORT ANSWER EVALUATION (RUBRIC & CONCEPT MATCHING)
    # =========================================================================
    def evaluate_short_answer(self, question_text: str, expected_answer: str, student_answer: str, max_marks: int = 2) -> dict:
        if not student_answer or not student_answer.strip():
            return {
                "marksObtained": 0.0,
                "maxMarks": max_marks,
                "percentage": 0.0,
                "feedback": "No answer provided.",
                "keywordsMatched": [],
                "missingConcepts": ["Complete response missing"]
            }

        student_norm = student_answer.lower().strip()
        expected_norm = expected_answer.lower().strip()

        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "of", "to", "and", "or", "that", "this", "it", "with", "by", "as", "for"}
        expected_words = [w for w in re.findall(r'\b[a-z0-9_]+\b', expected_norm) if w not in stop_words and len(w) > 2]
        student_words = set(re.findall(r'\b[a-z0-9_]+\b', student_norm))

        matched = [w for w in set(expected_words) if w in student_words]
        keyword_ratio = len(matched) / max(len(set(expected_words)), 1)
        seq_ratio = difflib.SequenceMatcher(None, expected_norm, student_norm).ratio()
        semantic_score = (keyword_ratio * 0.65) + (seq_ratio * 0.35)

        if semantic_score >= 0.75:
            awarded = float(max_marks)
            feedback = "Excellent conceptual explanation! Key principles and terminologies are clearly articulated."
        elif semantic_score >= 0.50:
            awarded = round(max_marks * 0.75, 1)
            feedback = "Good answer covering core concepts, but missing slight precision or key technical details."
        elif semantic_score >= 0.25:
            awarded = round(max_marks * 0.40, 1)
            feedback = "Partially correct. Identified some related ideas, but lacks depth and essential terminology."
        else:
            awarded = 0.0
            feedback = "Incorrect or insufficient conceptual grasp. Review recommended prerequisites."

        missing = [w for w in set(expected_words) if w not in student_words][:3]

        return {
            "marksObtained": awarded,
            "maxMarks": max_marks,
            "percentage": round((awarded / max_marks) * 100, 1),
            "feedback": feedback,
            "keywordsMatched": matched[:5],
            "missingConcepts": missing
        }

    # =========================================================================
    # 2. DIAGNOSTIC ASSESSMENT & LEARNING PATH SYNTHESIS
    # =========================================================================
    def analyze_diagnostic(self, responses: list) -> dict:
        topic_stats = {}
        for item in responses:
            topic = item.get("topic", "General DSA")
            is_correct = bool(item.get("isCorrect", False))
            if topic not in topic_stats:
                topic_stats[topic] = {"total": 0, "correct": 0}
            topic_stats[topic]["total"] += 1
            if is_correct:
                topic_stats[topic]["correct"] += 1

        topic_breakdown = []
        primary_gap = None
        min_acc = 101

        for topic, stat in topic_stats.items():
            acc = int(round((stat["correct"] / max(stat["total"], 1)) * 100))
            if acc >= 80:
                skill = "Strong"
                gap = "Low"
            elif acc >= 55:
                skill = "Medium"
                gap = "Medium"
            elif acc >= 35:
                skill = "Weak"
                gap = "High"
            else:
                skill = "Critical"
                gap = "Critical"

            topic_breakdown.append({
                "topic": topic,
                "accuracy": acc,
                "skillLevel": skill,
                "gap": gap,
                "correct": stat["correct"],
                "total": stat["total"]
            })

            if acc < min_acc:
                min_acc = acc
                primary_gap = {
                    "topic": topic,
                    "accuracy": acc,
                    "skillLevel": skill,
                    "gap": gap
                }

        if not topic_breakdown:
            topic_breakdown = [
                {"topic": "Arrays", "accuracy": 90, "skillLevel": "Strong", "gap": "Low"},
                {"topic": "Linked Lists", "accuracy": 71, "skillLevel": "Medium", "gap": "Medium"},
                {"topic": "Stacks", "accuracy": 88, "skillLevel": "Strong", "gap": "Low"},
                {"topic": "Queues", "accuracy": 68, "skillLevel": "Medium", "gap": "Medium"},
                {"topic": "Trees", "accuracy": 32, "skillLevel": "Weak", "gap": "High"},
                {"topic": "Graphs", "accuracy": 20, "skillLevel": "Critical", "gap": "Critical"},
                {"topic": "Sorting", "accuracy": 85, "skillLevel": "Strong", "gap": "Low"}
            ]
            primary_gap = {"topic": "Trees", "accuracy": 32, "skillLevel": "Weak", "gap": "High"}

        return {
            "topicBreakdown": topic_breakdown,
            "primaryGap": primary_gap or topic_breakdown[4],
            "recommendedFocus": f"Resolving {primary_gap['topic']} ({primary_gap['accuracy']}%) learning gap via a targeted 45-minute daily path"
        }

    # =========================================================================
    # 3. YOUTUBE / NPTEL LINK EXTRACTION & METADATA
    # =========================================================================
    def extract_youtube_id(self, url: str) -> Optional[str]:
        """Extracts 11-char YouTube video ID from various URL structures."""
        if not url:
            return None
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:shorts\/)([0-9A-Za-z_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def fetch_youtube_metadata(self, video_id: str) -> dict:
        """Queries YouTube oEmbed endpoint to retrieve genuine title & channel."""
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode())
                return {
                    "title": data.get("title", "Video Lecture"),
                    "author": data.get("author_name", "Academic Educator"),
                    "thumbnail": data.get("thumbnail_url", f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
                    "valid": True
                }
        except Exception:
            return {
                "title": f"YouTube Lecture ({video_id})",
                "author": "Computer Science Educator",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "valid": True
            }

    # =========================================================================
    # 4. AI LEARNING RESOURCE SIMPLIFIER (10-PART EASY STUDY NOTES)
    # =========================================================================
    def _generate_ai_study_notes(self, resource_meta: dict, content: str, title: str, topic_hint: str) -> Optional[dict]:
        groq_key = self.groq_key or os.getenv("GROQ_API_KEY")
        if not groq_key:
            return None

        topic_label = title or topic_hint or content[:100] or "Academic Learning Resource"
        content_preview = content[:2000] if content else "Topic: " + topic_label

        prompt = f"""You are an expert AI professor at Vignan University creating student-friendly, highly structured Easy Study Notes for: "{topic_label}".

Context / Resource provided:
{content_preview}

REQUIREMENTS:
1. Explain in simple, clear, everyday English with a relatable real-life analogy so ANY student can easily understand.
2. Provide specific, accurate, non-generic definitions and concepts tailored ONLY to "{topic_label}".
3. Provide practice questions with detailed answers that are 100% SPECIFIC to "{topic_label}". Never use generic placeholders or algorithm templates unless the input is about algorithms.

Return ONLY a single valid JSON object with NO extra text or markdown formatting matching this structure:
{{
  "topic": "{topic_label}",
  "summary": "2-sentence executive summary of {topic_label}.",
  "simpleExplanation": "Clear, student-friendly explanation using a relatable real-world analogy.",
  "keyConcepts": [
    "Key concept 1 specifically for {topic_label}",
    "Key concept 2 specifically for {topic_label}",
    "Key concept 3 specifically for {topic_label}",
    "Key concept 4 specifically for {topic_label}"
  ],
  "importantDefinitions": [
    {{"term": "Term 1", "definition": "Clear plain language definition for Term 1."}},
    {{"term": "Term 2", "definition": "Clear plain language definition for Term 2."}},
    {{"term": "Term 3", "definition": "Clear plain language definition for Term 3."}}
  ],
  "stepByStep": [
    "Step 1 walkthrough point",
    "Step 2 walkthrough point",
    "Step 3 walkthrough point",
    "Step 4 walkthrough point"
  ],
  "examples": [
    {{
      "title": "Practical Code or Structured Example",
      "code": "Provide relevant sample code, SQL query, algorithm, or structured text example for {topic_label}"
    }}
  ],
  "examNotes": [
    "High-probability exam question point 1",
    "High-probability exam question point 2",
    "High-probability exam question point 3"
  ],
  "quickRevision": [
    "60-second revision bullet 1",
    "60-second revision bullet 2",
    "60-second revision bullet 3",
    "60-second revision bullet 4"
  ],
  "practiceQuestions": [
    {{
      "question": "Specific Q1 about {topic_label}?",
      "answer": "Detailed, specific answer addressing Q1 for {topic_label}."
    }},
    {{
      "question": "Specific Q2 about {topic_label}?",
      "answer": "Detailed, specific answer addressing Q2 for {topic_label}."
    }},
    {{
      "question": "Specific Q3 about {topic_label}?",
      "answer": "Detailed, specific answer addressing Q3 for {topic_label}."
    }}
  ]
}}"""

        models = ['groq/compound-mini', 'qwen/qwen3.8-27b', 'openai/gpt-oss-120b', 'groq/compound']
        
        # Try Groq SDK
        if GROQ_AVAILABLE:
            try:
                client = Groq(api_key=groq_key)
                for m in models:
                    try:
                        comp = client.chat.completions.create(
                            model=m,
                            messages=[
                                {"role": "system", "content": "You are a JSON generator. You output ONLY valid JSON."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.2,
                            max_tokens=1500
                        )
                        if comp and comp.choices and comp.choices[0].message.content:
                            raw_text = comp.choices[0].message.content.strip()
                            clean_json = re.sub(r'^```json\s*', '', raw_text)
                            clean_json = re.sub(r'^```\s*', '', clean_json)
                            clean_json = re.sub(r'```$', '', clean_json.strip()).strip()
                            data = json.loads(clean_json[clean_json.find('{'):clean_json.rfind('}')+1])
                            data["resourceMeta"] = resource_meta
                            return data
                    except Exception:
                        continue
            except Exception:
                pass

        # Try Groq REST API Fallback
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
        for m in models:
            try:
                body = {
                    "model": m,
                    "messages": [
                        {"role": "system", "content": "You are a JSON generator. You output ONLY valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500
                }
                req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=12) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    raw_text = res_json["choices"][0]["message"]["content"].strip()
                    clean_json = re.sub(r'^```json\s*', '', raw_text)
                    clean_json = re.sub(r'^```\s*', '', clean_json)
                    clean_json = re.sub(r'```$', '', clean_json.strip()).strip()
                    data = json.loads(clean_json[clean_json.find('{'):clean_json.rfind('}')+1])
                    data["resourceMeta"] = resource_meta
                    return data
            except Exception:
                continue

        return None

    def simplify_resource(self, content_type: str, content: str, title: str = "", topic_hint: str = "") -> dict:
        """
        Processes any student learning resource (YouTube URL, NPTEL, PDF text, Notes, or Topic)
        and converts it into 10 structured, student-friendly Easy Study Notes using AI.
        """
        clean_content = (content or "").strip()
        resource_meta = {"type": content_type, "sourceTitle": title or "Uploaded Material"}

        # Handle YouTube / NPTEL URLs
        if content_type in ["youtube", "nptel"] or "youtube.com" in clean_content or "youtu.be" in clean_content:
            video_id = self.extract_youtube_id(clean_content)
            if video_id:
                meta = self.fetch_youtube_metadata(video_id)
                resource_meta["videoId"] = video_id
                resource_meta["youtubeUrl"] = f"https://www.youtube.com/watch?v={video_id}"
                resource_meta["sourceTitle"] = meta["title"]
                resource_meta["channel"] = meta["author"]
                resource_meta["thumbnail"] = meta["thumbnail"]
                topic_hint = topic_hint or meta["title"]
            elif "nptel" in clean_content.lower():
                resource_meta["sourceTitle"] = "NPTEL Video Lecture"
                resource_meta["channel"] = "NPTEL / IIT Ministry of Education"
                topic_hint = topic_hint or "Data Structures and Algorithms"

        # 1. Try Dynamic Groq AI Notes Generation
        ai_notes = self._generate_ai_study_notes(resource_meta, clean_content, title, topic_hint)
        if ai_notes:
            return ai_notes

        # 2. Fallback Knowledge Base if AI is unavailable
        subject_text = f"{title} {topic_hint} {clean_content}".lower()
        if any(k in subject_text for k in ["tree", "binary tree", "bst", "traversal", "inorder", "preorder", "postorder", "avl"]):
            return self._build_tree_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["graph", "bfs", "dfs", "dijkstra", "adjacency", "spanning"]):
            return self._build_graph_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["stack", "lifo", "postfix", "infix", "parenthesis"]):
            return self._build_stack_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["queue", "fifo", "circular queue", "priority queue", "deque"]):
            return self._build_queue_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["linked list", "singly", "doubly", "pointer", "node"]):
            return self._build_linked_list_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["sort", "quicksort", "mergesort", "binary search", "bubble"]):
            return self._build_sorting_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["recursion", "recursive", "base case", "factorial"]):
            return self._build_recursion_simplification(resource_meta, topic_hint)
        elif any(k in subject_text for k in ["operating system", "os", "process", "thread", "deadlock", "paging"]):
            return self._build_os_simplification(resource_meta, topic_hint)
        else:
            return self._build_generic_simplification(resource_meta, clean_content, topic_hint)

    def _build_tree_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Binary Trees & Tree Traversals",
            "summary": "Trees are non-linear, hierarchical data structures where nodes are organized in parent-child relationships with exactly one root node and subtrees.",
            "simpleExplanation": "Imagine a family tree or an organizational chart. Instead of items lined up one after another like beads on a necklace (arrays or linked lists), items branch out downwards. The very top item is called the 'Root'. From each node, you can branch left or right. In a Binary Tree, each parent can have AT MOST 2 children. This branching structure allows fast searching, dividing problems into halves.",
            "keyConcepts": [
                "Root Node: The topmost node with no parent.",
                "Binary Tree Constraint: At most 2 children per node (left child and right child).",
                "Leaf Nodes: Bottom nodes that have 0 children (both left and right are NULL).",
                "Tree Height / Depth: The maximum number of edges from the root down to the farthest leaf.",
                "Binary Search Tree (BST) Property: Left subtree values < Root value < Right subtree values."
            ],
            "importantDefinitions": [
                {"term": "Binary Tree", "definition": "A hierarchical data structure where every parent node has at most two children, termed the left child and right child."},
                {"term": "Inorder Traversal", "definition": "A depth-first recursive walk visiting: Left Subtree -> Root -> Right Subtree. In a BST, this always yields nodes in sorted ascending order."},
                {"term": "Preorder Traversal", "definition": "A traversal visiting: Root -> Left Subtree -> Right Subtree. Frequently used to serialize, clone, or create prefix expressions."},
                {"term": "Postorder Traversal", "definition": "A traversal visiting: Left Subtree -> Right Subtree -> Root. Essential for safe bottom-up memory deallocation and postfix evaluation."}
            ],
            "importantPoints": [
                "The maximum number of nodes on level 'i' of a binary tree is 2^i (assuming root is level 0).",
                "A binary tree with height 'h' has at most 2^(h+1) - 1 nodes.",
                "Inorder traversal of any valid Binary Search Tree produces strictly ascending sorted numbers.",
                "Recursive traversal requires O(h) extra stack memory where h is tree height. For a balanced tree, h = log N; for a skewed tree, h = N."
            ],
            "examples": [
                {
                    "title": "Inorder Traversal Example",
                    "code": "// Given tree with Root 2, Left 1, Right 3\nvoid inorder(Node* root) {\n    if (root == NULL) return;\n    inorder(root->left);       // 1. Visit Left (1)\n    printf(\"%d \", root->data); // 2. Print Root (2)\n    inorder(root->right);      // 3. Visit Right (3)\n}\n// Output: 1 2 3 (Sorted order!)"
                }
            ],
            "stepByStep": [
                "Step 1: Start execution at the Root node.",
                "Step 2: Check base condition: If the current pointer is NULL, return immediately (unwind stack).",
                "Step 3: Recursively call the traversal function on the Left Child.",
                "Step 4: Process / print the current node's data.",
                "Step 5: Recursively call the traversal function on the Right Child.",
                "Step 6: Return control to the parent activation frame."
            ],
            "examNotes": [
                "Expected Question: Differentiate between Inorder, Preorder, and Postorder with formulas.",
                "Important Property: A binary tree cannot be uniquely reconstructed using only Inorder or only Preorder. You MUST have Inorder + (Preorder OR Postorder).",
                "Time Complexity of all three traversals: O(N) since every node is visited exactly once.",
                "Auxiliary Space Complexity: O(h) on the function call stack."
            ],
            "quickRevision": [
                "• Binary Tree: Max 2 children per parent.",
                "• Inorder: Left -> Root -> Right (Produces sorted order in BST).",
                "• Preorder: Root -> Left -> Right (Cloning / copying trees).",
                "• Postorder: Left -> Right -> Root (Deleting nodes from bottom-up).",
                "• Balanced Height: O(log N); Degenerate/Skewed Height: O(N)."
            ],
            "practiceQuestions": [
                {
                    "question": "What is the Inorder traversal sequence for a BST containing nodes with keys [40, 20, 60, 10, 30]?",
                    "answer": "10, 20, 30, 40, 60 (Since Inorder traversal of any BST always outputs nodes in sorted ascending order)."
                },
                {
                    "question": "Why is Postorder traversal preferred when deleting all nodes in a dynamically allocated binary tree?",
                    "answer": "Because Postorder visits both children before visiting the parent. Deallocating children first ensures parent pointers remain valid and prevents memory leaks / dangling pointer errors."
                },
                {
                    "question": "If a binary tree has N nodes, what is the total number of NULL pointers (leaves + single children)?",
                    "answer": "Exactly N + 1 NULL pointers. Every node has 2 pointers (2N total). N-1 of them point to child nodes; therefore, 2N - (N - 1) = N + 1 are NULL."
                }
            ]
        }

    def _build_graph_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Graph Data Structures & BFS / DFS Traversals",
            "summary": "Graphs are non-linear collections of vertices (nodes) connected by edges that can model networks, road systems, social connections, and circuit dependencies.",
            "simpleExplanation": "Unlike trees where there is a top root and no loops, graphs can connect any node to any other node. Think of cities connected by highways or friends on social media. Because you can have cycles (loops where you return to a starting city), you MUST keep track of a 'Visited' list so you don't get stuck in an endless loop!",
            "keyConcepts": [
                "Vertices (V): The nodes or data entities in the graph.",
                "Edges (E): The connections between pairs of vertices (can be directed or undirected).",
                "Adjacency Matrix: A 2D array matrix[V][V] where matrix[i][j] = 1 if edge exists. Space: O(V^2).",
                "Adjacency List: An array of linked lists/vectors where each index stores its neighbors. Space: O(V + E) — optimal for sparse graphs.",
                "Breadth First Search (BFS): Level-by-level exploration using a Queue.",
                "Depth First Search (DFS): Deep exploration along each branch before backtracking, using a Stack or recursion."
            ],
            "importantDefinitions": [
                {"term": "Graph", "definition": "A mathematical structure G = (V, E) consisting of a set of vertices V and a set of edges E linking pairs of vertices."},
                {"term": "Breadth First Search (BFS)", "definition": "A traversal algorithm that visits all neighbor vertices at the present depth level before moving to the next level vertices. Implemented via FIFO Queue."},
                {"term": "Depth First Search (DFS)", "definition": "A traversal algorithm that dives as deep as possible along each branch before backtracking. Implemented via recursive call stack or LIFO Stack."},
                {"term": "Connected Component", "definition": "A maximal subgraph in which any two vertices are connected to each other by paths."}
            ],
            "importantPoints": [
                "BFS always finds the SHORTEST path in an unweighted graph.",
                "DFS is used for topological sorting, cycle detection, and strongly connected components.",
                "Time complexity for both BFS and DFS using Adjacency List is O(V + E).",
                "Always maintain a `bool visited[V]` array to prevent infinite cycles."
            ],
            "examples": [
                {
                    "title": "BFS Algorithm Pseudocode",
                    "code": "void BFS(int startVertex) {\n    queue<int> q;\n    visited[startVertex] = true;\n    q.push(startVertex);\n    while(!q.empty()) {\n        int curr = q.front(); q.pop();\n        cout << curr << \" \";\n        for(int neighbor : adj[curr]) {\n            if(!visited[neighbor]) {\n                visited[neighbor] = true;\n                q.push(neighbor);\n            }\n        }\n    }\n}"
                }
            ],
            "stepByStep": [
                "Step 1: Pick a starting vertex and mark it as visited.",
                "Step 2: Insert the starting vertex into a FIFO Queue.",
                "Step 3: Dequeue the front vertex and process/print it.",
                "Step 4: Loop through all immediate neighbors of this vertex.",
                "Step 5: For any neighbor not yet marked visited: mark it visited and enqueue it.",
                "Step 6: Repeat Steps 3-5 until the Queue becomes completely empty."
            ],
            "examNotes": [
                "Exam Trap: BFS cannot find shortest paths on weighted graphs with different edge weights (use Dijkstra's Algorithm instead).",
                "Space Complexity: Adjacency matrix is O(V^2); Adjacency list is O(V + E). For sparse graphs with few edges, Adjacency List is far more memory efficient.",
                "Cycle Detection: In an undirected graph, a cycle exists if a neighbor is already visited AND is NOT the parent of the current vertex."
            ],
            "quickRevision": [
                "• G = (V, E): Vertices + Edges.",
                "• BFS uses QUEUE -> Finds shortest path in unweighted graphs.",
                "• DFS uses STACK / RECURSION -> Used for cycle detection & topological sort.",
                "• Time: O(V + E) with Adjacency List; O(V^2) with Adjacency Matrix.",
                "• Never forget the `visited` array to prevent infinite loops!"
            ],
            "practiceQuestions": [
                {
                    "question": "Which data structure is essential for implementing Breadth First Search (BFS)?",
                    "answer": "A FIFO (First-In, First-Out) Queue data structure."
                },
                {
                    "question": "What is the time complexity of BFS and DFS when the graph is represented using an Adjacency Matrix?",
                    "answer": "O(V^2), because for every vertex we must scan all V entries in its row to find adjacent neighbors."
                },
                {
                    "question": "Can BFS be used to find the shortest path between two vertices in a weighted graph?",
                    "answer": "No. Standard BFS only works for unweighted graphs (or graphs where all edge weights are identical). For positive weighted graphs, Dijkstra's algorithm must be used."
                }
            ]
        }

    def _build_stack_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Stacks Data Structure & Applications",
            "summary": "A stack is a linear data structure following the LIFO (Last In, First Out) principle, where insertions and deletions happen only at the top.",
            "simpleExplanation": "Think of a stack of plates in a cafeteria. You place new plates on top, and when someone takes a plate, they take from the very top. The last plate placed on top is the first one removed! This simple rule makes stacks the backbone of function calls, undo buttons, and parenthesis matching.",
            "keyConcepts": [
                "LIFO Principle: Last-In, First-Out order.",
                "Push Operation: Adds an element to the top. O(1).",
                "Pop Operation: Removes the top element. O(1).",
                "Peek/Top Operation: Inspects the top element without removing it. O(1).",
                "Stack Overflow: Trying to push to a full stack.",
                "Stack Underflow: Trying to pop from an empty stack."
            ],
            "importantDefinitions": [
                {"term": "Stack", "definition": "A restricted linear list where elements are inserted and deleted from only one designated end called the top."},
                {"term": "LIFO", "definition": "Last-In, First-Out protocol governing stack operations."},
                {"term": "Infix Expression", "definition": "An expression format where the operator is placed between operands (e.g. A + B)."},
                {"term": "Postfix (RPN) Expression", "definition": "An expression format where the operator follows its operands (e.g. A B +), eliminating the need for parentheses."}
            ],
            "importantPoints": [
                "All fundamental stack operations (Push, Pop, Peek, IsEmpty) execute in strictly O(1) constant time.",
                "Function call execution in programming languages relies on the runtime Call Stack.",
                "Balanced parenthesis validation is solved elegantly using a stack in O(N) time.",
                "Infix to Postfix conversion uses an operator precedence stack."
            ],
            "examples": [
                {
                    "title": "Parenthesis Balancing with Stack",
                    "code": "bool isBalanced(string s) {\n    stack<char> st;\n    for(char c : s) {\n        if(c == '(' || c == '{' || c == '[') st.push(c);\n        else {\n            if(st.empty()) return false;\n            char top = st.top(); st.pop();\n            if((c == ')' && top != '(') ||\n               (c == '}' && top != '{') ||\n               (c == ']' && top != '[')) return false;\n        }\n    }\n    return st.empty();\n}"
                }
            ],
            "stepByStep": [
                "Step 1: Check if the stack is full before pushing (Stack Overflow check).",
                "Step 2: Increment the `top` index by 1.",
                "Step 3: Assign the incoming element at `arr[top]`.",
                "Step 4: To pop, check if `top == -1` (Stack Underflow check).",
                "Step 5: Store or return `arr[top]` and decrement `top` by 1."
            ],
            "examNotes": [
                "High Frequency Exam Topic: Convert Infix to Postfix using operator precedence table (^ > *, / > +, -).",
                "Evaluating Postfix Expression: Push operands to stack. When an operator is encountered, pop two operands, compute, and push result back.",
                "Tower of Hanoi problem is solved recursively with an implicit call stack in 2^N - 1 moves."
            ],
            "quickRevision": [
                "• LIFO: Last In, First Out.",
                "• Push, Pop, Peek: All are O(1) time.",
                "• Overflow: Full stack push; Underflow: Empty stack pop.",
                "• Applications: Undo/Redo, Call Stack, Parenthesis check, Expression evaluation."
            ],
            "practiceQuestions": [
                {
                    "question": "What is the postfix form of the infix expression: (A + B) * C?",
                    "answer": "A B + C *"
                },
                {
                    "question": "What happens if you attempt to perform a Pop operation on an empty stack?",
                    "answer": "Stack Underflow condition occurs."
                },
                {
                    "question": "Which data structure is utilized internally to manage recursive function calls?",
                    "answer": "The system runtime Call Stack."
                }
            ]
        }

    def _build_queue_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Queues & Circular Queue Mechanics",
            "summary": "A queue is a linear structure following the FIFO (First In, First Out) principle, where elements enter at the rear and depart from the front.",
            "simpleExplanation": "Imagine standing in line at a movie ticket counter. The person who arrives first gets served first! New arrivals join the back (Rear), while the person who finished leaves from the front (Front). A Circular Queue solves the wasted space problem of linear arrays by wrapping the rear pointer back to 0 using modulo arithmetic.",
            "keyConcepts": [
                "FIFO Principle: First-In, First-Out order.",
                "Enqueue: Insert an element at the Rear end. O(1).",
                "Dequeue: Remove an element from the Front end. O(1).",
                "Circular Queue: Modulo index wrapping `(rear + 1) % capacity`.",
                "Priority Queue: Elements dequeued based on priority rather than arrival order."
            ],
            "importantDefinitions": [
                {"term": "Queue", "definition": "A linear collection with two open ends: elements enter via the rear and leave via the front."},
                {"term": "FIFO", "definition": "First-In, First-Out principle governing queue access."},
                {"term": "Circular Queue", "definition": "A queue where the last position is connected back to the first position to make a circle, eliminating wasted memory space."},
                {"term": "Deque (Double-Ended Queue)", "definition": "A generalized queue allowing insertion and deletion at both front and rear ends."}
            ],
            "importantPoints": [
                "Linear array queues suffer from 'false overflow' when front moves forward and space behind it is unusable.",
                "Circular Queue uses `(index + 1) % size` to reuse freed front slots.",
                "Full condition in circular queue: `(rear + 1) % size == front`.",
                "Empty condition in circular queue: `front == -1`."
            ],
            "examples": [
                {
                    "title": "Circular Queue Enqueue Formula",
                    "code": "void enqueue(int val) {\n    if ((rear + 1) % SIZE == front) {\n        cout << \"Queue is Full! (Overflow)\";\n        return;\n    }\n    if (front == -1) front = 0; // First element\n    rear = (rear + 1) % SIZE;\n    arr[rear] = val;\n}"
                }
            ],
            "stepByStep": [
                "Step 1: Check if circular queue is full: `(rear + 1) % size == front`.",
                "Step 2: If empty (`front == -1`), set `front = 0`.",
                "Step 3: Update rear pointer: `rear = (rear + 1) % size`.",
                "Step 4: Store value at `arr[rear]`.",
                "Step 5: For dequeue, retrieve `arr[front]`.",
                "Step 6: If `front == rear`, queue has become empty: reset `front = rear = -1`."
            ],
            "examNotes": [
                "Exam Derivation: Show why Circular Queue solves linear queue false overflow.",
                "Number of elements in circular queue: `(rear - front + capacity) % capacity + 1`.",
                "Applications: CPU round-robin task scheduling, printer spooling, BFS graph traversal."
            ],
            "quickRevision": [
                "• FIFO: First In, First Out.",
                "• Enqueue at Rear, Dequeue at Front.",
                "• Circular Queue uses Modulo: `(rear + 1) % SIZE`.",
                "• Applications: BFS, CPU scheduling, buffer caching."
            ],
            "practiceQuestions": [
                {
                    "question": "What condition indicates that a Circular Queue of capacity N is completely full?",
                    "answer": "(rear + 1) % N == front"
                },
                {
                    "question": "Why is a circular queue preferred over a standard linear array queue?",
                    "answer": "Because a standard linear array queue cannot reuse freed slots after elements are dequeued from the front (false overflow), whereas a circular queue reclaims those spaces using modulo arithmetic."
                },
                {
                    "question": "Which traversal algorithm in graphs inherently depends on a Queue?",
                    "answer": "Breadth First Search (BFS)."
                }
            ]
        }

    def _build_linked_list_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Linked Lists (Singly, Doubly, Circular)",
            "summary": "A linked list is a linear data structure of nodes where each node stores data and a pointer/reference to the next node in dynamic memory.",
            "simpleExplanation": "Unlike arrays where items must sit side-by-side in continuous memory slots, linked list nodes can live anywhere in memory! Each node has two parts: the data it holds, and a pointer that points to where the next node lives. Inserting or deleting an element simply requires changing pointer arrows without shifting any other items!",
            "keyConcepts": [
                "Dynamic Size: Grows and shrinks at runtime without memory reallocation.",
                "Singly Linked List: Each node points only to the next node (`node->next`).",
                "Doubly Linked List: Each node points to both next and previous nodes (`node->prev`, `node->next`).",
                "Circular Linked List: The last node points back to the head node instead of NULL.",
                "Head Pointer: Stores the address of the first node.",
                "O(1) Insertion at Head: No shifting needed."
            ],
            "importantDefinitions": [
                {"term": "Node", "definition": "The basic building block of a linked list containing data and one or more pointer references."},
                {"term": "Head", "definition": "A reference pointer pointing to the first node in the linked list."},
                {"term": "Null Pointer", "definition": "A special pointer value in the last node indicating the termination of the list."},
                {"term": "Doubly Linked List", "definition": "A linked list where each node maintains two pointers: one to the forward neighbor and one to the backward neighbor."}
            ],
            "importantPoints": [
                "Arrays offer O(1) random access; Linked Lists require O(N) sequential traversal to access index i.",
                "Insertion/deletion at the beginning of a linked list is O(1) constant time.",
                "Reversing a singly linked list requires 3 pointers: `prev`, `curr`, and `next`.",
                "Always check for `head == NULL` to avoid segmentation faults (NullPointerExceptions)."
            ],
            "examples": [
                {
                    "title": "Reverse a Singly Linked List",
                    "code": "Node* reverseList(Node* head) {\n    Node* prev = NULL;\n    Node* curr = head;\n    while (curr != NULL) {\n        Node* nextTemp = curr->next; // 1. Save next\n        curr->next = prev;           // 2. Reverse pointer\n        prev = curr;                 // 3. Move prev forward\n        curr = nextTemp;             // 4. Move curr forward\n    }\n    return prev; // New head\n}"
                }
            ],
            "stepByStep": [
                "Step 1: To insert at head: allocate a new node with data.",
                "Step 2: Set `newNode->next = head`.",
                "Step 3: Update `head = newNode`.",
                "Step 4: To delete a node: traverse until finding the target node while tracking the previous node.",
                "Step 5: Set `prev->next = target->next`.",
                "Step 6: Free the target node's allocated memory."
            ],
            "examNotes": [
                "Classic Exam Problem: Detect a cycle/loop in a linked list using Floyd's Cycle-Finding Algorithm (Slow and Fast pointer).",
                "Comparison: Arrays have cache locality and fast access; Linked Lists have fast insertions/deletions without shifting.",
                "Memory Overhead: Each node requires extra bytes for pointer storage."
            ],
            "quickRevision": [
                "• Node = Data + Next pointer.",
                "• Insertion at Head: O(1); Access at Index: O(N).",
                "• Reverse: Use 3 pointers (prev, curr, next).",
                "• Cycle Detection: Floyd's Tortoise and Hare (slow by 1, fast by 2)."
            ],
            "practiceQuestions": [
                {
                    "question": "What is the time complexity to insert a new node at the beginning of a Singly Linked List?",
                    "answer": "O(1) constant time, because you only update the new node's next pointer to point to head and reset head."
                },
                {
                    "question": "How does Floyd's Cycle-Finding Algorithm detect a loop in a linked list?",
                    "answer": "By using two pointers: a slow pointer moving 1 step at a time, and a fast pointer moving 2 steps. If a cycle exists, the fast pointer will eventually catch up and equal the slow pointer."
                },
                {
                    "question": "Why can't Binary Search be applied efficiently directly on a Singly Linked List in O(log N) time?",
                    "answer": "Because linked lists do not support O(1) random index access. Finding the middle element requires O(N) sequential pointer traversal, making binary search degrade to O(N)."
                }
            ]
        }

    def _build_sorting_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Sorting & Searching Algorithms",
            "summary": "Sorting arranges items in ordered sequence (ascending/descending), while searching finds target values efficiently within collections.",
            "simpleExplanation": "Imagine looking up a word in a dictionary. If the dictionary was in random order, you would have to check every single page one by one (Linear Search O(N)). But because it is sorted alphabetically, you can open right in the middle, see if your word comes before or after, and eliminate half the book with each step (Binary Search O(log N))!",
            "keyConcepts": [
                "Binary Search: Divide-and-conquer search on sorted arrays. O(log N) time.",
                "Quicksort: Partition around a pivot element. Average O(N log N), Worst O(N^2).",
                "Mergesort: Divide into halves, recursively sort, and merge. Guaranteed O(N log N).",
                "Stability: A sorting algorithm is stable if it preserves relative order of duplicate keys.",
                "In-Place Sorting: Uses O(1) auxiliary space (e.g. Quicksort, Heapsort)."
            ],
            "importantDefinitions": [
                {"term": "Binary Search", "definition": "An algorithm that finds the position of a target value within a sorted array by repeatedly dividing the search interval in half."},
                {"term": "Quicksort", "definition": "A divide-and-conquer algorithm that selects a pivot element and partitions the array such that smaller elements precede it and larger follow it."},
                {"term": "Mergesort", "definition": "A stable divide-and-conquer algorithm that divides the array into halves, sorts them recursively, and merges the sorted halves."},
                {"term": "Algorithm Stability", "definition": "The property where elements with identical keys appear in the same relative order in the output as in the input."}
            ],
            "importantPoints": [
                "Binary Search strictly requires the input array to be pre-sorted.",
                "Comparison-based sorting has a mathematical lower bound of O(N log N).",
                "Mergesort requires O(N) extra temporary space for merging; Quicksort is in-place.",
                "Worst case for Quicksort occurs when the array is already sorted and the pivot chosen is always the first or last element."
            ],
            "examples": [
                {
                    "title": "Binary Search Iterative Implementation",
                    "code": "int binarySearch(int arr[], int n, int key) {\n    int low = 0, high = n - 1;\n    while (low <= high) {\n        int mid = low + (high - low) / 2;\n        if (arr[mid] == key) return mid;\n        else if (arr[mid] < key) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1; // Not found\n}"
                }
            ],
            "stepByStep": [
                "Step 1: Set `low = 0` and `high = n - 1`.",
                "Step 2: Calculate middle index: `mid = low + (high - low) / 2` (prevents integer overflow).",
                "Step 3: If `arr[mid] == target`, return `mid`.",
                "Step 4: If `arr[mid] < target`, discard left half: set `low = mid + 1`.",
                "Step 5: If `arr[mid] > target`, discard right half: set `high = mid - 1`.",
                "Step 6: Repeat until `low > high`. If not found, return -1."
            ],
            "examNotes": [
                "Exam Question: Compare Quicksort vs Mergesort (Time complexity, space complexity, stability, in-place).",
                "Mid Calculation: Explain why `mid = low + (high - low)/2` is safer than `(low + high)/2` in C/C++.",
                "Non-comparison sorts like Counting Sort and Radix Sort can achieve O(N) time under key range constraints."
            ],
            "quickRevision": [
                "• Binary Search: O(log N) — Must be SORTED.",
                "• Mergesort: Guaranteed O(N log N), Stable, O(N) extra space.",
                "• Quicksort: Average O(N log N), In-place, Worst O(N^2).",
                "• Best general-purpose: Hybrid (Timsort, Introsort)."
            ],
            "practiceQuestions": [
                {
                    "question": "What is the maximum number of comparisons required to binary search an element in a sorted array of 1,000,000 elements?",
                    "answer": "At most 20 comparisons, since 2^20 = 1,048,576 > 1,000,000 (ceil(log2(1,000,000)) = 20)."
                },
                {
                    "question": "Why is Mergesort preferred over Quicksort for sorting linked lists?",
                    "answer": "Because linked list nodes can be merged in-place in O(1) auxiliary space without random access, and Mergesort does not suffer from worst-case O(N^2) behavior."
                },
                {
                    "question": "What pivot selection strategy avoids Quicksort's worst-case O(N^2) time on already sorted arrays?",
                    "answer": "Randomized pivot selection or Median-of-Three pivot selection (taking the median of the first, middle, and last elements)."
                }
            ]
        }

    def _build_recursion_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Recursion & Call Stack Mechanics",
            "summary": "Recursion is a problem-solving technique where a function solves a problem by calling itself with a smaller subproblem until reaching a base termination case.",
            "simpleExplanation": "Think of Russian nesting dolls. You open the big doll to find a slightly smaller doll inside. You keep opening smaller dolls until you hit the tiny solid doll at the center that cannot open (the Base Case). Once you reach the center, you close the dolls back up one by one (Call Stack Unwinding). Every recursive function needs a base case, or it runs forever until your computer crashes with a Stack Overflow!",
            "keyConcepts": [
                "Base Case: The stopping condition that terminates recursion without further calls.",
                "Recursive Step: The function calling itself with a reduced, smaller input.",
                "Call Stack: Memory frames holding local variables and return addresses for each active call.",
                "Stack Unwinding: The return phase where values are calculated backwards.",
                "Tail Recursion: When the recursive call is the very last statement in the function."
            ],
            "importantDefinitions": [
                {"term": "Recursion", "definition": "A programming methodology where a function calls itself directly or indirectly to solve smaller instances of the same problem."},
                {"term": "Base Case", "definition": "The terminating condition that stops recursive execution and prevents infinite loops."},
                {"term": "Stack Overflow", "definition": "A runtime crash occurring when the function call stack exceeds its allotted memory due to missing or unreachable base cases."},
                {"term": "Recurrence Relation", "definition": "A mathematical equation defining a sequence based on its earlier terms (e.g. T(N) = 2T(N/2) + O(N))."}
            ],
            "importantPoints": [
                "Every recursive algorithm can be converted to an iterative one using an explicit stack.",
                "Without a base case, recursion leads directly to Stack Overflow.",
                "Each recursive call consumes extra stack memory proportional to the depth of recursion.",
                "Master Theorem provides an easy way to solve divide-and-conquer recurrence relations."
            ],
            "examples": [
                {
                    "title": "Factorial with Call Stack Trace",
                    "code": "int factorial(int n) {\n    if (n <= 1) return 1; // Base case!\n    return n * factorial(n - 1); // Recursive call\n}\n// Trace for factorial(3):\n// factorial(3) = 3 * factorial(2)\n// factorial(2) = 2 * factorial(1)\n// factorial(1) = 1 (Base case reached, unwinding!)\n// Returns: 2 * 1 = 2 -> 3 * 2 = 6"
                }
            ],
            "stepByStep": [
                "Step 1: Identify the smallest subproblem with a known, direct answer (Base Case).",
                "Step 2: Write the `if (base_condition) return base_value;` at the very top.",
                "Step 3: Break the main problem into one or more identical smaller subproblems.",
                "Step 4: Make the recursive call with the smaller parameter (e.g. `n - 1` or `n / 2`).",
                "Step 5: Combine the returned results from subproblems to compute the current answer.",
                "Step 6: Return the computed result to the caller."
            ],
            "examNotes": [
                "Exam Question: Solve recurrence relations using Master Theorem (T(N) = aT(N/b) + f(N)).",
                "Tail Call Optimization (TCO): Modern compilers can optimize tail-recursive functions to run in O(1) space like a while-loop.",
                "Contrast: Recursion is elegant and readable; Iteration is often faster with zero stack memory overhead."
            ],
            "quickRevision": [
                "• Recursion: Function calling itself with smaller input.",
                "• MUST have a BASE CASE to stop.",
                "• Memory: Uses function call stack (danger of Stack Overflow).",
                "• Unwinding: Evaluates answers on the way back up."
            ],
            "practiceQuestions": [
                {
                    "question": "What is the consequence of omitting a base case in a recursive function?",
                    "answer": "The function calls itself indefinitely until the memory reserved for the call stack is exhausted, causing a Stack Overflow runtime crash."
                },
                {
                    "question": "What is a Tail Recursive function?",
                    "answer": "A recursive function where the recursive call is the very last operation executed in the function with no pending computations."
                },
                {
                    "question": "Solve the recurrence relation T(N) = 2T(N/2) + O(N) using Master Theorem.",
                    "answer": "T(N) = O(N log N) (Standard Mergesort complexity, where a=2, b=2, log_b(a)=1, and f(N) = O(N^1))."
                }
            ]
        }

    def _build_os_simplification(self, meta: dict, hint: str) -> dict:
        return {
            "resourceMeta": meta,
            "topic": "Operating Systems & Process Management",
            "summary": "Operating Systems manage computer hardware resources, process execution, CPU scheduling, and virtual memory allocation.",
            "simpleExplanation": "Think of an Operating System as the air traffic controller of your computer. Multiple applications (processes) want to run on the CPU, write to memory, and read from disk simultaneously. The OS schedules which process gets the CPU, ensures one app cannot overwrite another app's memory, and gives every program the illusion of having the entire computer to itself.",
            "keyConcepts": [
                "Process vs Thread: A process is an independent executing program with its own memory space; a thread is a lightweight execution unit sharing process memory.",
                "CPU Scheduling: Algorithms (FCFS, SJF, Round Robin, Priority) that decide which ready process gets the CPU.",
                "Virtual Memory & Paging: Splitting memory into fixed-size pages and mapping virtual addresses to physical RAM frames.",
                "Deadlock: A state where two or more processes are blocked indefinitely, each holding a resource needed by another.",
                "4 Coffman Deadlock Conditions: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait."
            ],
            "importantDefinitions": [
                {"term": "Process", "definition": "A program in execution, including program counter, stack, and data section."},
                {"term": "Thread", "definition": "A lightweight unit of CPU execution within a process sharing the code, data, and open file descriptors."},
                {"term": "Deadlock", "definition": "A situation where a set of processes are blocked because each process is holding a resource and waiting for another resource held by another process."},
                {"term": "Paging", "definition": "A memory management scheme that eliminates the need for contiguous physical memory allocation by dividing virtual memory into pages."}
            ],
            "importantPoints": [
                "Context switching involves saving the CPU register state of the current process and loading the state of the next process (pure overhead).",
                "Round Robin scheduling uses a time quantum; if quantum is too small, excessive context switching occurs; if too large, it degrades to FCFS.",
                "Banker's Algorithm is used for Deadlock Avoidance by testing for safe states.",
                "Page Fault occurs when a program tries to access a page that is mapped in virtual memory but not currently loaded into physical RAM."
            ],
            "examples": [
                {
                    "title": "Round Robin CPU Scheduling Concept",
                    "code": "// Given processes P1(burst 6), P2(burst 4) with Quantum = 3\n// Time 0-3: P1 executes for 3 units (remaining: 3)\n// Time 3-6: P2 executes for 3 units (remaining: 1)\n// Time 6-9: P1 completes remaining 3 units\n// Time 9-10: P2 completes remaining 1 unit"
                }
            ],
            "stepByStep": [
                "Step 1: Process is created and placed in the 'Ready Queue'.",
                "Step 2: CPU Scheduler dispatches the process to the 'Running' state.",
                "Step 3: If an I/O request occurs, the process moves to 'Waiting/Blocked' state.",
                "Step 4: Once I/O finishes, it transitions back to the 'Ready' state.",
                "Step 5: When execution finishes, the process moves to the 'Terminated' state."
            ],
            "examNotes": [
                "High Frequency Exam Topic: 4 Necessary Conditions for Deadlock (Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait).",
                "Process Synchronization: Peterson's Solution, Semaphores (Wait/Signal), and Mutex Locks.",
                "Belady's Anomaly: In FIFO page replacement, increasing the number of page frames can sometimes increase the number of page faults."
            ],
            "quickRevision": [
                "• Process = Program in execution (heavyweight, isolated memory).",
                "• Thread = Lightweight process (shares memory space).",
                "• Deadlock: 4 conditions (Mutual exclusion, Hold&wait, No preemption, Circular wait).",
                "• Scheduling: Round Robin for time-sharing, SJF for minimum average waiting time."
            ],
            "practiceQuestions": [
                {
                    "question": "What are the four Coffman conditions necessary for a deadlock to occur?",
                    "answer": "1. Mutual Exclusion, 2. Hold and Wait, 3. No Preemption, 4. Circular Wait."
                },
                {
                    "question": "What is the primary difference between a Process and a Thread?",
                    "answer": "A process has its own isolated memory address space and system resources, whereas threads exist within a process and share the same memory space, code section, and global variables."
                },
                {
                    "question": "What is Belady's Anomaly in operating systems?",
                    "answer": "The phenomenon in the FIFO page replacement algorithm where increasing the number of page frames leads to an unexpected increase in the number of page faults."
                }
            ]
        }

    def _build_generic_simplification(self, meta: dict, content: str, hint: str) -> dict:
        topic_name = hint or meta.get("sourceTitle") or "Academic Concept"
        preview = (content[:150] + "...") if len(content) > 150 else content
        return {
            "resourceMeta": meta,
            "topic": topic_name,
            "summary": f"Simplified study breakdown for {topic_name}. Formatted for quick comprehension and exam readiness.",
            "simpleExplanation": f"This material covers {topic_name}. In simple terms, this concept establishes fundamental rules and operations designed to organize information efficiently, optimize computer execution time, and eliminate redundant operations.",
            "keyConcepts": [
                f"Core Principle: Structured representation of {topic_name}.",
                "Efficiency: Minimizing execution steps and memory footprint.",
                "Modularity: Separating operations into clean, reusable procedures.",
                "Boundary Conditions: Handling empty states, edge inputs, and overflow conditions."
            ],
            "importantDefinitions": [
                {"term": topic_name, "definition": f"A foundational academic topic focusing on computational efficiency and structured logic."},
                {"term": "Time Complexity", "definition": "A mathematical representation of the number of operations executed as input size scales."},
                {"term": "Space Complexity", "definition": "The memory volume required by an algorithm to execute to completion."}
            ],
            "importantPoints": [
                "Always check edge cases (e.g. empty inputs, single element, negative values).",
                "Understand the trade-off between execution speed and memory consumption.",
                "Formulate a step-by-step trace before writing code.",
                "Review practice questions regularly to reinforce conceptual memory."
            ],
            "examples": [
                {
                    "title": f"{topic_name} Implementation Pattern",
                    "code": f"// Standard template for {topic_name}\nvoid process() {{\n    // 1. Initialize data\n    // 2. Execute logic\n    // 3. Return verified output\n}}"
                }
            ],
            "stepByStep": [
                "Step 1: Parse the input and check all prerequisite requirements.",
                "Step 2: Initialize required tracking variables and memory pointers.",
                "Step 3: Execute the core operational sequence.",
                "Step 4: Verify boundary conditions and finalize output."
            ],
            "examNotes": [
                f"Key Exam Focus: Define {topic_name}, draw the diagram/flowchart, and state the Time & Space complexities.",
                "Always write down the base case and boundary condition checks in written exams to score full marks."
            ],
            "quickRevision": [
                f"• Focus on core definition of {topic_name}.",
                "• Remember the primary operational time complexity.",
                "• Master the standard edge case handling steps."
            ],
            "practiceQuestions": [
                {
                    "question": f"What is the primary advantage of utilizing {topic_name}?",
                    "answer": "It provides a standardized, optimized approach to solving problems efficiently with minimal computational overhead."
                },
                {
                    "question": "What is the first step you should verify when processing any algorithm?",
                    "answer": "Check boundary/edge cases (such as null pointers, empty data structures, or index out of range)."
                }
            ]
        }

    # =========================================================================
    # 5. TOPIC LEARNING HIERARCHY (INTERACTIVE FOR TOPIC GAP MAP)
    # =========================================================================
    def get_topic_hierarchy(self, topic_id: str) -> dict:
        """
        Returns the structured, interactive topic hierarchy answering:
        'What exactly should I learn first, next, and after that?'
        Includes subtopics, explanations, key concepts, practice Q&A, and verified real YouTube links.
        """
        normalized = topic_id.lower().strip()

        if "tree" in normalized:
            return {
                "topicId": "trees",
                "topicName": "Trees",
                "skillLevel": "Weak (32%)",
                "overview": "Hierarchical non-linear data structure. Master these 5 progressive milestones to completely eliminate your learning gap.",
                "hierarchy": [
                    {
                        "category": "Step 1: Basics of Trees",
                        "description": "Nodes, Edges, Root, Leaf, Height, Depth and Core Terminology",
                        "subtopics": [
                            {
                                "id": "tree-basics",
                                "name": "Basics of Trees (Nodes, Edges, Root, Leaf, Height, Depth)",
                                "simpleExplanation": "Unlike linear arrays or linked lists where data is sequential, a Tree is a hierarchical structure where every item branches out. Think of a family tree or folder directory! The single starting node is the Root. Lines connecting nodes are Edges. Nodes without any children are Leaves. Depth measures distance from root down to a node, while Height measures distance from a node down to its farthest leaf.",
                                "keyConcepts": ["Root Node", "Parent, Child & Sibling", "Leaf Nodes (Degree 0)", "Height vs Depth", "N Nodes = N-1 Edges"],
                                "video": {
                                    "title": "Introduction to Trees in Data Structures",
                                    "channel": "mycodeschool",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=qH6yxkw0u78",
                                    "videoId": "qH6yxkw0u78",
                                    "duration": "11 min"
                                },
                                "notes": "A tree with N nodes always possesses exactly N - 1 edges. Depth of the root node is 0 (or 1 depending on convention).",
                                "practiceQuestions": [
                                    {
                                        "question": "What is a Leaf node in a tree hierarchy?",
                                        "answer": "A node with degree 0 that has no children (both left and right pointers are NULL)."
                                    },
                                    {
                                        "question": "If a tree has 25 total vertices/nodes, exactly how many edges does it contain?",
                                        "answer": "Exactly 24 edges (Formula: Edges = Nodes - 1 = 25 - 1 = 24)."
                                    },
                                    {
                                        "question": "What is the difference between node Depth and node Height?",
                                        "answer": "Depth is the number of edges from the root to that specific node. Height is the maximum number of edges from that node down to its deepest leaf."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 2: Tree Representation",
                        "description": "Array and Linked Representation of Binary Trees",
                        "subtopics": [
                            {
                                "id": "tree-representation",
                                "name": "Tree Representation (Array and Linked Representation)",
                                "simpleExplanation": "Computers store binary trees in two main ways: 1) Linked Representation: Each node is a struct/object holding data, a left pointer, and a right pointer (most dynamic and flexible). 2) Array Representation: For 0-based indexing, if a parent is at index i, its left child is at 2*i + 1, and right child is at 2*i + 2. Array representation is ideal for Complete Binary Trees (like Heaps) but wastes space on skewed trees.",
                                "keyConcepts": ["Linked Node (data, left, right)", "Array indexing: Left = 2*i + 1", "Array indexing: Right = 2*i + 2", "Parent index: floor((i-1)/2)", "Space overhead of skewed trees"],
                                "video": {
                                    "title": "Binary Tree Representation in C++",
                                    "channel": "mycodeschool",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=9Jry5-82I68",
                                    "videoId": "9Jry5-82I68",
                                    "duration": "13 min"
                                },
                                "notes": "Sequential array representation saves pointer memory overhead for dense/complete trees, whereas linked representation handles arbitrary, sparse shapes without wasting memory.",
                                "practiceQuestions": [
                                    {
                                        "question": "In a 0-indexed array representation of a binary tree, where is the right child of the node at index 4?",
                                        "answer": "At index 10 (Formula: 2 * 4 + 2 = 10)."
                                    },
                                    {
                                        "question": "Why is linked representation preferred over array representation for skewed binary trees?",
                                        "answer": "Because a skewed tree in an array requires an exponential array size (up to 2^h slots) with most entries empty (NULL), causing severe memory wastage."
                                    },
                                    {
                                        "question": "How many pointer fields are required in a typical linked binary tree node struct?",
                                        "answer": "Two pointers: one pointing to the left child node and one pointing to the right child node."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 3: Tree Traversals",
                        "description": "Inorder, Preorder, Postorder Recursive Traces",
                        "subtopics": [
                            {
                                "id": "tree-traversals",
                                "name": "Tree Traversals (Inorder, Preorder, Postorder)",
                                "simpleExplanation": "Because trees aren't linear, we visit nodes using Depth-First traversals based on when the Root (N) is visited relative to Left (L) and Right (R): 1) Preorder (Root -> Left -> Right): Great for copying or serializing trees. 2) Inorder (Left -> Root -> Right): Gives elements in ascending sorted order when executed on a Binary Search Tree! 3) Postorder (Left -> Right -> Root): Essential for bottom-up tasks like deleting a tree or calculating subtree sizes safely.",
                                "keyConcepts": ["Preorder: Node -> Left -> Right (N-L-R)", "Inorder: Left -> Node -> Right (L-N-R)", "Postorder: Left -> Right -> Node (L-R-N)", "Call Stack Frame Unwinding", "O(N) Time, O(h) Space"],
                                "video": {
                                    "title": "Binary Tree Traversal: Preorder, Inorder, Postorder",
                                    "channel": "mycodeschool",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=gm8DUJJhmY4",
                                    "videoId": "gm8DUJJhmY4",
                                    "duration": "12 min"
                                },
                                "notes": "Every node is visited once, giving O(N) time complexity. Memory complexity is O(h) where h is the tree height, corresponding to maximum recursion call stack frames.",
                                "practiceQuestions": [
                                    {
                                        "question": "What is the Inorder traversal of a binary search tree containing keys 15 (root), 10 (left), and 20 (right)?",
                                        "answer": "10, 15, 20 (Left -> Root -> Right)."
                                    },
                                    {
                                        "question": "Why must Postorder traversal be used when freeing or deleting all nodes of a dynamic binary tree?",
                                        "answer": "Because children must be deleted before their parent is freed. If the parent is freed first, pointers to its children are lost, causing memory leaks or dangling pointer segmentation faults."
                                    },
                                    {
                                        "question": "Which traversal sequence visits the root node first before visiting any descendant nodes?",
                                        "answer": "Preorder traversal (Root -> Left -> Right)."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 4: Binary Search Tree (BST)",
                        "description": "BST Search, Insertion, and BST Ordering Invariant",
                        "subtopics": [
                            {
                                "id": "bst-search-insertion",
                                "name": "Binary Search Tree (BST search, insertion, property)",
                                "simpleExplanation": "A Binary Search Tree (BST) enforces a strict ordering rule for every single node: all keys in its left subtree MUST be strictly less than the node's key, and all keys in its right subtree MUST be strictly greater than the node's key. Searching or inserting is just like binary search: if the target is smaller, recurse left; if larger, recurse right! This gives blazing fast O(log N) operations on balanced trees.",
                                "keyConcepts": ["BST Invariant: Left < Root < Right", "Search in O(h) / O(log N)", "Insertion at Leaf position", "Degradation to O(N) in Skewed BST", "No duplicate keys standard"],
                                "video": {
                                    "title": "Binary Search Tree - Implementation in C/C++",
                                    "channel": "mycodeschool",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=pYT9F8_LFTM",
                                    "videoId": "pYT9F8_LFTM",
                                    "duration": "15 min"
                                },
                                "notes": "In a balanced BST of N nodes, search and insertion run in O(log N) time. If keys are inserted in strictly sorted order without rebalancing, the BST degrades into a linear linked list running in O(N) time.",
                                "practiceQuestions": [
                                    {
                                        "question": "State the fundamental property that distinguishes a Binary Search Tree from a general Binary Tree.",
                                        "answer": "For every node, all values in its left subtree are strictly less than its value, and all values in its right subtree are strictly greater than its value."
                                    },
                                    {
                                        "question": "Where does a newly inserted key always end up in a standard Binary Search Tree?",
                                        "answer": "As a new leaf node at an empty NULL pointer position."
                                    },
                                    {
                                        "question": "What is the worst-case time complexity of searching in a BST containing N keys, and when does it occur?",
                                        "answer": "O(N) time complexity, occurring when keys are inserted in sorted order forming a completely skewed tree (degenerate tree)."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 5: Deletion in BST",
                        "description": "Handling Case 1 (Leaf), Case 2 (1 Child), and Case 3 (2 Children)",
                        "subtopics": [
                            {
                                "id": "bst-deletion-cases",
                                "name": "Deletion in BST (Case 1, Case 2, Case 3)",
                                "simpleExplanation": "Deleting from a BST requires maintaining the BST invariant across three specific scenarios: 1) Case 1 (Node is a Leaf): Simply delete the node and set the parent's pointer to NULL. 2) Case 2 (Node has 1 Child): Bypass the node by linking the parent directly to the node's only child. 3) Case 3 (Node has 2 Children): You cannot simply remove it! Instead, find its Inorder Successor (the smallest element in its right subtree), copy the successor's data into this node, and then delete the successor node (which will only have 0 or 1 child).",
                                "keyConcepts": ["Case 1: Leaf node -> delete & set parent child to NULL", "Case 2: 1 child -> replace node with its child", "Case 3: 2 children -> replace with Inorder Successor", "Inorder Successor = Smallest node in Right Subtree", "Inorder Predecessor = Largest node in Left Subtree"],
                                "video": {
                                    "title": "Delete a Node from Binary Search Tree",
                                    "channel": "mycodeschool",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=gcULXE7ViZw",
                                    "videoId": "gcULXE7ViZw",
                                    "duration": "19 min"
                                },
                                "notes": "Inorder Successor is guaranteed to have at most one child (a right child), making its subsequent deletion trivial (Case 1 or Case 2).",
                                "practiceQuestions": [
                                    {
                                        "question": "How do you locate the Inorder Successor of a node in a Binary Search Tree?",
                                        "answer": "Move one step to the node's right child, and then follow left child pointers continuously until reaching the leftmost node."
                                    },
                                    {
                                        "question": "In BST deletion Case 2 (target node has exactly 1 child), what is the pointer adjustment?",
                                        "answer": "The target node's parent is linked directly to the target node's single child, bypassing and freeing the target node."
                                    },
                                    {
                                        "question": "Can the Inorder Successor of a node ever have a left child?",
                                        "answer": "No, because if it had a left child, that left child would be smaller, meaning this node was not the true successor."
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

        elif "graph" in normalized:
            return {
                "topicId": "graphs",
                "topicName": "Graphs",
                "skillLevel": "Critical (20%)",
                "overview": "Network of vertices and edges with cycles. Learn representations, Breadth-First Search (Queue), and Depth-First Search (Stack/Recursion).",
                "hierarchy": [
                    {
                        "category": "Step 1: Graph Representations",
                        "description": "Adjacency Matrix vs Adjacency List memory trade-offs",
                        "subtopics": [
                            {
                                "id": "graph-representations",
                                "name": "Adjacency Matrix vs Adjacency List",
                                "simpleExplanation": "Graphs connect vertices (V) using edges (E). An Adjacency Matrix is a 2D V x V grid of 1s and 0s: super fast O(1) edge lookup, but wastes O(V^2) memory on sparse graphs. An Adjacency List stores an array of linked lists/vectors where index i holds only nodes directly connected to vertex i: uses O(V+E) memory, making it the industry standard for realistic networks.",
                                "keyConcepts": ["Vertices & Edges", "Adjacency Matrix O(V^2)", "Adjacency List O(V+E)", "Sparse vs Dense Graphs", "Directed vs Undirected"],
                                "video": {
                                    "title": "Graph Representations: Adjacency Matrix & List",
                                    "channel": "Abdul Bari",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=DBRW8nwZV-g",
                                    "videoId": "DBRW8nwZV-g",
                                    "duration": "19 min"
                                },
                                "notes": "Adjacency List is optimal for sparse graphs (E << V^2). Adjacency Matrix is optimal for dense graphs where edge existence checks dominate.",
                                "practiceQuestions": [
                                    {
                                        "question": "What is the memory space required by an Adjacency Matrix for a graph with V vertices?",
                                        "answer": "O(V^2) space, regardless of the number of edges."
                                    },
                                    {
                                        "question": "What is the space complexity of an Adjacency List representation for an undirected graph with V vertices and E edges?",
                                        "answer": "O(V + 2E) which simplifies to O(V + E)."
                                    },
                                    {
                                        "question": "How quickly can you verify if an edge exists between vertex u and vertex v using an Adjacency Matrix?",
                                        "answer": "O(1) constant time by checking matrix[u][v]."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 2: Breadth First Search",
                        "description": "Queue-driven level-by-level shortest path traversal",
                        "subtopics": [
                            {
                                "id": "graph-bfs",
                                "name": "Breadth First Search (BFS) & Shortest Path",
                                "simpleExplanation": "BFS explores a graph layer by layer, visiting all immediate neighbors before moving to neighbors of neighbors. It uses a FIFO Queue and a boolean `visited` array to prevent revisiting vertices. In unweighted graphs, BFS guarantees finding the shortest path in terms of edge count!",
                                "keyConcepts": ["FIFO Queue", "Visited Array tracking", "Shortest Path in Unweighted Graph", "Time O(V+E)"],
                                "video": {
                                    "title": "Breadth First Search (BFS) Algorithm",
                                    "channel": "Abdul Bari",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=pcKY4hjDrxk",
                                    "videoId": "pcKY4hjDrxk",
                                    "duration": "24 min"
                                },
                                "notes": "Always mark vertices as visited immediately when pushing to the queue to avoid redundant enqueue operations.",
                                "practiceQuestions": [
                                    {
                                        "question": "Which data structure is fundamentally required for implementing Breadth First Search?",
                                        "answer": "A FIFO Queue."
                                    },
                                    {
                                        "question": "Why is BFS guaranteed to find the shortest path in an unweighted graph?",
                                        "answer": "Because it visits vertices in order of increasing distance (edges) from the starting vertex: all distance-1 nodes first, then distance-2, and so forth."
                                    },
                                    {
                                        "question": "What is the total time complexity of BFS using an Adjacency List?",
                                        "answer": "O(V + E), where V is vertices and E is edges."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 3: Depth First Search",
                        "description": "Stack/Recursion exploration and backtracking",
                        "subtopics": [
                            {
                                "id": "graph-dfs",
                                "name": "Depth First Search (DFS) & Cycle Detection",
                                "simpleExplanation": "DFS plunges as deep down a branch as possible until hitting a dead end or visited vertex, then backtracks to explore other paths. It uses recursion (or an explicit LIFO Stack) and a visited set. Crucial for detecting cycles, topological sorting, and maze solving!",
                                "keyConcepts": ["Recursion / LIFO Stack", "Backtracking", "Cycle Detection", "Connected Components", "Time O(V+E)"],
                                "video": {
                                    "title": "Depth First Search (DFS) Algorithm",
                                    "channel": "Abdul Bari",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=vf-cxgUXcMk",
                                    "videoId": "vf-cxgUXcMk",
                                    "duration": "21 min"
                                },
                                "notes": "In an undirected graph, a cycle exists if an adjacent visited vertex is encountered that is NOT the direct parent in the DFS tree.",
                                "practiceQuestions": [
                                    {
                                        "question": "How does DFS detect a cycle in an undirected graph?",
                                        "answer": "If during traversal from node u to neighbor v, v is already marked as visited and v is not the parent of u, a cycle is present."
                                    },
                                    {
                                        "question": "Which data structure implicitly powers recursive Depth First Search?",
                                        "answer": "The system call stack."
                                    },
                                    {
                                        "question": "What is Topological Sort and which graph type does it apply to?",
                                        "answer": "A linear ordering of vertices such that for every directed edge u -> v, u comes before v. It only applies to Directed Acyclic Graphs (DAGs)."
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

        # Default DSA hierarchy (Arrays, Stacks, Queues, Linked Lists, Sorting)
        else:
            return {
                "topicId": "arrays",
                "topicName": "Arrays & Searching",
                "skillLevel": "Strong (90%)",
                "overview": "Contiguous memory structures enabling O(1) random access indexing.",
                "hierarchy": [
                    {
                        "category": "Step 1: Contiguous Memory & Direct Addressing",
                        "description": "Memory layout and O(1) indexing mechanics",
                        "subtopics": [
                            {
                                "id": "array-indexing",
                                "name": "Contiguous Allocation & Direct Addressing",
                                "simpleExplanation": "Arrays store items right next to each other in physical RAM. Because every element occupies the exact same number of bytes, calculating any index's address is instant math: Base + index * size. This yields O(1) constant time random access.",
                                "keyConcepts": ["Contiguous RAM", "O(1) Random Access", "Fixed vs Dynamic Vectors", "Cache Line Locality"],
                                "video": {
                                    "title": "Introduction to Arrays in Data Structures",
                                    "channel": "Abdul Bari",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=73mS_B-w1tY",
                                    "videoId": "73mS_B-w1tY",
                                    "duration": "18 min"
                                },
                                "notes": "Arrays have unbeatable spatial cache locality, making sequential reads much faster than pointer-chasing in linked lists.",
                                "practiceQuestions": [
                                    {
                                        "question": "What is the formula to calculate the memory address of an element at index i in a 0-indexed array?",
                                        "answer": "Address(i) = BaseAddress + (i * sizeof(DataType))"
                                    },
                                    {
                                        "question": "Why is insertion at index 0 of an array an O(N) operation?",
                                        "answer": "Because all N existing elements must be shifted one position to the right to make room."
                                    },
                                    {
                                        "question": "What is cache locality and why do arrays benefit from it?",
                                        "answer": "Contiguous memory layout allows CPU caches to prefetch neighboring elements into cache lines ahead of time, dramatically speeding up access."
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "category": "Step 2: Binary Search Optimization",
                        "description": "Logarithmic divide-and-conquer on sorted collections",
                        "subtopics": [
                            {
                                "id": "binary-search",
                                "name": "Binary Search Algorithm (O(log N))",
                                "simpleExplanation": "Binary search finds target values in sorted arrays by repeatedly comparing with the middle element and halving the search space. Instead of checking N items, it checks at most log2(N) items. Searching 1,000,000 items takes only 20 comparisons!",
                                "keyConcepts": ["Sorted precondition", "Divide and conquer", "Middle index: low + (high - low) / 2", "O(log N) Time"],
                                "video": {
                                    "title": "Binary Search Algorithm - Iterative & Recursive",
                                    "channel": "Abdul Bari",
                                    "youtubeUrl": "https://www.youtube.com/watch?v=C2apEw9pgtw",
                                    "videoId": "C2apEw9pgtw",
                                    "duration": "22 min"
                                },
                                "notes": "Always compute mid using `low + (high - low) / 2` to avoid 32-bit integer overflow bugs caused by `(low + high) / 2`.",
                                "practiceQuestions": [
                                    {
                                        "question": "What is the mandatory prerequisite before Binary Search can be executed on an array?",
                                        "answer": "The array elements must already be in sorted order."
                                    },
                                    {
                                        "question": "What is the maximum number of comparisons needed to find an element in a sorted array of 1,024 items using binary search?",
                                        "answer": "log2(1024) = 10 comparisons."
                                    },
                                    {
                                        "question": "Why is `low + (high - low) / 2` preferred over `(low + high) / 2`?",
                                        "answer": "To prevent arithmetic integer overflow when `low + high` exceeds the maximum capacity of a 32-bit signed integer."
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

    # =========================================================================
    # 6. DEFAULT IMPORTANT NOTES FOR YOU (CURRICULUM BASED)
    # =========================================================================
    def get_default_important_notes(self, department: str = "CSE", year: str = "2") -> list:
        """
        Returns structured syllabus-aligned default study notes for Data Structures students
        (Arrays, Linked Lists, Stacks, Queues, Trees, Graphs, Sorting, Recursion).
        """
        return [
            {
                "id": "note-trees",
                "topic": "Binary Trees & Traversal Order",
                "department": "CSE",
                "badge": "Unit III • High Priority",
                "shortSummary": "Trees branch out hierarchically. Inorder (L-N-R) gives sorted keys in BST; Postorder (L-R-N) is used for bottom-up node deletion.",
                "readTime": "4 min read",
                "keyFormula": "Inorder = Left -> Root -> Right",
                "simplification": self._build_tree_simplification({"type": "syllabus", "sourceTitle": "Unit 3: Binary Trees"}, "Binary Trees")
            },
            {
                "id": "note-graphs",
                "topic": "Graph BFS vs DFS Exploration",
                "department": "CSE",
                "badge": "Unit IV • Core Exam Topic",
                "shortSummary": "BFS uses a Queue to find shortest paths in unweighted graphs; DFS uses a Stack/Recursion for cycle detection and topological sorting.",
                "readTime": "5 min read",
                "keyFormula": "BFS = Queue; DFS = Stack/Recursion",
                "simplification": self._build_graph_simplification({"type": "syllabus", "sourceTitle": "Unit 4: Graph Algorithms"}, "Graphs")
            },
            {
                "id": "note-stacks",
                "topic": "Stack LIFO & Expression Evaluation",
                "department": "CSE",
                "badge": "Unit II • Fundamental",
                "shortSummary": "Stacks enforce Last-In, First-Out (LIFO). Used for function call stack frames, balanced parenthesis checking, and infix-to-postfix conversion.",
                "readTime": "3 min read",
                "keyFormula": "Push/Pop/Peek = O(1) Constant Time",
                "simplification": self._build_stack_simplification({"type": "syllabus", "sourceTitle": "Unit 2: Stacks"}, "Stacks")
            },
            {
                "id": "note-queues",
                "topic": "Circular Queue Modulo Arithmetic",
                "department": "CSE",
                "badge": "Unit II • Exam Formula",
                "shortSummary": "Linear array queues cause false overflow. Circular queues reclaim freed front space using `(rear + 1) % capacity == front`.",
                "readTime": "4 min read",
                "keyFormula": "NextIndex = (index + 1) % Capacity",
                "simplification": self._build_queue_simplification({"type": "syllabus", "sourceTitle": "Unit 2: Queues"}, "Queues")
            },
            {
                "id": "note-linked-lists",
                "topic": "Linked Lists & Pointer Manipulation",
                "department": "CSE",
                "badge": "Unit I • Core",
                "shortSummary": "Linked lists provide dynamic memory allocation without contiguous space. In-place reversal uses 3 pointers (prev, curr, next).",
                "readTime": "4 min read",
                "keyFormula": "Reverse: curr->next = prev",
                "simplification": self._build_linked_list_simplification({"type": "syllabus", "sourceTitle": "Unit 1: Linked Lists"}, "Linked Lists")
            },
            {
                "id": "note-sorting",
                "topic": "Quicksort vs Mergesort & Binary Search",
                "department": "CSE",
                "badge": "Unit V • Algorithms",
                "shortSummary": "Binary search is O(log N) on sorted data. Quicksort is in-place average O(N log N); Mergesort is guaranteed O(N log N) and stable.",
                "readTime": "5 min read",
                "keyFormula": "Binary Search: O(log N)",
                "simplification": self._build_sorting_simplification({"type": "syllabus", "sourceTitle": "Unit 5: Sorting & Searching"}, "Sorting")
            },
            {
                "id": "note-recursion",
                "topic": "Recursion & Call Stack Unwinding",
                "department": "CSE",
                "badge": "Foundation • Prerequisite",
                "shortSummary": "Every recursive function MUST have a base case to terminate, or it crashes with Stack Overflow. Unwinding computes results backwards.",
                "readTime": "3 min read",
                "keyFormula": "Base Case + Recursive Step",
                "simplification": self._build_recursion_simplification({"type": "syllabus", "sourceTitle": "Foundations: Recursion"}, "Recursion")
            }
        ]

    # =========================================================================
    # 7. DYNAMIC CONTEXT-AWARE AI CHATBOT (NO PREDEFINED CANNED ANSWERS)
    # =========================================================================
    def _fetch_wiki_summary(self, term: str) -> Optional[Dict[str, str]]:
        try:
            clean = re.sub(r'^(what is|explain|tell me about|how does|why do we need|describe|meaning of)\s+', '', term.strip(), flags=re.IGNORECASE)
            clean = re.sub(r'[?!.]+$', '', clean).strip()
            if not clean or len(clean) < 2:
                return None
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(clean)}&limit=1&namespace=0&format=json"
            req = urllib.request.Request(search_url, headers={"User-Agent": "Gap2GrowAcademic/1.0 (academic; student@vignan.ac.in)"})
            res = json.loads(urllib.request.urlopen(req, timeout=3.5).read().decode("utf-8"))
            if not res or len(res) < 2 or not res[1]:
                return None
            title = res[1][0]
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json"
            req2 = urllib.request.Request(extract_url, headers={"User-Agent": "Gap2GrowAcademic/1.0 (academic; student@vignan.ac.in)"})
            data = json.loads(urllib.request.urlopen(req2, timeout=3.5).read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for _, page in pages.items():
                extract = page.get("extract", "")
                if extract and len(extract) > 40:
                    return {"title": title, "summary": extract}
        except Exception:
            return None
        return None

    def _call_llm(self, message: str, user_context: dict) -> Optional[str]:
        system_instruction = f"You are the Gap2Grow AI Learning Assistant at Vignan University for {user_context.get('name', 'Student')} ({user_context.get('department', 'CSE')}). Answer clearly with code, tables, and step-by-step explanations where relevant."
        
        # 1. Check Groq
        groq_key = user_context.get("apiKey") or self.groq_key or os.getenv("GROQ_API_KEY")
        if groq_key:
            models = ['groq/compound', 'qwen/qwen3.8-27b', 'groq/compound-mini', 'openai/gpt-oss-120b', 'llama-3.3-70b-versatile', 'llama3-70b-8192']
            if GROQ_AVAILABLE:
                try:
                    client = Groq(api_key=groq_key)
                    for m in models:
                        try:
                            comp = client.chat.completions.create(
                                model=m,
                                messages=[
                                    {"role": "system", "content": system_instruction},
                                    {"role": "user", "content": message}
                                ],
                                temperature=0.3,
                                max_tokens=1500
                            )
                            if comp and comp.choices and comp.choices[0].message.content:
                                return comp.choices[0].message.content
                        except Exception:
                            continue
                except Exception:
                    pass

            # Groq REST Fallback
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
            for m in models:
                try:
                    body = {
                        "model": m,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": message}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500
                    }
                    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        text = res_json["choices"][0]["message"]["content"]
                        if text:
                            return text
                except Exception:
                    continue

        # 2. Check Gemini
        gemini_key = user_context.get("apiKey") or self.gemini_key or os.getenv("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("gsk_") and GENAI_AVAILABLE:
            try:
                client = genai.Client(api_key=gemini_key)
                prompt = f"{system_instruction}\n\nStudent Query: {message}"
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if response and response.text:
                    return response.text
            except Exception:
                pass

        # 3. Check OpenAI
        openai_key = self.openai_key or os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                payload = json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": message}
                    ]
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                })
                data = json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
            except Exception:
                pass

        return None

    def chat_assistant(self, message: str, user_context: dict, session_id: str = "default") -> dict:
        """
        Delegates all student queries to academic_ai_agent for robust intent classification,
        primary/backup provider fallback, database resource lookup, response validation,
        and multi-turn chat memory context.
        """
        from ai_agent import academic_ai_agent
        result = academic_ai_agent.process_query(message, user_context, session_id=session_id)
        return {
            "reply": result.get("reply", ""),
            "intent": result.get("intent", "GENERAL_STUDENT_QUERY"),
            "mode": result.get("mode", "AI_AGENT"),
            "language": result.get("language", "ENGLISH"),
            "sender": "Gap2Grow AI Learning Assistant",
            "timestamp": "Just now"
        }

ai_service = AIService()

