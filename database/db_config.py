import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_cluster=os.getenv("MONGO_URL")

client = MongoClient(mongo_cluster)
db = client["iso-bot-db"]
threads = db["threads"]

def delete_db():
    client.drop_database("iso-bot-db")
    print("Database deleted!")

def save_message(thread_id, message, title="None"):
    update_fields = {"$push": {"messages": message}}
    if title:  # Only set title if provided and thread is new
        update_fields["$setOnInsert"] = {"title": title}
    threads.update_one(
        {"thread_id": thread_id},
        update_fields,
        upsert=True
    )
    
def get_all_threads():
    # Get thread_id and last message (or some preview)
    thread_list = []
    for t in threads.find({}, {"thread_id": 1, "messages": 1}):
        last_msg = t["messages"][-1]["content"] if t.get("messages") else ""
        thread_list.append({"thread_id": t["thread_id"], "preview": last_msg[:50]})
    return thread_list

def get_thread_messages(thread_id):
    doc = threads.find_one({"thread_id": thread_id})
    return doc["messages"] if doc and "messages" in doc else []
