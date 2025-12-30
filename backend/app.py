from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

# Load environment variables from .env file (look in parent directory)
# Get the backend directory, then go up one level to project root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
env_path = os.path.join(PROJECT_ROOT, '.env')
# Also try loading from current directory and common locations
load_dotenv(env_path, override=True)
load_dotenv('.env', override=False)  # Try current dir as fallback
load_dotenv('/app/.env', override=False)  # Try /app as fallback (Docker)
print(f"📁 Loading .env from: {env_path}", flush=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

# 🔑 OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print(" Error: OPENAI_API_KEY not found in environment variables!", flush=True)
    # Debug: check if .env file exists and what's in it
    if os.path.exists(env_path):
        print(f"  Debug: .env file exists at {env_path}", flush=True)
        with open(env_path, 'r') as f:
            first_line = f.readline().strip()
            if 'OPENAI' in first_line.upper():
                print(f"  Debug: Found OPENAI in .env: {first_line[:30]}...", flush=True)
else:
    print(f"✅ OpenAI API key loaded successfully (length: {len(OPENAI_API_KEY)})", flush=True)

client = OpenAI(api_key=OPENAI_API_KEY)

# 📂 Paths
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "json_rules")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "rag_index"

# 📚 Initialize ChromaDB
RAG_COLLECTION = None
CHROMA_ERROR = None
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    RAG_COLLECTION = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    count = RAG_COLLECTION.count()
    print(f"ChromaDB collection loaded: {count} chunks.", flush=True)
except Exception as e:
    CHROMA_ERROR = str(e)
    print(f" Error loading ChromaDB collection: {e}", flush=True)
    print("  Warning: ChromaDB not initialized. Run 'build_rag_index.py' first.", flush=True)


def load_rules():
    rules = []
    if not os.path.exists(DATA_DIR):
        return rules
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "rules" in data:
                    rules.extend(data["rules"])
                elif isinstance(data, list):
                    rules.extend(data)
    return rules


def rule_matches(rule, user):
    cond = rule.get("applies_when", {})

    # Business Type
    if cond.get("business_type"):
        if user.get("business_type") not in cond["business_type"]:
            return False

    # Food Type
    if cond.get("food_type"):
        if user.get("food_type", "כל סוגי המזון") not in cond["food_type"]:
            return False

    # Area
    area = user.get("area_sqm")
    if cond.get("min_area") and area is not None and area < cond["min_area"]:
        return False
    if cond.get("max_area") and area is not None and area > cond["max_area"]:
        return False

    # Seating
    seats = user.get("seating_capacity")
    if cond.get("seating_capacity") and seats is not None:
        try:
            if isinstance(cond["seating_capacity"], int) and seats > cond["seating_capacity"]:
                return False
            if isinstance(cond["seating_capacity"], str) and "עד" in cond["seating_capacity"]:
                limit = int(cond["seating_capacity"].replace("עד", "").strip())
                if seats > limit:
                    return False
        except Exception:
            pass

    # Boolean fields
    for field in ["has_gas", "serves_meat", "has_delivery", "has_alcohol"]:
        if field in cond:
            if user.get(field) not in cond[field]:
                return False

    return True


def retrieve_relevant_chunks(question, top_k=5):
    """Retrieves top-k relevant chunks using ChromaDB vector search."""
    if not RAG_COLLECTION:
        if CHROMA_ERROR:
            raise Exception(f"ChromaDB error: {CHROMA_ERROR}")
        return []

    try:
        # 1. Embed the question
        resp = client.embeddings.create(
            input=question,
            model="text-embedding-3-small"
        )
        query_embedding = resp.data[0].embedding

        # 2. Query ChromaDB for similar chunks
        results = RAG_COLLECTION.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # 3. Format results
        chunks = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                chunk_id = results["ids"][0][i]
                chunk_text = results["documents"][0][i]
                distance = results["distances"][0][i] if "distances" in results else None
                
                # Convert distance to similarity score (ChromaDB uses distance, lower is better)
                # For cosine similarity, similarity = 1 - distance
                score = 1 - distance if distance is not None else None
                
                chunks.append({
                    "id": chunk_id,
                    "chunk": chunk_text,
                    "score": score
                })
                
                # Log retrieval results
                print(f"   - Score: {score:.4f} | Chunk ID: {chunk_id}", flush=True)
        
        print(f"🔍 Found {len(chunks)} relevant chunks from ChromaDB.", flush=True)
        return chunks

    except Exception as e:
        print(f" Retrieval error: {e}", flush=True)
        return []


@app.route("/")
def health():
    """Health check endpoint"""
    try:
        chroma_status = "loaded" if RAG_COLLECTION else "not loaded"
        chroma_count = RAG_COLLECTION.count() if RAG_COLLECTION else 0
        return jsonify({
            "status": "ok", 
            "message": "Licensing API is running!",
            "chroma_db": chroma_status,
            "chroma_chunks": chroma_count,
            "openai_key": "loaded" if OPENAI_API_KEY else "missing"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }), 500


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.json or {}
        business_name = data.get("business_name", "עסק ללא שם")

        user = {
            "business_name": business_name,
            "business_type": data.get("business_type", "לא מוגדר"),
            "area_sqm": int(data.get("area_sqm")) if str(data.get("area_sqm")).isdigit() else None,
            "seating_capacity": int(data.get("seating_capacity")) if str(data.get("seating_capacity")).isdigit() else None,
            "food_type": data.get("food_type", "כל סוגי המזון"),
            "has_gas": bool(data.get("has_gas")),
            "serves_meat": bool(data.get("serves_meat")),
            "has_delivery": bool(data.get("has_delivery")),
            "has_alcohol": bool(data.get("has_alcohol")),
        }

        print("Report Request:", user, flush=True)

        rules = load_rules()
        matched = [r for r in rules if rule_matches(r, user)]

        prompt = f"""
        צור דוח רישוי לעסק בשם "{user['business_name']}".
        סוג העסק: {user['business_type']}, שטח: {user['area_sqm'] or "לא צויין"} מ"ר, מקומות ישיבה: {user['seating_capacity'] or "לא צויין"}.

        דרישות רגולטוריות שנמצאו בקבצי JSON:
        {json.dumps(matched, ensure_ascii=False, indent=2)}

        החזר את התשובה אך ורק כ־JSON תקין עם המבנה הבא:
        {{
        "executive_summary": "תקציר מנהלים...",
        "recommendations": {{
            "before_opening": ["שלב 1: ...", "שלב 2: ..."],
            "during_setup": ["שלב 3: ..."],
            "after_opening": ["שלב 4: ..."]
        }},
        "requirements_by_priority": [
            {{ "category": "...", "title": "...", "priority": "...", "actions": ["..."], "estimated_cost": "...", "estimated_time": "..." }}
        ],
        "estimated_cost": "...",
        "estimated_time": "..."
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        ai_data = json.loads(response.choices[0].message.content)

        return jsonify({
            **user,
            "matched_rules_count": len(matched),
            "matched_rules": matched,
            **ai_data
        })

    except Exception as e:
        print(" Error:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/rag", methods=["POST"])
def rag_endpoint():
    try:
        data = request.json or {}
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        print(f"🤔 RAG Question: {question}", flush=True)

        # 1. Retrieve Context
        relevant_chunks = retrieve_relevant_chunks(question, top_k=5)
        
        context_text = "\n\n".join([f"--- מקור {c['id']} ---\n{c['chunk']}" for c in relevant_chunks])
        sources = [{"id": c["id"], "preview": c["chunk"][:200] + "..."} for c in relevant_chunks]

        # 2. Build Prompt with Protection
       # 2. Build Prompt (RAG strict, best-practice)
        system_message = """
            אתה עוזר מומחה לרישוי עסקים בישראל.

            כללים מחייבים:
            1) אתה עונה אך ורק לפי המידע שמופיע ב-Context שמסופק לך.
            2) אסור לך להשתמש בידע חיצוני, לנחש, להשלים פרטים, או להמציא תקנות.
            3) אם המידע לא מופיע ב-Context, עליך לענות בדיוק:
            "לא נמצא מידע רלוונטי במאגר"

            סגנון תשובה:
            - עברית בלבד
            - תשובה קצרה וברורה
            - אם מתאים: רשימת נקודות
            - אל תזכיר "Context", "embedding", "RAG", או פרטים פנימיים של המערכת
        """

        user_prompt = f"""
            כותרת: קטעי רגולציה רלוונטיים (Context)
            {context_text}

            כותרת: שאלת המשתמש
            {question}

            הנחיה:
            ענה רק לפי הקטעים שצורפו למעלה. אם אין שם תשובה — כתוב בדיוק:
            "לא נמצא מידע רלוונטי במאגר"
        """
        # 3. Call AI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0  # Low temperature for factual accuracy
        )

        answer = response.choices[0].message.content.strip()

        return jsonify({
            "answer": answer,
            "sources": sources
        })

    except Exception as e:
        error_msg = str(e)
        print(f" RAG Error: {error_msg}", flush=True)
        
        # Provide more helpful error messages
        if "401" in error_msg or "API key" in error_msg.lower():
            return jsonify({
                "error": "OpenAI API key is missing or invalid. Please set OPENAI_API_KEY environment variable."
            }), 500
        elif "disturbed" in error_msg.lower() or "locked" in error_msg.lower() or "chromadb" in error_msg.lower():
            return jsonify({
                "error": f"ChromaDB database error: {error_msg}. Try restarting the server or rebuilding the index."
            }), 500
        elif "empty" in error_msg.lower() or "no chunks" in error_msg.lower():
            return jsonify({
                "error": "RAG index is empty. Please rebuild the index using build_rag_index.py"
            }), 500
        else:
            return jsonify({
                "error": f"An error occurred: {error_msg}"
            }), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_RUN_PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
