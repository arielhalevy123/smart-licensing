import os
import json
import re
from docx import Document
from openai import OpenAI
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

# Configuration
DOCX_PATH = "18-07-2022_4.2A.docx"
INDEX_OUTPUT_PATH = "backend/rag_index.json"
PREVIEW_OUTPUT_PATH = "backend/rag_preview.txt"
EMBEDDING_MODEL = "text-embedding-3-small"
MIN_CHARS = 500
MAX_CHARS = 2000

# Initialize OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  Warning: OPENAI_API_KEY not found in environment variables.")

client = OpenAI(api_key=api_key)

# Regex to identify section starts like "1. ", "1.2. ", "12.3.4"
# Must match start of line, optional whitespace, digits+dots, then space or end
SECTION_RE = re.compile(r'^\s*(\d+(\.\d+)*)\.?\s+')

def iter_block_items(parent):
    """
    Yields each paragraph and table child within *parent*, in document order.
    Each item is either a Paragraph or a Table instance.
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Something's not right")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def extract_docx(path):
    """
    Reads DOCX content in strict document order.
    Returns a single string with all text.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    document = Document(path)
    lines = []

    def process_block(block):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                lines.append(text)
        elif isinstance(block, Table):
            for row in block.rows:
                # Extract text from each cell
                cell_texts = [cell.text.strip() for cell in row.cells]
                # Join with pipe if any content exists
                row_content = " | ".join(cell_texts)
                # Only add if row has some non-empty content
                if any(c for c in cell_texts):
                    lines.append(row_content)

    # Iterate over main document body
    for block in iter_block_items(document):
        process_block(block)

    full_text = "\n".join(lines)
    print(f"✅ Extracted {len(full_text)} characters from {path}")
    return full_text

def split_into_sections(full_text):
    """
    Splits text into logical sections based on numbering.
    Returns a list of dicts: {"section_id": "...", "text": "..."}
    """
    lines = full_text.split('\n')
    sections = []
    
    current_id = "intro" # For text before the first numbered section
    current_lines = []

    for line in lines:
        match = SECTION_RE.match(line)
        if match:
            # Found a new section start
            # Save previous section if it has content
            if current_lines:
                sections.append({
                    "section_id": current_id,
                    "text": "\n".join(current_lines).strip()
                })
            
            # Start new section
            current_id = match.group(1) # Extract the numbering (e.g., "6.7.4")
            current_lines = [line]
        else:
            # Continue current section
            current_lines.append(line)

    # Add the last section
    if current_lines:
        sections.append({
            "section_id": current_id,
            "text": "\n".join(current_lines).strip()
        })

    # Filter out empty intro if it's empty
    sections = [s for s in sections if s['text'].strip()]
    
    print(f"✂️  Identified {len(sections)} logical sections.")
    return sections

def build_chunks(sections):
    """
    Groups 2-3 sections into chunks based on character limits.
    Returns list of dicts: {"id": "sec1;sec2", "chunk": "..."}
    """
    chunks = []
    i = 0
    total_sections = len(sections)

    while i < total_sections:
        # Start a new chunk with the current section
        current_section = sections[i]
        
        # HANDLE LARGE SECTIONS: If a single section is too big, split it
        if len(current_section['text']) > MAX_CHARS:
            # Split this section into smaller parts
            large_text = current_section['text']
            parts = [large_text[j:j+MAX_CHARS] for j in range(0, len(large_text), MAX_CHARS)]
            
            for idx, part in enumerate(parts):
                chunks.append({
                    "id": f"{current_section['section_id']}_part{idx+1}",
                    "chunk": part
                })
            i += 1
            continue

        chunk_ids = [current_section['section_id']]
        chunk_text = current_section['text']
        
        # Try to add next section (i+1)
        next_idx = i + 1
        if next_idx < total_sections:
            next_section = sections[next_idx]
            combined_text = chunk_text + "\n\n" + next_section['text']
            
            # Condition: Always try to group at least 2 if under max limit
            # OR if the first one was very short (under MIN_CHARS), we definitely want to add more.
            if len(combined_text) <= MAX_CHARS:
                chunk_text = combined_text
                chunk_ids.append(next_section['section_id'])
                
                # Try to add a third section (i+2)
                next_next_idx = i + 2
                if next_next_idx < total_sections:
                    third_section = sections[next_next_idx]
                    combined_three = chunk_text + "\n\n" + third_section['text']
                    
                    if len(combined_three) <= MAX_CHARS:
                        chunk_text = combined_three
                        chunk_ids.append(third_section['section_id'])
                        i += 3 # Consumed 3 sections
                    else:
                        i += 2 # Consumed 2 sections
                else:
                    i += 2 # Consumed 2 sections (end of list)
            else:
                # Next section makes it too big, stick with 1
                i += 1
        else:
            # Last section alone
            i += 1

        chunks.append({
            "id": ";".join(chunk_ids),
            "chunk": chunk_text
        })

    print(f"📦 Created {len(chunks)} chunks from {total_sections} sections.")
    return chunks

def generate_embeddings(chunks):
    """
    Generates embeddings for chunks using OpenAI API.
    Updates chunks in-place with 'embedding' key.
    """
    print(f"🚀 Generating embeddings for {len(chunks)} chunks...")
    
    batch_size = 1  # Reduced to 1 to prevent token limit errors
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [item['chunk'] for item in batch]
        
        try:
            response = client.embeddings.create(
                input=texts,
                model=EMBEDDING_MODEL
            )
            
            for j, data_item in enumerate(response.data):
                batch[j]['embedding'] = data_item.embedding
                
            print(f"   Processed batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")
            
        except Exception as e:
            print(f"❌ Error generating embeddings for batch starting at {i}: {e}")
            # Critical error - we don't want to save partial data with missing embeddings usually
            # But for now let's raise so we notice
            raise e

    # Validation
    missing_embeddings = [c for c in chunks if 'embedding' not in c]
    if missing_embeddings:
        raise ValueError(f"❌ Failed: {len(missing_embeddings)} chunks are missing embeddings!")

    return chunks

def save_preview(chunks):
    """Saves a text preview of chunks for manual inspection."""
    with open(PREVIEW_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(f"=== CHUNK ID: {c['id']} ===\n")
            f.write(c['chunk'])
            f.write("\n\n" + "-"*50 + "\n\n")
    print(f"📝 Preview saved to {PREVIEW_OUTPUT_PATH}")

def main():
    print("🎬 Starting RAG Index Build Process...")

    try:
        # 1. Extract
        raw_text = extract_docx(DOCX_PATH)
        
        # 2. Sectioning
        sections = split_into_sections(raw_text)
        
        # 3. Chunking
        chunks = build_chunks(sections)
        
        # 4. Preview (Sanity Check)
        save_preview(chunks)

        # 5. Embedding
        final_chunks = generate_embeddings(chunks)

        # 6. Save
        print(f"💾 Saving index to {INDEX_OUTPUT_PATH}...")
        os.makedirs(os.path.dirname(INDEX_OUTPUT_PATH), exist_ok=True)
        with open(INDEX_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2)

        # 7. Final Verification
        print("✅ Sanity Check: Verifying output...")
        with open(INDEX_OUTPUT_PATH, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            print(f"   - Loaded {len(saved_data)} chunks from disk.")
            first_chunk = saved_data[0]
            print(f"   - Sample ID: {first_chunk.get('id')}")
            print(f"   - Has embedding? {'yes' if 'embedding' in first_chunk else 'NO'}")
            
        print("🎉 RAG Index built successfully!")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
