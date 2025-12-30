# שלב בסיס
FROM python:3.11-slim

# סביבת עבודה
WORKDIR /app

# התקנת תלויות
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# העתקת קוד - כולל קובץ DOCX מהשורש
COPY backend/ backend/
COPY 18-07-2022_4.2A.docx .

# חשיפת פורט Flask
EXPOSE 5000

# הרצה עם Gunicorn - צריך לציין את הנתיב הנכון
WORKDIR /app/backend
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]