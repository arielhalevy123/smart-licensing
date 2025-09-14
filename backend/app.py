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

        rules = load_rules()
        matched = [
            r for r in rules
            if r.get("applies_when", {}).get("business_type", "") in [business_type, "", None]
        ]

        system = (
            "אתה מסייע רישוי עסקים. החזר אך ורק JSON חוקי, ללא טקסט נוסף, לפי הסכימה המדויקת להלן."
            " אין להחזיר Markdown. אין שדות מיותרים. מותר להשאיר ערכים ריקים אם לא בטוח."
        )

        # סכימה: שים לב לשמות השדות — זה מה שה-frontend ירנדר
        schema = {
            "business": {
                "name": business_name,
                "type": business_type,
                "area_sqm": area,
                "seating_capacity": seats
            },
            "executive_summary_html": "",  # HTML קצר וסדור, לא Markdown
            "recommendations": [],         # רשימת מחרוזות
            "estimated_cost": "",          # טווח עלות כולל (מחרוזת)
            "estimated_time": "",          # טווח זמן כולל (מחרוזת)
            "requirements_by_priority": [  # רשימת דרישות מפורטות
                # {
                #   "category": "בריאות ותברואה",
                #   "title": "רישיון בריאות",
                #   "priority": "קריטי" | "גבוהה" | "בינונית" | "נמוכה",
                #   "actions": ["...", "..."],
                #   "related_to": "מטבח/מחסן/שירותים/בטיחות אש/רישוי עסק...",
                #   "estimated_cost": "₪ ...",
                #   "estimated_time": "..."
                # }
            ]
        }

        user_payload = {
            "business": schema["business"],
            "matched_rules": matched
        }

        prompt = (
            "קלט עסק וחוקי רישוי רלוונטיים בקובצי JSON.\n"
            "בנה דוח תמציתי ומעשי. מלא את כל השדות בסכימה הבאה:\n"
            + json.dumps(schema, ensure_ascii=False, indent=2) +
            "\n\nדרישות:\n"
            "- executive_summary_html יהיה HTML קצר, עם כותרות משנה קצרות, נקודות תבליט, וללא CSS inline.\n"
            "- requirements_by_priority: קבץ לפי היגיון מהחוקים, עם עדיפות ('קריטי', 'גבוהה', 'בינונית').\n"
            "- אל תחזיר Markdown.\n"
            "- החזר JSON חוקי בלבד."
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "נתוני קלט:"},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
            ],
            temperature=0.4
        )

        raw = resp.choices[0].message.content
        try:
            ai = json.loads(raw)
        except Exception:
            # נפילה חכמה: אם משום מה לא JSON לגמרי, נחזיר את הטקסט כדי שלא תיחסם הזרימה
            ai = {"executive_summary_html": raw}

        # הוסף מידע שמיש ל-frontend גם אם ה-AI לא מילא הכל
        ai.setdefault("business", schema["business"])
        ai.setdefault("estimated_cost", "2,500 ₪ - 8,000 ₪ (הערכה בלבד)")
        ai.setdefault("estimated_time", "6-20 שבועות (הערכה בלבד)")
        ai.setdefault("requirements_by_priority", [])

        return jsonify(ai)

    except Exception as e:
        print("❌ שגיאה בשרת:", str(e), flush=True)
        return jsonify({"error": str(e)}), 500