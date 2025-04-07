
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret123'

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'hotel.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT,
                        age INTEGER,
                        is_admin INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS hotels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        location TEXT,
                        image_path TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hotel_id INTEGER,
                        room_type TEXT,
                        is_booked INTEGER DEFAULT 0,
                        FOREIGN KEY (hotel_id) REFERENCES hotels(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        room_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (room_id) REFERENCES rooms(id))''')
        c.execute("SELECT * FROM users WHERE username = ?", ('admin',))
        if not c.fetchone():
            c.execute("""INSERT INTO users (username, email, password, age, is_admin)
                         VALUES (?, ?, ?, ?, ?)""",
                      ('admin', 'admin@example.com', 'admin123', 30, 1))
            conn.commit()
            print("Admin user created: username='admin', password='admin123'")
        conn.commit()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pwd))
            user = c.fetchone()
            if user:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['is_admin'] = bool(user[5])
                if session['is_admin']:
                    return redirect('/admin')
                return redirect('/dashboard')
            else:
                flash("Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        email = request.form['email']
        pwd = request.form['password']
        age = int(request.form['age'])
        if age < 18:
            flash("Age must be at least 18")
            return redirect('/register')
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, email, password, age) VALUES (?, ?, ?, ?)",
                          (uname, email, pwd, age))
                conn.commit()
                return redirect('/login')
        except sqlite3.IntegrityError:
            flash("Username already exists")
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM hotels")
        hotels = [dict(id=row[0], name=row[1], location=row[2], image_path=row[3]) for row in c.fetchall()]
    return render_template('user_dashboard.html', hotels=hotels)

@app.route('/hotel/<int:hotel_id>', methods=['GET'])
def hotel_detail(hotel_id):
    if 'user_id' not in session:
        return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,))
        hotel = c.fetchone()
        c.execute("SELECT * FROM rooms WHERE hotel_id=?", (hotel_id,))
        rooms = [dict(id=row[0], room_type=row[2], is_booked=row[3]) for row in c.fetchall()]
    return render_template('hotel_detail.html', hotel={'id': hotel[0], 'name': hotel[1], 'location': hotel[2]}, rooms=rooms)

@app.route('/book/<int:room_id>', methods=['POST'])
def book_room(room_id):
    if 'user_id' not in session:
        return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT is_booked FROM rooms WHERE id=?", (room_id,))
        status = c.fetchone()
        if status and status[0] == 0:
            c.execute("UPDATE rooms SET is_booked=1 WHERE id=?", (room_id,))
            c.execute("INSERT INTO bookings (user_id, room_id) VALUES (?, ?)", (session['user_id'], room_id))
            conn.commit()
    return redirect('/dashboard')

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM hotels")
        hotels = [dict(id=row[0], name=row[1], location=row[2], image_path=row[3]) for row in c.fetchall()]
    return render_template('admin_dashboard.html', hotels=hotels)

@app.route('/add_hotel', methods=['GET', 'POST'])
def add_hotel():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        image_path = request.form['image_path']
        rooms = int(request.form['rooms'])
        room_type = request.form['room_type']
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO hotels (name, location, image_path) VALUES (?, ?, ?)", (name, location, image_path))
            hotel_id = c.lastrowid
            for _ in range(rooms):
                c.execute("INSERT INTO rooms (hotel_id, room_type) VALUES (?, ?)", (hotel_id, room_type))
            conn.commit()
        return redirect('/admin')
    return render_template('add_hotel.html')

@app.route('/delete_hotel/<int:hotel_id>', methods=['POST'])
def delete_hotel(hotel_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM bookings WHERE room_id IN (SELECT id FROM rooms WHERE hotel_id=?)", (hotel_id,))
        c.execute("DELETE FROM rooms WHERE hotel_id=?", (hotel_id,))
        c.execute("DELETE FROM hotels WHERE id=?", (hotel_id,))
        conn.commit()
    return redirect('/admin')

if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)
    init_db()
    app.run(debug=True)
