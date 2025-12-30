# שלב בסיס
FROM python:3.11-slim

# סביבת עבודה
WORKDIR /app

# התקנת תלויות
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת קוד backend
COPY backend/ ./backend/

# העתקת קובץ DOCX מהתיקייה הראשית
COPY regulations.docx /app/regulations.docx

# חשיפת פורט Flask
EXPOSE 5000

# הרצה עם Gunicorn (עדיף מ-fla sk run)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]