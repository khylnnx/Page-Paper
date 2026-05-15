from flask import Flask, render_template, request, jsonify, session, send_from_directory 
import json
import os # For file path operations
import sqlite3 # For database operations
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_cors import CORS 

app = Flask(__name__, template_folder='Page & Paper/templates', static_folder='Page & Paper/static')
CORS(app)  # Enable CORS for all routes
# Use a stable secret key for persistent sessions across server restarts
# Users will stay logged in across browser restarts until they explicitly sign out
app.secret_key = 'your-stable-secret-key-change-this-in-production'

# Configure session to be persistent (not expire when browser closes)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 2592000  # 30 days in seconds

# Use absolute paths for JSON files 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database configuration
DATABASE_FILE = os.path.join(BASE_DIR, 'data', 'bookstore.db')

# Books data (still using JSON for now)
BOOKS_FILE = os.path.join(BASE_DIR, 'data', 'books.json')
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

BOOKS_FILE = os.path.join(BASE_DIR, 'data', 'fantasy.json')
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database functions
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_image TEXT,
            address TEXT,
            phone TEXT,
            preferences TEXT,  -- JSON string
            genres TEXT,       -- JSON string
            created_at TEXT NOT NULL
        )
    ''')

    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            payment TEXT NOT NULL,
            image TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create subscribers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            subscribed_at TEXT NOT NULL
        )
    ''')

    # Create questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create messages table for owner messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            sender_name TEXT,
            sender_email TEXT,
            timestamp TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_subscribers():
    conn = get_db_connection()
    subscribers = conn.execute('SELECT email FROM subscribers').fetchall()
    conn.close()
    return [row['email'] for row in subscribers]

def save_subscribers(subscribers):
    conn = get_db_connection()
    conn.execute('DELETE FROM subscribers')  # Clear existing
    for email in subscribers:
        conn.execute('INSERT INTO subscribers (email) VALUES (?)', (email,))
    conn.commit()
    conn.close()

def load_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return [dict(row) for row in users]

def save_users(users):
    conn = get_db_connection()
    conn.execute('DELETE FROM users')  # Clear existing
    for user in users:
        conn.execute('''
            INSERT INTO users (id, name, email, password, preferences, genres, profile_image, address, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['id'], user['name'], user['email'], user['password'],
            json.dumps(user.get('preferences', {})),
            json.dumps(user.get('genres', [])),
            user.get('profile_image'),
            user.get('address'),
            user.get('phone'),
            user.get('created_at')
        ))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    if user:
        user_dict = dict(user)
        user_dict['preferences'] = json.loads(user_dict['preferences']) if user_dict['preferences'] else {}
        user_dict['genres'] = json.loads(user_dict['genres']) if user_dict['genres'] else []
        return user_dict
    return None

def create_user(name, email, password):
    # Check if user already exists
    if get_user_by_email(email):
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user = {
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'preferences': {
            'theme_color': '#EAE2C6',
            'reading_progress': 50,
            'reading_time': '',
            'favorite_url': '',
            'updates': [],
            'romance_rating': 0
        },
        'genres': [],
        'created_at': str(datetime.now())
    }
    
    cursor.execute('''
        INSERT INTO users (name, email, password, preferences, genres, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user['name'], user['email'], user['password'],
        json.dumps(user['preferences']),
        json.dumps(user['genres']),
        user['created_at']
    ))
    
    user['id'] = cursor.lastrowid
    conn.commit()
    conn.close()
    return user

@app.route('/')
def home():
    return render_template('main(Page&Paper).html')

@app.route('/about-us')
def about():
    return render_template('About Us(Page&Paper).html')

@app.route('/owner-founder')
def owner():
    return render_template('Owner_Founder.html')

@app.route('/dashboard')
def dashboard():
    user_data = None
    if 'user_id' in session:
        user = get_user_by_email(session['user_email'])
        if user:
            user_data = {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'preferences': user['preferences'],
                'genres': user['genres']
            }
    return render_template('Dashboard(Page&Paper).html', user=user_data)

@app.route('/romance')
def romance():
    return render_template('romance_book.html')

@app.route('/fantasy')
def fantasy():
    return render_template('fantasy_book.html')

@app.route('/science-fiction')
def science_fiction():
    return render_template('science_fiction_book.html')

@app.route('/mystery')
def mystery():
    return render_template('mystery_book.html')

@app.route('/poetry')
def poetry():
    return render_template('poetry_book.html')

@app.route('/books_iframe')
def books_iframe():
    return render_template('books_iframe.html')

# Serve JSON data files
@app.route('/data/<filename>')
def serve_data_file(filename):
    try:
        data_folder = os.path.join(BASE_DIR, 'data')
        response = send_from_directory(data_folder, filename)
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        return jsonify({'error': f'File not found: {filename}'}), 404

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400
    
    conn = get_db_connection()
    existing = conn.execute('SELECT email FROM subscribers WHERE email = ?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'message': 'Email already subscribed'}), 400
    
    conn.execute('INSERT INTO subscribers (email, subscribed_at) VALUES (?, ?)', 
                (email, str(datetime.now())))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Successfully subscribed!'})

@app.route('/pinterest')
def pinterest():
    return render_template('pinterest_bookstore.html')

@app.route('/contact-submit', methods=['POST'])
def contact_submit():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({'message': 'Question is required'}), 400

    conn = get_db_connection()
    # Require authentication for submitting questions
    if 'user_id' not in session:
        conn.close()
        return jsonify({'message': 'Authentication required to submit a question'}), 401

    user_id = session['user_id']
    conn.execute('INSERT INTO questions (question, user_id, timestamp) VALUES (?, ?, ?)',
                 (question, user_id, str(datetime.now())))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Question submitted successfully!'})

@app.route('/submit-message', methods=['POST'])
def submit_message():
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'message': 'Message is required'}), 400

    # Require authentication for sending owner messages
    if 'user_id' not in session:
        return jsonify({'message': 'Authentication required to send a message'}), 401

    conn = get_db_connection()
    # Fetch user info to populate sender fields
    user = conn.execute('SELECT name, email FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    sender_name = user['name'] if user and user['name'] else None
    sender_email = user['email'] if user and user['email'] else None

    conn.execute('INSERT INTO messages (message, sender_name, sender_email, timestamp) VALUES (?, ?, ?, ?)',
                (message, sender_name, sender_email, str(datetime.now())))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Message sent successfully!'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'error': 'Name, email, and password are required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    user = create_user(name, email, password)
    if not user:
        return jsonify({'error': 'User already exists'}), 400
    
    session['user_id'] = user['id']
    session['user_email'] = user['email']
    return jsonify({
        'message': 'Registration successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'profile_image': user.get('profile_image'),
            'address': user.get('address'),
            'phone': user.get('phone')
        }
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'No account found with this email address. Please register first.'}), 401
    
    if not check_password_hash(user['password'], password):
        return jsonify({'error': 'Incorrect password. Please try again.'}), 401
    
    session['user_id'] = user['id']
    session['user_email'] = user['email']
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'profile_image': user.get('profile_image'),
            'address': user.get('address'),
            'phone': user.get('phone')
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = get_user_by_email(session['user_email'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'profile_image': user.get('profile_image'),
        'address': user.get('address'),
        'phone': user.get('phone'),
        'preferences': user['preferences'],
        'genres': user['genres']
    })

@app.route('/api/preferences', methods=['POST'])
def save_preferences():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    conn = get_db_connection()
    
    # Get current user preferences
    user = conn.execute('SELECT preferences FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    current_prefs = json.loads(user['preferences']) if user['preferences'] else {}
    current_prefs.update(data)
    
    conn.execute('UPDATE users SET preferences = ? WHERE id = ?', 
                (json.dumps(current_prefs), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Preferences saved successfully'})

@app.route('/api/genres', methods=['POST'])
def save_genres():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    genres = data.get('genres', [])
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET genres = ? WHERE id = ?', 
                (json.dumps(genres), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Genres saved successfully'})

@app.route('/api/user/update', methods=['POST'])
def update_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    user_dict = dict(user)
    user_dict['preferences'] = json.loads(user_dict['preferences']) if user_dict['preferences'] else {}
    user_dict['genres'] = json.loads(user_dict['genres']) if user_dict['genres'] else []
    
    # Handle profile image upload
    if 'profile_image' in request.files:
        file = request.files['profile_image']
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            user_dict['profile_image'] = f"/data/uploads/{filename}"
    
    # Handle form data (JSON)
    if request.is_json:
        data = request.get_json()
        # Update allowed fields
        allowed_fields = ['name', 'address', 'phone']
        for field in allowed_fields:
            if field in data:
                user_dict[field] = data[field]
    
    # Handle form data (form-encoded)
    else:
        allowed_fields = ['name', 'address', 'phone']
        for field in allowed_fields:
            if field in request.form:
                user_dict[field] = request.form[field]
    
    # Update database
    conn.execute('''
        UPDATE users SET name = ?, address = ?, phone = ?, profile_image = ? WHERE id = ?
    ''', (
        user_dict['name'], user_dict['address'], user_dict['phone'], 
        user_dict.get('profile_image'), session['user_id']
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/books')
def get_books():
    sort = request.args.get('sort', 'title')
    availability = request.args.get('availability', 'all')
    genre = request.args.get('genre', 'Romance')
    
    # Map genre to JSON filename
    genre_file_map = {
        'fantasy': 'fantasy.json',
        'science_fiction': 'science_fiction.json',
        'science-fiction': 'science_fiction.json',
        'mystery': 'mystery.json',
        'poetry': 'poetry.json',
        'romance': 'books.json'
    }
    
    # Get the filename for the genre
    filename = genre_file_map.get(genre.lower(), 'books.json')
    books_file = os.path.join(BASE_DIR, 'data', filename)
    
    # Load books from appropriate JSON file
    if os.path.exists(books_file):
        with open(books_file, 'r') as f:
            all_books = json.load(f)
    else:
        return jsonify({'error': 'Books data not found'}), 404
    
    # Capitalize genre for matching (Romance, Fantasy, Science Fiction, Mystery, Poetry)
    genre_map = {
        'fantasy': 'Fantasy',
        'science_fiction': 'Science Fiction',
        'science-fiction': 'Science Fiction',
        'mystery': 'Mystery',
        'poetry': 'Poetry',
        'romance': 'Romance'
    }
    genre_name = genre_map.get(genre.lower(), genre)
    books = [book for book in all_books if book.get('category') == genre_name]
    
    # Apply availability filter
    if availability == 'in-stock':
        books = [book for book in books if book.get('stock', 0) > 0]
    elif availability == 'out-of-stock':
        books = [book for book in books if book.get('stock', 0) == 0]
    
    # Apply sorting
    if sort == 'title':
        books.sort(key=lambda x: x.get('title', '').lower())
    elif sort == 'author':
        books.sort(key=lambda x: x.get('author', '').lower())
    elif sort == 'price-low':
        books.sort(key=lambda x: x.get('price', 0))
    elif sort == 'price-high':
        books.sort(key=lambda x: x.get('price', 0), reverse=True)
    
    return jsonify(books)

@app.route('/api/order', methods=['POST'])
def place_order():
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to place an order. Please sign in to your dashboard first.'}), 401
    
    # Check if user has completed their account settings
    user = get_user_by_email(session['user_email'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check required account fields
    required_fields = ['name', 'address', 'phone']
    missing_fields = []
    for field in required_fields:
        if not user.get(field) or user.get(field).strip() == '':
            missing_fields.append(field.title())
    
    if missing_fields:
        return jsonify({
            'error': f'Please complete your account settings before placing an order. Missing: {", ".join(missing_fields)}. Go to your dashboard and fill out your profile information.'
        }), 400
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['title', 'author', 'price', 'quantity', 'payment', 'genre']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Map genre to JSON filename
    genre_file_map = {
        'fantasy': 'fantasy.json',
        'science_fiction': 'science_fiction.json',
        'science-fiction': 'science_fiction.json',
        'mystery': 'mystery.json',
        'poetry': 'poetry.json',
        'romance': 'books.json'
    }
    
    # Get the filename for the genre
    filename = genre_file_map.get(data['genre'].lower(), 'books.json')
    books_file = os.path.join(BASE_DIR, 'data', filename)
    
    # Load books from JSON file and check/update stock
    try:
        with open(books_file, 'r') as f:
            all_books = json.load(f)
        
        # Find the book by title and author
        book_found = False
        available_stock = 0
        for book in all_books:
            if book.get('title').lower() == data['title'].lower() and book.get('author').lower() == data['author'].lower():
                available_stock = book.get('stock', 0)
                book_found = True
                break
        
        if not book_found:
            return jsonify({'error': 'Book not found'}), 404
        
        if data['quantity'] > available_stock:
            return jsonify({'error': f'Insufficient stock. Only {available_stock} copies available.'}), 400
        
        # Reduce stock
        for book in all_books:
            if book.get('title').lower() == data['title'].lower() and book.get('author').lower() == data['author'].lower():
                book['stock'] = max(0, book.get('stock', 0) - data['quantity'])
                break
        
        # Save updated books back to JSON file
        with open(books_file, 'w') as f:
            json.dump(all_books, f, indent=2)
        
    except Exception as e:
        print(f'Error updating stock: {str(e)}')
        return jsonify({'error': 'Failed to update inventory'}), 500
    
    conn = get_db_connection()
    
    # Insert order into database
    conn.execute('''
        INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        None, session['user_id'], session['user_email'], data['title'], data['author'],
        data['price'], data['quantity'], data['payment'], data.get('image'), str(datetime.now())
    ))
    
    order_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()
    
    return jsonify({'order_id': order_id, 'message': 'Order placed successfully!'})

@app.route('/api/orders')
def get_orders():
    # Debug: print session to help diagnose missing orders in purchases modal
    try:
        print('DEBUG /api/orders - session keys:', dict(session))
    except Exception:
        print('DEBUG /api/orders - session unavailable')

    if 'user_id' not in session:
        print('DEBUG /api/orders - unauthenticated request')
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY timestamp DESC', 
                         (session['user_id'],)).fetchall()
    orders_list = [dict(row) for row in orders]
    print(f"DEBUG /api/orders - returning {len(orders_list)} orders for user_id={session.get('user_id')}")
    conn.close()
    return jsonify(orders_list)

@app.route('/data/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve Romance PDF with a safe URL (handles spaces in filename)
@app.route('/pdfs/romance')
def serve_romance_pdf():
    # Serve the PDF inline from the app static folder
    try:
        response = send_from_directory(app.static_folder, 'Romance Book.pdf')
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename="Romance Book Overview.pdf"'
        return response
    except Exception:
        return jsonify({'error': 'PDF not found'}), 404

# Serve Fantasy PDF
@app.route('/pdfs/fantasy')
def serve_fantasy_pdf():
    try:
        response = send_from_directory(app.static_folder, 'Fantasy Book.pdf')
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename="Fantasy Book Overview.pdf"'
        return response
    except Exception:
        return jsonify({'error': 'PDF not found'}), 404

# Serve Science Fiction PDF
@app.route('/pdfs/science-fiction')
def serve_science_fiction_pdf():
    try:
        response = send_from_directory(app.static_folder, 'Science Fiction Book.pdf')
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename="Science Fiction Book Overview.pdf"'
        return response
    except Exception:
        return jsonify({'error': 'PDF not found'}), 404

# Serve Mystery PDF
@app.route('/pdfs/mystery')
def serve_mystery_pdf():
    try:
        response = send_from_directory(app.static_folder, 'Mystery Book.pdf')
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename="Mystery Book Overview.pdf"'
        return response
    except Exception:
        return jsonify({'error': 'PDF not found'}), 404

# Serve Poetry PDF
@app.route('/pdfs/poetry')
def serve_poetry_pdf():
    try:
        response = send_from_directory(app.static_folder, 'Poetry Book.pdf')
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename="Poetry Book Overview.pdf"'
        return response
    except Exception:
        return jsonify({'error': 'PDF not found'}), 404


# Public reviews endpoint (returns questions as reviews)
@app.route('/reviews')
def get_reviews():
    conn = get_db_connection()
    rows = conn.execute('SELECT id, question, timestamp FROM questions ORDER BY timestamp DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/admin')
def admin():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    subscribers = conn.execute('SELECT * FROM subscribers').fetchall()
    questions = conn.execute('SELECT * FROM questions').fetchall()
    messages = conn.execute('SELECT * FROM messages').fetchall()
    conn.close()
    
    # Create email to user_id mapping
    email_to_id = {user['email']: user['id'] for user in users}
    user_id_to_info = {user['id']: {'name': user['name'], 'email': user['email']} for user in users}
    
    # Add user_id to subscribers
    subscribers_list = []
    for sub in subscribers:
        sub_dict = dict(sub)
        sub_dict['user_id'] = email_to_id.get(sub['email'], 'N/A')
        subscribers_list.append(sub_dict)
    
    # Process questions like subscribers - show question ID and user info
    questions_list = []
    for q in questions:
        q_dict = dict(q)
        user_info = user_id_to_info.get(q_dict['user_id'])
        if user_info:
            q_dict['user_name'] = user_info['name']
            q_dict['user_email'] = user_info['email']
        else:
            q_dict['user_name'] = 'Unknown'
            q_dict['user_email'] = 'N/A'
        questions_list.append(q_dict)
    
    return render_template('admin.html', 
                         users=[dict(row) for row in users],
                         orders=[dict(row) for row in orders],
                         subscribers=subscribers_list,
                         questions=questions_list,
                         messages=[dict(row) for row in messages])

if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
