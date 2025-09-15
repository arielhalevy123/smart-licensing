
# Smart Licensing – Business Licensing Assessment System

## Project Description
An interactive system designed to help business owners in Israel understand the relevant licensing requirements for their business.  
The system collects data from the user (business type, size, seating capacity, additional features) and generates a personalized report by combining structured JSON rules with an AI language model (OpenAI GPT).

![Homepage](docs/screenshots/homepage.png)

## Installation & Setup
### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- OpenAI API Key (stored as environment variable `OPENAI_API_KEY`)

### Installation
```bash
git clone https://github.com/username/smart-licensing.git
cd smart-licensing
docker-compose up --build
```

### Local Run
```bash
export OPENAI_API_KEY=your_key_here
python app.py
```

### Access
- Frontend: https://smart-licensing.site  
- Backend API: https://smart-licensing.site/api/generate-report

![AI Report](docs/screenshots/report-ai.png)

## Dependencies
- Flask 3.0.3
- Gunicorn 23.0.0
- openai 1.3.5
- TailwindCSS (CDN)
- Lucide Icons

---

## Technical Documentation

### System Architecture
- **Frontend** – Static HTML/CSS/JS served via Nginx
- **Backend** – Flask API running with Gunicorn in Docker
- **Database** – JSON files with rules and configurations
- **AI Integration** – OpenAI GPT-4o-mini for customized reports

Basic Diagram:
```
User ←→ Nginx ←→ Flask API ←→ OpenAI API
                      ↑
                   JSON Rules
```

### API Documentation
- `GET /` – Health check
- `POST /api/generate-report`
  - Input: JSON with business details
  - Output: Personalized report (executive summary, requirements, recommendations, cost/time estimates)

### Data Structure (example from rules.json)
```json
{
  "id": "R801",
  "title": "Kitchen Cleaning Principles",
  "applies_when": { "business_type": "Institutional Kitchen" },
  "actions": [
    "Perform basic cleaning process for tools and surfaces",
    "Daily cleaning frequency"
  ],
  "priority": "Critical"
}
```

### Matching Algorithm
1. Load rules from JSON files
2. Filter rules by business type and features
3. Build a prompt including business data + matched rules
4. Send prompt to OpenAI
5. Process AI response and display structured report

![Rules List](docs/screenshots/rules-list.png)

---

## AI Usage Documentation

### Development Tools
- ChatGPT / Cursor AI – for quick coding
- GitHub Copilot – for code suggestions
- Replit – for rapid testing

### Main Language Model
- GPT-4o-mini (OpenAI) – chosen for speed and strong performance

### Example Prompts
```
Create a licensing report for a business named "On-the-Go Cafe".
Business type: Cafe, Area: 45 sqm, Seating: 20.

Regulatory requirements found in the file:
[...]

Please generate a clear report including:
- Executive summary
- Mandatory requirements by priority
- Action recommendations
- Preparation timeline
- Cost estimates
```

---

## Learnings & Improvements

### Development Log
- Issue: JSON files not loaded in Docker → Solution: COPY into image
- Issue: `openai.ChatCompletion` deprecated → Solution: update to `client.chat.completions.create`
- Issue: 404 between Nginx and API → Solution: update `proxy_pass`

### Future Improvements
- Support additional business types
- Replace JSON with PostgreSQL database
- Multi-language support (Hebrew/English)
- Admin panel for rule management

### Key Takeaways
- Using AI significantly accelerates development
- Important to validate library version compatibility (openai 0.x → 1.x)
- Docker/Nginx deployment enables smooth cloud migration

