from langchain.schema import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, MessagesState, START
from langgraph.checkpoint.memory import MemorySaver
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import uuid
# file import
from config.db_config import save_message, get_thread_messages, threads
from config.vertex_config import llm, instruction, vector_store
from pdf_parser import process_pdf_for_embedding


def call_model(state: MessagesState):
    user_input = state['messages'][-1].content
    history = state.get("history", [])

    results = vector_store.similarity_search(user_input, k=5)

    context = ""
    for idx, doc in enumerate(results, 1):
        code = doc.metadata.get("code", f"Section {idx}")
        context += f"[{code}]: {doc.page_content}\n"

    history_lines = []
    for m in state["messages"]:
        if hasattr(m, "content"):
            role = "User" if m.type == "human" else "Bot"
            history_lines.append(f"{role}: {m.content}")

    prompt = (
        f"{instruction}\n\n"
        f"Conversation so far:\n"
        + "\n".join(history_lines)
        + f"\n\nContext:\n{context}\n\nUser question: {user_input}\n\nAnswer:"
    )

    response = llm.invoke(prompt)
    history.append({"question": user_input, "answer": response})
    state["messages"].append(AIMessage(content=response))
    return {
        "messages": state["messages"],
        "history": history,
        "answer": response
    }

# Set up LangGraph state machine
graph = StateGraph(MessagesState)
graph.add_node("RAG", call_model)
graph.add_edge(START, "RAG")
graph.add_edge("RAG", END)
memory = MemorySaver()
compiled_graph = graph.compile(checkpointer=memory)  

# --- FastAPI section ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

class ChatRequest(BaseModel):
    message: str
    history: list 
    thread_id: str = None

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    messages = []
    for msg in req.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=req.message))
    state = {
        "messages": messages,
        "history": [],
        "thread_id": thread_id,
    }
    config = {"configurable": {"thread_id": thread_id}}

    # --- Set chat title only if this is the very first message in this thread ---
    is_new_chat = len(req.history) == 0
    chat_title = req.message[:50] if is_new_chat else None

    # SAVE user message; set title only on new chat
    save_message(thread_id, {"role": "user", "content": req.message}, title=chat_title)

    new_state = compiled_graph.invoke(state, config)
    print("Thread ID: ", thread_id)

    # Find last assistant answer in messages
    answer = "[No answer found]"
    for msg in reversed(new_state["messages"]):
        if isinstance(msg, AIMessage):
            answer = msg.content
            break

    response_messages = [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in new_state["messages"]
    ]

    # SAVE only the last AI message (no need to update title here)
    ai_msg = new_state["messages"][-1]   # last message is always AI
    save_message(thread_id, {"role": "assistant", "content": ai_msg.content})

    return {
        "answer": answer,
        "messages": response_messages,
        "thread_id": thread_id
    }


@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Save PDF to a temporary file
    suffix = os.path.splitext(file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    # Parse, chunk, and embed
    num_chunks = process_pdf_for_embedding(temp_path)
    os.remove(temp_path)  # cleanup

    return {"status": "ok", "filename": file.filename, "chunks_added": num_chunks}


@app.get("/get_thread/{thread_id}")
async def get_thread(thread_id: str):
    """
    Returns the full chat history for a thread_id.
    """
    messages = get_thread_messages(thread_id)
    return {"thread_id": thread_id, "messages": messages}

@app.get("/get_threads")
def get_threads():
    all_threads = threads.find({}, {"thread_id": 1, "title": 1})
    thread_list = [{"thread_id": t["thread_id"], "title": t.get("title", "No Title")} for t in all_threads]
    return thread_list

@app.post("/create_thread")
async def create_thread(data: dict):
    thread_id = data.get("thread_id")
    title = data.get("title", "Untitled Chat")
    threads.update_one(
        {"thread_id": thread_id},
        {"$setOnInsert": {"thread_id": thread_id, "title": title, "messages": []}},
        upsert=True
    )
    return {"status": "ok"}

@app.post("/update_thread_title")
async def update_thread_title(data: dict):
    thread_id = data.get("thread_id")
    title = data.get("title")
    threads.update_one({"thread_id": thread_id}, {"$set": {"title": title}})
    return {"status": "ok"}
