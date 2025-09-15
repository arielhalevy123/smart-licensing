from flask import Flask, request, jsonify
import os
import json
from openai import OpenAI

app = Flask(__name__)

# 🔑 הגדרת הלקוח של OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ שגיאה: לא נמצא OPENAI_API_KEY במשתני הסביבה!", flush=True)

client = OpenAI(api_key=OPENAI_API_KEY)

# 📂 נתיב לקבצי החוקים
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


def rule_matches(rule, user):
    cond = rule.get("applies_when", {})

    # סוג עסק
    if cond.get("business_type"):
        if user.get("business_type") not in cond["business_type"]:
            return False

    # סוג מזון
    if cond.get("food_type"):
        if user.get("food_type", "כל סוגי המזון") not in cond["food_type"]:
            return False

    # שטח
    area = user.get("area_sqm")
    if cond.get("min_area") and area is not None and area < cond["min_area"]:
        return False
    if cond.get("max_area") and area is not None and area > cond["max_area"]:
        return False

    # מקומות ישיבה
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

    # שדות בוליאניים
    for field in ["has_gas", "serves_meat", "has_delivery", "has_alcohol"]:
        if field in cond:
            if user.get(field) not in cond[field]:
                return False

    return True


@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.json or {}
        business_name = data.get("business_name", "עסק ללא שם")

        # המרה לערכים נכונים
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

        print("📥 בקשה התקבלה מה-Frontend:", user, flush=True)

        # טען את כל החוקים
        rules = load_rules()
        print("📚 סך כל החוקים בקובץ:", len(rules), flush=True)

        # סינון חוקים רלוונטיים
        matched = [r for r in rules if rule_matches(r, user)]

        print("✅ חוקים שנמצאו לעסק:", len(matched), flush=True)
        for r in matched[:5]:
            print("-", r["id"], r["title"], flush=True)

        # פרומפט ל-AI
        prompt = f"""
        צור דוח רישוי לעסק בשם "{user['business_name']}".
        סוג העסק: {user['business_type']}, שטח: {user['area_sqm'] or "לא צויין"} מ"ר, מקומות ישיבה: {user['seating_capacity'] or "לא צויין"}.

        דרישות רגולטוריות שנמצאו בקבצי JSON:
        {json.dumps(matched, ensure_ascii=False, indent=2)}

        החזר את התשובה אך ורק כ־JSON תקין עם המבנה הבא:
        {{
        "executive_summary": "תקציר מנהלים מפורט (לפחות 4–6 משפטים, כולל מצב רגולטורי, סיכונים, יתרונות, נקודות קריטיות)",
        "recommendations": {{
            "before_opening": [
                "שלב 1: איסוף מסמכים נדרשים (לדוגמה: רישיון עסק בסיסי)",
                "שלב 2: ...",
                "שלב 3: ..."
            ],
            "during_setup": [
                "שלב 4: קבלת אישור כיבוי אש והתקנת ציוד בטיחות מתאים (לדוגמה: מטפי כיבוי, שילוט חירום)",
                "שלב 5: ...",
                "שלב 6: ..."
            ],
            "after_opening": [
                "שלב 7: תחזוקת ציוד שוטפת (לדוגמה: ניקוי יומי למטבח או טיפול במכונות)",
                "שלב 8: ...",
                "שלב 9: ..."
            ]
        }},
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

        הנחיות מחייבות:
        - חובה לספק לפחות 3 פריטים לכל שלב (before_opening, during_setup, after_opening).
        - כל פריט חייב להיות בפורמט "שלב X: טקסט פעולה".
        - לפחות אחד בכל שלב חייב להכיל דוגמה אמיתית (כמו אלו שנתתי), ואת שאר השלבים להשלים בהתאם.
        - אסור להחזיר "אין המלצות נוספות".
        - החזר JSON בלבד, ללא טקסט חופשי.
        """

        print("📤 שולח ל-OpenAI...", flush=True)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        ai_text = response.choices[0].message.content
        ai_data = json.loads(ai_text)

        print("✅ תשובה התקבלה מה-OpenAI (tokens):", response.usage.total_tokens, flush=True)

        return jsonify({
            **user,
            "matched_rules_count": len(matched),
            "matched_rules": matched,
            **ai_data
        })

    except Exception as e:
        print("❌ שגיאה בשרת:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)