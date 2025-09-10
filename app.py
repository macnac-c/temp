import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import bcrypt

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- PostgreSQL Connection Configuration ---
# Example format: "dbname=mental_health_db user=your_user password=your_password host=localhost"
# For a Homebrew installation on Mac, 'user' is typically your macOS username.
DATABASE_URL = os.environ.get('DATABASE_URL', 'dbname=mental_health_db user=mahimachauhan password=')

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- Database Schema Setup (Run these SQL commands in your psql terminal) ---
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
#     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
# );

# ----------------- Routes -----------------

# Home Page (works for logged-in and guest users)
@app.route("/")
def home():
    user_email = session.get("email")
    return render_template("index.html", user=user_email)

# Chatbot Page
@app.route("/chatbot")
def chatbot():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("chatbot.html")

# Mood Tracker Page
@app.route("/mood")
def mood():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("mood.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"].encode("utf-8")
        
        print(f"Attempting login for email: {email}")
        
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
                user_record = cursor.fetchone()
                
                if user_record:
                    print(f"User found.")
                    if bcrypt.checkpw(password, bytes(user_record[0])):
                        print("Password check successful. Redirecting to home page.")
                        session["email"] = email
                        return redirect(url_for("home"))
                    else:
                        print("Password check failed.")
                else:
                    print("User not found in database.")
                
                return render_template("login.html", message="Invalid email or password.")
        except Exception as e:
            print(f"Database error during login: {e}")
            return render_template("login.html", message="An error occurred. Please try again.")

    return render_template("login.html")

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"].encode("utf-8")
        confirm = request.form["confirm"].encode("utf-8")

        if password != confirm:
            return render_template("register.html", message="Passwords do not match!")
        
        try:
            with get_db_connection() as conn, conn.cursor() as cursor:
                # Check for existing user
                cursor.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    return render_template("register.html", message="Email or username already exists. Please try another one.")
                
                # Hash password and insert new user
                hashed = bcrypt.hashpw(password, bcrypt.gensalt())
                cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed))
                conn.commit()
                print("Registration successful. Redirecting to login page.")
                
                return redirect(url_for("login"))
        except Exception as e:
            print(f"Database error during registration: {e}")
            return render_template("register.html", message="An error occurred. Please try again.")
            
    return render_template("register.html")

# Chatbot response
@app.route("/get_response", methods=["POST"])
def get_response():
    if "email" not in session:
        return jsonify({"response": "Please login to chat with Moody."})

    data = request.json
    user_message = data.get("message", "").lower()
    reply = ""

    if "stress" in user_message:
        reply = "I hear you’re stressed. Try taking deep breaths. Would you like to see relaxation resources?"
    elif "depress" in user_message:
        reply = "I’m sorry you’re feeling down. You’re not alone — talking helps. Want me to connect you to a counselor resource?"
    else:
        reply = "I’m here to listen. Can you tell me more about how you’re feeling?"

    # Store chat in DB
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO chats (email, user_message, ai_reply) VALUES (%s, %s, %s)",
                           (session["email"], user_message, reply))
            conn.commit()
    except Exception as e:
        print(f"Failed to save chat: {e}")

    return jsonify({"response": reply})

# Mood submission
@app.route("/submit_mood", methods=["POST"])
def submit_mood():
    if "email" not in session:
        return jsonify({"message": "Please login to submit your mood."})

    data = request.json
    mood = data.get("mood")
    
    try:
        with get_db_connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO moods (email, mood) VALUES (%s, %s)", (session["email"], mood))
            conn.commit()
    except Exception as e:
        print(f"Failed to save mood: {e}")
        return jsonify({"message": "An error occurred while saving your mood."})

    return jsonify({"message": f"Your mood '{mood}' has been recorded. Thank you for sharing."})

# Logout
@app.route("/logout")
def logout():
    session.pop("email", None)
    return redirect(url_for("home"))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
