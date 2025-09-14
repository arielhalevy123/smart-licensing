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


@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    try:
        data = request.json or {}
        business_name = data.get("business_name", "עסק ללא שם")
        business_type = data.get("business_type", "לא מוגדר")
        area = data.get("area_sqm", "לא צויין")
        seats = data.get("seating_capacity", "לא צויין")

        print("📥 בקשה התקבלה מה-Frontend:", data, flush=True)

        # טען את כל החוקים
        rules = load_rules()

        # סינון חוקים רלוונטיים
        matched = [
            r for r in rules
            if r.get("applies_when", {}).get("business_type", "") in [business_type, "", None]
        ]

        # פרומפט ל-AI
        prompt = f"""
            צור דוח רישוי לעסק בשם "{business_name}".
            סוג העסק: {business_type}, שטח: {area} מ"ר, מקומות ישיבה: {seats}.

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
                "estimated_cost": "800-2500 ₪",
                "estimated_time": "4-8 שבועות"
                }}
            ],
            "estimated_cost": "סה\"כ ~5000 ₪",
            "estimated_time": "6-20 שבועות"
            }}
            """

        print("📤 שולח ל-OpenAI...", flush=True)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        ai_text = response.choices[0].message.content.strip()
        if ai_text.startswith("```"):
            ai_text = ai_text.strip("`")        # מוריד את כל ה־`
            ai_text = ai_text.replace("json", "", 1).strip()  # מסיר json בהתחלה אם קיים
        try:
            ai_data = json.loads(ai_text)
        except json.JSONDecodeError:
            ai_data = {"executive_summary": ai_text}  # fallback
        print("✅ תשובה התקבלה מה-OpenAI (tokens):", response.usage.total_tokens, flush=True)

        return jsonify({
            "business_name": business_name,
            "business_type": business_type,
            "matched_rules": matched,
            **ai_data
        })

    except Exception as e:
        print("❌ שגיאה בשרת:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)