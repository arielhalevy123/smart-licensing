# שלב בסיס
FROM python:3.11-slim

# סביבת עבודה
WORKDIR /app

# התקנת תלויות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת קוד
COPY . .

# חשיפת פורט Flask
EXPOSE 5000

# הרצה עם Gunicorn (עדיף מ-flask run)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]