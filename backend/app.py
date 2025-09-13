from flask import Flask, request, jsonify
import os
import json
import openai

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# נתיב לקבצי החוקים
DATA_DIR = os.path.join(os.path.dirname(__file__), "json_rules")

def load_rules():
    rules = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)

                # אם זה בפורמט {"rules": [...]}
                if isinstance(data, dict) and "rules" in data:
                    rules.extend(data["rules"])

                # אם זה בפורמט רשימה בלבד
                elif isinstance(data, list):
                    rules.extend(data)

    return rules

@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    data = request.json or {}
    business_name = data.get("business_name", "עסק ללא שם")
    business_type = data.get("business_type", "לא מוגדר")
    area = data.get("area_sqm", "לא צויין")
    seats = data.get("seating_capacity", "לא צויין")

    # טען את כל החוקים מכל הקבצים
    rules = load_rules()

    # סינון חוקים רלוונטיים
    matched = [
        r for r in rules
        if r.get("applies_when", {}).get("business_type", "") in [business_type, "", None]
    ]

    # פרומפט ל־AI
    prompt = f"""
    צור דוח רישוי לעסק בשם "{business_name}".
    סוג העסק: {business_type}, שטח: {area} מ"ר, מקומות ישיבה: {seats}.

    דרישות רגולטוריות שנמצאו בקבצי JSON:
    {json.dumps(matched, ensure_ascii=False, indent=2)}

    אנא הפק דוח ברור עם:
    - תקציר מנהלים
    - דרישות חובה לפי עדיפות
    - המלצות פעולה
    - לוח זמנים להיערכות
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({
            "executive_summary": response.choices[0].message.content,
            "business_name": business_name,
            "business_type": business_type,
            "matched_rules": matched
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)