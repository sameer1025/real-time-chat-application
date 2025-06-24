from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDTextButton, MDFlatButton
from kivymd.uix.list import OneLineAvatarIconListItem, TwoLineAvatarIconListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from plyer import filechooser
from kivy.clock import Clock
from datetime import datetime
import re
import os
import random
import mysql.connector
from mysql.connector import Error
import hashlib
import json

# Import our sentiment analyzer
from sentiment_analyzer import SentimentAnalyzer

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chat_app_db',
    'user': 'root',
    'password': 'Sameer@1278'  # Change this to your MySQL password
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.create_database_and_tables()
    
    def create_connection(self):
        """Create database connection"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
        return False
    
    def create_database_and_tables(self):
        """Create database and required tables"""
        connection = None
        cursor = None
        try:
            # Connect without specifying database first
            temp_config = DB_CONFIG.copy()
            temp_config.pop('database')
            
            connection = mysql.connector.connect(**temp_config)
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            cursor.execute(f"USE {DB_CONFIG['database']}")
            
            # Create users table with proper DEFAULT values
            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                about TEXT,
                profile_pic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                is_online BOOLEAN DEFAULT FALSE
            )
            """
            
            # Create friends table
            create_friends_table = """
            CREATE TABLE IF NOT EXISTS friends (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                friend_id INT NOT NULL,
                status ENUM('pending', 'accepted', 'blocked') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (friend_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_friendship (user_id, friend_id)
            )
            """
            
            # Create messages table
            create_messages_table = """
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT NOT NULL,
                receiver_id INT NOT NULL,
                message_text TEXT NOT NULL,
                message_type ENUM('text', 'image', 'file', 'voice') DEFAULT 'text',
                status ENUM('sent', 'delivered', 'read') DEFAULT 'sent',
                sentiment VARCHAR(20) DEFAULT NULL,
                emotions TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
            
            # Create chat_sessions table
            create_chat_sessions_table = """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user1_id INT NOT NULL,
                user2_id INT NOT NULL,
                last_message_id INT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (last_message_id) REFERENCES messages(id) ON DELETE SET NULL,
                UNIQUE KEY unique_chat (user1_id, user2_id)
            )
            """
            
            cursor.execute(create_users_table)
            cursor.execute(create_friends_table)
            cursor.execute(create_messages_table)
            cursor.execute(create_chat_sessions_table)
            
            connection.commit()
            print("Database and tables created successfully!")
            
            # Insert sample users if table is empty
            self.insert_sample_data(cursor)
            connection.commit()
            
            # Add sample messages
            self.add_sample_messages()
        
        except Error as e:
            print(f"Error creating database: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    
    def insert_sample_data(self, cursor):
        """Insert sample users and friends data"""
        try:
            # Check if users table is empty
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert sample users
                sample_users = [
                    ('john_doe', 'john@example.com', self.hash_password('1234'), 'John Doe', 'Software Developer passionate about mobile apps', 'https://cdn-icons-png.flaticon.com/512/147/147144.png'),
                    ('jane_smith', 'jane@demo.com', self.hash_password('abcd'), 'Jane Smith', 'Designer who loves creating beautiful interfaces', 'https://cdn-icons-png.flaticon.com/512/2922/2922510.png'),
                    ('alice_j', 'alice@example.com', self.hash_password('alice123'), 'Alice Johnson', 'Marketing specialist and coffee lover', 'https://cdn-icons-png.flaticon.com/512/2922/2922506.png'),
                    ('bob_w', 'bob@example.com', self.hash_password('bob123'), 'Bob Wilson', 'Project manager and tech enthusiast', 'https://cdn-icons-png.flaticon.com/512/147/147133.png'),
                    ('emma_d', 'emma@example.com', self.hash_password('emma123'), 'Emma Davis', 'Graphic designer and artist', 'https://cdn-icons-png.flaticon.com/512/2922/2922561.png'),
                    ('mike_c', 'mike@example.com', self.hash_password('mike123'), 'Mike Chen', 'Full-stack developer', 'https://cdn-icons-png.flaticon.com/512/147/147142.png'),
                    ('sarah_m', 'sarah@example.com', self.hash_password('sarah123'), 'Sarah Miller', 'UX/UI Designer', 'https://cdn-icons-png.flaticon.com/512/2922/2922510.png'),
                    ('david_b', 'david@example.com', self.hash_password('david123'), 'David Brown', 'Data scientist', 'https://cdn-icons-png.flaticon.com/512/147/147140.png')
                ]
                
                insert_user_query = """
                INSERT INTO users (username, email, password_hash, name, about, profile_pic)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.executemany(insert_user_query, sample_users)
                print("Sample users inserted successfully!")
                
                # Insert sample friendships
                sample_friendships = [
                    (1, 3), (1, 4), (1, 5),  # john_doe friends with alice, bob, emma
                    (2, 3), (2, 6), (2, 7),  # jane_smith friends with alice, mike, sarah
                    (3, 4), (3, 5), (3, 6),  # alice friends with bob, emma, mike
                    (4, 7), (4, 8),          # bob friends with sarah, david
                    (5, 6), (5, 7),          # emma friends with mike, sarah
                    (6, 8),                  # mike friends with david
                    (7, 8)                   # sarah friends with david
                ]
                
                insert_friendship_query = """
                INSERT INTO friends (user_id, friend_id, status)
                VALUES (%s, %s, 'accepted')
                """
                
                # Insert bidirectional friendships
                all_friendships = []
                for user_id, friend_id in sample_friendships:
                    all_friendships.append((user_id, friend_id))
                    all_friendships.append((friend_id, user_id))
                
                cursor.executemany(insert_friendship_query, all_friendships)
                print("Sample friendships created successfully!")
                
        except Error as e:
            print(f"Error inserting sample data: {e}")
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return self.hash_password(password) == hashed_password
    
    def create_user(self, username, email, password, name):
        """Create a new user"""
        try:
            if not self.create_connection():
                return False, "Database connection failed"
            
            cursor = self.connection.cursor()
            
            # Check if username or email already exists
            check_query = "SELECT id FROM users WHERE username = %s OR email = %s"
            cursor.execute(check_query, (username, email))
            
            if cursor.fetchone():
                return False, "Username or email already exists"
            
            # Insert new user
            password_hash = self.hash_password(password)
            insert_query = """
            INSERT INTO users (username, email, password_hash, name)
            VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (username, email, password_hash, name))
            self.connection.commit()
            
            return True, "User created successfully"
            
        except Error as e:
            return False, f"Error creating user: {e}"
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def authenticate_user(self, identifier, password):
        """Authenticate user by username/email and password"""
        try:
            if not self.create_connection():
                return None, "Database connection failed"
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Find user by username or email
            query = """
            SELECT id, username, email, password_hash, name, about, profile_pic
            FROM users 
            WHERE username = %s OR email = %s
            """
            
            cursor.execute(query, (identifier, identifier))
            user = cursor.fetchone()
            
            if not user:
                return None, "User not found"
            
            # Verify password
            if not self.verify_password(password, user['password_hash']):
                return None, "Incorrect password"
            
            # Update last login and online status
            update_query = """
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP, is_online = TRUE 
            WHERE id = %s
            """
            cursor.execute(update_query, (user['id'],))
            self.connection.commit()
            
            # Remove password hash from returned data
            user.pop('password_hash')
            
            # Handle None values properly
            user['name'] = user['name'] or ''
            user['about'] = user['about'] or 'Hey there! I am using Chat App.'
            user['profile_pic'] = user['profile_pic'] or 'https://cdn-icons-png.flaticon.com/512/149/149071.png'
            
            return user, "Login successful"
            
        except Error as e:
            return None, f"Authentication error: {e}"
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def get_user_friends(self, user_id):
        """Get list of user's friends"""
        try:
            if not self.create_connection():
                return []
            
            cursor = self.connection.cursor(dictionary=True)
            
            query = """
            SELECT u.id, u.username, u.name, u.profile_pic, u.is_online, u.last_login,
                   m.message_text as last_message, m.created_at as last_message_time,
                   COUNT(unread.id) as unread_count
            FROM friends f
            JOIN users u ON f.friend_id = u.id
            LEFT JOIN messages m ON (
                (m.sender_id = u.id AND m.receiver_id = %s) OR 
                (m.sender_id = %s AND m.receiver_id = u.id)
            ) AND m.id = (
                SELECT MAX(id) FROM messages 
                WHERE (sender_id = u.id AND receiver_id = %s) OR 
                      (sender_id = %s AND receiver_id = u.id)
            )
            LEFT JOIN messages unread ON (
                unread.sender_id = u.id AND unread.receiver_id = %s AND unread.status != 'read'
            )
            WHERE f.user_id = %s AND f.status = 'accepted'
            GROUP BY u.id, u.username, u.name, u.profile_pic, u.is_online, u.last_login, m.message_text, m.created_at
            ORDER BY m.created_at DESC, u.name
            """
            
            cursor.execute(query, (user_id, user_id, user_id, user_id, user_id, user_id))
            friends = cursor.fetchall()
            
            # Format the data with proper None handling
            formatted_friends = []
            for friend in friends:
                last_message_time = "No messages"
                if friend['last_message_time']:
                    time_diff = datetime.now() - friend['last_message_time']
                    if time_diff.days > 0:
                        last_message_time = f"{time_diff.days} days ago"
                    elif time_diff.seconds > 3600:
                        last_message_time = f"{time_diff.seconds // 3600} hours ago"
                    elif time_diff.seconds > 60:
                        last_message_time = f"{time_diff.seconds // 60} min ago"
                    else:
                        last_message_time = "Just now"
                
                formatted_friends.append({
                    'id': str(friend['id']),
                    'name': friend['name'] or 'Unknown User',
                    'username': friend['username'] or 'unknown',
                    'profile_pic': friend['profile_pic'] or 'https://cdn-icons-png.flaticon.com/512/149/149071.png',
                    'last_message': friend['last_message'] or "No messages yet",
                    'last_message_time': last_message_time,
                    'online_status': bool(friend['is_online']),
                    'last_seen': f"Last seen {last_message_time}" if not friend['is_online'] else "Online",
                    'unread_count': int(friend['unread_count'] or 0)
                })
            
            return formatted_friends
            
        except Error as e:
            print(f"Error getting friends: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def get_chat_messages(self, user_id, friend_id):
        """Get chat messages between two users"""
        try:
            if not self.create_connection():
                return []
            
            cursor = self.connection.cursor(dictionary=True)
            
            query = """
            SELECT m.id, m.sender_id, m.receiver_id, m.message_text, m.message_type, 
                   m.status, m.sentiment, m.emotions, m.created_at, u.name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = %s AND m.receiver_id = %s) OR 
                  (m.sender_id = %s AND m.receiver_id = %s)
            ORDER BY m.created_at ASC
            """
            
            cursor.execute(query, (user_id, friend_id, friend_id, user_id))
            messages = cursor.fetchall()
            
            # Format messages with proper None handling
            formatted_messages = []
            for msg in messages:
                # Parse emotions from JSON string if exists
                emotions = {}
                if msg['emotions']:
                    try:
                        emotions = json.loads(msg['emotions'])
                    except:
                        emotions = {}
                
                formatted_messages.append({
                    'id': msg['id'],
                    'sender': 'me' if msg['sender_id'] == user_id else str(msg['sender_id']),
                    'message': msg['message_text'] or '',
                    'timestamp': msg['created_at'].strftime("%I:%M %p") if msg['created_at'] else '',
                    'status': msg['status'] or 'sent',
                    'type': msg['message_type'] or 'text',
                    'sentiment': msg['sentiment'],
                    'emotions': emotions
                })
            
            return formatted_messages
            
        except Error as e:
            print(f"Error getting messages: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def send_message(self, sender_id, receiver_id, message_text, message_type='text', sentiment=None, emotions=None):
        """Send a message with sentiment analysis"""
        try:
            if not self.create_connection():
                return False
            
            cursor = self.connection.cursor()
            
            # Convert emotions dict to JSON string
            emotions_json = json.dumps(emotions) if emotions else None
            
            query = """
            INSERT INTO messages (sender_id, receiver_id, message_text, message_type, sentiment, emotions)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (sender_id, receiver_id, message_text, message_type, sentiment, emotions_json))
            self.connection.commit()
            
            message_id = cursor.lastrowid
            
            # Update or create chat session
            self.update_chat_session(sender_id, receiver_id, message_id)
            
            return True
            
        except Error as e:
            print(f"Error sending message: {e}")
            return False
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def update_chat_session(self, user1_id, user2_id, last_message_id):
        """Update or create chat session"""
        try:
            if not self.create_connection():
                return
            
            cursor = self.connection.cursor()
            
            # Check if chat session exists
            check_query = """
            SELECT id FROM chat_sessions 
            WHERE (user1_id = %s AND user2_id = %s) OR (user1_id = %s AND user2_id = %s)
            """
            cursor.execute(check_query, (user1_id, user2_id, user2_id, user1_id))
            session = cursor.fetchone()
            
            if session:
                # Update existing session
                update_query = """
                UPDATE chat_sessions 
                SET last_message_id = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
                """
                cursor.execute(update_query, (last_message_id, session[0]))
            else:
                # Create new session
                insert_query = """
                INSERT INTO chat_sessions (user1_id, user2_id, last_message_id)
                VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (user1_id, user2_id, last_message_id))
            
            self.connection.commit()
            
        except Error as e:
            print(f"Error updating chat session: {e}")
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def update_user_profile(self, user_id, name=None, about=None, profile_pic=None):
        """Update user profile"""
        try:
            if not self.create_connection():
                return False
            
            cursor = self.connection.cursor()
            
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = %s")
                values.append(name)
            if about is not None:
                updates.append("about = %s")
                values.append(about)
            if profile_pic is not None:
                updates.append("profile_pic = %s")
                values.append(profile_pic)
            
            if not updates:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
            
            cursor.execute(query, values)
            self.connection.commit()
            
            return True
            
        except Error as e:
            print(f"Error updating profile: {e}")
            return False
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()
    
    def set_user_offline(self, user_id):
        """Set user offline status"""
        try:
            if not self.create_connection():
                return
            
            cursor = self.connection.cursor()
            
            query = "UPDATE users SET is_online = FALSE WHERE id = %s"
            cursor.execute(query, (user_id,))
            self.connection.commit()
            
        except Error as e:
            print(f"Error setting user offline: {e}")
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()

    def auto_add_friends_for_user(self, user_id):
        """Automatically add some random friends for a user"""
        try:
            if not self.create_connection():
                return False
            
            cursor = self.connection.cursor()
            
            # Get all users except the current user
            query = "SELECT id FROM users WHERE id != %s LIMIT 5"
            cursor.execute(query, (user_id,))
            potential_friends = cursor.fetchall()
            
            if not potential_friends:
                return False
            
            # Check existing friendships
            existing_query = "SELECT friend_id FROM friends WHERE user_id = %s"
            cursor.execute(existing_query, (user_id,))
            existing_friends = [row[0] for row in cursor.fetchall()]
            
            # Add friendships with users who aren't already friends
            friendships_to_add = []
            for friend_row in potential_friends:
                friend_id = friend_row[0]
                if friend_id not in existing_friends:
                    # Add bidirectional friendship
                    friendships_to_add.extend([
                        (user_id, friend_id),
                        (friend_id, user_id)
                    ])
            
            if friendships_to_add:
                insert_friendship_query = """
                INSERT IGNORE INTO friends (user_id, friend_id, status)
                VALUES (%s, %s, 'accepted')
                """
                cursor.executemany(insert_friendship_query, friendships_to_add)
                self.connection.commit()
                
                print(f"Added {len(friendships_to_add)//2} friends for user {user_id}")
                return True
            
            return False
            
        except Error as e:
            print(f"Error auto-adding friends: {e}")
            return False
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()

    def add_sample_messages(self):
        """Add some sample messages between users"""
        try:
            if not self.create_connection():
                return
            
            cursor = self.connection.cursor()
            
            # Check if messages already exist
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            if message_count > 0:
                return  # Messages already exist
            
            # Sample messages between different users
            sample_messages = [
                (1, 2, "Hey! How are you doing?", 'text'),
                (2, 1, "I'm doing great! Thanks for asking", 'text'),
                (1, 2, "That's awesome! Want to grab coffee sometime?", 'text'),
                (3, 1, "Hi John! Did you finish the project?", 'text'),
                (1, 3, "Almost done! Just need to test a few more features", 'text'),
                (4, 2, "Jane, loved your latest design work!", 'text'),
                (2, 4, "Thank you Bob! I really appreciate the feedback", 'text'),
                (5, 1, "John, are you free for a quick call?", 'text'),
                (1, 5, "Sure Emma! Give me 5 minutes", 'text'),
                (6, 3, "Alice, the new update looks fantastic!", 'text'),
                (3, 6, "Thanks Mike! Took a lot of work but worth it", 'text'),
                (7, 4, "Bob, can you review my latest mockups?", 'text'),
                (4, 7, "Of course Sarah! Send them over", 'text'),
                (8, 5, "Emma, great presentation today!", 'text'),
                (5, 8, "Thanks David! Your feedback was really helpful", 'text'),
            ]
            
            insert_message_query = """
            INSERT INTO messages (sender_id, receiver_id, message_text, message_type, created_at)
            VALUES (%s, %s, %s, %s, NOW() - INTERVAL FLOOR(RAND() * 24) HOUR)
            """
            
            cursor.executemany(insert_message_query, sample_messages)
            self.connection.commit()
            print("Sample messages added successfully!")
            
        except Error as e:
            print(f"Error adding sample messages: {e}")
        finally:
            if self.connection and self.connection.is_connected():
                cursor.close()
                self.connection.close()

# Initialize database manager
db_manager = DatabaseManager()

KV = '''
ScreenManager:
    SignInScreen:
    SignUpScreen:
    HomeScreen:
    FriendsScreen:
    ChatScreen:
    ProfileScreen:
    SettingsScreen:
    FullScreenPhotoScreen:

<SignInScreen>:
    name: 'signin'
    FloatLayout:
        BoxLayout:
            orientation: 'vertical'
            padding: dp(40)
            spacing: dp(8)
            size_hint: 0.9, None
            height: self.minimum_height
            pos_hint: {"center_x": 0.5, "center_y": 0.5}

            MDLabel:
                text: "Chat App"
                font_style: "H3"
                halign: "center"
                size_hint_y: None
                height: self.texture_size[1]
                theme_text_color: "Primary"

            MDTextField:
                id: login_input
                hint_text: "Username or Email"
                icon_right: "account"
                helper_text: "Enter your username or email"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_text: app.clear_login_errors(); app.validate_login_input()

            MDTextField:
                id: password_input
                hint_text: "Password"
                password: True
                helper_text: "Enter your password"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_focus: app.toggle_password_checkbox_visibility('signin', self.focus)
                on_text: app.toggle_password_checkbox_visibility('signin', self.focus or bool(self.text)); app.clear_login_errors()

            BoxLayout:
                id: password_checkbox_container
                orientation: 'horizontal'
                size_hint_y: None
                height: 0
                opacity: 0
                spacing: dp(10)

                MDCheckbox:
                    id: show_password_checkbox
                    size_hint: None, None
                    size: dp(40), dp(40)
                    pos_hint: {"center_y": .5}
                    on_active: app.toggle_login_password_visibility()

                MDLabel:
                    text: "Show Password"
                    size_hint_y: None
                    height: dp(40)
                    theme_text_color: "Primary"
                    valign: "center"

            MDRaisedButton:
                text: "SIGN IN"
                size_hint_x: None
                width: dp(150)
                height: dp(48)
                md_bg_color: app.theme_cls.primary_color
                pos_hint: {"center_x": .5}
                on_release: app.login()

            MDTextButton:
                text: "Don't have an account? Sign up"
                pos_hint: {"center_x": .5}
                size_hint_y: None
                height: dp(36)
                on_release: root.manager.current = 'signup'

<SignUpScreen>:
    name: 'signup'
    FloatLayout:
        BoxLayout:
            orientation: 'vertical'
            padding: dp(40)
            spacing: dp(6)
            size_hint: 0.9, None
            height: self.minimum_height
            pos_hint: {"center_x": 0.5, "center_y": 0.5}

            MDLabel:
                text: "Sign Up"
                font_style: "H5"
                halign: "center"
                size_hint_y: None
                height: self.texture_size[1]
                theme_text_color: "Primary"

            MDTextField:
                id: signup_username_input
                hint_text: "Username"
                icon_right: "account"
                helper_text: "Enter a username (max 16 characters)"
                helper_text_mode: "on_focus"
                max_text_length: 16
                size_hint_y: None
                height: dp(56)
                on_text: app.clear_signup_errors(); app.validate_signup_username()

            MDTextField:
                id: signup_email_input
                hint_text: "Email"
                icon_right: "email"
                helper_text: "Enter a valid email (e.g., user@gmail.com)"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_text: app.clear_signup_errors(); app.validate_signup_email()

            MDTextField:
                id: signup_name_input
                hint_text: "Full Name"
                icon_right: "account-circle"
                helper_text: "Enter your full name"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_text: app.clear_signup_errors()

            MDTextField:
                id: signup_password
                hint_text: "Password"
                password: True
                helper_text: "Minimum 6 characters"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_focus: app.toggle_password_checkbox_visibility('signup_password', self.focus)
                on_text: app.toggle_password_checkbox_visibility('signup_password', self.focus or bool(self.text)); app.clear_signup_errors(); app.validate_signup_password()

            BoxLayout:
                id: signup_password_checkbox_container
                orientation: 'horizontal'
                size_hint_y: None
                height: 0
                opacity: 0
                spacing: dp(10)

                MDCheckbox:
                    id: show_signup_password_checkbox
                    size_hint: None, None
                    size: dp(40), dp(40)
                    pos_hint: {"center_y": .5}
                    on_active: app.toggle_signup_password_visibility()

                MDLabel:
                    text: "Show Password"
                    size_hint_y: None
                    height: dp(40)
                    theme_text_color: "Primary"
                    valign: "center"

            MDTextField:
                id: signup_confirm_password
                hint_text: "Confirm Password"
                password: True
                helper_text: "Re-enter your password"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_focus: app.toggle_password_checkbox_visibility('signup_confirm', self.focus)
                on_text: app.toggle_password_checkbox_visibility('signup_confirm', self.focus or bool(self.text)); app.clear_signup_errors(); app.validate_signup_confirm_password()

            BoxLayout:
                id: confirm_password_checkbox_container
                orientation: 'horizontal'
                size_hint_y: None
                height: 0
                opacity: 0
                spacing: dp(10)

                MDCheckbox:
                    id: show_confirm_password_checkbox
                    size_hint: None, None
                    size: dp(40), dp(40)
                    pos_hint: {"center_y": .5}
                    on_active: app.toggle_signup_confirm_password_visibility()

                MDLabel:
                    text: "Show Confirm Password"
                    size_hint_y: None
                    height: dp(40)
                    theme_text_color: "Primary"
                    valign: "center"

            MDRaisedButton:
                text: "SIGN UP"
                size_hint_x: None
                width: dp(150)
                height: dp(48)
                md_bg_color: app.theme_cls.primary_color
                pos_hint: {"center_x": .5}
                on_release: app.signup()

            MDTextButton:
                text: "Already have an account? Sign in"
                pos_hint: {"center_x": .5}
                size_hint_y: None
                height: dp(36)
                on_release: root.manager.current = 'signin'

<HomeScreen>:
    name: 'home'
    BoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Chat App"
            right_action_items: [["dots-vertical", lambda x: app.open_menu(self)], ["account-plus", lambda x: app.show_add_friend_dialog()]]
        
        # Search Bar Section
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(70)
            padding: dp(15)
            spacing: dp(10)
            
            MDIcon:
                icon: "magnify"
                size_hint_x: None
                width: dp(24)
                theme_icon_color: "Primary"
                pos_hint: {"center_y": 0.5}
            
            MDTextField:
                id: search_input
                hint_text: "Search friends..."
                helper_text: "Type to search friends"
                helper_text_mode: "on_focus"
                size_hint_y: None
                height: dp(56)
                on_text: app.handle_search_input(self.text)
        
        # Friends List Section
        ScrollView:
            MDList:
                id: home_friends_list

<FriendsScreen>:
    name: 'friends'
    BoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Friends"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'home')]]
            right_action_items: [["account-plus", lambda x: app.show_add_friend_dialog()]]
        
        ScrollView:
            MDList:
                id: friends_list

<ChatScreen>:
    name: 'chat'
    BoxLayout:
        orientation: 'vertical'
        
        # Chat Header
        MDTopAppBar:
            id: chat_header
            title: "Friend Name"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'home')]]
            right_action_items: [["phone", lambda x: app.voice_call()], ["video", lambda x: app.video_call()], ["dots-vertical", lambda x: app.open_chat_menu(self)]]
        
        # Online Status Bar
        BoxLayout:
            id: status_bar
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(30)
            padding: [dp(15), dp(5)]
            spacing: dp(10)
            
            MDIcon:
                id: status_icon
                icon: "circle"
                size_hint_x: None
                width: dp(12)
                theme_icon_color: "Custom"
                icon_color: 0, 1, 0, 1  # Green for online
            
            MDLabel:
                id: status_text
                text: "Online"
                font_style: "Caption"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: dp(20)
        
        # Messages Area
        ScrollView:
            id: messages_scroll
            do_scroll_x: False
            
            MDBoxLayout:
                id: messages_container
                orientation: 'vertical'
                spacing: dp(5)
                padding: dp(10)
                size_hint_y: None
                height: self.minimum_height
        
        # Typing Indicator
        BoxLayout:
            id: typing_indicator
            orientation: 'horizontal'
            size_hint_y: None
            height: 0
            opacity: 0
            padding: [dp(15), dp(5)]
            spacing: dp(10)
            
            MDIcon:
                icon: "circle"
                size_hint_x: None
                width: dp(8)
                theme_icon_color: "Primary"
            
            MDLabel:
                text: "Friend is typing..."
                font_style: "Caption"
                theme_text_color: "Primary"
                size_hint_y: None
                height: dp(20)
        
        # Message Input Area
        MDCard:
            size_hint_y: None
            height: dp(60)
            elevation: 3
            padding: dp(5)
            
            BoxLayout:
                orientation: 'horizontal'
                spacing: dp(5)
                
                # Attachment Button
                MDIconButton:
                    icon: "attachment"
                    theme_icon_color: "Primary"
                    on_release: app.show_attachment_options()
                
                # Message Input
                MDTextField:
                    id: message_input
                    hint_text: "Type a message..."
                    multiline: False
                    size_hint_y: None
                    height: dp(40)
                    on_text: app.on_message_text_change(self.text)
                    on_text_validate: app.send_message()
                
                # Emoji Button
                MDIconButton:
                    icon: "emoticon-happy"
                    theme_icon_color: "Primary"
                    on_release: app.show_emoji_picker()
                
                # Send/Voice Button
                MDIconButton:
                    id: send_voice_button
                    icon: "microphone"
                    theme_icon_color: "Primary"
                    on_release: app.send_message_or_voice()

<ProfileScreen>:
    name: 'profile'
    BoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Profile"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'home')]]
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                padding: dp(20)
                spacing: dp(20)
                size_hint_y: None
                height: self.minimum_height
                
                # Profile Photo Section
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(200)
                    spacing: dp(10)
                    
                    # Circular Profile Photo (Clickable)
                    FloatLayout:
                        size_hint_y: None
                        height: dp(150)
                        
                        MDCard:
                            id: profile_photo_card
                            size_hint: None, None
                            size: dp(120), dp(120)
                            pos_hint: {"center_x": 0.5, "center_y": 0.5}
                            md_bg_color: app.theme_cls.primary_color
                            radius: [60]
                            elevation: 3
                            on_release: app.open_fullscreen_photo()
                            
                            Image:
                                id: profile_image
                                source: "https://cdn-icons-png.flaticon.com/512/149/149071.png"
                    
                    # Edit Button
                    MDTextButton:
                        id: edit_photo_btn
                        text: "Edit"
                        size_hint_y: None
                        height: dp(36)
                        pos_hint: {"center_x": 0.5}
                        theme_text_color: "Primary"
                        on_release: app.toggle_photo_edit_mode()
                
                # Photo Edit Options (Hidden by default)
                BoxLayout:
                    id: photo_edit_container
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: 0
                    opacity: 0
                    spacing: dp(10)
                    
                    MDRaisedButton:
                        text: "Browse D: Drive"
                        size_hint_x: 0.5
                        on_release: app.choose_profile_photo()
                        
                    MDFlatButton:
                        text: "Cancel"
                        size_hint_x: 0.5
                        on_release: app.cancel_photo_edit()
                
                # Name Section
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(56)
                    spacing: dp(15)
                    
                    MDIcon:
                        icon: "account"
                        size_hint_x: None
                        width: dp(24)
                        theme_icon_color: "Primary"
                        pos_hint: {"center_y": 0.5}
                    
                    MDTextField:
                        id: profile_name
                        hint_text: "Full Name"
                        text: ""
                        helper_text: "Enter your full name"
                        helper_text_mode: "on_focus"
                        size_hint_y: None
                        height: dp(56)
                
                # About Section
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(100)
                    spacing: dp(15)
                    
                    MDIcon:
                        icon: "information"
                        size_hint_x: None
                        width: dp(24)
                        theme_icon_color: "Primary"
                        pos_hint: {"top": 1}
                        y: self.parent.height - dp(30)
                    
                    MDTextField:
                        id: profile_about
                        hint_text: "About"
                        text: ""
                        helper_text: "Tell us about yourself"
                        helper_text_mode: "on_focus"
                        multiline: True
                        size_hint_y: None
                        height: dp(100)
                
                # Save Button
                MDRaisedButton:
                    text: "SAVE CHANGES"
                    size_hint_x: None
                    width: dp(200)
                    height: dp(48)
                    md_bg_color: app.theme_cls.primary_color
                    pos_hint: {"center_x": 0.5}
                    on_release: app.save_profile_changes()

<SettingsScreen>:
    name: 'settings'
    BoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Settings"
            left_action_items: [["arrow-left", lambda x: setattr(root.manager, 'current', 'home')]]
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                padding: dp(20)
                spacing: dp(15)
                size_hint_y: None
                height: self.minimum_height
                
                # Account Settings Section
                MDLabel:
                    text: "Account Settings"
                    font_style: "H6"
                    theme_text_color: "Primary"
                    size_hint_y: None
                    height: dp(40)
                
                MDCard:
                    orientation: 'vertical'
                    padding: dp(15)
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(200)
                    elevation: 2
                    
                    # Change Password
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(15)
                        
                        MDIcon:
                            icon: "lock"
                            size_hint_x: None
                            width: dp(24)
                            theme_icon_color: "Primary"
                            pos_hint: {"center_y": 0.5}
                        
                        MDLabel:
                            text: "Change Password"
                            theme_text_color: "Primary"
                            valign: "center"
                        
                        MDIconButton:
                            icon: "chevron-right"
                            theme_icon_color: "Primary"
                            on_release: app.show_change_password_dialog()
                    
                    MDSeparator:
                    
                    # Two-Factor Authentication
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(15)
                        
                        MDIcon:
                            icon: "shield-check"
                            size_hint_x: None
                            width: dp(24)
                            theme_icon_color: "Primary"
                            pos_hint: {"center_y": 0.5}
                        
                        MDLabel:
                            text: "Two-Factor Authentication"
                            theme_text_color: "Primary"
                            valign: "center"
                        
                        MDSwitch:
                            id: two_factor_switch
                            pos_hint: {"center_y": 0.5}
                            on_active: app.toggle_two_factor(self.active)
                    
                    MDSeparator:
                    
                    # Account Privacy
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(15)
                        
                        MDIcon:
                            icon: "account-lock"
                            size_hint_x: None
                            width: dp(24)
                            theme_icon_color: "Primary"
                            pos_hint: {"center_y": 0.5}
                        
                        MDLabel:
                            text: "Private Account"
                            theme_text_color: "Primary"
                            valign: "center"
                        
                        MDSwitch:
                            id: private_account_switch
                            pos_hint: {"center_y": 0.5}
                            on_active: app.toggle_private_account(self.active)

<FullScreenPhotoScreen>:
    name: 'fullscreen_photo'
    FloatLayout:
        md_bg_color: 0, 0, 0, 1  # Black background
        
        # Back arrow button (top-left)
        MDIconButton:
            icon: "arrow-left"
            pos_hint: {"left": 0.05, "top": 0.95}
            theme_icon_color: "Custom"
            icon_color: 1, 1, 1, 1  # White color
            on_release: app.close_fullscreen_photo()
        
        # Close button (top-right)
        MDIconButton:
            icon: "close"
            pos_hint: {"right": 0.95, "top": 0.95}
            theme_icon_color: "Custom"
            icon_color: 1, 1, 1, 1  # White color
            on_release: app.close_fullscreen_photo()
        
        # Full screen image
        Image:
            id: fullscreen_image
            source: ""
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            size_hint: 0.9, 0.9
'''

class MessageBubble(MDCard):
    def __init__(self, message_data, is_sent=False, **kwargs):
        super().__init__(**kwargs)
        self.message_data = message_data
        self.is_sent = is_sent
        self.setup_bubble()
    
    def setup_bubble(self):
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 90  # Increased height for sentiment info at top
        self.padding = 10
        self.spacing = 3
        self.elevation = 2
        
        # Get sentiment and set colors
        sentiment = self.message_data.get('sentiment', 'neutral')
        
        if self.is_sent:
            if sentiment == 'negative':
                self.md_bg_color = (0.8, 0.2, 0.2, 1)  # Red for negative sent messages
            else:
                self.md_bg_color = (0.2, 0.6, 1, 1)  # Blue for other sent messages
            self.pos_hint = {"right": 0.95}
            self.size_hint_x = 0.7
        else:
            if sentiment == 'negative':
                self.md_bg_color = (0.6, 0.2, 0.2, 1)  # Dark red for negative received messages
            else:
                self.md_bg_color = (0.3, 0.3, 0.3, 1)  # Gray for other received messages
            self.pos_hint = {"left": 0.05}
            self.size_hint_x = 0.7
        
        # Sentiment info at the top
        if sentiment:
            sentiment_label = MDLabel(
                text=f"Sentiment: {sentiment.upper()}",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1) if sentiment == 'negative' else (0.9, 0.9, 0.9, 1),
                size_hint_y=None,
                height=15,
                halign="left" if not self.is_sent else "right"
            )
            self.add_widget(sentiment_label)
        
        # Message text with None handling
        message_text = self.message_data.get('message', '') or ''
        message_label = MDLabel(
            text=str(message_text),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=35,
            halign="left" if not self.is_sent else "right"
        )
        self.add_widget(message_label)
        
        # Time and status
        time_status_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=20,
            spacing=5
        )
        
        timestamp = self.message_data.get('timestamp', '') or ''
        time_label = MDLabel(
            text=str(timestamp),
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(0.8, 0.8, 0.8, 1),
            size_hint_x=None,
            width=60,
            halign="right" if self.is_sent else "left"
        )
        
        if self.is_sent:
            status_icon = MDIcon(
                icon=self.get_status_icon(),
                size_hint_x=None,
                width=16,
                theme_icon_color="Custom",
                icon_color=self.get_status_color()
            )
            time_status_box.add_widget(time_label)
            time_status_box.add_widget(status_icon)
        else:
            time_status_box.add_widget(time_label)
        
        self.add_widget(time_status_box)

    def get_status_icon(self):
        status = self.message_data.get('status', 'sent') or 'sent'
        if status == 'sent':
            return 'check'
        elif status == 'delivered':
            return 'check-all'
        elif status == 'read':
            return 'check-all'
        return 'check'
    
    def get_status_color(self):
        status = self.message_data.get('status', 'sent') or 'sent'
        if status == 'read':
            return (0, 1, 0, 1)  # Green for read
        elif status == 'delivered':
            return (0.8, 0.8, 0.8, 1)  # Gray for delivered
        return (0.6, 0.6, 0.6, 1)  # Light gray for sent

class SignInScreen(Screen):
    pass

class SignUpScreen(Screen):
    pass

class HomeScreen(Screen):
    pass

class FriendsScreen(Screen):
    pass

class ChatScreen(Screen):
    pass

class ProfileScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class FullScreenPhotoScreen(Screen):
    pass

class ChatApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = None
        self.current_friend = None
        self.current_friend_data = None
        self.search_clear_event = None
        self.dialog = None
        self.typing_timer = None
        self.sentiment_analyzer = SentimentAnalyzer()  # Initialize sentiment analyzer
        self.pending_message = None  # Store message pending confirmation

    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)

    def on_start(self):
        """Initialize the app after building"""
        # Test database connection
        if db_manager.create_connection():
            self.show_snackbar("Database connected successfully!")
        else:
            self.show_snackbar("Database connection failed!")

    def show_snackbar(self, message):
        """Helper method to show snackbar messages"""
        snackbar = Snackbar()
        snackbar.text = message
        snackbar.open()

    def safe_text_assignment(self, widget, value, default=""):
        """Safely assign text to widget, handling None values"""
        if value is None:
            widget.text = default
        else:
            widget.text = str(value)

    def load_friends_list_on_home(self):
        """Load friends from database into the home screen friends list"""
        if not self.current_user:
            return
        
        home_screen = self.root.get_screen('home')
        friends_list_widget = home_screen.ids.home_friends_list
        
        # Clear existing friends
        friends_list_widget.clear_widgets()
        
        # Get friends from database
        friends = db_manager.get_user_friends(self.current_user['id'])
        
        if not friends:
            # Show a message if no friends found
            no_friends_item = OneLineAvatarIconListItem(
                text="No friends yet. Add some friends to start chatting!",
                disabled=True
            )
            friends_list_widget.add_widget(no_friends_item)
            return
        
        for friend in friends:
            # Create friend item with profile picture
            item = TwoLineAvatarIconListItem(
                text=str(friend.get('name', 'Unknown User')),
                secondary_text=str(friend.get('last_message', 'No messages yet')),
                on_release=lambda x, friend_data=friend: self.open_chat_from_home(friend_data)
            )
            
            # Add profile picture (placeholder for now)
            profile_icon = MDIcon(
                icon="account-circle",
                size_hint_x=None,
                width=(40),
                theme_icon_color="Primary"
            )
            item.add_widget(profile_icon)
            
            # Add online status indicator
            if friend.get('online_status', False):
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom",
                    icon_color=(0, 1, 0, 1),  # Green for online
                    size_hint_x=None,
                    width=(12),
                    pos_hint={"right": 0.95, "center_y": 0.7}
                )
            else:
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom", 
                    icon_color=(0.5, 0.5, 0.5, 1),  # Gray for offline
                    size_hint_x=None,
                    width=(12),
                    pos_hint={"right": 0.95, "center_y": 0.7}
                )
            
            item.add_widget(status_icon)
            
            # Add unread count badge
            unread_count = friend.get('unread_count', 0)
            if unread_count > 0:
                badge_card = MDCard(
                    size_hint=(None, None),
                    size=((24), (24)),
                    md_bg_color=(1, 0, 0, 1),  # Red background
                    radius=[(12)],
                    pos_hint={"right": 0.95, "center_y": 0.3},
                    elevation=2
                )
                
                badge_label = MDLabel(
                    text=str(unread_count),
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),  # White text
                    halign="center",
                    valign="center",
                    font_style="Caption"
                )
                
                badge_card.add_widget(badge_label)
                item.add_widget(badge_card)
            
            friends_list_widget.add_widget(item)

    def load_friends_list(self):
        """Load friends from database into the friends screen list"""
        if not self.current_user:
            return
        
        friends_screen = self.root.get_screen('friends')
        friends_list_widget = friends_screen.ids.friends_list
        
        # Clear existing friends
        friends_list_widget.clear_widgets()
        
        # Get friends from database
        friends = db_manager.get_user_friends(self.current_user['id'])
        
        for friend in friends:
            item = TwoLineAvatarIconListItem(
                text=str(friend.get('name', 'Unknown User')),
                secondary_text=str(friend.get('last_message', 'No messages yet')),
                on_release=lambda x, friend_data=friend: self.open_chat(friend_data)
            )
            
            # Add online status indicator
            if friend.get('online_status', False):
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom",
                    icon_color=(0, 1, 0, 1),
                    size_hint_x=None,
                    width=12
                )
            else:
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom", 
                    icon_color=(0.5, 0.5, 0.5, 1),
                    size_hint_x=None,
                    width=12
                )
            
            item.add_widget(status_icon)
            
            # Add unread count badge
            unread_count = friend.get('unread_count', 0)
            if unread_count > 0:
                badge = MDLabel(
                    text=str(unread_count),
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),
                    size_hint=(None, None),
                    size=(24, 24),
                    pos_hint={"right": 0.9, "center_y": 0.5},
                    halign="center",
                    valign="center"
                )
                badge_card = MDCard(
                    size_hint=(None, None),
                    size=(24, 24),
                    md_bg_color=(1, 0, 0, 1),
                    radius=[12],
                    pos_hint={"right": 0.9, "center_y": 0.5}
                )
                badge_card.add_widget(badge)
                item.add_widget(badge_card)
            
            friends_list_widget.add_widget(item)

    def open_chat_from_home(self, friend_data):
        """Open chat with specific friend from home screen"""
        self.open_chat(friend_data)

    def open_chat(self, friend_data):
        """Open chat with specific friend"""
        self.current_friend_data = friend_data
        
        # Update chat screen header
        chat_screen = self.root.get_screen('chat')
        chat_screen.ids.chat_header.title = str(friend_data.get('name', 'Unknown User'))
        
        # Update online status
        if friend_data.get('online_status', False):
            chat_screen.ids.status_icon.icon_color = (0, 1, 0, 1)
            chat_screen.ids.status_text.text = "Online"
        else:
            chat_screen.ids.status_icon.icon_color = (0.5, 0.5, 0.5, 1)
            last_seen = friend_data.get('last_seen', 'Offline')
            chat_screen.ids.status_text.text = str(last_seen)
        
        # Load chat messages from database
        self.load_chat_messages(friend_data['id'])
        
        # Navigate to chat screen
        self.root.current = 'chat'

    def load_chat_messages(self, friend_id):
        """Load messages for the current chat from database"""
        if not self.current_user:
            return
        
        chat_screen = self.root.get_screen('chat')
        messages_container = chat_screen.ids.messages_container
        
        # Clear existing messages
        messages_container.clear_widgets()
        
        # Load messages from database
        messages = db_manager.get_chat_messages(self.current_user['id'], int(friend_id))
        
        for message in messages:
            is_sent = message['sender'] == 'me'
            bubble = MessageBubble(message, is_sent=is_sent)
            messages_container.add_widget(bubble)
        
        # Scroll to bottom
        Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)

    def scroll_to_bottom(self):
        """Scroll messages to bottom"""
        try:
            chat_screen = self.root.get_screen('chat')
            scroll_view = chat_screen.ids.messages_scroll
            scroll_view.scroll_y = 0
        except:
            pass

    def send_message(self):
        """Send a message and save to database with sentiment analysis"""
        if not self.current_user or not self.current_friend_data:
            return
        
        chat_screen = self.root.get_screen('chat')
        message_input = chat_screen.ids.message_input
        message_text = message_input.text.strip()
        
        if not message_text:
            return
        
        # Analyze sentiment and emotions
        sentiment_info = self.sentiment_analyzer.analyze_sentiment(message_text)
        emotion_counts = self.sentiment_analyzer.analyze_emotions(message_text)
        sentiment = sentiment_info['sentiment']
        
        # If message is negative, ask for confirmation
        if sentiment == 'negative':
            self.pending_message = {
                'text': message_text,
                'sentiment_info': sentiment_info,
                'emotion_counts': emotion_counts
            }
            self.show_negative_message_confirmation()
            return
        
        # Send the message normally for positive/neutral
        self.actually_send_message(message_text, sentiment_info, emotion_counts)

    def show_negative_message_confirmation(self):
        """Show confirmation dialog for negative messages"""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Negative Message Detected",
                text=f"Your message appears to have negative sentiment. Are you sure you want to send it?\n\nMessage: \"{self.pending_message['text']}\"",
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.cancel_negative_message
                    ),
                    MDRaisedButton(
                        text="SEND ANYWAY",
                        md_bg_color=(1, 0, 0, 1),  # Red button
                        on_release=self.confirm_negative_message
                    ),
                ],
            )
        else:
            self.dialog.title = "Negative Message Detected"
            self.dialog.text = f"Your message appears to have negative sentiment. Are you sure you want to send it?\n\nMessage: \"{self.pending_message['text']}\""
        
        self.dialog.open()

    def cancel_negative_message(self, *args):
        """Cancel sending negative message"""
        self.close_dialog()
        self.pending_message = None
        self.show_snackbar("Message cancelled")

    def confirm_negative_message(self, *args):
        """Confirm and send negative message"""
        self.close_dialog()
        if self.pending_message:
            self.actually_send_message(
                self.pending_message['text'],
                self.pending_message['sentiment_info'],
                self.pending_message['emotion_counts']
            )
            self.pending_message = None

    def actually_send_message(self, message_text, sentiment_info, emotion_counts):
        """Actually send the message to database and UI"""
        sentiment = sentiment_info['sentiment']
        
        # Show sentiment analysis result (without emojis)
        sentiment_message = f"Message sentiment: {sentiment.title()}"
        if emotion_counts:
            top_emotion = emotion_counts.most_common(1)[0][0]
            sentiment_message += f" | Emotion: {top_emotion.title()}"
        
        self.show_snackbar(sentiment_message)
        
        # Save message to database with sentiment data
        success = db_manager.send_message(
            self.current_user['id'], 
            int(self.current_friend_data['id']), 
            message_text,
            'text',
            sentiment,
            dict(emotion_counts)
        )
        
        if success:
            # Create new message for UI with sentiment info
            new_message = {
                "id": 0,  # Will be set by database
                "sender": "me",
                "message": message_text,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "status": "sent",
                "type": "text",
                "sentiment": sentiment,
                "emotions": dict(emotion_counts)
            }
            
            # Add message bubble to UI
            chat_screen = self.root.get_screen('chat')
            messages_container = chat_screen.ids.messages_container
            bubble = MessageBubble(new_message, is_sent=True)
            messages_container.add_widget(bubble)
            
            # Clear input
            message_input = chat_screen.ids.message_input
            message_input.text = ""
            
            # Scroll to bottom
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)
            
            # Update friends list on home screen
            Clock.schedule_once(lambda dt: self.load_friends_list_on_home(), 0.5)
            
            # Simulate message status updates
            Clock.schedule_once(lambda dt: self.update_message_status(new_message, "delivered"), 1)
            Clock.schedule_once(lambda dt: self.update_message_status(new_message, "read"), 3)
            
            # Simulate friend response (for demo)
            Clock.schedule_once(lambda dt: self.simulate_friend_response(), 5)
        else:
            self.show_snackbar("Failed to send message")

    def update_message_status(self, message, status):
        """Update message status"""
        message['status'] = status
        # In a real app, you would update the UI here

    def simulate_friend_response(self):
        """Simulate a response from friend (for demo purposes)"""
        if not self.current_friend_data or not self.current_user:
            return
        
        responses = [
            "That's interesting!",
            "I agree with you",
            "Tell me more about that",
            "Sounds good to me!",
            "Thanks for sharing!",
            "I'll think about it",
            "Great idea!"
        ]
        
        response_text = random.choice(responses)
        
        # Analyze sentiment of friend's response
        sentiment_info = self.sentiment_analyzer.analyze_sentiment(response_text)
        emotion_counts = self.sentiment_analyzer.analyze_emotions(response_text)
        sentiment = sentiment_info['sentiment']
        
        # Save response to database
        success = db_manager.send_message(
            int(self.current_friend_data['id']),
            self.current_user['id'], 
            response_text,
            'text',
            sentiment,
            dict(emotion_counts)
        )
        
        if success:
            response_message = {
                "id": 0,
                "sender": self.current_friend_data['id'],
                "message": response_text,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "status": "read",
                "type": "text",
                "sentiment": sentiment,
                "emotions": dict(emotion_counts)
            }
            
            # Add message bubble to UI
            chat_screen = self.root.get_screen('chat')
            messages_container = chat_screen.ids.messages_container
            bubble = MessageBubble(response_message, is_sent=False)
            messages_container.add_widget(bubble)
            
            # Scroll to bottom
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(), 0.1)
            
            # Update friends list on home screen
            Clock.schedule_once(lambda dt: self.load_friends_list_on_home(), 0.5)

    def on_message_text_change(self, text):
        """Handle message input text changes"""
        chat_screen = self.root.get_screen('chat')
        send_button = chat_screen.ids.send_voice_button
        
        if text.strip():
            send_button.icon = "send"
            # Show typing indicator to friend (in real app)
            self.show_typing_indicator()
        else:
            send_button.icon = "microphone"
            self.hide_typing_indicator()

    def show_typing_indicator(self):
        """Show typing indicator"""
        # Cancel existing timer
        if self.typing_timer:
            self.typing_timer.cancel()
        
        # Set timer to hide typing indicator after 3 seconds
        self.typing_timer = Clock.schedule_once(lambda dt: self.hide_typing_indicator(), 3)

    def hide_typing_indicator(self):
        """Hide typing indicator"""
        if self.typing_timer:
            self.typing_timer.cancel()
            self.typing_timer = None

    def send_message_or_voice(self):
        """Send message or start voice recording"""
        chat_screen = self.root.get_screen('chat')
        message_input = chat_screen.ids.message_input
        send_button = chat_screen.ids.send_voice_button
        
        if message_input.text.strip():
            self.send_message()
        else:
            # Start voice recording
            self.show_snackbar("Voice recording started... (Demo)")

    def show_attachment_options(self):
        """Show attachment options"""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Send Attachment",
                text="Choose attachment type:",
                buttons=[
                    MDFlatButton(
                        text="CAMERA",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.handle_attachment("camera")
                    ),
                    MDFlatButton(
                        text="GALLERY",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.handle_attachment("gallery")
                    ),
                    MDFlatButton(
                        text="DOCUMENT",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.handle_attachment("document")
                    ),
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog
                    ),
                ],
            )
        self.dialog.open()

    def handle_attachment(self, attachment_type):
        """Handle attachment selection"""
        self.close_dialog()
        self.show_snackbar(f"{attachment_type.title()} attachment selected (Demo)")

    def show_emoji_picker(self):
        """Show emoji picker"""
        emojis = ["😀", "😂", "😍", "🤔", "👍", "❤️", "🎉", "🔥", "💯", "🙌"]
        emoji_text = " ".join(emojis)
        
        if not self.dialog:
            self.dialog = MDDialog(
                title="Choose Emoji",
                text=emoji_text,
                buttons=[
                    MDFlatButton(
                        text="CLOSE",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog
                    ),
                ],
            )
        self.dialog.open()

    def voice_call(self):
        """Start voice call"""
        if self.current_friend_data:
            friend_name = self.current_friend_data.get('name', 'Unknown User')
            self.show_snackbar(f"Starting voice call with {friend_name}...")

    def video_call(self):
        """Start video call"""
        if self.current_friend_data:
            friend_name = self.current_friend_data.get('name', 'Unknown User')
            self.show_snackbar(f"Starting video call with {friend_name}...")

    def open_chat_menu(self, button):
        """Open chat options menu"""
        menu_items = [
            {
                "text": "View Profile",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="profile": self.chat_menu_callback("profile"),
            },
            {
                "text": "Sentiment Analysis",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="sentiment": self.chat_menu_callback("sentiment"),
            },
            {
                "text": "Media & Files",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="media": self.chat_menu_callback("media"),
            },
            {
                "text": "Clear Chat",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="clear": self.chat_menu_callback("clear"),
            },
            {
                "text": "Block Contact",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="block": self.chat_menu_callback("block"),
            }
        ]
        self.menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            width_mult=4,
        )
        self.menu.open()

    def chat_menu_callback(self, action):
        """Handle chat menu actions"""
        self.menu.dismiss()
        if self.current_friend_data:
            friend_name = self.current_friend_data.get('name', 'Unknown User')
            if action == "profile":
                self.show_snackbar(f"Viewing {friend_name}'s profile")
            elif action == "sentiment":
                self.show_sentiment_analysis_dialog()
            elif action == "media":
                self.show_snackbar("Media & Files viewer opened")
            elif action == "clear":
                self.show_snackbar("Chat cleared")
            elif action == "block":
                self.show_snackbar(f"{friend_name} blocked")

    def show_sentiment_analysis_dialog(self):
        """Show detailed sentiment analysis for the current chat"""
        if not self.current_friend_data:
            return
        
        # Get recent messages for analysis
        messages = db_manager.get_chat_messages(self.current_user['id'], int(self.current_friend_data['id']))
        
        if not messages:
            self.show_snackbar("No messages to analyze")
            return
        
        # Analyze recent messages
        recent_messages = messages[-10:]  # Last 10 messages
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for msg in recent_messages:
            sentiment = msg.get('sentiment', 'neutral')
            if sentiment == 'positive':
                positive_count += 1
            elif sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1
        
        total_messages = len(recent_messages)
        
        analysis_text = f"Chat Sentiment Analysis (Last {total_messages} messages):\n\n"
        analysis_text += f"Positive: {positive_count} ({positive_count/total_messages*100:.1f}%)\n"
        analysis_text += f"Negative: {negative_count} ({negative_count/total_messages*100:.1f}%)\n"
        analysis_text += f"Neutral: {neutral_count} ({neutral_count/total_messages*100:.1f}%)\n\n"
        
        if positive_count > negative_count:
            analysis_text += "Overall mood: Positive conversation!"
        elif negative_count > positive_count:
            analysis_text += "Overall mood: Some negative sentiment detected"
        else:
            analysis_text += "Overall mood: Balanced conversation"
        
        if not self.dialog:
            self.dialog = MDDialog(
                title="Sentiment Analysis",
                text=analysis_text,
                buttons=[
                    MDFlatButton(
                        text="CLOSE",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog
                    ),
                ],
            )
        else:
            self.dialog.text = analysis_text
            self.dialog.title = "Sentiment Analysis"
        
        self.dialog.open()

    def show_add_friend_dialog(self):
        """Show add friend dialog"""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Add Friend",
                text="Enter username or phone number to add a new friend:",
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog
                    ),
                    MDRaisedButton(
                        text="ADD",
                        on_release=self.close_dialog
                    ),
                ],
            )
        self.dialog.open()

    def handle_search_input(self, text):
        """Handle search input with filtering functionality"""
        if not self.current_user:
            return
            
        if text.strip():
            # Filter friends based on search text
            self.filter_friends_list(text.strip().lower())
            
            # Cancel any existing clear event
            if self.search_clear_event:
                self.search_clear_event.cancel()
            
            # Schedule text to be cleared after 3 seconds
            self.search_clear_event = Clock.schedule_once(
                lambda dt: self.clear_search_text(), 3.0
            )
        else:
            # Show all friends when search is empty
            self.load_friends_list_on_home()

    def filter_friends_list(self, search_text):
        """Filter friends list based on search text"""
        if not self.current_user:
            return
        
        home_screen = self.root.get_screen('home')
        friends_list_widget = home_screen.ids.home_friends_list
        
        # Clear existing friends
        friends_list_widget.clear_widgets()
        
        # Get all friends from database
        all_friends = db_manager.get_user_friends(self.current_user['id'])
        
        # Filter friends based on search text
        filtered_friends = [
            friend for friend in all_friends
            if search_text in friend.get('name', '').lower() or 
               search_text in friend.get('username', '').lower() or
               search_text in friend.get('last_message', '').lower()
        ]
        
        if not filtered_friends:
            # Show no results message
            no_results_item = OneLineAvatarIconListItem(
                text=f"No friends found matching '{search_text}'",
                disabled=True
            )
            friends_list_widget.add_widget(no_results_item)
            return
        
        # Display filtered friends
        for friend in filtered_friends:
            item = TwoLineAvatarIconListItem(
                text=str(friend.get('name', 'Unknown User')),
                secondary_text=str(friend.get('last_message', 'No messages yet')),
                on_release=lambda x, friend_data=friend: self.open_chat_from_home(friend_data)
            )
            
            # Add profile picture icon
            profile_icon = MDIcon(
                icon="account-circle",
                size_hint_x=None,
                width=(40),
                theme_icon_color="Primary"
            )
            item.add_widget(profile_icon)
            
            # Add online status indicator
            if friend.get('online_status', False):
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom",
                    icon_color=(0, 1, 0, 1),
                    size_hint_x=None,
                    width=(12),
                    pos_hint={"right": 0.95, "center_y": 0.7}
                )
            else:
                status_icon = MDIcon(
                    icon="circle",
                    theme_icon_color="Custom", 
                    icon_color=(0.5, 0.5, 0.5, 1),
                    size_hint_x=None,
                    width=(12),
                    pos_hint={"right": 0.95, "center_y": 0.7}
                )
            
            item.add_widget(status_icon)
            friends_list_widget.add_widget(item)

    def clear_search_text(self):
        """Clear the search text field"""
        try:
            screen = self.root.get_screen("home")
            search_field = screen.ids.search_input
            search_field.text = ""
            self.search_clear_event = None
            # Reload full friends list
            self.load_friends_list_on_home()
        except:
            pass

    # Settings Functions
    def toggle_two_factor(self, active):
        """Toggle two-factor authentication"""
        status = "enabled" if active else "disabled"
        self.show_snackbar(f"Two-factor authentication {status}")

    def toggle_private_account(self, active):
        """Toggle private account setting"""
        status = "enabled" if active else "disabled"
        self.show_snackbar(f"Private account {status}")

    def show_change_password_dialog(self):
        """Show change password dialog"""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Change Password",
                text="This feature will allow you to change your password securely.",
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_dialog
                    ),
                    MDRaisedButton(
                        text="CONTINUE",
                        on_release=self.close_dialog
                    ),
                ],
            )
        self.dialog.open()

    def close_dialog(self, *args):
        """Close any open dialog"""
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def clear_signin_form(self):
        """Clear all signin form fields and reset states"""
        screen = self.root.get_screen("signin")
        
        # Clear text fields
        screen.ids.login_input.text = ""
        screen.ids.password_input.text = ""
        
        # Reset error states
        screen.ids.login_input.error = False
        screen.ids.password_input.error = False
        
        # Reset helper texts
        screen.ids.login_input.helper_text = "Enter your username or email"
        screen.ids.password_input.helper_text = "Enter your password"
        
        # Hide password checkbox if visible
        container = screen.ids.password_checkbox_container
        container.height = 0
        container.opacity = 0
        
        # Reset checkbox state
        screen.ids.show_password_checkbox.active = False
        
        # Ensure password field is hidden
        screen.ids.password_input.password = True

    def clear_login_errors(self):
        """Clear error states when user starts typing"""
        screen = self.root.get_screen("signin")
        login_field = screen.ids.login_input
        password_field = screen.ids.password_input
        
        # Reset error states
        login_field.error = False
        password_field.error = False
        login_field.helper_text = "Enter your username or email"
        password_field.helper_text = "Enter your password"

    def clear_signup_errors(self):
        """Clear error states in signup form when user starts typing"""
        screen = self.root.get_screen("signup")
        username_field = screen.ids.signup_username_input
        email_field = screen.ids.signup_email_input
        name_field = screen.ids.signup_name_input
        password_field = screen.ids.signup_password
        confirm_field = screen.ids.signup_confirm_password
        
        # Reset error states
        username_field.error = False
        email_field.error = False
        name_field.error = False
        password_field.error = False
        confirm_field.error = False
        
        # Reset helper texts
        username_field.helper_text = "Enter a username (max 16 characters)"
        email_field.helper_text = "Enter a valid email (e.g., user@gmail.com)"
        name_field.helper_text = "Enter your full name"
        password_field.helper_text = "Minimum 6 characters"
        confirm_field.helper_text = "Re-enter your password"

    def validate_login_input(self):
        """Real-time validation for login input (username or email)"""
        screen = self.root.get_screen("signin")
        login_field = screen.ids.login_input
        text = login_field.text.strip()
        
        if not text:
            return
            
        # Check if it looks like an email
        if '@' in text:
            if not self.is_valid_email(text):
                login_field.error = True
                login_field.helper_text = "Invalid email format"
            else:
                login_field.error = False
                login_field.helper_text = "Enter your username or email"

    def validate_signup_username(self):
        """Real-time validation for signup username"""
        screen = self.root.get_screen("signup")
        username_field = screen.ids.signup_username_input
        text = username_field.text.strip()
        
        if not text:
            return
        
        # Basic validation - in real app, check against database
        if len(text) < 3:
            username_field.error = True
            username_field.helper_text = "Username must be at least 3 characters"
        else:
            username_field.error = False
            username_field.helper_text = "Enter a username (max 16 characters)"

    def validate_signup_email(self):
        """Real-time validation for signup email"""
        screen = self.root.get_screen("signup")
        email_field = screen.ids.signup_email_input
        text = email_field.text.strip()
        
        if not text:
            return
            
        # Check email format
        if not self.is_valid_email(text):
            email_field.error = True
            email_field.helper_text = "Invalid email format"
        else:
            email_field.error = False
            email_field.helper_text = "Enter a valid email (e.g., user@gmail.com)"

    def validate_signup_password(self):
        """Real-time validation for signup password"""
        screen = self.root.get_screen("signup")
        password_field = screen.ids.signup_password
        text = password_field.text.strip()
        
        if not text:
            return
            
        if len(text) < 6:
            password_field.error = True
            password_field.helper_text = "Password must be at least 6 characters"
        else:
            password_field.error = False
            password_field.helper_text = "Minimum 6 characters"

    def validate_signup_confirm_password(self):
        """Real-time validation for confirm password"""
        screen = self.root.get_screen("signup")
        password_field = screen.ids.signup_password
        confirm_field = screen.ids.signup_confirm_password
        
        password_text = password_field.text.strip()
        confirm_text = confirm_field.text.strip()
        
        if not confirm_text:
            return
            
        if password_text != confirm_text:
            confirm_field.error = True
            confirm_field.helper_text = "Passwords do not match"
        else:
            confirm_field.error = False
            confirm_field.helper_text = "Re-enter your password"

    def toggle_password_checkbox_visibility(self, field_type, show):
        """Toggle visibility of password checkbox based on field focus and content"""
        if field_type == 'signin':
            screen = self.root.get_screen("signin")
            container = screen.ids.password_checkbox_container
        elif field_type == 'signup_password':
            screen = self.root.get_screen("signup")
            container = screen.ids.signup_password_checkbox_container
        elif field_type == 'signup_confirm':
            screen = self.root.get_screen("signup")
            container = screen.ids.confirm_password_checkbox_container
        
        if show:
            # Show checkbox with animation
            container.height = 40
            container.opacity = 1
        else:
            # Hide checkbox with animation
            container.height = 0
            container.opacity = 0

    def login(self):
        """Login user using database authentication"""
        screen = self.root.get_screen("signin")
        identifier = screen.ids.login_input.text.strip()
        password = screen.ids.password_input.text.strip()
        
        login_field = screen.ids.login_input
        password_field = screen.ids.password_input
        
        # Reset previous errors
        self.clear_login_errors()
        
        # Check if fields are empty
        if not identifier:
            login_field.error = True
            login_field.helper_text = "Username or email is required"
            return
            
        if not password:
            password_field.error = True
            password_field.helper_text = "Password is required"
            return
        
        # If it looks like an email, validate email format
        if '@' in identifier and not self.is_valid_email(identifier):
            login_field.error = True
            login_field.helper_text = "Invalid email format"
            self.show_snackbar("Invalid email format!")
            return
        
        # Authenticate user with database
        user, message = db_manager.authenticate_user(identifier, password)
        
        if user:
            # Successful login
            self.current_user = user
            self.load_user_profile()
            self.show_snackbar("Login successful!")
            self.root.current = 'home'
        else:
            # Login failed
            if "not found" in message.lower():
                login_field.error = True
                login_field.helper_text = message
            elif "incorrect password" in message.lower():
                password_field.error = True
                password_field.helper_text = message
            else:
                login_field.error = True
                login_field.helper_text = message
            
            self.show_snackbar(message)

    def signup(self):
        """Signup user using database"""
        screen = self.root.get_screen("signup")
        username = screen.ids.signup_username_input.text.strip()
        email = screen.ids.signup_email_input.text.strip()
        name = screen.ids.signup_name_input.text.strip()
        password = screen.ids.signup_password.text.strip()
        confirm_password = screen.ids.signup_confirm_password.text.strip()
        
        username_field = screen.ids.signup_username_input
        email_field = screen.ids.signup_email_input
        name_field = screen.ids.signup_name_input
        password_field = screen.ids.signup_password
        confirm_field = screen.ids.signup_confirm_password
        
        # Reset previous errors
        self.clear_signup_errors()
        
        has_error = False
        
        # Validate all fields
        if not username:
            username_field.error = True
            username_field.helper_text = "Username is required"
            has_error = True
        elif len(username) < 3:
            username_field.error = True
            username_field.helper_text = "Username must be at least 3 characters"
            has_error = True
            
        if not email:
            email_field.error = True
            email_field.helper_text = "Email is required"
            has_error = True
        elif not self.is_valid_email(email):
            email_field.error = True
            email_field.helper_text = "Invalid email format"
            has_error = True
        
        if not name:
            name_field.error = True
            name_field.helper_text = "Full name is required"
            has_error = True
            
        if not password:
            password_field.error = True
            password_field.helper_text = "Password is required"
            has_error = True
        elif len(password) < 6:
            password_field.error = True
            password_field.helper_text = "Password must be at least 6 characters"
            has_error = True
            
        if not confirm_password:
            confirm_field.error = True
            confirm_field.helper_text = "Please confirm your password"
            has_error = True
        elif password != confirm_password:
            confirm_field.error = True
            confirm_field.helper_text = "Passwords do not match"
            has_error = True
        
        if has_error:
            return
        
        # Create user in database
        success, message = db_manager.create_user(username, email, password, name)
        
        if success:
            self.show_snackbar("Signup successful! Please login.")
            self.root.current = 'signin'
        else:
            if "username" in message.lower():
                username_field.error = True
                username_field.helper_text = message
            elif "email" in message.lower():
                email_field.error = True
                email_field.helper_text = message
            
            self.show_snackbar(message)

    def logout(self):
        """Logout user and clear signin form"""
        # Set user offline in database
        if self.current_user:
            db_manager.set_user_offline(self.current_user['id'])
        
        # Clear current user
        self.current_user = None
        self.current_friend_data = None
        
        # Clear signin form completely
        self.clear_signin_form()
        
        # Show logout message
        self.show_snackbar("Logged out successfully!")
        
        # Go to signin screen
        self.root.current = 'signin'

    def open_menu(self, button):
        menu_items = [
            {
                "text": "Profile",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="Profile": self.menu_callback("profile"),
            },
            {
                "text": "Settings",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="Settings": self.menu_callback("settings"),
            },
            {
                "text": "Logout",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="Logout": self.menu_callback("logout"),
            }
        ]
        self.menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            width_mult=3,
        )
        self.menu.open()

    def menu_callback(self, screen_name):
        self.menu.dismiss()
        if screen_name == "logout":
            self.logout()
        elif screen_name == "profile":
            self.root.current = screen_name
        elif screen_name == "settings":
            self.root.current = screen_name

    def toggle_login_password_visibility(self):
        screen = self.root.get_screen("signin")
        field = screen.ids.password_input
        checkbox = screen.ids.show_password_checkbox
        field.password = not checkbox.active

    def toggle_signup_password_visibility(self):
        screen = self.root.get_screen("signup")
        field = screen.ids.signup_password
        checkbox = screen.ids.show_signup_password_checkbox
        field.password = not checkbox.active

    def toggle_signup_confirm_password_visibility(self):
        screen = self.root.get_screen("signup")
        field = screen.ids.signup_confirm_password
        checkbox = screen.ids.show_confirm_password_checkbox
        field.password = not checkbox.active

    @staticmethod
    def is_valid_email(email):
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return re.match(pattern, email) is not None

    def toggle_photo_edit_mode(self):
        """Toggle photo edit mode"""
        screen = self.root.get_screen("profile")
        container = screen.ids.photo_edit_container
        edit_btn = screen.ids.edit_photo_btn
        
        if container.opacity == 0:
            # Show edit options
            container.height = 48
            container.opacity = 1
            edit_btn.text = "Cancel"
        else:
            # Hide edit options
            container.height = 0
            container.opacity = 0
            edit_btn.text = "Edit"

    def choose_profile_photo(self):
        """Open file picker to choose photo from D: drive"""
        try:
            # Set the path to D: drive
            d_drive_path = "D:\\"
            
            # Check if D: drive exists
            if not os.path.exists(d_drive_path):
                self.show_snackbar("D: drive not found!")
                return
            
            # Open file chooser starting from D: drive
            filechooser.open_file(
                on_selection=self.handle_photo_selection,
                path=d_drive_path,
                filters=[
                    ("Image files", "*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"),
                    ("All files", "*.*")
                ],
                title="Select Profile Photo from D: Drive"
            )
            
        except Exception as e:
            self.show_snackbar(f"Error opening file picker: {str(e)}")

    def handle_photo_selection(self, selection):
        """Handle the selected photo file"""
        if selection:
            try:
                selected_file = selection[0]
                
                # Validate that it's an image file
                valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
                if not selected_file.lower().endswith(valid_extensions):
                    self.show_snackbar("Please select a valid image file!")
                    return
                
                # Check if file exists
                if not os.path.exists(selected_file):
                    self.show_snackbar("Selected file does not exist!")
                    return
                
                # Update profile image
                screen = self.root.get_screen("profile")
                profile_image = screen.ids.profile_image
                profile_image.source = selected_file
                
                # Update current user's profile pic in database
                if self.current_user:
                    success = db_manager.update_user_profile(
                        self.current_user['id'], 
                        profile_pic=selected_file
                    )
                    if success:
                        self.current_user['profile_pic'] = selected_file
                
                self.show_snackbar(f"Profile photo updated!\nFile: {os.path.basename(selected_file)}")
                self.cancel_photo_edit()
                
            except Exception as e:
                self.show_snackbar(f"Error loading image: {str(e)}")
        else:
            self.show_snackbar("No file selected")

    def cancel_photo_edit(self):
        """Cancel photo editing"""
        screen = self.root.get_screen("profile")
        container = screen.ids.photo_edit_container
        edit_btn = screen.ids.edit_photo_btn
        
        container.height = 0
        container.opacity = 0
        edit_btn.text = "Edit"

    def open_fullscreen_photo(self):
        """Open profile photo in fullscreen view"""
        profile_screen = self.root.get_screen("profile")
        fullscreen_screen = self.root.get_screen("fullscreen_photo")
        
        # Get current profile image source
        current_image_source = profile_screen.ids.profile_image.source
        
        # Set the fullscreen image source
        fullscreen_screen.ids.fullscreen_image.source = current_image_source
        
        # Switch to fullscreen view
        self.root.current = 'fullscreen_photo'

    def close_fullscreen_photo(self):
        """Close fullscreen photo view and return to profile"""
        self.root.current = 'profile'

    def save_profile_changes(self):
        """Save profile changes to database and go to home screen"""
        screen = self.root.get_screen("profile")
        name = screen.ids.profile_name.text.strip()
        about = screen.ids.profile_about.text.strip()
        
        if not name:
            self.show_snackbar("Name cannot be empty!")
            return
        
        # Update current user data in database
        if self.current_user:
            success = db_manager.update_user_profile(
                self.current_user['id'], 
                name=name, 
                about=about
            )
            
            if success:
                self.current_user['name'] = name
                self.current_user['about'] = about
                self.show_snackbar("Profile updated successfully!")
            else:
                self.show_snackbar("Failed to update profile!")
                return
        
        # Go to home screen (which has the menu bar)
        self.root.current = 'home'

    def load_user_profile(self):
        """Load current user's profile data with proper None handling"""
        if not self.current_user:
            return
            
        screen = self.root.get_screen("profile")
        
        # Safely handle None values with proper defaults
        name = self.current_user.get('name') or ''
        about = self.current_user.get('about') or "Hey there! I'm using Chat App."
        profile_pic = self.current_user.get('profile_pic') or 'https://cdn-icons-png.flaticon.com/512/149/149071.png'
        
        # Use safe text assignment
        self.safe_text_assignment(screen.ids.profile_name, name, '')
        self.safe_text_assignment(screen.ids.profile_about, about, "Hey there! I'm using Chat App.")
        screen.ids.profile_image.source = str(profile_pic)
        
        # Auto-add friends if user has no friends
        friends = db_manager.get_user_friends(self.current_user['id'])
        if not friends:
            # Automatically add some friends for new users
            success = db_manager.auto_add_friends_for_user(self.current_user['id'])
            if success:
                self.show_snackbar("Welcome! We've added some friends for you to start chatting!")
        
        # Load friends list on home screen
        self.load_friends_list_on_home()

if __name__ == "__main__":
    ChatApp().run()
