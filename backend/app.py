from flask import Flask, request, jsonify
import os
import json
from openai import OpenAI

app = Flask(__name__)

# הגדרת הלקוח של OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ שגיאה: לא נמצא OPENAI_API_KEY במשתני הסביבה!", flush=True)

client = OpenAI(api_key=OPENAI_API_KEY)

# נתיב לקבצי החוקים
DATA_DIR = os.path.join(os.path.dirname(__file__), "json_rules")


def load_rules():
    rules = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "rules" in data:
                    rules.extend(data["rules"])
                elif isinstance(data, list):
                    rules.extend(data)
    return rules


def rule_matches(rule, business_type, area, seats, food_type):
    cond = rule.get("applies_when", {})

    # סוג עסק
    if cond.get("business_type"):
        if business_type not in cond["business_type"]:
            return False

    # סוג מזון
    if cond.get("food_type"):
        if food_type not in cond["food_type"]:
            return False

    # שטח
    if cond.get("min_area") and area is not None and area < cond["min_area"]:
        return False
    if cond.get("max_area") and area is not None and area > cond["max_area"]:
        return False

    # מקומות ישיבה
    if cond.get("seating_capacity") and seats is not None:
        try:
            # אם בחוק יש ערך מספרי – נשווה
            if isinstance(cond["seating_capacity"], int) and seats > cond["seating_capacity"]:
                return False
            # אם זה טקסט כמו "עד 200"
            if isinstance(cond["seating_capacity"], str) and "עד" in cond["seating_capacity"]:
                limit = int(cond["seating_capacity"].replace("עד", "").strip())
                if seats > limit:
                    return False
        except Exception:
            pass

    return True


@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.json or {}
        business_name = data.get("business_name", "עסק ללא שם")
        business_type = data.get("business_type", "לא מוגדר")
        area = int(data.get("area_sqm")) if str(data.get("area_sqm")).isdigit() else None
        seats = int(data.get("seating_capacity")) if str(data.get("seating_capacity")).isdigit() else None
        food_type = data.get("food_type") or "כל סוגי המזון"  # ברירת מחדל

        print("📥 בקשה התקבלה מה-Frontend:", data, flush=True)

        # טען את כל החוקים
        rules = load_rules()
        print("📚 סך כל החוקים בקובץ:", len(rules), flush=True)

        # סינון חוקים רלוונטיים
        matched = [
            r for r in rules
            if rule_matches(r, business_type, area, seats, food_type)
        ]

        print("✅ חוקים שנמצאו לעסק:", len(matched), flush=True)
        for r in matched[:5]:  # נדפיס רק 5 ראשונים לבדיקה
            print("-", r["id"], r["title"], flush=True)

        # פרומפט ל-AI
        prompt = f"""
        צור דוח רישוי לעסק בשם "{business_name}".
        סוג העסק: {business_type}, שטח: {area or "לא צויין"} מ"ר, מקומות ישיבה: {seats or "לא צויין"}.

        דרישות רגולטוריות שנמצאו בקבצי JSON:
        {json.dumps(matched, ensure_ascii=False, indent=2)}

        החזר את התשובה אך ורק כ־JSON תקין עם המבנה הבא:
        {{
        "executive_summary": "תקציר מנהלים קצר",
        "recommendations": ["המלצה 1", "המלצה 2"],
        "requirements_by_priority": [
            {{
            "category": "בריאות ותברואה",
            "title": "רישיון בריאות",
            "priority": "קריטי",
            "actions": ["פעולה 1", "פעולה 2"],
            "estimated_cost": "טווח מחיר משוער ₪",
            "estimated_time": "טווח זמן משוער"
            }}
        ],
        "estimated_cost": "סך הכל טווח מחיר משוער",
        "estimated_time": "סך הכל טווח זמן משוער"
        }}
        """

        print("📤 שולח ל-OpenAI...", flush=True)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}  # JSON מובטח
        )

        ai_text = response.choices[0].message.content
        ai_data = json.loads(ai_text)

        print("✅ תשובה התקבלה מה-OpenAI (tokens):", response.usage.total_tokens, flush=True)

        return jsonify({
            "business_name": business_name,
            "business_type": business_type,
            "matched_rules_count": len(matched),
            "matched_rules": matched,
            **ai_data
        })

    except Exception as e:
        print("❌ שגיאה בשרת:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)