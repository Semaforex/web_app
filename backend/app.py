import os
import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
# this allows your react app on a different port to talk to python
CORS(app) 

@app.route('/api/test', methods=['POST'])
def run_test():
    try:
        # connect to the database
        mongo_uri = os.environ.get("MONGODB_URI")
        client = MongoClient(mongo_uri)
        collection = client.todo_app.tasks
        
        # do something: insert a test document
        doc = {"message": "hello from react and python!", "time": datetime.datetime.utcnow()}
        collection.insert_one(doc)
        
        # count how many tests we've run total
        total_tests = collection.count_documents({})
        
        return jsonify({
            "status": "success", 
            "message": "database updated!",
            "total_tasks_in_db": total_tests
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)