import os
import json
import numpy as np
from docx import Document
from openai import OpenAI

# Configuration
DOCX_PATH = "18-07-2022_4.2A.docx"
INDEX_OUTPUT_PATH = "backend/rag_index.json"
CHUNK_SIZE = 800  # characters
OVERLAP = 100
EMBEDDING_MODEL = "text-embedding-3-small"  # Cost-effective and high performance

# Initialize OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  Warning: OPENAI_API_KEY not found in environment variables.")
    # You might want to exit here if strict, but for now we'll let it fail later if not set.

client = OpenAI(api_key=api_key)

def extract_text_from_docx(path):
    """Extracts text from a DOCX file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    doc = Document(path)
    full_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)
    return "\n".join(full_text)

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """Splits text into chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def generate_embeddings(chunks):
    """Generates embeddings for a list of text chunks."""
    data = []
    print(f"🚀 Generating embeddings for {len(chunks)} chunks...")
    
    # Process in batches to avoid hitting rate limits or payload limits
    batch_size = 20
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        try:
            response = client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL
            )
            for j, item in enumerate(response.data):
                data.append({
                    "id": i + j,
                    "chunk": batch[j],
                    "embedding": item.embedding
                })
            print(f"   Processed batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")
        except Exception as e:
            print(f"❌ Error processing batch starting at index {i}: {e}")
            
    return data

def main():
    print("📂 Starting RAG Index Build Process...")
    
    try:
        # 1. Load Data
        print(f"📖 Loading document: {DOCX_PATH}")
        raw_text = extract_text_from_docx(DOCX_PATH)
        print(f"✅ Loaded {len(raw_text)} characters.")

        # 2. Chunk Data
        chunks = chunk_text(raw_text)
        print(f"✂️  Split into {len(chunks)} chunks.")

        # 3. Embed Data
        index_data = generate_embeddings(chunks)

        # 4. Save Index
        print(f"💾 Saving index to {INDEX_OUTPUT_PATH}...")
        with open(INDEX_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print("🎉 RAG Index built successfully!")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()

