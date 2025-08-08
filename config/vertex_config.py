from langchain_google_vertexai import (
    VertexAI, VertexAIEmbeddings, 
    VectorSearchVectorStore)
from dotenv import load_dotenv
import vertexai
import os

load_dotenv()
# loading env variables
PROJECT_ID=os.getenv("PROJECT_ID")
REGION=os.getenv("REGION")
INDEX_ID=os.getenv("INDEX_ID")
ENDPOINT_ID=os.getenv("ENDPOINT_ID")
BUCKET_NAME=os.getenv("BUCKET_NAME")

# Initializing vector store
embeddings = VertexAIEmbeddings(model_name="text-embedding-005") 
vector_store =  VectorSearchVectorStore.from_components(
    project_id=PROJECT_ID,
    region=REGION,
    gcs_bucket_name=BUCKET_NAME,
    index_id=INDEX_ID,
    endpoint_id=ENDPOINT_ID,
    embedding=embeddings,
    batch_size=1000,
    stream_update=True
)

# Prompt
instruction = (
    "You are linked with ISO database"
    "The prompt should be in a Legal-style clause citation in responses (e.g., “as per ISO 26262 Part 6, Clause 6.4”)"
    "If a document is not found, ask the user to upload the document if they can as you only have limited information"
    "Your response should be in bullet forms, and avoid long paragraphs"
    "Give suitable headings followed by bullet points"
    "Always remember previous responses in case the user wants a summary"
    "If the user greets or says hello, answer accordingly"
)

# LLM Model
llm = VertexAI(model_name="gemini-2.5-flash")