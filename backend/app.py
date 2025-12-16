from flask import Flask, request, jsonify
import os
import json
import numpy as np
from openai import OpenAI

app = Flask(__name__)

# 🔑 OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print(" Error: OPENAI_API_KEY not found in environment variables!", flush=True)

client = OpenAI(api_key=OPENAI_API_KEY)

# 📂 Paths
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "json_rules")
RAG_INDEX_PATH = os.path.join(BASE_DIR, "rag_index.json")

# 📚 Load RAG Index
RAG_INDEX = []
if os.path.exists(RAG_INDEX_PATH):
    try:
        with open(RAG_INDEX_PATH, encoding="utf-8") as f:
            RAG_INDEX = json.load(f)
        print(f"RAG Index loaded: {len(RAG_INDEX)} chunks.", flush=True)
    except Exception as e:
        print(f" Error loading RAG index: {e}", flush=True)
else:
    print("  Warning: rag_index.json not found. Run 'build_rag_index.py' first.", flush=True)


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
    """Retrieves top-k relevant chunks using cosine similarity."""
    if not RAG_INDEX:
        return []

    try:
        # 1. Embed the question
        resp = client.embeddings.create(
            input=question,
            model="text-embedding-3-small"
        )
        q_vec = np.array(resp.data[0].embedding)

        # 2. Calculate Similarity
        results = []
        for item in RAG_INDEX:
            chunk_vec = np.array(item["embedding"])
            # Cosine similarity for normalized vectors is just the dot product
            score = np.dot(q_vec, chunk_vec)
            results.append((score, item))

        # 3. Sort and Select
        results.sort(key=lambda x: x[0], reverse=True)
        top_items = results[:top_k]
        
        # Log retrieval results
        print(f"🔍 Found {len(results)} chunks. Selected top {top_k}.", flush=True)
        for score, item in top_items:
            print(f"   - Score: {score:.4f} | Chunk ID: {item['id']}", flush=True)

        return [item for score, item in top_items]

    except Exception as e:
        print(f" Retrieval error: {e}", flush=True)
        return []


@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})


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
        print(f" RAG Error: {e}", flush=True)
        return jsonify({"error": "An error occurred while processing your request."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
