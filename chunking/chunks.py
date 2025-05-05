import re
import os
import spacy
import tiktoken
import argparse
import json

# Setup NLP model and tokenizer
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

tokenizer = tiktoken.encoding_for_model("text-embedding-3-small")

# Constants
CHUNK_LIMIT = 8192
SAFE_LIMIT = 2000

def token_count(text):
    return len(tokenizer.encode(text))

def break_into_subchunks(text, max_tokens=SAFE_LIMIT):
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    return [tokenizer.decode(tokens[i:i + max_tokens]) for i in range(0, len(tokens), max_tokens)]

def heading_based_split(md_text, level=2):
    header_pattern = rf'(?=^{"#" * level} )'
    raw_segments = re.split(header_pattern, md_text, flags=re.MULTILINE)
    
    final_chunks = []
    for section in raw_segments:
        cleaned = section.strip()
        if cleaned:
            final_chunks.extend(break_into_subchunks(cleaned, max_tokens=CHUNK_LIMIT // 2))
    return final_chunks

def semantic_split(md_text, max_sents=5):
    doc = nlp(md_text)
    sents = [sent.text for sent in doc.sents]

    grouped = []
    buffer = []
    for idx, sentence in enumerate(sents):
        buffer.append(sentence)
        if (idx + 1) % max_sents == 0:
            joined = " ".join(buffer)
            grouped.extend(break_into_subchunks(joined, max_tokens=CHUNK_LIMIT // 2))
            buffer = []
    if buffer:
        grouped.extend(break_into_subchunks(" ".join(buffer), max_tokens=CHUNK_LIMIT // 2))
    return grouped

def recursive_split(text, max_tokens=CHUNK_LIMIT):
    if token_count(text) <= max_tokens:
        return [text]

    for splitter in ["\n\n", "\n", ". "]:
        parts = text.split(splitter)
        if len(parts) == 1:
            continue

        chunks, current = [], ""
        for part in parts:
            candidate = (current + splitter + part).strip() if current else part.strip()
            if token_count(candidate) <= max_tokens:
                current = candidate
            else:
                if current:
                    chunks.extend(recursive_split(current, max_tokens))
                current = part.strip()
        if current:
            chunks.extend(recursive_split(current, max_tokens))
        return chunks

    return break_into_subchunks(text, max_tokens=max_tokens)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Choose a chunking strategy.")
    parser.add_argument("--strategy", choices=["heading", "semantic", "recursive"], required=True, help="Choose chunking strategy.")
    parser.add_argument("--input", default="chunks/Q1 (1).md", help="Path to Markdown input file.")
    parser.add_argument("--preview", action="store_true", help="Print chunks to console.")
    parser.add_argument("--save", action="store_true", help="Save chunks to .txt and .json")

    args = parser.parse_args()
    strategy = args.strategy
    md_input_path = args.input

    if not os.path.exists(md_input_path):
        print(f"❌ File not found: {md_input_path}")
        exit(1)

    with open(md_input_path, "r", encoding="utf-8") as file:
        markdown_data = file.read()

    print(f"\n🔹 Applying '{strategy}' chunking strategy...")

    if strategy == "heading":
        chunks = heading_based_split(markdown_data)
    elif strategy == "semantic":
        chunks = semantic_split(markdown_data)
    elif strategy == "recursive":
        chunks = recursive_split(markdown_data)
    else:
        raise ValueError("❌ Invalid strategy selected.")

    print(f"✅ Total Chunks Created: {len(chunks)}")

    if args.preview:
        print("\n📋 Preview of Chunks:\n" + "-" * 30)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n🔹 Chunk {i}:\n{'-'*20}\n{chunk}\n")

    if args.save:
        os.makedirs("chunks", exist_ok=True)

        txt_path = f"chunks/{strategy}_chunks.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks, 1):
                f.write(f"--- Chunk {i} ---\n{chunk}\n\n")

        json_path = f"chunks/{strategy}_chunks.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(chunks, jf, indent=2)

        print(f"\n💾 Saved chunks to:\n- {txt_path}\n- {json_path}")
    
    print(f"\n🔢 Final Count: {len(chunks)} chunks generated using '{strategy}' strategy.")
