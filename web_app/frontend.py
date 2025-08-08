import streamlit as st
from dotenv import load_dotenv
import requests
import uuid
import os 

st.set_page_config(layout="wide")  # (optional, but looks better!)

st.markdown("""
<style>
/* Frosted glass sidebar */
[data-testid="stSidebar"] {
    background: rgba(16, 24, 32, 0.75) !important;
    backdrop-filter: blur(8px) !important;
    border-right: 2px solid #ffd47e33;
}
[data-testid="stSidebar"] .stTitle, [data-testid="stSidebar"] h1 {
    color: #ffd47e !important;
    font-size: 2rem !important;
    font-weight: bold !important;
    letter-spacing: 1px;
    margin-top: 1rem;
}
[data-testid="stSidebar"] button, .css-1wvake5 {
    background: rgba(50, 73, 104, 0.7) !important;
    border-radius: 1.2em !important;
    box-shadow: 0 2px 8px #111a2b22 !important;
    color: #ffd47e !important;
    font-weight: 600;
    margin-bottom: 0.5em !important;
    border: 1px solid #ffd47e33 !important;
    transition: background 0.2s;
}
[data-testid="stSidebar"] button:hover {
    background: #ffd47e !important;
    color: #222d3b !important;
}
[data-testid="stSidebar"] .stButton {
    width: 100%;
    margin: 1em 0;
}

/* Chat bubbles */
.stChatMessage.user {
    background: linear-gradient(90deg, #3a71ff 0%, #5b9fff 100%) !important;
    color: #fff !important;
    border-radius: 1.5em 1.5em 0.2em 1.5em !important;
    margin-left: 30%;
    margin-right: 0;
    font-size: 1.09rem !important;
    font-weight: 500;
}
.stChatMessage.assistant {
    background: linear-gradient(90deg, #232f41 0%, #28354a 100%) !important;
    color: #ffd47e !important;
    border-radius: 1.5em 1.5em 1.5em 0.2em !important;
    margin-right: 30%;
    margin-left: 0;
    font-size: 1.09rem !important;
    font-weight: 400;
    border: 1px solid #ffd47e33;
}
/* Chat bubble shadow */
.stChatMessage {
    box-shadow: 0 4px 32px -10px #111a2b20;
}

/* Chat header */
.stTitle, .header-title {
    text-align: center !important;
    color: #ffd47e !important;
    margin-bottom: 0.2em !important;
    font-size: 2.7rem !important;
    font-weight: bold;
    letter-spacing: 1.5px;
    text-shadow: 0 2px 16px #0008;
}

/* Input area */
.stChatInput > div > div > input {
    background: #222d3b !important;
    color: #ffd47e !important;
    border-radius: 12px !important;
    font-size: 1.1em !important;
    padding: 0.8em !important;
    border: 1.5px solid #ffd47e55 !important;
}
.stChatInput > div > div > button {
    background: #ffd47e !important;
    color: #222d3b !important;
    border-radius: 2em !important;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 0.5em 1.5em !important;
    box-shadow: 0 2px 10px #ffd47e22;
    transition: background 0.2s;
}
.stChatInput > div > div > button:hover {
    background: #ffedb3 !important;
    color: #222d3b !important;
}
.stChatMessage {
    animation: fadeInChat 0.6s cubic-bezier(0.39, 0.575, 0.565, 1) both;
}
@keyframes fadeInChat {
    0% {
        opacity: 0;
        transform: translateY(20px) scale(0.98);
        filter: blur(2px);
    }
    70% {
        opacity: 0.8;
        filter: blur(0.7px);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}
</style>
""", unsafe_allow_html=True)

load_dotenv()
BACKEND_IMG=os.getenv("BACKEND_IMG")

with st.sidebar:
        
    st.title("💬 Chats")
    try:                       
        threads = requests.get(f"{BACKEND_IMG}/get_threads").json()
    except Exception as e:
        st.warning("Couldn't connect to backend. Is it running?")
        threads = []

    selected_thread_id = st.session_state.get("thread_id")

    # Display list of threads
    for t in threads:
        if st.button(f"📁 {t['title']}", key=t['thread_id']):
            thread_data = requests.get(f"{BACKEND_IMG}/get_thread/{t['thread_id']}").json()
            st.session_state.messages = thread_data["messages"]
            st.session_state.thread_id = t["thread_id"]
            st.session_state.thread_title = t['title']

    # New chat
    if st.button("➕ New Chat", key="new-chat"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.thread_title = "Untitled Chat"
        # Optionally: notify backend about the new chat (so it's visible in sidebar immediately)
        requests.post(f"{BACKEND_IMG}/create_thread", json={
            "thread_id": st.session_state.thread_id,
            "title": st.session_state.thread_title
        })

    # Show editable title for selected chat
    if "thread_id" in st.session_state and st.session_state.thread_id:
        current_title = st.session_state.get("thread_title", "Untitled Chat")
        new_title = st.text_input("Chat Title", value=current_title, key="title_input")
        if new_title != current_title:
            st.session_state.thread_title = new_title
            # Update in backend
            requests.post(f"{BACKEND_IMG}/update_thread_title", json={
                "thread_id": st.session_state.thread_id,
                "title": new_title
            })

    uploaded_pdf = st.file_uploader(" ", type="pdf", label_visibility="collapsed", accept_multiple_files=False)
    if uploaded_pdf:
        st.success(f"Uploaded: {uploaded_pdf.name}")

col1, col2 = st.columns([0.6, 3.4])
image_path = os.path.join(os.path.dirname(__file__), "static", "image.png")
with col1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image(image_path, width=70)
with col2:
    st.markdown("""
<div style="display:flex;align-items:center;gap:1.3em;margin-top:1.5em;margin-bottom:0.7em;">
    <span style="font-size:2.3rem;font-weight:700;color:#ffd47e;font-family: 'Segoe UI', 'Arial', sans-serif;">ISO Compliance Bot</span>
</div>
""", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# Session & history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Show chat history
for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role):
        st.markdown(msg["content"])


if prompt := st.chat_input("What can I do for you?"):
    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare backend payload
    payload = {
        "message": prompt,
        "history": [m for m in st.session_state.messages if m["role"] == "user" or m["role"] == "assistant"],
        "thread_id": st.session_state.thread_id
    }
    # Call backend
    try:
        response = requests.post(f"{BACKEND_IMG}/chat", json=payload, timeout=90).json()
        reply = response.get("answer", "[No answer found]")
        st.session_state.thread_id = response.get("thread_id", st.session_state.thread_id)
    except Exception as e:
        reply = f"[Backend error: {e}]"

    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
