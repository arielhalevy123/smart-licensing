# Smart Licensing – Business Licensing Assessment System

## Project Description

Smart Licensing is a hybrid system designed to assess business licensing requirements in Israel. It combines deterministic rule-based logic with Generative AI to provide accurate, regulatory-compliant reports for business owners.

The system operates in two main modes:
1.  **Licensing Report Generation:** Matches business characteristics against a structured database of regulatory rules, then uses an LLM to generate an executive summary, action plan, and cost estimates.
2.  **Regulatory Q&A (RAG):** A Retrieval-Augmented Generation system that allows users to ask free-text questions about licensing regulations, retrieving answers from indexed regulatory documents.

## System Architecture

The project follows a decoupled client-server architecture:

*   **Frontend:** Static HTML, CSS (Tailwind), and vanilla JavaScript. Serves as a wizard for data collection and a dashboard for report viewing.
*   **Backend:** Python Flask application. Handles API requests, rule matching logic, and OpenAI integrations.
*   **Data Storage:**
    *   `json_rules/`: Directory containing structured JSON files defining regulatory rules.
    *   `rag_index.json`: A local vector index containing embedded chunks of regulatory documents for the RAG system.
*   **AI Integration:** OpenAI `gpt-4o-mini` is used for:
    *   Summarizing matched rules into a cohesive report.
    *   Answering questions based strictly on retrieved context.

### Logic Flow

#### 1. Report Generation (`/api/generate-report`)
The report generation process is a hybrid of deterministic and probabilistic logic:
1.  **Input:** User provides business details (type, area, seating, boolean flags).
2.  **Rule Matching (Deterministic):** The backend iterates through all rules in `json_rules/*.json`. A rule matches only if:
    *   The business type is in the rule's `business_type` list.
    *   Numeric constraints (area, seating) are met.
    *   Boolean conditions (gas, meat, alcohol) match the input.
3.  **AI Synthesis (Probabilistic):** The matched rules are injected into a prompt for `gpt-4o-mini`. The AI is instructed to:
    *   Generate an executive summary.
    *   Create a step-by-step recommendation plan (Pre-opening, Setup, Post-opening).
    *   Estimate costs and timelines based on the rules provided.
    *   **Note:** The AI does *not* invent regulations; it summarizes the provided matched rules.

#### 2. RAG Q&A (`/api/rag`)
1.  **Indexing (Offline):** The script `build_rag_index.py` parses the regulatory DOCX file, chunks the text, and generates embeddings using `text-embedding-3-small`.
2.  **Retrieval (Online):** When a user asks a question:
    *   The question is embedded.
    *   The system calculates cosine similarity against the `rag_index.json`.
    *   The top 5 most relevant text chunks are retrieved.
3.  **Generation:** `gpt-4o-mini` answers the question using *only* the retrieved context, with strict instructions to state if information is missing.

## Installation & Setup

### Prerequisites
*   Python 3.11+
*   OpenAI API Key

### Local Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **Set up environment variables:**
    Export your OpenAI API key:
    ```bash
    export OPENAI_API_KEY=your_key_here
    ```

4.  **Run the application:**
    ```bash
    python backend/app.py
    ```
    The server will start at `http://localhost:5000`.

### Building the RAG Index (Optional)
If you modify the source documents (e.g., `18-07-2022_4.2A.docx`), you must rebuild the index:
```bash
python backend/build_rag_index.py
```

## API Documentation

### `POST /api/generate-report`
Generates a full licensing report based on business parameters.

**Request Body:**
```json
{
  "business_name": "My Cafe",
  "business_type": "cafe",
  "area_sqm": 50,
  "seating_capacity": 20,
  "has_gas": false,
  "serves_meat": false,
  "has_delivery": true,
  "has_alcohol": false
}
```

**Response:**
Returns a JSON object containing:
*   `matched_rules`: Array of raw rule objects from the JSON database.
*   `executive_summary`: AI-generated summary string.
*   `recommendations`: AI-generated object with `before_opening`, `during_setup`, `after_opening` lists.
*   `estimated_cost`: AI-generated cost estimate string.
*   `estimated_time`: AI-generated timeline string.

### `POST /api/rag`
Answers a specific question using the indexed regulatory documents.

**Request Body:**
```json
{
  "question": "What are the ventilation requirements for a kitchen?"
}
```

**Response:**
```json
{
  "answer": "The answer based on the document context...",
  "sources": [
    { "id": "section_id", "preview": "Text snippet..." }
  ]
}
```

## Known Limitations

1.  **Data Staticity:** The system relies on static JSON files and a pre-built RAG index. Changes in regulations require manually updating the JSON files or re-running the index builder.
2.  **Rule Coverage:** The accuracy of the "Matched Rules" depends entirely on the completeness of the `json_rules` database.
3.  **AI Hallucinations:** While the prompts are engineered to be grounded in the provided context, LLMs may still occasionally hallucinate or misinterpret complex regulatory nuances.
4.  **Language:** The system is currently optimized for Hebrew input and output.
