from flask import Blueprint, request, jsonify
from extensions import db
from models import Event

events_bp = Blueprint("events", __name__)

# ----------------- Get All Events -----------------
@events_bp.route("/", methods=["GET"])
def get_events():
    events = Event.query.all()
    return jsonify([
        {
            "id": e.id,
            "title": e.title,
            "date": e.date,
            "time": e.time,
            "location": e.location,
            "description": e.description,
            "category": e.category
        }
        for e in events
    ])

# ----------------- Create Event -----------------
@events_bp.route("/", methods=["POST"])
def create_event():
    data = request.json
    new_event = Event(
        title=data["title"],
        description=data["description"],
        category=data["category"],
        date=data["date"],
        time=data["time"],
        location=data["location"]
    )
    db.session.add(new_event)
    db.session.commit()

    return jsonify({"message": "Event created successfully", "event_id": new_event.id}), 201

# ----------------- Get Single Event -----------------
@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify({
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "date": event.date,
        "time": event.time,
        "location": event.location
    })

# ----------------- Update Event -----------------
@events_bp.route("/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    data = request.json
    event.title = data.get("title", event.title)
    event.description = data.get("description", event.description)
    event.category = data.get("category", event.category)
    event.date = data.get("date", event.date)
    event.time = data.get("time", event.time)
    event.location = data.get("location", event.location)

    db.session.commit()
    return jsonify({"message": "Event updated successfully"})

# ----------------- Delete Event -----------------
@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Event deleted successfully"})