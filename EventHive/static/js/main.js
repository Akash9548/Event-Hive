// ---------------------- Auth ----------------------
async function loginUser(e) {
    e.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch("/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_name", data.name);
        localStorage.setItem("role", data.role);
        localStorage.setItem("user_email", email);
        window.location.href = data.role === "organizer" ? "/organizer.html" : "/dashboard.html";
    } else {
        alert(data.error);
    }
}

async function registerUser(e) {
    e.preventDefault();
    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const phone = document.getElementById("phone").value;
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;

    const res = await fetch("/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, phone, password, role })
    });

    const data = await res.json();
    if (res.ok) {
        // Store user info in localStorage after registration
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_name", name);
        localStorage.setItem("user_email", email);
        localStorage.setItem("user_phone", phone);
        localStorage.setItem("role", role);
        
        alert("Registered successfully! Redirecting to dashboard.");
        window.location.href = role === "organizer" ? "/organizer.html" : "/dashboard.html";
    } else {
        alert(data.error);
    }
}

function logoutUser() {
    localStorage.clear();
    window.location.href = "/login.html";
}

// ---------------------- Attendee Pages ----------------------
async function loadEvents(containerId = "eventsContainer") {
    const res = await fetch("/events/");
    const events = await res.json();
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";
    events.forEach(ev => {
        const div = document.createElement("div");
        div.classList.add("event-card");
        div.innerHTML = `
            <h3>${ev.title}</h3>
            <p>${ev.date} | ${ev.time}</p>
            <p>${ev.location}</p>
            <button onclick="buyTicket(${ev.id})">Buy Ticket</button>
        `;
        container.appendChild(div);
    });
}

async function loadUserBookings(containerId = "bookingsContainer") {
    const user_id = localStorage.getItem("user_id");
    if (!user_id) return;

    const res = await fetch(`/bookings/user/${user_id}`);
    const bookings = await res.json();
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";
    bookings.forEach(b => {
        const div = document.createElement("div");
        div.classList.add("booking-card");
        div.innerHTML = `
            <p>Event ID: ${b.event_id}</p>
            <p>Tickets: ${b.quantity} (${b.ticket_type})</p>
            <p>Status: ${b.status}</p>
            ${b.status === "confirmed" ? `<a href="/bookings/${b.booking_id}/ticket" target="_blank">Download Ticket</a>` : ""}
        `;
        container.appendChild(div);
    });
}

// ---------------------- Razorpay Checkout ----------------------
async function buyTicket(event_id) {
    const user_id = localStorage.getItem("user_id");
    if (!user_id) {
        alert("Please login first.");
        window.location.href = "/login.html";
        return;
    }

    const ticket_type = "General";
    const quantity = 1;
    const amount = 500;

    const orderRes = await fetch("/bookings/create-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id, event_id, ticket_type, quantity, amount })
    });

    const orderData = await orderRes.json();
    if (!orderRes.ok) {
        alert(orderData.error);
        return;
    }

    // Handle test mode
    if (orderData.test_mode) {
        // Simulate payment success with a confirmation dialog
        const confirmPayment = confirm("TEST MODE: Simulate successful payment? Click OK for success, Cancel for failure.");
        
        if (confirmPayment) {
            // Simulate successful payment - will send REAL email
            const verifyRes = await fetch("/bookings/verify-payment", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    razorpay_order_id: orderData.order_id,
                    razorpay_payment_id: `test_pay_${orderData.booking_id}`,
                    razorpay_signature: "test_signature",
                    booking_id: orderData.booking_id,
                    test_mode: true
                })
            });

            const verifyData = await verifyRes.json();
            if (verifyRes.ok && verifyData.status === "success") {
                if (verifyData.email === "sent") {
                    alert("TEST MODE: Payment successful! A real email with your ticket has been sent.");
                } else {
                    alert("TEST MODE: Payment successful! But email sending failed.");
                }
                if (typeof loadUserBookings === 'function') {
                    loadUserBookings();
                }
                // Redirect to tickets page
                window.location.href = "/tickets.html";
            } else {
                alert("TEST MODE: Payment failed.");
            }
        } else {
            // Simulate payment failure
            alert("TEST MODE: Payment was cancelled by user.");
        }
        return;
    }

    // Real Razorpay integration
    const options = {
        key: orderData.key,
        amount: orderData.amount,
        currency: orderData.currency,
        name: "EventHive",
        description: `Tickets for Event ID ${event_id}`,
        order_id: orderData.order_id,
        handler: async function(response) {
            const verifyRes = await fetch("/bookings/verify-payment", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    razorpay_order_id: response.razorpay_order_id,
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_signature: response.razorpay_signature,
                    booking_id: orderData.booking_id
                })
            });

            const verifyData = await verifyRes.json();
            if (verifyRes.ok && verifyData.status === "success") {
                if (verifyData.email === "sent") {
                    alert("Payment successful! Ticket sent to your email.");
                } else {
                    alert("Payment successful! But email sending failed.");
                }
                if (typeof loadUserBookings === 'function') {
                    loadUserBookings();
                }
                window.location.href = "/tickets.html";
            } else {
                alert("Payment failed or signature invalid.");
            }
        },
        prefill: { 
            name: localStorage.getItem("user_name") || "",
            email: localStorage.getItem("user_email") || "",
            contact: localStorage.getItem("user_phone") || ""
        },
        theme: { color: "#3399cc" }
    };

    const rzp = new Razorpay(options);
    rzp.open();
}

// ---------------------- Organizer Pages ----------------------
async function loadOrganizerEvents() {
    const res = await fetch("/events/");
    const events = await res.json();
    const container = document.getElementById("organizerEvents");
    if (!container) return;

    container.innerHTML = "";
    events.forEach(ev => {
        const div = document.createElement("div");
        div.classList.add("event-card");
        div.innerHTML = `
            <h3>${ev.title}</h3>
            <p>${ev.date} | ${ev.time}</p>
            <p>${ev.location}</p>
            <button onclick="viewEventBookings(${ev.id})">View Bookings</button>
            <button onclick="editEvent(${ev.id})">Edit Event</button>
        `;
        container.appendChild(div);
    });
}

async function viewEventBookings(event_id) {
    const res = await fetch(`/bookings/event/${event_id}`);
    const bookings = await res.json();
    
    let html = `<h3>Bookings for Event ${event_id}</h3>`;
    html += `<div class="bookings-grid">`;
    
    bookings.forEach(b => {
        html += `
            <div class="booking-card">
                <p><strong>Booking ID:</strong> ${b.booking_id}</p>
                <p><strong>User ID:</strong> ${b.user_id}</p>
                <p><strong>Type:</strong> ${b.ticket_type}</p>
                <p><strong>Quantity:</strong> ${b.quantity}</p>
                <p><strong>Status:</strong> ${b.status}</p>
            </div>
        `;
    });
    
    html += `</div>`;
    
    const container = document.getElementById("organizerEvents");
    if (container) {
        container.innerHTML = html;
    }
}

function editEvent(event_id) {
    window.location.href = `/edit_event.html?id=${event_id}`;
}

// ---------------------- Utility Functions ----------------------
function checkAuth() {
    const user_id = localStorage.getItem("user_id");
    if (!user_id) {
        window.location.href = "/login.html";
        return false;
    }
    return true;
}

function displayUserInfo() {
    const userName = localStorage.getItem("user_name");
    const userRole = localStorage.getItem("role");
    
    if (userName) {
        const userInfoElement = document.getElementById("userInfo");
        if (userInfoElement) {
            userInfoElement.textContent = `Welcome, ${userName} (${userRole})`;
        }
    }
}

// Add test mode indicator that shows payment is simulated but emails are real
function showHybridModeIndicator() {
    const modeIndicator = document.createElement('div');
    modeIndicator.style.position = 'fixed';
    modeIndicator.style.top = '10px';
    modeIndicator.style.right = '10px';
    modeIndicator.style.backgroundColor = 'orange';
    modeIndicator.style.color = 'black';
    modeIndicator.style.padding = '5px 10px';
    modeIndicator.style.borderRadius = '5px';
    modeIndicator.style.zIndex = '1000';
    modeIndicator.style.fontWeight = 'bold';
    modeIndicator.textContent = 'TEST MODE (Real Emails)';
    modeIndicator.title = 'Payments are simulated but emails are sent for real';
    
    document.body.appendChild(modeIndicator);
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", function() {
    displayUserInfo();
    showHybridModeIndicator();
    
    // Check if user is authenticated on protected pages
    const protectedPages = ["dashboard.html", "booking.html", "organizer.html", "create_event.html", "event_bookings.html", "edit_event.html", "tickets.html"];
    const currentPage = window.location.pathname.split("/").pop();
    
    if (protectedPages.includes(currentPage) && !checkAuth()) {
        return;
    }
    
    // Initialize page-specific functions
    if (typeof loadEvents === 'function' && document.getElementById("eventsContainer")) {
        loadEvents();
    }
    
    if (typeof loadUserBookings === 'function' && document.getElementById("bookingsContainer")) {
        loadUserBookings();
    }
    
    if (typeof loadOrganizerEvents === 'function' && document.getElementById("organizerEvents")) {
        loadOrganizerEvents();
    }
});