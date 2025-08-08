from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import json

# file import
from config.vertex_config import vector_store

data_path = "../data/iso_docs.jsonl"
PROCESSED_LOG_PATH = "../data/processed_codes.txt"

def load_processed_codes(log_path=PROCESSED_LOG_PATH):
    processed_codes = set()
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                processed_codes.add(line.strip())
    except FileNotFoundError:
        pass
    return processed_codes

def save_processed_codes(processed_codes, log_path=PROCESSED_LOG_PATH):
    with open(log_path, "w", encoding="utf-8") as f:
        for code in processed_codes:
            f.write(f"{code}\n")

def main():
    already_processed = load_processed_codes()
    new_documents = load_documents(already_processed)
    if not new_documents:
        print("No new documents to embed.")
        return
    chunks = split_text(new_documents)
    embed_to_vectorstore(chunks)
    # Save newly processed codes
    all_processed = already_processed | set(doc.metadata["code"] for doc in new_documents)
    save_processed_codes(all_processed)

def load_documents(already_processed):
    docs = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            code = entry.get("code", "")
            if code in already_processed:
                continue  # Skip duplicates
            docs.append(Document(
                page_content=f"{code} {entry['text']}",
                metadata={"code": code}
            ))
    return docs

def split_text(documents: list[Document], chunk_size=1000, chunk_overlap=120):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks = []
    for doc in documents:
        doc_chunks = text_splitter.split_documents([doc]) 
        for chunk in doc_chunks:
            code = doc.metadata.get("code", "")
            chunk.page_content = f"{code} {chunk.page_content}"
            chunks.append(chunk)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks

def embed_to_vectorstore(chunks: list[Document], batch_size=1000):
    try:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vector_store.add_documents(batch)
            print(f"Added {len(batch)} chunks ({i+1}-{i+len(batch)})")
        print(f"Total: {len(chunks)} ISO clause chunks added.")
    except Exception as e:
        print("Error Adding Documents to Vector Store\n", e)


if __name__ == "__main__":
    main()
