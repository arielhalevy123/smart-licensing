import os
import json
import re
import sys
import math
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
    print("  Warning: OPENAI_API_KEY not found in environment variables.")

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
    print(f"Extracted {len(full_text)} characters from {path}")
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
    
    print(f"  Identified {len(sections)} logical sections.")
    return sections

def split_large_section(section_id, text, max_chars=1200):
    # פיצול גס לפי תווים (פשוט ומהיר). אפשר לשפר לפי טוקנים בהמשך.
    if len(text) <= max_chars:
        return [{"id": section_id, "chunk": text}]
    parts = []
    for idx in range(0, len(text), max_chars):
        part_num = idx // max_chars + 1
        parts.append({
            "id": f"{section_id}_part{part_num}",
            "chunk": text[idx:idx+max_chars]
        })
    return parts


def sections_to_items(sections, max_chars=1200):
    items = []
    for s in sections:
        items.extend(split_large_section(s["section_id"], s["text"], max_chars=max_chars))
    print(f" Created {len(items)} items (sections + split parts).")
    return items


def load_existing_index(path):
    if not os.path.exists(path):
        return [], set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    existing_ids = {item["id"] for item in data if "id" in item}
    return data, existing_ids


def append_index(path, existing_data, new_items):
    # Merge by id (no duplicates)
    merged = {item["id"]: item for item in existing_data if "id" in item}
    for item in new_items:
        merged[item["id"]] = item  # overwrite/update

    all_data = list(merged.values())

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    return all_data


def embed_items_incremental(items, existing_ids, batch_size=5):
    todo = [it for it in items if it["id"] not in existing_ids]
    print(f" Remaining to embed: {len(todo)} (skipping {len(items)-len(todo)} already embedded)")

    embedded = []
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i+batch_size]
        texts = [b["chunk"] for b in batch]

        try:
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        except Exception as e:
            print(f" Embedding failed at batch {i//batch_size + 1}: {e}")
            # Save partial progress before exiting
            if embedded:
                existing_data, _ = load_existing_index(INDEX_OUTPUT_PATH)
                append_index(INDEX_OUTPUT_PATH, existing_data, embedded)
                print(f" Saved partial progress: +{len(embedded)} items")
            raise

        for j, r in enumerate(resp.data):
            embedded.append({
                "id": batch[j]["id"],
                "chunk": batch[j]["chunk"],
                "embedding": r.embedding
            })

        # checkpoint save every batch
        existing_data, _ = load_existing_index(INDEX_OUTPUT_PATH)
        append_index(INDEX_OUTPUT_PATH, existing_data, embedded)
        embedded = []  # clear buffer after saving

        print(f"   Batch {i//batch_size + 1}/{(len(todo)+batch_size-1)//batch_size}")

    return []  # because we already saved incrementally

def save_preview(items):
    """Saves a text preview of items for manual inspection."""
    with open(PREVIEW_OUTPUT_PATH, "w", encoding="utf-8") as f:
        for it in items:
            f.write(f"=== ITEM ID: {it['id']} ===\n")
            f.write(it["chunk"])
            f.write("\n\n" + "-"*50 + "\n\n")
    print(f" Preview saved to {PREVIEW_OUTPUT_PATH}")


def main():
    print(" Starting RAG Index Build Process...")

    try:
        # 0) Load existing index (resume support)
        existing_data, existing_ids = load_existing_index(INDEX_OUTPUT_PATH)

        # 1) Extract
        raw_text = extract_docx(DOCX_PATH)

        # 2) Sectioning
        sections = split_into_sections(raw_text)

        # ---- PARTITION (run in 3 parts) ----
        part = int(sys.argv[1]) if len(sys.argv) > 1 else 1     # 1..3
        parts = int(sys.argv[2]) if len(sys.argv) > 2 else 3    # default 3

        total = len(sections)
        chunk_size = math.ceil(total / parts)
        start = (part - 1) * chunk_size
        end = min(part * chunk_size, total)

        print(f" Running part {part}/{parts}: sections[{start}:{end}] out of {total}")
        sections = sections[start:end]
        # ------------------------------------

        # 3) Convert sections -> items (split big sections if needed)
        items = sections_to_items(sections, max_chars=1200)

        # 4) Preview (Sanity Check)
        save_preview(items)

        
        # 5) Embed only missing items (saves incrementally to disk)
        embed_items_incremental(items, existing_ids, batch_size=10)

        # 6) Reload final index from disk (source of truth)
        final, _ = load_existing_index(INDEX_OUTPUT_PATH)
        print(f"Total saved items: {len(final)}")

        # 7) Final Verification
        print("Sanity Check: Verifying output...")
        if not final:
            raise RuntimeError("Index file is empty after embedding. Something went wrong.")
        print(f"   - Sample ID: {final[0].get('id')}")
        print(f"   - Has embedding? {'yes' if 'embedding' in final[0] else 'NO'}")  

        print(" RAG Index built successfully!")

    except Exception as e:
        print(f" Critical Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()