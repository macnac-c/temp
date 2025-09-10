import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g
from flask_babel import Babel, gettext as _
import bcrypt
import datetime

# Create the Flask application instance.
app = Flask(__name__)
# Set a secret key for session management and security.
app.secret_key = "supersecretkey"

# --- PostgreSQL Connection Configuration ---
# Get the database URL from an environment variable for security.
# The fallback is for local development with Homebrew.
DATABASE_URL = os.environ.get('DATABASE_URL', 'dbname=mental_health_db user=mahimachauhan password=')

def get_db_connection():
    """
    Establishes and returns a new database connection.
    This function is called by each route that needs to interact with the database.
    """
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- Babel Configuration for Internationalization ---
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
# The correct way to set the locale selector in newer Flask-Babel versions.
# This function is used by Flask-Babel to determine the user's preferred language.
def get_locale():
    """Determines the best language for the user."""
    # Try to get the language from the session
    if 'lang' in session:
        g.locale = session['lang']
        return session['lang']
    # Fallback to the default language if not in session
    g.locale = app.config['BABEL_DEFAULT_LOCALE']
    return g.locale

babel = Babel(app, locale_selector=get_locale)

# --- Database Schema Setup (Run these SQL commands in your psql terminal) ---
# These commands create the tables required by the application.
# They only need to be run once to set up the database.
#
# CREATE TABLE users (
#     id SERIAL PRIMARY KEY,
#     username VARCHAR(255) UNIQUE NOT NULL,
#     email VARCHAR(255) UNIQUE NOT NULL,
#     password BYTEA NOT NULL
# );
#
# CREATE TABLE moods (
#     id SERIAL PRIMARY KEY,
#     email VARCHAR(255) NOT NULL,
#     mood VARCHAR(255) NOT NULL,
#     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
# );
#
# CREATE TABLE chats (
#     id SERIAL PRIMARY KEY,
#     email VARCHAR(255) NOT NULL,
#     user_message TEXT NOT NULL,
#     ai_reply TEXT NOT NULL,
#     created_at TIMESTAMP WITH TIME-ZONE DEFAULT CURRENT_TIMESTAMP
# );
#
# CREATE TABLE bookings (
#     id SERIAL PRIMARY KEY,
#     email VARCHAR(255) NOT NULL,
#     counselor VARCHAR(255) NOT NULL,
#     date DATE NOT NULL,
#     time TIME NOT NULL,
#     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
# );
#
# CREATE TABLE posts (
#    id SERIAL PRIMARY KEY,
#    email VARCHAR(255) NOT NULL,
#    content TEXT NOT NULL,
#    is_anonymous BOOLEAN DEFAULT TRUE,
#    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
# );

# ----------------- Routes -----------------

# Route to set the language
@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    """Sets the language and redirects to the homepage."""
    session['lang'] = lang_code
    return redirect(url_for('home'))

# Home Page (works for logged-in and guest users)
@app.route("/")
def home():
    # Get the username from the session; it will be None if the user is not logged in.
    user = session.get("username")
    return render_template("index.html", user=user)

# Chatbot Page - requires login
@app.route("/chatbot")
def chatbot():
    # Redirect to the login page if no username is found in the session.
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chatbot.html")

# Mood Tracker Page - requires login
@app.route("/mood")
def mood():
    # Redirect to the login page if no username is found in the session.
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("mood.html")

# Booking Page - requires login
@app.route("/booking")
def booking():
    # Redirect to the login page if no username is found in the session.
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("booking.html")

# Resources Page - requires login
@app.route("/resources")
def resources():
    # Redirect to the login page if no username is found in the session.
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("resources.html")

# Forum Page - requires login
@app.route("/forum", methods=["GET", "POST"])
def forum():
    # Redirect to the login page if no username is found in the session.
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Handle new post submission
    if request.method == "POST":
        content = request.form["content"]
        is_anonymous = request.form.get("is_anonymous") == "true"
        # Use the username from the session to identify the user
        username = session["username"]
        
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                # To maintain consistency, we will store the username in the email column
                # It's better to store the email but for the sake of simplicity, we will stick with username
                # as you have changed it previously.
                cursor.execute(
                    "INSERT INTO posts (email, content, is_anonymous) VALUES (%s, %s, %s)",
                    (username, content, is_anonymous)
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to save forum post: {e}")

    # Fetch all posts to display on the forum page
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT id, email, content, is_anonymous, created_at FROM posts ORDER BY created_at DESC")
            posts_data = cursor.fetchall()
            posts_list = []
            for post in posts_data:
                username = None
                # If the post is not anonymous, get the username
                if not post[3]:
                    # As we are storing username in email column, let's fetch it accordingly
                    cursor.execute("SELECT username FROM users WHERE email = %s", (post[1],))
                    user_record = cursor.fetchone()
                    if user_record:
                        username = user_record[0]

                posts_list.append({
                    "id": post[0],
                    "email": post[1],
                    "content": post[2],
                    "is_anonymous": post[3],
                    "created_at": post[4],
                    "username": username
                })
        
        return render_template("forum.html", posts=posts_list)
    except Exception as e:
        print(f"Failed to fetch posts: {e}")
        return render_template("forum.html", posts=[])


# Login route - handles both displaying the page and processing the form
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"].encode("utf-8")
        
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                # Retrieve the username and hashed password from the database
                cursor.execute("SELECT username, password FROM users WHERE email = %s", (email,))
                user_record = cursor.fetchone()
                
                if user_record:
                    # Check if the entered password matches the hashed password in the database
                    if bcrypt.checkpw(password, bytes(user_record[1])):
                        # If successful, store the username in the session and redirect to home
                        session["username"] = user_record[0]
                        return redirect(url_for("home"))
                
                # If user not found or password doesn't match, show an error message
                return render_template("login.html", message=_("Invalid email or password."))
        except Exception as e:
            print(f"Database error during login: {e}")
            return render_template("login.html", message=_("An error occurred. Please try again."))

    return render_template("login.html")

# Register route - handles both displaying the page and processing the form
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"].encode("utf-8")
        confirm = request.form["confirm"].encode("utf-8")

        # Check if passwords match
        if password != confirm:
            return render_template("register.html", message=_("Passwords do not match!"))
        
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                # Check if email or username already exists
                cursor.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    return render_template("register.html", message=_("Email or username already exists. Please try another one."))
                
                # Hash the password and insert the new user into the database
                hashed = bcrypt.hashpw(password, bcrypt.gensalt())
                cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed))
                conn.commit()
                # Redirect to the login page after successful registration
                return redirect(url_for("login"))
        except Exception as e:
            print(f"Database error during registration: {e}")
            return render_template("register.html", message=_("An error occurred. Please try again."))
            
    return render_template("register.html")

# Chatbot response - handles API call from JavaScript
@app.route("/get_response", methods=["POST"])
def get_response():
    # Ensure the user is logged in
    if "username" not in session:
        return jsonify({"response": _("Please login to chat with Moody.")})

    data = request.json
    user_message = data.get("message", "").lower()
    reply = ""

    # Simple keyword-based logic for the chatbot
    if "stress" in user_message:
        reply = _("I hear you’re stressed. Try taking deep breaths. Would you like to see relaxation resources?")
    elif "depress" in user_message:
        reply = _("I’m sorry you’re feeling down. You’re not alone — talking helps. Want me to connect you to a counselor resource?")
    else:
        reply = _("I’m here to listen. Can you tell me more about how you’re feeling?")

    # Store the chat conversation in the database
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Storing the username in the email column for consistency
            cursor.execute("INSERT INTO chats (email, user_message, ai_reply) VALUES (%s, %s, %s)",
                           (session["username"], user_message, reply))
            conn.commit()
    except Exception as e:
        print(f"Failed to save chat: {e}")

    return jsonify({"response": reply})

# Mood submission - handles API call from JavaScript
@app.route("/submit_mood", methods=["POST"])
def submit_mood():
    # Ensure the user is logged in
    if "username" not in session:
        return jsonify({"message": _("Please login to submit your mood.")})

    data = request.json
    mood = data.get("mood")
    
    # Store the mood entry in the database
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Storing the username in the email column for consistency
            cursor.execute("INSERT INTO moods (email, mood) VALUES (%s, %s)", (session["username"], mood))
            conn.commit()
    except Exception as e:
        print(f"Failed to save mood: {e}")
        return jsonify({"message": _("An error occurred while saving your mood.")})

    return jsonify({"message": _("Your mood '%(mood)s' has been recorded. Thank you for sharing.", mood=mood)})

# Booking an appointment - handles form submission
@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    # Ensure the user is logged in
    if "username" not in session:
        return redirect(url_for("login"))
    
    try:
        # Get form data
        counselor = request.form["counselor"]
        date = request.form["date"]
        time = request.form["time"]
        
        # Insert booking into the database
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Storing the username in the email column for consistency
            cursor.execute(
                "INSERT INTO bookings (email, counselor, date, time) VALUES (%s, %s, %s, %s)",
                (session["username"], counselor, date, time)
            )
            conn.commit()
            print(f"Appointment booked for {session['username']} with {counselor} on {date} at {time}.")
            # Redirect to home after a successful booking
            return redirect(url_for("home"))
    except Exception as e:
        print(f"Failed to book appointment: {e}")
        return redirect(url_for("home"))

# Logout route - clears the session
@app.route("/logout")
def logout():
    # Remove the username from the session
    session.pop("username", None)
    return redirect(url_for("home"))

# Admin Dashboard Page - requires login (for hackathon)
@app.route("/admin_dashboard")
def admin_dashboard():
    # Basic access control for hackathon - requires login
    if "username" not in session:
        return redirect(url_for("login"))
    
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Mood trends
            cursor.execute("SELECT mood, COUNT(*) FROM moods GROUP BY mood ORDER BY count DESC LIMIT 5")
            mood_trends = cursor.fetchall()

            # Chatbot activity
            cursor.execute("SELECT COUNT(*) FROM chats")
            total_chats = cursor.fetchone()[0]
            
            # Count common keywords
            cursor.execute("SELECT COUNT(*) FROM chats WHERE LOWER(user_message) LIKE %s", ('%stress%',))
            stress_chats = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chats WHERE LOWER(user_message) LIKE %s", ('%depress%',))
            depress_chats = cursor.fetchone()[0]
            
            chat_keywords = {
                'stress': stress_chats,
                'depress': depress_chats
            }

            # Booking activity
            cursor.execute("SELECT COUNT(*) FROM bookings")
            total_bookings = cursor.fetchone()[0]

            cursor.execute("SELECT counselor, COUNT(*) FROM bookings GROUP BY counselor ORDER BY count DESC LIMIT 1")
            most_booked_counselor = cursor.fetchone()
            if most_booked_counselor:
                most_booked_counselor = most_booked_counselor[0]
            else:
                most_booked_counselor = "N/A"

    except Exception as e:
        print(f"Failed to fetch dashboard data: {e}")
        mood_trends = []
        total_chats = 0
        chat_keywords = {}
        total_bookings = 0
        most_booked_counselor = "N/A"

    return render_template(
        "admin_dashboard.html",
        mood_trends=mood_trends,
        total_chats=total_chats,
        chat_keywords=chat_keywords,
        total_bookings=total_bookings,
        most_booked_counselor=most_booked_counselor
    )

# This is the entry point of the application
if __name__ == "__main__":
    app.run(debug=True)
