from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

# טען מפתח OpenAI ממשתנה סביבה
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Licensing API is running!"})

@app.route("/generate-report", methods=["POST"])
def generate_report():
    data = request.json or {}
    business_name = data.get("business_name", "עסק ללא שם")
    business_type = data.get("business_type", "לא מוגדר")
    area = data.get("area_sqm", "לא צויין")
    seats = data.get("seating_capacity", "לא צויין")

    prompt = f"""
    צור דוח רישוי לעסק בשם {business_name}.
    סוג העסק: {business_type}, שטח: {area} מ"ר, מקומות ישיבה: {seats}.
    הדגש דרישות רגולטוריות, המלצות ולוח זמנים.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({
            "executive_summary": response.choices[0].message.content,
            "business_name": business_name,
            "business_type": business_type
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)