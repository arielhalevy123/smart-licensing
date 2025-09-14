from flask import Flask, request, jsonify
import os
import json
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    data = request.json or {}
    business_name = data.get("business_name", "עסק ללא שם")
    business_type = data.get("business_type", "לא מוגדר")
    area = data.get("area_sqm", "לא צויין")
    seats = data.get("seating_capacity", "לא צויין")

    rules = load_rules()
    matched = [
        r for r in rules
        if r.get("applies_when", {}).get("business_type", "") in [business_type, "", None]
    ]

    prompt = f"""
    אתה מקבל נתוני עסק:
    - שם: {business_name}
    - סוג: {business_type}
    - שטח: {area} מ"ר
    - מקומות ישיבה: {seats}

    דרישות רגולטוריות שנמצאו:
    {json.dumps(matched, ensure_ascii=False, indent=2)}

    הפק דוח רישוי מפורט **בפורמט JSON בלבד** עם השדות:
    {{
    "executive_summary": "תקציר מנהלים ברור",
    "estimated_cost": "טווח עלויות משוער (לדוגמה: ₪2,500-₪8,000)",
    "estimated_time": "טווח זמן משוער (לדוגמה: 6-20 שבועות)",
    "recommendations": "המלצות מעשיות לבעל העסק",
    "requirements_by_priority": [
        {{
        "title": "כותרת הדרישה",
        "priority": "קריטי/גבוה/בינוני",
        "actions": ["פעולה 1", "פעולה 2"],
        "related_to": "למשל: משרד הבריאות / בטיחות אש",
        "estimated_cost": "₪500-₪1,500",
        "estimated_time": "2-6 שבועות"
        }}
    ]
    }}

    שים לב:
    - השתמש בדרישות שהעברתי לך בתוך JSON (`matched`).
    - אל תחזיר טקסט חופשי, רק JSON תקין.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # קבל טקסט מה-AI ופרסר ל-JSON
        content = response.choices[0].message.content
        report = json.loads(content)

        return jsonify({
            **report,
            "business_name": business_name,
            "business_type": business_type,
            "matched_rules": matched
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)