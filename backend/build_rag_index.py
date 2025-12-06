import os
import json
import re
from docx import Document
from openai import OpenAI

# Configuration
DOCX_PATH = "18-07-2022_4.2A.docx"
INDEX_OUTPUT_PATH = "backend/rag_index.json"
PREVIEW_PATH = "rag_sections_preview.txt"   # רק לצורך בדיקה אנושית
EMBEDDING_MODEL = "text-embedding-3-small"

# Initialize OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  Warning: OPENAI_API_KEY not found in environment variables.")

client = OpenAI(api_key=api_key)

# סעיף משפטי: 1.  / 1.1. / 1.2.3. / 2.10.4.1
SECTION_RE = re.compile(r'^\s*(\d+(\.\d+)*\.?)\s+')

def extract_blocks_from_docx(path):
    """
    מחזיר רשימה של בלוקים טקסטואליים (פסקאות ושורות מטבלאות).
    כל בלוק הוא מחרוזת.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    doc = Document(path)
    blocks = []

    # פסקאות
    print("   ... Reading paragraphs ...")
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            blocks.append(text)

    # טבלאות
    print("   ... Reading tables ...")
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                blocks.append(row_text)

    print(f"✅ Collected {len(blocks)} text blocks (paragraphs + tables)")
    return blocks

def split_blocks_to_sections(blocks):
    """
    חותך את רשימת הבלוקים לסעיפים לפי מספור:
    כל בלוק שמתחיל ב- 1. / 1.1. / 1.2.3. וכו' פותח סעיף חדש.
    כל מה שבא אחר כך ולא מתחיל במספור – מצטרף לסעיף האחרון.
    """
    sections = []
    current_id = None
    current_parts = []

    for block in blocks:
        m = SECTION_RE.match(block)
        if m:
            # התחלה של סעיף חדש
            # קודם נסגור את הקודם אם קיים
            if current_id is not None and current_parts:
                full_text = "\n".join(current_parts).strip()
                if full_text:
                    sections.append({
                        "id": current_id,
                        "chunk": full_text
                    })

            # חילוץ המספור (למשל "1.7.2.3")
            sec_id = m.group(1).rstrip(".")
            current_id = sec_id
            current_parts = [block]
        else:
            # שורה שממשיכה את הסעיף האחרון
            if current_id is None:
                # טקסט לפני סעיף ראשון – אפשר לדלג, או לשמור לסעיף INTRO
                # כאן מדלגים כדי לא ללכלך את האינדקס.
                continue
            current_parts.append(block)

    # לסגור את הסעיף האחרון
    if current_id is not None and current_parts:
        full_text = "\n".join(current_parts).strip()
        if full_text:
            sections.append({
                "id": current_id,
                "chunk": full_text
            })

    print(f"✂️  Split into {len(sections)} numbered sections.")
    return sections

def save_preview(sections, path=PREVIEW_PATH):
    """
    שומר קובץ טקסט לקריאה אנושית, כדי שתראה איך הסקריפט חתך את הסעיפים.
    לא חובה בשביל המערכת, אבל מאוד עוזר לבדיקה.
    """
    with open(path, "w", encoding="utf-8") as f:
        for s in sections:
            f.write(f"===== סעיף {s['id']} =====\n")
            f.write(s["chunk"])
            f.write("\n\n")
    print(f"🔍 Preview saved to {path}")

def generate_embeddings(sections):
    """
    מייצר embeddings לכל סעיף ומחזיר את אותה רשימת סעיפים
    עם שדה נוסף "embedding" בכל אובייקט.
    """
    print(f"🚀 Generating embeddings for {len(sections)} sections...")
    batch_size = 20
    idx = 0

    for i in range(0, len(sections), batch_size):
        batch = sections[i:i+batch_size]
        texts = [s["chunk"] for s in batch]

        try:
            response = client.embeddings.create(
                input=texts,
                model=EMBEDDING_MODEL
            )
            for j, item in enumerate(response.data):
                sections[idx]["embedding"] = item.embedding
                idx += 1
            print(f"   Processed batch {i // batch_size + 1}/{(len(sections) + batch_size - 1) // batch_size}")
        except Exception as e:
            print(f"❌ Error processing batch starting at index {i}: {e}")

    missing = [s for s in sections if "embedding" not in s]
    if missing:
        print(f"⚠️ Warning: {len(missing)} sections have no embedding")
    return sections

def main():
    print("📂 Starting RAG Index Build Process (by legal sections)...")

    try:
        # 1. Load raw blocks (paragraphs + tables)
        print(f"📖 Loading document: {DOCX_PATH}")
        blocks = extract_blocks_from_docx(DOCX_PATH)

        # 2. Split into logical sections by numbering
        sections = split_blocks_to_sections(blocks)

        # 3. Save preview for manual inspection
        save_preview(sections)

        # 4. Generate embeddings
        sections_with_emb = generate_embeddings(sections)

        # 5. Save final index
        print(f"💾 Saving index to {INDEX_OUTPUT_PATH}...")
        os.makedirs(os.path.dirname(INDEX_OUTPUT_PATH), exist_ok=True)
        with open(INDEX_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(sections_with_emb, f, ensure_ascii=False, indent=2)

        print("🎉 RAG Index built successfully!")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()