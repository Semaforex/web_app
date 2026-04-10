import os
from datetime import date, datetime, timedelta, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)
# this allows your react app on a different port to talk to python
CORS(app) 


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value


def _get_mongo_client() -> MongoClient:
    mongo_uri = _get_env("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError("MONGODB_URI environment variable is not set.")
    return MongoClient(mongo_uri)


def _get_db(client: MongoClient):
    # keep the existing db name so you don't lose your Render/Mongo wiring
    return client.todo_app


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _serializer() -> URLSafeTimedSerializer:
    # On Render, set SECRET_KEY. Locally, falls back so dev works.
    secret = _get_env("SECRET_KEY", "dev-secret-change-me")
    return URLSafeTimedSerializer(secret_key=secret, salt="single-user-auth")


def _issue_token() -> str:
    return _serializer().dumps({"sub": "single-user"})


def _require_auth() -> None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise PermissionError("Missing Bearer token.")
    token = header.removeprefix("Bearer ").strip()
    if not token:
        raise PermissionError("Missing Bearer token.")
    try:
        data = _serializer().loads(token, max_age=60 * 60 * 24 * 30)  # 30 days
    except SignatureExpired as e:
        raise PermissionError("Session expired. Please log in again.") from e
    except BadSignature as e:
        raise PermissionError("Invalid session. Please log in again.") from e
    if data.get("sub") != "single-user":
        raise PermissionError("Invalid session. Please log in again.")


def _user_doc_defaults() -> dict:
    return {"_id": "singleton", "points": 0, "updated_at": _now_utc()}


def _get_user(db) -> dict:
    users = db.users
    user = users.find_one({"_id": "singleton"})
    if not user:
        users.insert_one(_user_doc_defaults())
        user = users.find_one({"_id": "singleton"})
    return user or _user_doc_defaults()


def _safe_int(value, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except Exception:
        return default


def _task_to_json(task: dict) -> dict:
    return {
        "id": str(task.get("_id")),
        "name": task.get("name"),
        "deadline": task.get("deadline"),
        "difficulty": task.get("difficulty"),
        "points": task.get("points"),
        "repeatDaily": bool(task.get("repeat_daily", False)),
        "completed": bool(task.get("completed", False)),
        "createdAt": task.get("created_at").isoformat() if task.get("created_at") else None,
        "completedAt": task.get("completed_at").isoformat() if task.get("completed_at") else None,
    }


SHOP_ITEMS = [
    {"id": "coffee", "name": "Coffee", "cost": 10},
    {"id": "movie_night", "name": "Movie night", "cost": 25},
    {"id": "new_game", "name": "New game", "cost": 60},
]


@app.errorhandler(PermissionError)
def _handle_permission_error(e: PermissionError):
    return jsonify({"error": str(e)}), 401


@app.errorhandler(RuntimeError)
def _handle_runtime_error(e: RuntimeError):
    return jsonify({"error": str(e)}), 500


@app.errorhandler(Exception)
def _handle_unexpected_error(e: Exception):
    # Avoid turning common client mistakes into blank 500s.
    # In production you might hide details; for now we surface a message for debugging.
    return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    password = body.get("password") or ""
    expected = _get_env("APP_PASSWORD", "changeme")
    if password != expected:
        return jsonify({"error": "Invalid password."}), 401
    return jsonify({"token": _issue_token()}), 200


@app.route("/api/me", methods=["GET"])
def me():
    _require_auth()
    client = _get_mongo_client()
    try:
        db = _get_db(client)
        user = _get_user(db)
        return jsonify({"points": int(user.get("points", 0))}), 200
    finally:
        client.close()


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    _require_auth()
    client = _get_mongo_client()
    try:
        db = _get_db(client)
        tasks = list(db.tasks.find().sort("created_at", -1))
        return jsonify({"tasks": [_task_to_json(t) for t in tasks]}), 200
    finally:
        client.close()


@app.route("/api/tasks", methods=["POST"])
def create_task():
    _require_auth()
    body = request.get_json(silent=True) or {}

    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Task name is required."}), 400

    deadline = body.get("deadline")
    deadline = deadline.strip() if isinstance(deadline, str) else None
    difficulty = body.get("difficulty")
    difficulty = difficulty.strip() if isinstance(difficulty, str) and difficulty.strip() else None
    points = _safe_int(body.get("points"))
    if points is not None and points < 0:
        return jsonify({"error": "Points must be a non-negative integer."}), 400
    repeat_daily = bool(body.get("repeatDaily", False))

    doc = {
        "name": name,
        "deadline": deadline or None,
        "difficulty": difficulty,
        "points": points or 0,
        "repeat_daily": repeat_daily,
        "completed": False,
        "created_at": _now_utc(),
        "completed_at": None,
    }

    client = _get_mongo_client()
    try:
        db = _get_db(client)
        res = db.tasks.insert_one(doc)
        created = db.tasks.find_one({"_id": res.inserted_id})
        return jsonify({"task": _task_to_json(created or doc)}), 201
    finally:
        client.close()


@app.route("/api/tasks/<task_id>/complete", methods=["POST"])
def complete_task(task_id: str):
    _require_auth()
    from bson.errors import InvalidId  # local import keeps startup lean
    from bson.objectid import ObjectId  # local import keeps startup lean

    client = _get_mongo_client()
    try:
        db = _get_db(client)
        tasks = db.tasks
        users = db.users

        try:
            oid = ObjectId(task_id)
        except (InvalidId, TypeError):
            return jsonify({"error": "Invalid task id."}), 400

        task = tasks.find_one({"_id": oid})
        if not task:
            return jsonify({"error": "Task not found."}), 404
        if task.get("completed"):
            return jsonify({"error": "Task already completed."}), 400

        points = int(task.get("points", 0) or 0)
        now = _now_utc()

        tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {"completed": True, "completed_at": now}},
        )

        new_task_json = None
        if task.get("repeat_daily"):
            next_deadline = None
            raw_deadline = task.get("deadline")
            if isinstance(raw_deadline, str) and raw_deadline.strip():
                try:
                    d = datetime.strptime(raw_deadline.strip(), "%Y-%m-%d").date()
                    next_deadline = (d + timedelta(days=1)).isoformat()
                except Exception:
                    next_deadline = None

            next_doc = {
                "name": task.get("name"),
                "deadline": next_deadline,
                "difficulty": task.get("difficulty"),
                "points": int(task.get("points", 0) or 0),
                "repeat_daily": True,
                "completed": False,
                "created_at": now,
                "completed_at": None,
            }
            res = tasks.insert_one(next_doc)
            created_next = tasks.find_one({"_id": res.inserted_id})
            new_task_json = _task_to_json(created_next or next_doc)

        users.update_one(
            {"_id": "singleton"},
            {
                "$setOnInsert": {"_id": "singleton"},
                "$inc": {"points": points},
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

        user = _get_user(db)
        updated = tasks.find_one({"_id": task["_id"]})
        return (
            jsonify(
                {
                    "task": _task_to_json(updated or task),
                    "newTask": new_task_json,
                    "points": int(user.get("points", 0)),
                }
            ),
            200,
        )
    finally:
        client.close()


@app.route("/api/shop", methods=["GET"])
def shop():
    _require_auth()
    return jsonify({"items": SHOP_ITEMS}), 200


@app.route("/api/shop/purchase", methods=["POST"])
def purchase():
    _require_auth()
    body = request.get_json(silent=True) or {}
    item_id = (body.get("itemId") or "").strip()
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found."}), 404

    client = _get_mongo_client()
    try:
        db = _get_db(client)
        users = db.users
        purchases = db.purchases

        user = _get_user(db)
        current_points = int(user.get("points", 0))
        cost = int(item["cost"])
        if current_points < cost:
            return jsonify({"error": "Not enough points."}), 400

        now = _now_utc()
        users.update_one(
            {"_id": "singleton"},
            {
                "$setOnInsert": {"_id": "singleton"},
                "$inc": {"points": -cost},
                "$set": {"updated_at": now},
            },
            upsert=True,
        )
        purchases.insert_one({"user_id": "singleton", "item_id": item_id, "cost": cost, "created_at": now})
        user2 = _get_user(db)
        return jsonify({"points": int(user2.get("points", 0))}), 200
    finally:
        client.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True)