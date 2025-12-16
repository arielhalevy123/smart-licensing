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

        print("📥 Report Request:", user, flush=True)

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
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # 0) Expand query for retrieval (not for final answer)
        retrieval_query = expand_query_for_retrieval(question)

        print(f"RAG Question: {question}", flush=True)
        print(f"RAG Retrieval Query: {retrieval_query}", flush=True)

        # 1) Retrieve Context
        relevant_chunks = retrieve_relevant_chunks(retrieval_query, top_k=5)

        context_text = "\n\n".join(
            [f"--- SOURCE_ID: {c['id']} ---\n{c['chunk']}" for c in relevant_chunks]
        )
        sources = [{"id": c["id"], "preview": (c["chunk"][:200] + "...") if len(c["chunk"]) > 200 else c["chunk"]}
                   for c in relevant_chunks]

        # 2) Build Prompt (best practices + strict JSON)
        system_message = """
            אתה עוזר מומחה לרישוי עסקים בישראל.

            מטרה:
            לענות לשאלת המשתמש אך ורק על סמך ה-Context שסופק לך.

            כללים מחייבים:
            1) אסור להשתמש בידע כללי, ניחושים או ניסיון. מותר להשתמש רק במה שמופיע ב-Context.
            2) אם אין ב-Context מידע שמאפשר לענות בצורה ברורה — החזר answer בדיוק:
            "לא נמצא מידע רלוונטי במאגר"
            3) אם יש מידע חלקי — תן מה שכן נמצא וציין מה חסר ב-missing_info.
            4) אל תמציא חוקים/תקנות/מספרי סעיפים/דרישות שלא מופיעים ב-Context.
            5) כתוב בעברית.

            פלט מחייב:
            החזר JSON בלבד (בלי טקסט מסביב) במבנה:
            {
            "answer": string,
            "confidence": "high" | "medium" | "low",
            "citations": [string],   // רשימת SOURCE_ID ששימשו בפועל
            "missing_info": [string] // מה חסר כדי לענות טוב יותר (אפשר ריק)
            }
        """

        user_prompt = f"""
            # Context (מקורות מידע)
            {context_text}

            # Question
            {question}

            # Instructions
            ענה לפי הכללים והחזר JSON בלבד לפי המבנה.
        """

        # 3) Call AI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()

        # 4) Parse JSON safely (in case model returns extra text)
        try:
            parsed = json.loads(raw)
        except Exception:
            # fallback: wrap as low confidence
            parsed = {
                "answer": raw if raw else "לא נמצא מידע רלוונטי במאגר",
                "confidence": "low",
                "citations": [],
                "missing_info": ["המודל לא החזיר JSON תקין; יש להפעיל תיקון/JSON mode."]
            }

        # 5) If model forgot to cite, keep the original sources list anyway
        return jsonify({
            "answer": parsed.get("answer", ""),
            "confidence": parsed.get("confidence", "low"),
            "citations": parsed.get("citations", []),
            "missing_info": parsed.get("missing_info", []),
            "sources": sources
        })

    except Exception as e:
        print(f"RAG Error: {e}", flush=True)
        return jsonify({"error": "An error occurred while processing your request."}), 500