from langchain_community.document_loaders import PyPDFLoader, PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
import sys, os
from web_app.vertex_config import vector_store
from PyPDF2 import PdfReader
import os

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 120

def parse_and_chunk_pdf(pdf_path_or_dir):
    """
    Loads and splits PDF file(s) into chunks, adding PDF metadata to each chunk.
    """
    chunks = []

    # Single PDF file
    if os.path.isfile(pdf_path_or_dir):
        loader = PyPDFLoader(pdf_path_or_dir)
        docs = loader.load()
        # Try to get PDF metadata (title, author, etc)
        meta = get_pdf_metadata(pdf_path_or_dir)
        for doc in docs:
            # If you want page number: doc.metadata.get("page")
            doc.metadata.update(meta)
        chunks.extend(split_docs_with_metadata(docs))
    # Directory of PDFs
    elif os.path.isdir(pdf_path_or_dir):
        for fname in os.listdir(pdf_path_or_dir):
            if fname.lower().endswith(".pdf"):
                full_path = os.path.join(pdf_path_or_dir, fname)
                loader = PyPDFLoader(full_path)
                docs = loader.load()
                meta = get_pdf_metadata(full_path)
                for doc in docs:
                    doc.metadata.update(meta)
                chunks.extend(split_docs_with_metadata(docs))
    else:
        raise FileNotFoundError(f"No PDF found at: {pdf_path_or_dir}")

    print(f"Split into {len(chunks)} chunks with metadata.")
    return chunks

def get_pdf_metadata(pdf_path):
    """Extracts basic PDF metadata using PyPDF2."""
    meta = {
        "filename": os.path.basename(pdf_path)
    }
    try:
        reader = PdfReader(pdf_path)
        doc_info = reader.metadata or {}
        meta["title"] = doc_info.title if doc_info.title else meta["filename"]
        meta["author"] = doc_info.author if doc_info.author else ""
    except Exception:
        meta["title"] = meta["filename"]
        meta["author"] = ""
    return meta

def split_docs_with_metadata(docs):
    """
    Split documents using chunking, preserving and copying metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )
    out_chunks = []
    for doc in docs:
        splits = splitter.split_documents([doc])
        # Ensure metadata (like filename, title, author) is in each chunk
        for chunk in splits:
            chunk.metadata.update(doc.metadata)
            out_chunks.append(chunk)
    return out_chunks

def embed_chunks_to_vectorstore(chunks, batch_size=1000):
    try:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vector_store.add_documents(batch)
            print(f"Added {len(batch)} chunks ({i+1}-{i+len(batch)})")
        print(f"Total: {len(chunks)} chunks with PDF metadata embedded.")
    except Exception as e:
        print("Error Adding Chunks to Vector Store\n", e)

def process_pdf_for_embedding(pdf_path_or_dir):
    chunks = parse_and_chunk_pdf(pdf_path_or_dir)
    embed_chunks_to_vectorstore(chunks)
    return len(chunks)

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "./pdfs"
    process_pdf_for_embedding(path)
