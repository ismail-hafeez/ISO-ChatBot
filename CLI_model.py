from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document, AIMessage
from langgraph.graph import StateGraph, END, MessagesState,START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import uuid
# file imports
from config.vertex_config import vector_store, instruction, llm
from config.db_config import save_message

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

    # STREAMING CHANGE STARTS HERE
    response_content = ""
    print("\nAssistant:", end=" ", flush=True)
    for chunk in llm.stream(prompt):
        part = getattr(chunk, "content", chunk)
        print(part, end="", flush=True)
        response_content += part
    print()  # Newline

    history.append({"question": user_input, "answer": response_content})
    state["messages"].append(AIMessage(content=response_content))
    return {
        "messages": state["messages"],
        "history": history,
        "answer": response_content
    }

# Set up LangGraph state machine
graph = StateGraph(MessagesState)
graph.add_node("RAG", call_model)
graph.add_edge(START, "RAG")
graph.add_edge("RAG", END)

memory = MemorySaver()
# thread_id must match in config and state
THREAD_ID = str(uuid.uuid4())
config = {"configurable": {"thread_id": THREAD_ID}}
app=graph.compile(checkpointer=memory)

def run_model():
    state = {
        "messages": [],
        "history": []
    }
    while True:
        user = input("User: ")
        if user.lower() == 'exit':
            break

        # Create user message object
        user_msg = HumanMessage(content=user)
        state["messages"].append(user_msg)

        # SAVE USER MESSAGE TO DB
        save_message(THREAD_ID, {"role": "user", "content": user_msg.content})

        # Generate response
        state = app.invoke(state, config)

        # Find last assistant message (should be appended by call_model)
        for mssg in state['messages']:
            mssg.pretty_print()

        # SAVE ASSISTANT MESSAGE TO DB
        ai_msg = state["messages"][-1]   # last message is always AI
        save_message(THREAD_ID, {"role": "assistant", "content": ai_msg.content})


if __name__=="__main__":
    run_model()
