import os
import json
from docx import Document
from openai import OpenAI

# 📌 ודא שיש לך משתנה סביבה OPENAI_API_KEY
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ⚙️ פרטי המשתמש – דוגמה
user_input = {
    "business_name": "ינתי",
    "business_type": "bar",
    "area_sqm": 110,
    "seating_capacity": 220,
    "employees": 11,
    "city": "ביאליק",
    "has_gas": False,
    "serves_meat": True,
    "has_delivery": True,
    "has_alcohol": False
}


def extract_text_from_docx(docx_path):
    """קריאת כל הטקסט והטבלאות מקובץ Word"""
    doc = Document(docx_path)
    full_text = []

    # פסקאות רגילות
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())

    # טבלאות
    for table in doc.tables:
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_data:
                full_text.append(" | ".join(row_data))

    return "\n".join(full_text)


def convert_rules_with_ai(text, start_id=1):
    """שולח חלק טקסט ל-ChatGPT ומחזיר JSON"""
    prompt = f"""
אתה מקבל קטע מתוך קובץ עם חוקים ודרישות (כולל טבלאות ופסקאות).
עליך להחזיר JSON עם מבנה של חוקים רלוונטיים לנתוני העסק הבאים:

{json.dumps(user_input, ensure_ascii=False, indent=2)}

המבנה של כל חוק יהיה כך:

{{
  "id": "RXXX",   ← מספר רץ החל מ-{start_id}
  "title": "שם החוק",
  "applies_when": {{
    "business_type": ["{user_input['business_type']}"],
    "food_type": ["כל סוגי המזון"],
    "min_area": null,
    "max_area": null,
    "seating_capacity": null
  }},
  "actions": ["פעולה 1", "פעולה 2"],
  "priority": "קריטי"
}}

חשוב:
- למספר את החוקים ברצף (לא לאפס בין חלקים).
- אם אין חוקים בקטע – החזר {{"rules": []}} בלבד.

קטע מתוך הקובץ:
{text}
    """

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    ai_text = response.choices[0].message.content
    return json.loads(ai_text)


def split_text(text, chunk_size=5000):
    """פיצול הטקסט לחתיכות קטנות יותר"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


if __name__ == "__main__":
    docx_file = "18-07-2022_4.2A.docx"   # ← שם הקובץ שלך
    output_file = "rules.json"

    print("📂 קורא את הקובץ...")
    text = extract_text_from_docx(docx_file)

    chunks = split_text(text, chunk_size=5000)
    print(f"✂️ הקובץ פוצל ל-{len(chunks)} חלקים")

    # 👇 קח רק חצי ראשון של הקובץ
    half_index = len(chunks) // 2
    chunks = chunks[:half_index]
    print(f"📂 מעבד רק {len(chunks)} חלקים (חצי קובץ)")

    all_rules = {"rules": []}
    current_id = 1

    for i, chunk in enumerate(chunks, start=1):
        print(f"🤖 שולח ל-ChatGPT חלק {i}/{len(chunks)}...")
        try:
            ai_data = convert_rules_with_ai(chunk, start_id=current_id)

            rules = ai_data.get("rules", [])
            for j, rule in enumerate(rules, start=0):
                rule["id"] = f"R{current_id + j:04d}"
            current_id += len(rules)

            all_rules["rules"].extend(rules)
        except Exception as e:
            print(f"❌ שגיאה בחלק {i}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)

    print(f"✅ קובץ JSON נוצר בהצלחה: {output_file}")
