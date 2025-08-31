from flask import Blueprint, request, jsonify, send_file, current_app
from extensions import db
from models import Booking, Event, User, Ticket
from utils.qr import generate_qr
from flask_mail import Message

import io, hmac, hashlib, logging, time
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import razorpay

bookings_bp = Blueprint("bookings", __name__)

# -------- Helpers --------
def _get_razorpay_client():
    """Check if we have real Razorpay credentials, otherwise use test mode."""
    key_id = current_app.config.get("RAZORPAY_KEY_ID")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET")
    
    # If keys are placeholders or test_mode, use test mode
    if (not key_id or not key_secret or 
        key_id == "test_mode" or key_id == "rzp_test_xxxxxxxx" or
        key_secret == "test_mode" or key_secret == "your_secret_key"):
        return None  # Test mode
    
    try:
        import razorpay
        return razorpay.Client(auth=(key_id, key_secret))
    except ImportError:
        return None

def _create_or_get_ticket(event_id, ticket_type, price):
    """Create a ticket if it doesn't exist, or return existing one."""
    ticket = Ticket.query.filter_by(event_id=event_id, type=ticket_type).first()
    if not ticket:
        ticket = Ticket(
            event_id=event_id,
            type=ticket_type,
            price=price,
            max_quantity=100  # Default value
        )
        db.session.add(ticket)
        db.session.commit()
    return ticket

def _make_ticket_pdf_buffer(booking, event, user, qr_path):
    """Return BytesIO of a 1-page PDF ticket with QR image embedded."""
    qr_img = Image.open(qr_path)
    qr_reader = ImageReader(qr_img)

    buf = io.BytesIO()
    p = canvas.Canvas(buf)
    
    # Set up dimensions
    page_width, page_height = 595, 842  # A4 size in points
    margin = 50
    content_width = page_width - 2 * margin
    
    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(margin, page_height - margin - 30, "EventHive Ticket")
    p.line(margin, page_height - margin - 40, page_width - margin, page_height - margin - 40)
    
    # Event details - left side
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, page_height - margin - 80, "Event Details:")
    
    p.setFont("Helvetica", 12)
    y_position = page_height - margin - 110
    p.drawString(margin, y_position, f"Event: {event.title}")
    p.drawString(margin, y_position - 25, f"Date: {event.date} at {event.time}")
    p.drawString(margin, y_position - 50, f"Location: {event.location}")
    
    # Attendee details
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, y_position - 100, "Attendee Details:")
    
    p.setFont("Helvetica", 12)
    p.drawString(margin, y_position - 125, f"Name: {user.name}")
    p.drawString(margin, y_position - 150, f"Ticket Type: {booking.ticket_type}")
    p.drawString(margin, y_position - 175, f"Quantity: {booking.quantity}")
    p.drawString(margin, y_position - 200, f"Booking ID: {booking.id}")
    p.drawString(margin, y_position - 225, f"Status: {booking.status}")
    
    # QR code - right side
    qr_size = 150
    qr_x = page_width - margin - qr_size - 50  # Right side with some margin
    qr_y = y_position - 100  # Aligned with attendee details
    
    p.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
    
    # QR code label
    p.setFont("Helvetica-Bold", 10)
    p.drawString(qr_x, qr_y - 20, "Scan at event entrance")
    
    # Add test mode watermark if in test mode
    client = _get_razorpay_client()
    if client is None:
        p.setFont("Helvetica-Oblique", 12)
        p.setFillColorRGB(1, 0, 0)  # Red color for test mode
        p.drawString(margin, margin + 20, "TEST MODE - NOT A REAL TICKET")
        p.setFillColorRGB(0, 0, 0)  # Reset to black
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(margin, margin, "Thank you for using EventHive!")
    
    p.showPage()
    p.save()
    buf.seek(0)
    return buf

def _send_ticket_email(booking, recipient_email=None):
    """Generate QR + PDF and email ticket to the specified recipient."""
    event = Event.query.get(booking.event_id)
    user = User.query.get(booking.user_id)

    if not user:
        raise ValueError("User not found for booking")

    # Use the provided recipient email, or fall back to user's registered email
    email_to_send = recipient_email or user.email
    
    if not email_to_send:
        raise ValueError("No email address specified for ticket delivery")

    qr_data = f"BookingID:{booking.id} | Event:{event.title} | User:{user.name} | Tickets:{booking.quantity}"
    qr_path = generate_qr(qr_data, booking.id)
    pdf_buf = _make_ticket_pdf_buffer(booking, event, user, qr_path)

    # Check if we're in test mode for payments
    client = _get_razorpay_client()
    if client is None:
        # Payment test mode, but send REAL email
        logging.info(f"Payment Test Mode: Sending REAL email to {email_to_send} for booking {booking.id}")
    else:
        logging.info(f"Production Mode: Sending email to {email_to_send} for booking {booking.id}")

    # ALWAYS try to send email (if Gmail is configured)
    msg = Message(
        subject=f"Your Ticket for {event.title}",
        sender=current_app.config.get("MAIL_USERNAME"),
        recipients=[email_to_send],  # Send to the specified email
        body=(
            f"Hi {user.name},\n\n"
            f"Your booking for '{event.title}' is confirmed!\n"
            f"Booking ID: {booking.id}\n"
            f"Tickets: {booking.quantity} ({booking.ticket_type})\n\n"
            f"Your ticket is attached as a PDF with QR code.\n"
            f"Please show it at the event entrance.\n\n"
            f"Thanks,\nEventHive"
        ),
    )

    pdf_buf.seek(0)
    msg.attach(f"ticket_{booking.id}.pdf", "application/pdf", pdf_buf.read())

    mail = current_app.extensions.get("mail")
    try:
        mail.send(msg)
        return True
    except Exception as e:
        logging.error(f"Email sending failed for booking {booking.id}: {e}")
        # Even if email fails, don't raise exception - just return False
        return False
    
def _generate_test_signature(order_id, payment_id):
    """Generate a test signature for test mode."""
    secret = "test_secret_key"
    return hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

# ----------------- Step 1: Create Order -----------------
@bookings_bp.route("/create-order", methods=["POST"])
def create_order():
    data = request.json or {}
    user_id = data.get("user_id")
    event_id = data.get("event_id")
    ticket_type = data.get("ticket_type")
    quantity = int(data.get("quantity", 1))
    amount = data.get("amount")
    customer_email = data.get("customer_email")
    if not all([user_id, event_id, ticket_type, amount]):
        return jsonify({"error": "user_id, event_id, ticket_type, amount are required"}), 400

    try:
        amount = int(amount)
    except Exception:
        return jsonify({"error": "amount must be an integer value in INR"}), 400

    if amount <= 0 or quantity <= 0:
        return jsonify({"error": "amount and quantity must be > 0"}), 400

    user = User.query.get(user_id)
    event = Event.query.get(event_id)
    if not user or not event:
        return jsonify({"error": "Invalid user or event"}), 400

    # Create or get ticket first
    ticket_price = amount / quantity  # Calculate price per ticket
    ticket = _create_or_get_ticket(event_id, ticket_type, ticket_price)

    # Create booking with the ticket_id
    booking = Booking(
        user_id=user_id,
        event_id=event_id,
        ticket_id=ticket.id,  # This was missing - causing the error
        ticket_type=ticket_type,
        quantity=quantity,
        status="pending",
    )   
    db.session.add(booking)
    db.session.commit()

    # Check if we're in test mode
    client = _get_razorpay_client()
    if client is None:
        # Test mode - simulate Razorpay response
        test_order_id = f"test_order_{booking.id}_{int(time.time())}"
        return jsonify({
            "key": "test_key",
            "order_id": test_order_id,
            "amount": amount * 100,
            "currency": "INR",
            "booking_id": booking.id,
            "test_mode": True,
            "customer_email": customer_email
        }), 201

    try:
        # Real Razorpay integration
        rp_order = client.order.create({
            "amount": amount * 100,
            "currency": "INR",
            "receipt": f"booking_{booking.id}",
            "payment_capture": 1
        })

        return jsonify({
            "key": current_app.config.get("RAZORPAY_KEY_ID"),
            "order_id": rp_order["id"],
            "amount": rp_order["amount"],
            "currency": rp_order["currency"],
            "booking_id": booking.id,
            "test_mode": False,
            "customer_email": customer_email
        }), 201
        
    except Exception as e:
        booking.status = "failed"
        db.session.commit()
        return jsonify({"error": f"Payment gateway error: {str(e)}"}), 500

# ----------------- Step 2: Verify Payment -----------------
@bookings_bp.route("/verify-payment", methods=["POST"])
def verify_payment():
    data = request.json or {}
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    booking_id = data.get("booking_id")
    customer_email = data.get("customer_email")  # Get email from booking process
    test_mode = data.get("test_mode", False)

    if not all([order_id, booking_id]):
        return jsonify({"error": "Missing required fields"}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    # Check if we're in test mode
    client = _get_razorpay_client()
    if client is None or test_mode:
        # Test mode - simulate successful payment
        if not payment_id:
            payment_id = f"test_pay_{booking.id}_{int(time.time())}"
        if not signature:
            signature = _generate_test_signature(order_id, payment_id)
        
        booking.status = "confirmed"
        db.session.commit()
        
        # Try sending REAL email to the provided email address
        email_sent = _send_ticket_email(booking, customer_email)
        email_status = "sent" if email_sent else "failed"

        return jsonify({
            "status": "success",
            "payment_id": payment_id,
            "booking_id": booking.id,
            "email": email_status,
            "test_mode": True
        }), 200

    # Real verification
    if not payment_id or not signature:
        return jsonify({"error": "Missing payment details"}), 400

    secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    generated_signature = hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != signature:
        booking.status = "failed"
        db.session.commit()
        return jsonify({"status": "failed", "reason": "Invalid signature"}), 400

    # Confirm booking
    booking.status = "confirmed"
    db.session.commit()

    # Try sending REAL email to the provided email address
    email_sent = _send_ticket_email(booking, customer_email)
    email_status = "sent" if email_sent else "failed"

    return jsonify({
        "status": "success",
        "payment_id": payment_id,
        "booking_id": booking.id,
        "email": email_status,
        "test_mode": False
    }), 200

# ----------------- All Bookings for a Specific Event (Organizer) -----------------
@bookings_bp.route("/event/<int:event_id>", methods=["GET"])
def get_event_bookings(event_id):
    bookings = Booking.query.filter_by(event_id=event_id).all()
    return jsonify([{
        "booking_id": b.id,
        "user_id": b.user_id,
        "ticket_type": b.ticket_type,
        "quantity": b.quantity,
        "status": b.status
    } for b in bookings])

# ----------------- Booking Details -----------------
@bookings_bp.route("/<int:booking_id>", methods=["GET"])
def get_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    event = Event.query.get(booking.event_id)
    user = User.query.get(booking.user_id)
    return jsonify({
        "booking_id": booking.id,
        "event": event.title if event else None,
        "user": user.name if user else None,
        "ticket_type": booking.ticket_type,
        "quantity": booking.quantity,
        "status": booking.status
    })

# ----------------- All Bookings for a User -----------------
@bookings_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_bookings(user_id):
    bookings = Booking.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "booking_id": b.id,
        "event_id": b.event_id,
        "ticket_type": b.ticket_type,
        "quantity": b.quantity,
        "status": b.status
    } for b in bookings])

# ----------------- Download Ticket (PDF with QR) -----------------
@bookings_bp.route("/<int:booking_id>/ticket", methods=["GET"])
def download_ticket(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    event = Event.query.get(booking.event_id)
    user = User.query.get(booking.user_id)

    qr_data = f"BookingID:{booking.id} | Event:{event.title} | User:{user.name} | Tickets:{booking.quantity}"
    qr_path = generate_qr(qr_data, booking.id)

    pdf_buf = _make_ticket_pdf_buffer(booking, event, user, qr_path)

    return send_file(
        pdf_buf,
        as_attachment=True,
        download_name=f"ticket_{booking.id}.pdf",
        mimetype="application/pdf"
    )