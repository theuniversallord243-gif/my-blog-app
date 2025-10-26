from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, make_response
import json
import os
import secrets
import re
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import uuid
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = True  # Always use secure cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['UPLOAD_FOLDER'] = os.path.abspath('static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024




ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Prevent HTML caching for debugging
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Database setup
DB_FILE = 'blog_app.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT,
                channel TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bio TEXT DEFAULT '',
                profile_pic TEXT DEFAULT '',
                followers_count INTEGER DEFAULT 0,
                following_count INTEGER DEFAULT 0,
                posts_count INTEGER DEFAULT 0,
                security_question TEXT DEFAULT '',
                security_answer TEXT DEFAULT ''
            )
        ''')
        
        # Create blogs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_username TEXT NOT NULL,
                channel TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                images TEXT DEFAULT "[]"
            )
        ''')
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_username TEXT NOT NULL,
                receiver_username TEXT NOT NULL,
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (sender_username) REFERENCES users(username),
                FOREIGN KEY (receiver_username) REFERENCES users(username)
            )
        ''')
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_username TEXT NOT NULL,
                user2_username TEXT NOT NULL,
                last_message_id INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1_username, user2_username),
                FOREIGN KEY (user1_username) REFERENCES users(username),
                FOREIGN KEY (user2_username) REFERENCES users(username),
                FOREIGN KEY (last_message_id) REFERENCES messages(id)
            )
        ''')
        
        # Create password reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # Create comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blog_id) REFERENCES blogs(id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        # Create follows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_username TEXT NOT NULL,
                following_username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_username, following_username),
                FOREIGN KEY (follower_username) REFERENCES users(username),
                FOREIGN KEY (following_username) REFERENCES users(username)
            )
        ''')
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_username TEXT NOT NULL,
                from_username TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                blog_id INTEGER,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_username) REFERENCES users(username),
                FOREIGN KEY (from_username) REFERENCES users(username),
                FOREIGN KEY (blog_id) REFERENCES blogs(id)
            )
        ''')
        
        # Create likes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blog_id, username),
                FOREIGN KEY (blog_id) REFERENCES blogs(id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        
        conn.commit()

init_db()

# Security validation functions
def validate_password(password):
    """Password validation - simplified for better user experience"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    # Count different character types
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    # Require at least 3 out of 4 character types
    char_types = sum([has_upper, has_lower, has_digit, has_special])
    if char_types < 3:
        return False, "Password must contain at least 3 of: uppercase, lowercase, number, special character"
    
    return True, "Valid password"

def validate_email(email):
    """Email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text):
    """Basic input sanitization - remove HTML tags only"""
    if not text:
        return ""
    text = str(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    return text.strip()

# Helper functions
def get_user_security_question(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT security_question FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Error getting security question: {e}")
        return None

def get_user_by_username(username):
    try:
        # First check SQLite database
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_username: {e}")
        return None
    
    if result:
        columns = ['id', 'username', 'email', 'password_hash', 'channel', 'created_at', 
                  'bio', 'profile_pic', 'followers_count', 'following_count', 'posts_count', 'security_question', 'security_answer']
        return dict(zip(columns, result))
    
    # If not found in SQLite, check JSON file for backward compatibility
    json_file = 'users.json'
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                users = json.load(f)
            if username in users:
                user_data = users[username]
                return {
                    'id': None,
                    'username': username,
                    'email': user_data.get('email', ''),
                    'password_hash': user_data.get('password'),
                    'channel': user_data.get('channel', 'general'),
                    'created_at': user_data.get('created_at')
                }
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    
    return None

def create_user(username, email, password_hash, channel, security_question, security_answer):
    try:
        print(f"Creating user - Username: '{username}', Email: '{email}', Channel: '{channel}'")
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, channel, security_question, security_answer)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, channel, security_question, security_answer))
            conn.commit()
            print(f"User '{username}' created successfully in database")
            return True
    except sqlite3.IntegrityError as e:
        print(f"User creation failed - duplicate username: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Database error in create_user: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in create_user: {e}")
        return False

def get_blogs():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blogs ORDER BY created_at DESC')
            results = cursor.fetchall()
        
        blogs = []
        for row in results:
            try:
                # Parse images
                images = []
                if row[6]:
                    try:
                        images = json.loads(row[6])
                    except (json.JSONDecodeError, TypeError):
                        images = []
                
                # Get likes count
                likes_count = get_likes_count(row[0])
                
                blog = {
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'author': row[3],
                    'channel': row[4],
                    'date': row[5],
                    'images': images,
                    'likes': likes_count
                }
                blogs.append(blog)
            except Exception as e:
                print(f"Error processing blog row: {e}")
                continue
        return blogs
    except sqlite3.Error as e:
        print(f"Database error in get_blogs: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_blogs: {e}")
        return []

def create_blog_db(title, content, author, channel):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Sanitize inputs
            title = sanitize_input(title)[:200]
            content = sanitize_input(content)[:10000]
            author = sanitize_input(author)[:50]
            channel = sanitize_input(channel)[:50]
            
            cursor.execute('''
                INSERT INTO blogs (title, content, author_username, channel)
                VALUES (?, ?, ?, ?)
            ''', (title, content, author, channel))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error in create_blog_db: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in create_blog_db: {e}")
        return False

def create_blog_with_images(title, content, author, channel, image_urls):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Sanitize inputs
            title = sanitize_input(title)[:200]
            content = sanitize_input(content)[:10000]
            author = sanitize_input(author)[:50]
            channel = sanitize_input(channel)[:50]
            
            # Convert image URLs to JSON
            images_json = json.dumps(image_urls)
            
            cursor.execute('''
                INSERT INTO blogs (title, content, author_username, channel, images)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, content, author, channel, images_json))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error in create_blog_with_images: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in create_blog_with_images: {e}")
        return False



# Messaging helper functions
def send_message(sender_username, receiver_username, message_text):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Sanitize inputs
            message_text = sanitize_input(message_text)[:1000]
            
            # Insert message
            cursor.execute('''
                INSERT INTO messages (sender_username, receiver_username, message_text)
                VALUES (?, ?, ?)
            ''', (sender_username, receiver_username, message_text))
            
            message_id = cursor.lastrowid
            
            # Update or create conversation
            cursor.execute('''
                INSERT OR REPLACE INTO conversations (user1_username, user2_username, last_message_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (min(sender_username, receiver_username), max(sender_username, receiver_username), message_id))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_conversations(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, m.message_text, m.created_at, m.sender_username,
                       CASE WHEN c.user1_username = ? THEN c.user2_username ELSE c.user1_username END as other_user
                FROM conversations c
                LEFT JOIN messages m ON c.last_message_id = m.id
                WHERE c.user1_username = ? OR c.user2_username = ?
                ORDER BY c.updated_at DESC
            ''', (username, username, username))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []

def get_messages(user1, user2, limit=50):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM messages 
                WHERE (sender_username = ? AND receiver_username = ?) 
                   OR (sender_username = ? AND receiver_username = ?)
                ORDER BY created_at DESC LIMIT ?
            ''', (user1, user2, user2, user1, limit))
            return cursor.fetchall()[::-1]
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

# Password reset helper functions
def generate_reset_token(username):
    """Generate secure password reset token"""
    try:
        # Create token with username and current timestamp
        token_data = {'username': username, 'timestamp': time.time()}
        token = serializer.dumps(token_data, salt='password-reset')
        
        # Store token hash in database
        token_hash = generate_password_hash(token)
        expires_at = datetime.now() + timedelta(minutes=30)  # 30 minute expiry
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Invalidate old tokens for this user
            cursor.execute('UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE username = ? AND used_at IS NULL', (username,))
            # Insert new token
            cursor.execute('''
                INSERT INTO password_reset_tokens (username, token_hash, expires_at)
                VALUES (?, ?, ?)
            ''', (username, token_hash, expires_at))
            conn.commit()
        
        return token
    except Exception as e:
        print(f"Error generating reset token: {e}")
        return None

def verify_reset_token(token, max_age=1800):  # 30 minutes
    """Verify password reset token"""
    try:
        # Decode token
        token_data = serializer.loads(token, salt='password-reset', max_age=max_age)
        username = token_data['username']
        
        # Check if token exists and is unused
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM password_reset_tokens 
                WHERE username = ? AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            ''', (username,))
            
            if cursor.fetchone():
                return username
        return None
    except Exception as e:
        print(f"Error verifying reset token: {e}")
        return None

def consume_reset_token(token):
    """Mark token as used"""
    try:
        username = verify_reset_token(token)
        if username:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE password_reset_tokens 
                    SET used_at = CURRENT_TIMESTAMP 
                    WHERE username = ? AND used_at IS NULL
                ''', (username,))
                conn.commit()
        return username
    except Exception as e:
        print(f"Error consuming reset token: {e}")
        return None

def send_reset_email(email, username, token):
    """Send password reset email"""
    try:
        reset_url = url_for('reset_password', token=token, _external=True)
        
        # Print for development
        print(f"\n=== PASSWORD RESET EMAIL ===")
        print(f"To: {email}")
        print(f"Username: {username}")
        print(f"Reset URL: {reset_url}")
        print(f"================================\n")
        
        # Try to send actual email if configured
        try:
            if app.config.get('MAIL_USERNAME'):
                msg = Message(
                    subject='Password Reset Request - Blog App',
                    recipients=[email],
                    html=f'''
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #333;">Password Reset Request</h2>
                        <p>Hello {username},</p>
                        <p>You requested a password reset for your Blog App account. Click the link below to reset your password:</p>
                        <p style="margin: 20px 0;">
                            <a href="{reset_url}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset Password</a>
                        </p>
                        <p><strong>This link will expire in 30 minutes.</strong></p>
                        <p>If you didn't request this reset, please ignore this email. Your password will remain unchanged.</p>
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                        <p style="color: #666; font-size: 12px;">Blog App Security Team</p>
                    </div>
                    '''
                )
                mail.send(msg)
                print("Email sent successfully!")
        except Exception as mail_error:
            print(f"Email sending failed: {mail_error}")
            # Still return True since we showed the reset URL in console
        
        return True
    except Exception as e:
        print(f"Error sending reset email: {e}")
        return False

# Comment helper functions
def add_comment(blog_id, username, comment_text):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO comments (blog_id, username, comment_text)
                VALUES (?, ?, ?)
            ''', (blog_id, username, sanitize_input(comment_text)[:500]))
            
            # Get blog author to send notification
            cursor.execute('SELECT author_username, title FROM blogs WHERE id = ?', (blog_id,))
            blog_result = cursor.fetchone()
            
            if blog_result and blog_result[0] != username:
                blog_author = blog_result[0]
                blog_title = blog_result[1]
                create_notification(
                    blog_author, 
                    username, 
                    'comment', 
                    f'{username} commented on your blog "{blog_title[:30]}..."',
                    blog_id
                )
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error adding comment: {e}")
        return False

def get_comments(blog_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, comment_text, created_at
                FROM comments
                WHERE blog_id = ?
                ORDER BY created_at ASC
            ''', (blog_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting comments: {e}")
        return []

# Follow system functions
def follow_user(follower, following):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO follows (follower_username, following_username)
                VALUES (?, ?)
            ''', (follower, following))
            conn.commit()
            # Create notification
            create_notification(following, follower, 'follow', f'{follower} started following you')
            return True
    except Exception as e:
        print(f"Error following user: {e}")
        return False

def unfollow_user(follower, following):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM follows 
                WHERE follower_username = ? AND following_username = ?
            ''', (follower, following))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error unfollowing user: {e}")
        return False

def is_following(follower, following):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM follows 
                WHERE follower_username = ? AND following_username = ?
            ''', (follower, following))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error checking follow status: {e}")
        return False

def get_followers_count(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM follows WHERE following_username = ?', (username,))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting followers count: {e}")
        return 0

def get_following_count(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM follows WHERE follower_username = ?', (username,))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting following count: {e}")
        return 0

# Notification system functions
def create_notification(user_username, from_username, type, message, blog_id=None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_username, from_username, type, message, blog_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_username, from_username, type, message, blog_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False

def get_notifications(username, limit=20):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, from_username, type, message, blog_id, is_read, created_at
                FROM notifications
                WHERE user_username = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (username, limit))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return []

def get_unread_notifications_count(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM notifications 
                WHERE user_username = ? AND is_read = FALSE
            ''', (username,))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting unread notifications count: {e}")
        return 0

def mark_notifications_read(username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE notifications SET is_read = TRUE 
                WHERE user_username = ? AND is_read = FALSE
            ''', (username,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error marking notifications as read: {e}")
        return False

# Like system functions
def like_blog(blog_id, username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO likes (blog_id, username)
                VALUES (?, ?)
            ''', (blog_id, username))
            
            # Get blog author to send notification
            cursor.execute('SELECT author_username, title FROM blogs WHERE id = ?', (blog_id,))
            blog_result = cursor.fetchone()
            
            if blog_result and blog_result[0] != username:
                blog_author = blog_result[0]
                blog_title = blog_result[1]
                create_notification(
                    blog_author, 
                    username, 
                    'like', 
                    f'{username} liked your blog "{blog_title[:30]}..."',
                    blog_id
                )
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error liking blog: {e}")
        return False

def unlike_blog(blog_id, username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM likes 
                WHERE blog_id = ? AND username = ?
            ''', (blog_id, username))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error unliking blog: {e}")
        return False

def is_liked_by_user(blog_id, username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM likes 
                WHERE blog_id = ? AND username = ?
            ''', (blog_id, username))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error checking like status: {e}")
        return False

def get_likes_count(blog_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM likes WHERE blog_id = ?', (blog_id,))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting likes count: {e}")
        return 0

# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    blogs = get_blogs()
    
    if search_query:
        # Search across all blogs regardless of channel
        filtered_blogs = []
        query_lower = search_query.lower()
        for blog in blogs:
            if (query_lower in blog['title'].lower() or 
                query_lower in blog['content'].lower() or 
                query_lower in blog['author'].lower()):
                filtered_blogs.append(blog)
        blogs = filtered_blogs
    # Show all blogs to everyone (logged in or not)
    
    return render_template('index.html', blogs=blogs, search_query=search_query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username:
                flash('Username is required!', 'error')
                return render_template('login_modern.html')
            
            if not password:
                flash('Password is required!', 'error')
                return render_template('login_modern.html')
            
            user = get_user_by_username(username)
            
            if user and user.get('password_hash'):
                if check_password_hash(user['password_hash'], password):
                    session['username'] = username
                    session['channel'] = user.get('channel', 'general')
                    session.permanent = True
                    flash('Login successful!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Incorrect password!', 'error')
            else:
                flash('Username not found!', 'error')
        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('login_modern.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            channel = request.form.get('channel', '').strip()
            security_question = request.form.get('security_question', '').strip()
            security_answer = request.form.get('security_answer', '').strip()
            
            print(f"Registration attempt - Username: '{username}', Email: '{email}', Channel: '{channel}', Password length: {len(password)}")
            
            # Simple validation
            if not username or len(username) < 2:
                print(f"Username validation failed: '{username}', length: {len(username) if username else 0}")
                flash('Username must be at least 2 characters', 'error')
                return render_template('register_modern.html')
            
            if not email or '@' not in email:
                print(f"Email validation failed: '{email}'")
                flash('Valid email is required', 'error')
                return render_template('register_modern.html')
            
            if not password or len(password) < 4:
                print(f"Password validation failed: length {len(password) if password else 0}")
                flash('Password must be at least 4 characters', 'error')
                return render_template('register_modern.html')
            
            if not channel:
                channel = 'general'  # Default channel if not provided
                print(f"Channel set to default: '{channel}'")
            
            if not security_question:
                print(f"Security question validation failed")
                flash('Security question is required', 'error')
                return render_template('register_modern.html')
            
            if not security_answer or len(security_answer) < 2:
                print(f"Security answer validation failed")
                flash('Security answer must be at least 2 characters', 'error')
                return render_template('register_modern.html')
            
            # Check if user exists
            existing_user = get_user_by_username(username)
            if existing_user:
                print(f"User already exists: {username}")
                flash('Username already exists', 'error')
                return render_template('register_modern.html')
            
            print(f"All validations passed, creating user...")
            
            # Create user
            password_hash = generate_password_hash(password)
            print(f"Password hash generated: {password_hash[:20]}...")
            
            success = create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                channel=channel,
                security_question=security_question,
                security_answer=security_answer.lower()  # Store in lowercase for case-insensitive comparison
            )
            
            if success:
                print(f"User created successfully: {username}")
                session['username'] = username
                session['channel'] = channel
                session.permanent = True
                flash('Registration successful!', 'success')
                return redirect(url_for('index'))
            else:
                print(f"Failed to create user: {username}")
                flash('Registration failed. Username might already exist or database error.', 'error')
                
        except Exception as e:
            print(f"Registration error: {e}")
            import traceback
            traceback.print_exc()
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('register_modern.html')

@app.route('/blog/<int:blog_id>', methods=['GET', 'POST'])
def view_blog(blog_id):
    # Handle comment submission
    if request.method == 'POST' and 'username' in session:
        comment_text = request.form.get('comment', '').strip()
        if comment_text and len(comment_text) >= 3:
            if add_comment(blog_id, session['username'], comment_text):
                flash('Comment added successfully!', 'success')
            else:
                flash('Failed to add comment!', 'error')
        else:
            flash('Comment must be at least 3 characters!', 'error')
        return redirect(url_for('view_blog', blog_id=blog_id))
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blogs WHERE id = ?', (blog_id,))
            result = cursor.fetchone()
        
        if not result:
            flash('Blog not found!', 'error')
            return redirect(url_for('index'))
    except sqlite3.Error as e:
        print(f"Database error in view_blog: {e}")
        flash('Error loading blog', 'error')
        return redirect(url_for('index'))
    
    # Parse images
    images = []
    if result[6]:
        try:
            images = json.loads(result[6])
        except (json.JSONDecodeError, TypeError):
            images = []
    
    blog = {
        'id': result[0],
        'title': result[1],
        'content': result[2],
        'author': result[3],
        'channel': result[4],
        'date': result[5],
        'images': images
    }
    
    # Get comments and likes
    comments = get_comments(blog_id)
    likes_count = get_likes_count(blog_id)
    is_liked = False
    if 'username' in session:
        is_liked = is_liked_by_user(blog_id, session['username'])
    
    return render_template('blog_detail.html', blog=blog, comments=comments, likes_count=likes_count, is_liked=is_liked)

@app.route('/create', methods=['GET', 'POST'])
def create_blog():
    if 'username' not in session:
        flash('Please login to create a blog!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            title = sanitize_input(request.form.get('title', '').strip())
            content = sanitize_input(request.form.get('content', '').strip())
            
            # STRICT VALIDATION: Title AND Content AND Image required
            if not title or len(title) < 3:
                flash('Title is required and must be at least 3 characters!', 'error')
                return render_template('create.html')
            
            if not content or len(content) < 10:
                flash('Content is required and must be at least 10 characters!', 'error')
                return render_template('create.html')
            
            # Check if image is uploaded
            if 'images' not in request.files:
                flash('Image is required! Please upload at least one image.', 'error')
                return render_template('create.html')
            
            files = request.files.getlist('images')
            if not files or not files[0].filename:
                flash('Image is required! Please upload at least one image.', 'error')
                return render_template('create.html')
            
            if len(title) > 200:
                flash('Title cannot exceed 200 characters!', 'error')
                return render_template('create.html')
            
            if len(content) > 10000:
                flash('Content cannot exceed 10,000 characters!', 'error')
                return render_template('create.html')
            
            # Handle image uploads with validation
            image_urls = []
            for file in files:
                if file and file.filename:
                    # File type validation
                    if not allowed_file(file.filename):
                        flash('Invalid file type! Only PNG, JPG, JPEG, GIF, WEBP allowed.', 'error')
                        return render_template('create.html')
                    
                    # File size validation (5MB max)
                    file.seek(0, 2)  # Go to end of file
                    file_size = file.tell()
                    file.seek(0)  # Reset to beginning
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        flash('File too large! Maximum size is 5MB per image.', 'error')
                        return render_template('create.html')
                    
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    image_urls.append(unique_filename)
            
            # Final check: Must have at least one image
            if not image_urls:
                flash('At least one valid image is required!', 'error')
                return render_template('create.html')
            
            success = create_blog_with_images(title, content, session['username'], session.get('channel', 'general'), image_urls)
            if success:
                flash('Blog created successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Failed to create blog. Please try again.', 'error')
        
        except Exception as e:
            print(f"Create blog error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('create.html')

def update_user_password(username, password_hash):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (password_hash, username))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating password: {e}")
        return False

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('Please login to view profile!', 'error')
        return redirect(url_for('login'))
    
    username = session['username']
    user = get_user_by_username(username)
    
    if request.method == 'POST':
        bio = sanitize_input(request.form.get('bio', '').strip())
        
        # Update bio in database
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET bio = ? WHERE username = ?', (bio[:500], username))
                conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            print(f"Error updating profile: {e}")
            flash('Failed to update profile. Please try again.', 'error')
        return redirect(url_for('profile'))
    
    # Get user's blogs
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blogs WHERE author_username = ? ORDER BY created_at DESC', (username,))
            user_blogs = cursor.fetchall()
            
            # Get user bio
            cursor.execute('SELECT bio FROM users WHERE username = ?', (username,))
            bio_result = cursor.fetchone()
            bio = bio_result[0] if bio_result and bio_result[0] else ''
    except Exception as e:
        print(f"Error fetching profile data: {e}")
        user_blogs = []
        bio = ''
    
    blogs = []
    for row in user_blogs:
        # Parse images
        images = []
        if row[6]:
            try:
                images = json.loads(row[6])
            except (json.JSONDecodeError, TypeError):
                images = []
        
        blog = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'author': row[3],
            'channel': row[4],
            'date': row[5],
            'images': images
        }
        blogs.append(blog)
    
    return render_template('profile.html', user=user, blogs=blogs, bio=bio)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Simple approach: Just username and email verification
        username = sanitize_input(request.form.get('username', '').strip())
        email = sanitize_input(request.form.get('email', '').strip().lower())
        
        if not username:
            flash('Username is required!', 'error')
            return render_template('forgot_password.html')
            
        if not email:
            flash('Email is required!', 'error')
            return render_template('forgot_password.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address!', 'error')
            return render_template('forgot_password.html')
        
        # Verify username and email combination
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username FROM users WHERE username = ? AND LOWER(email) = ?', (username, email))
                result = cursor.fetchone()
                
                if result:
                    token = generate_reset_token(username)
                    if token:
                        reset_url = url_for('reset_password', token=token, _external=True)
                        return render_template('forgot_password.html', reset_url=reset_url)
                    else:
                        flash('Failed to generate reset token. Please try again.', 'error')
                else:
                    flash('Username and email combination not found!', 'error')
        except Exception as e:
            print(f"Error in forgot password: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    username = verify_reset_token(token)
    if not username:
        flash('Invalid or expired reset token!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(msg, 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('reset_password.html', token=token)
        
        consumed_username = consume_reset_token(token)
        if consumed_username:
            success = update_user_password(consumed_username, generate_password_hash(password, method='pbkdf2:sha256', salt_length=16))
            if success:
                flash('Password reset successful! Please login with your new password.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Failed to update password. Please try again.', 'error')
        else:
            flash('Token has already been used or is invalid!', 'error')
            return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/edit/<int:blog_id>', methods=['GET', 'POST'])
def edit_blog(blog_id):
    if 'username' not in session:
        flash('Please login to edit blogs!', 'error')
        return redirect(url_for('login'))
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blogs WHERE id = ?', (blog_id,))
            result = cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Database error in edit_blog: {e}")
        flash('Error loading blog', 'error')
        return redirect(url_for('index'))
    
    if not result:
        flash('Blog not found!', 'error')
        return redirect(url_for('index'))
    
    # Check if user owns this blog
    if result[3] != session['username']:
        flash('You can only edit your own blogs!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = sanitize_input(request.form.get('title', '').strip())
        content = sanitize_input(request.form.get('content', '').strip())
        
        if not title or len(title) < 3:
            flash('Title must be at least 3 characters!', 'error')
        elif not content or len(content) < 10:
            flash('Content must be at least 10 characters!', 'error')
        else:
            try:
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE blogs SET title = ?, content = ? WHERE id = ?', (title, content, blog_id))
                    conn.commit()
                flash('Blog updated successfully!', 'success')
                return redirect(url_for('view_blog', blog_id=blog_id))
            except sqlite3.Error as e:
                print(f"Edit blog error: {e}")
                flash('Failed to update blog. Please try again.', 'error')
    
    blog = {
        'id': result[0],
        'title': result[1],
        'content': result[2],
        'author': result[3],
        'channel': result[4],
        'date': result[5]
    }
    
    return render_template('edit_blog.html', blog=blog)

@app.route('/delete/<int:blog_id>', methods=['POST'])
def delete_blog(blog_id):
    if 'username' not in session:
        flash('Please login to delete blogs!', 'error')
        return redirect(url_for('login'))
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT author_username FROM blogs WHERE id = ?', (blog_id,))
            result = cursor.fetchone()
            
            if not result:
                flash('Blog not found!', 'error')
                return redirect(url_for('index'))
            
            if result[0] != session['username']:
                flash('You can only delete your own blogs!', 'error')
                return redirect(url_for('index'))
            
            cursor.execute('DELETE FROM blogs WHERE id = ?', (blog_id,))
            conn.commit()
        flash('Blog deleted successfully!', 'success')
    except sqlite3.Error as e:
        print(f"Delete blog error: {e}")
        flash('Failed to delete blog. Please try again.', 'error')
    
    return redirect(url_for('profile'))

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/sitemap.xml')
def sitemap():
    """Generate XML sitemap for SEO"""
    pages = []
    base_url = 'https://my-blog-app-utli.onrender.com'
    
    # Static pages
    pages.append({'loc': f'{base_url}/', 'priority': '1.0', 'changefreq': 'daily'})
    pages.append({'loc': f'{base_url}/login', 'priority': '0.5', 'changefreq': 'monthly'})
    pages.append({'loc': f'{base_url}/register', 'priority': '0.5', 'changefreq': 'monthly'})
    
    # Blog posts
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, created_at FROM blogs ORDER BY created_at DESC')
            blogs = cursor.fetchall()
            for blog_id, created_at in blogs:
                pages.append({
                    'loc': f'{base_url}/blog/{blog_id}',
                    'priority': '0.8',
                    'changefreq': 'weekly',
                    'lastmod': created_at.split()[0] if created_at else datetime.now().strftime('%Y-%m-%d')
                })
    except Exception as e:
        print(f"Sitemap error: {e}")
    
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        sitemap_xml += '  <url>\n'
        sitemap_xml += f'    <loc>{page["loc"]}</loc>\n'
        if 'lastmod' in page:
            sitemap_xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
        sitemap_xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        sitemap_xml += f'    <priority>{page["priority"]}</priority>\n'
        sitemap_xml += '  </url>\n'
    sitemap_xml += '</urlset>'
    
    response = make_response(sitemap_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

@app.route('/robots.txt')
def robots():
    """Robots.txt for search engines"""
    robots_txt = '''User-agent: *
Allow: /
Sitemap: https://my-blog-app-utli.onrender.com/sitemap.xml
'''
    response = make_response(robots_txt)
    response.headers['Content-Type'] = 'text/plain'
    return response

@app.route('/googleeef8bc3a48e26c4fb.html')
def google_verification():
    """Google Search Console verification"""
    return send_from_directory('static', 'googleeef8bc3a48e26c4fb.html')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images"""
    print(f"Image requested: {filename}")
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        print(f"Image not found: {filename}")
        return '', 404

@app.route('/follow/<username>', methods=['POST'])
def follow_user_route(username):
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    current_user = session['username']
    if current_user == username:
        return jsonify({'success': False, 'message': 'Cannot follow yourself'}), 400
    
    if follow_user(current_user, username):
        return jsonify({'success': True, 'message': f'Now following {username}'})
    else:
        return jsonify({'success': False, 'message': 'Failed to follow user'}), 500

@app.route('/unfollow/<username>', methods=['POST'])
def unfollow_user_route(username):
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    current_user = session['username']
    if unfollow_user(current_user, username):
        return jsonify({'success': True, 'message': f'Unfollowed {username}'})
    else:
        return jsonify({'success': False, 'message': 'Failed to unfollow user'}), 500

@app.route('/notifications')
def notifications():
    if 'username' not in session:
        flash('Please login to view notifications!', 'error')
        return redirect(url_for('login'))
    
    username = session['username']
    notifications = get_notifications(username)
    mark_notifications_read(username)
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/api/notifications/count')
def notifications_count():
    if 'username' not in session:
        return jsonify({'count': 0})
    
    count = get_unread_notifications_count(session['username'])
    return jsonify({'count': count})

@app.route('/api/security-question/<username>')
def get_security_question_api(username):
    question = get_user_security_question(username)
    if question:
        return jsonify({'question': question})
    else:
        return jsonify({'question': None}), 404

@app.route('/like/<int:blog_id>', methods=['POST'])
def like_blog_route(blog_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    username = session['username']
    
    if is_liked_by_user(blog_id, username):
        if unlike_blog(blog_id, username):
            likes_count = get_likes_count(blog_id)
            return jsonify({'success': True, 'liked': False, 'likes_count': likes_count})
        else:
            return jsonify({'success': False, 'message': 'Failed to unlike'}), 500
    else:
        if like_blog(blog_id, username):
            likes_count = get_likes_count(blog_id)
            return jsonify({'success': True, 'liked': True, 'likes_count': likes_count})
        else:
            return jsonify({'success': False, 'message': 'Failed to like'}), 500

@app.route('/user/<username>')
def user_profile(username):
    user = get_user_by_username(username)
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('index'))
    
    # Get user's blogs
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blogs WHERE author_username = ? ORDER BY created_at DESC', (username,))
            user_blogs = cursor.fetchall()
            
            cursor.execute('SELECT bio FROM users WHERE username = ?', (username,))
            bio_result = cursor.fetchone()
            bio = bio_result[0] if bio_result and bio_result[0] else ''
    except Exception as e:
        print(f"Error fetching user profile data: {e}")
        user_blogs = []
        bio = ''
    
    blogs = []
    for row in user_blogs:
        images = []
        if row[6]:
            try:
                images = json.loads(row[6])
            except (json.JSONDecodeError, TypeError):
                images = []
        
        blog = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'author': row[3],
            'channel': row[4],
            'date': row[5],
            'images': images
        }
        blogs.append(blog)
    
    # Get follow stats
    followers_count = get_followers_count(username)
    following_count = get_following_count(username)
    
    # Check if current user is following this user
    is_following_user = False
    if 'username' in session and session['username'] != username:
        is_following_user = is_following(session['username'], username)
    
    return render_template('user_profile.html', 
                         user=user, 
                         blogs=blogs, 
                         bio=bio,
                         followers_count=followers_count,
                         following_count=following_count,
                         is_following=is_following_user)

@app.route('/debug/blogs')
def debug_blogs():
    """Debug route to see what's in database"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, images FROM blogs')
            results = cursor.fetchall()
        return jsonify([{'id': r[0], 'title': r[1], 'images': r[2]} for r in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    print(f"404 Error: {request.url}")
    # Don't redirect static files (images, css, js) - just return 404
    if request.path.startswith('/static/'):
        return 'File not found', 404
    return redirect(url_for('index'))

@app.context_processor
def inject_user():
    notification_count = 0
    if 'username' in session:
        notification_count = get_unread_notifications_count(session['username'])
    
    return {
        'current_user': session.get('username'),
        'user_channel': session.get('channel'),
        'notification_count': notification_count
    }

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.config['SESSION_COOKIE_SECURE'] = False  # Disable for local HTTP
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)