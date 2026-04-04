import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from bson.objectid import ObjectId

def run_database_test():
    # 1. get the connection string from the environment variable
    # render will inject this automatically once you set it in their dashboard
    mongo_uri = os.environ.get("MONGODB_URI")
    
    if not mongo_uri:
        print("error: MONGODB_URI environment variable is not set.")
        print("export it locally like this: export MONGODB_URI='your_string_here'")
        sys.exit(1)

    print("-> attempting to connect to mongodb atlas...")
    
    try:
        # 2. connect to the cluster (timeout set to 5 seconds so it doesn't hang forever if it fails)
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # trigger a quick server ping to verify the connection
        client.admin.command('ping')
        print("-> successfully connected to mongodb atlas!\n")
        
        # 3. select the database and collection
        db = client.todo_app
        tasks_collection = db.tasks
        
        # clear out old test data so we have a clean slate (optional but good for testing)
        tasks_collection.delete_many({})
        
        # 4. create 10 realistic tasks with slightly different timestamps
        print("-> inserting 10 test tasks...")
        base_time = datetime.utcnow()
        new_tasks = [
            {"title": "buy groceries for the week", "completed": False, "created_at": base_time - timedelta(minutes=100)},
            {"title": "finish python backend", "completed": True, "created_at": base_time - timedelta(minutes=90)},
            {"title": "deploy frontend to render", "completed": False, "created_at": base_time - timedelta(minutes=80)},
            {"title": "add network access ip", "completed": True, "created_at": base_time - timedelta(minutes=70)},
            {"title": "walk the dog", "completed": False, "created_at": base_time - timedelta(minutes=60)},
            {"title": "test database connection", "completed": True, "created_at": base_time - timedelta(minutes=50)},
            {"title": "read documentation", "completed": False, "created_at": base_time - timedelta(minutes=40)},
            {"title": "fix that one weird bug", "completed": False, "created_at": base_time - timedelta(minutes=30)},
            {"title": "drink some water", "completed": True, "created_at": base_time - timedelta(minutes=20)},
            {"title": "celebrate when it works", "completed": False, "created_at": base_time - timedelta(minutes=10)}
        ]
        
        insert_result = tasks_collection.insert_many(new_tasks)
        print(f"-> successfully inserted {len(insert_result.inserted_ids)} tasks.\n")
        
        # 5. read the 5 most recent tasks (sorting by created_at descending)
        print("-> fetching the 5 most recent tasks:")
        recent_tasks = tasks_collection.find().sort("created_at", -1).limit(5)
        for task in recent_tasks:
            status = "[x]" if task["completed"] else "[ ]"
            print(f"   {status} {task['title']} (created: {task['created_at'].strftime('%H:%M:%S')})")
        print("\n")
            
        # 6. read one specific document by its unique _id
        print("-> fetching one specific task by its _id:")
        first_id = insert_result.inserted_ids[0]
        single_task = tasks_collection.find_one({"_id": first_id})
        if single_task:
            print(f"   found task: {single_task['title']} (id: {single_task['_id']})\n")
            
    except ServerSelectionTimeoutError:
        print("error: could not connect to mongodb. check your username, password, and ip access list.")
    except Exception as e:
        print(f"an unexpected error occurred: {e}")
    finally:
        # 7. always close the connection when done
        if 'client' in locals():
            client.close()
            print("-> database connection closed.")

if __name__ == "__main__":
    run_database_test()