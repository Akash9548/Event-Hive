# view_db.py
from app import create_app
from extensions import db
from models import User, Event, Booking, Ticket

def view_database():
    app = create_app()
    
    with app.app_context():
        print("=== USERS ===")
        users = User.query.all()
        for user in users:
            print(f"ID: {user.id}, Name: {user.name}, Email: {user.email}, Role: {user.role}")
        
        print("\n=== EVENTS ===")
        events = Event.query.all()
        for event in events:
            print(f"ID: {event.id}, Title: {event.title}, Date: {event.date}, Location: {event.location}")
        
        print("\n=== BOOKINGS ===")
        bookings = Booking.query.all()
        for booking in bookings:
            print(f"ID: {booking.id}, User: {booking.user_id}, Event: {booking.event_id}, Status: {booking.status}")
        
        print("\n=== TICKETS ===")
        tickets = Ticket.query.all()
        for ticket in tickets:
            print(f"ID: {ticket.id}, Event: {ticket.event_id}, Type: {ticket.type}, Price: {ticket.price}")

if __name__ == "__main__":
    view_database()