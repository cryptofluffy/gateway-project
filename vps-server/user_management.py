#!/usr/bin/env python3
"""
Benutzer-Management System für VPN Gateway Pro
Vollständiges System mit SQLite-Datenbank, Authentifizierung und Rollen
"""

import sqlite3
import hashlib
import secrets
import datetime
import jwt
from functools import wraps
from flask import Flask, request, jsonify, session, redirect, url_for, render_template

class UserDatabase:
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Datenbankverbindung herstellen"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Zugriff auf Spalten per Name
        return conn
    
    def init_database(self):
        """Datenbank-Schema initialisieren"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Benutzer-Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                two_factor_secret TEXT,
                two_factor_enabled BOOLEAN DEFAULT 0
            )
        ''')
        
        # Sessions-Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Lizenz-Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                license_key TEXT UNIQUE NOT NULL,
                license_type TEXT NOT NULL,
                gateway_limit INTEGER DEFAULT 1,
                client_limit INTEGER DEFAULT 50,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Audit-Log-Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Standard-Admin erstellen falls noch nicht vorhanden
        self.create_default_admin()
    
    def create_default_admin(self):
        """Standard-Administrator erstellen"""
        try:
            admin_exists = self.get_user_by_username('admin')
            if not admin_exists:
                self.create_user(
                    username='admin',
                    email='admin@vpngateway.local',
                    password='admin123',  # Sollte nach erstem Login geändert werden
                    role='admin'
                )
                print("✅ Standard-Admin erstellt: admin / admin123")
        except:
            pass
    
    def hash_password(self, password, salt=None):
        """Passwort sicher hashen"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # PBKDF2 mit SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100k Iterationen
        )
        
        return password_hash.hex(), salt
    
    def verify_password(self, password, password_hash, salt):
        """Passwort verifizieren"""
        hash_to_check, _ = self.hash_password(password, salt)
        return hash_to_check == password_hash
    
    def create_user(self, username, email, password, role='user'):
        """Neuen Benutzer erstellen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Passwort hashen
            password_hash, salt = self.hash_password(password)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, salt, role))
            
            user_id = cursor.lastrowid
            
            conn.commit()
            
            # Audit-Log nach commit
            self.log_action(user_id, 'USER_CREATED', f'User {username} created')
            
            return user_id
            
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                raise ValueError("Benutzername bereits vergeben")
            elif 'email' in str(e):
                raise ValueError("E-Mail bereits registriert")
            else:
                raise ValueError("Benutzer konnte nicht erstellt werden")
        finally:
            conn.close()
    
    def authenticate_user(self, username, password, ip_address=None):
        """Benutzer authentifizieren"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Benutzer suchen
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, role, is_active,
                       failed_login_attempts, locked_until
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            
            user = cursor.fetchone()
            
            if not user:
                self.log_action(None, 'LOGIN_FAILED', f'Unknown user: {username}', ip_address)
                return None
            
            # Account-Sperrung prüfen
            if user['locked_until'] and datetime.datetime.now() < datetime.datetime.fromisoformat(user['locked_until']):
                self.log_action(user['id'], 'LOGIN_BLOCKED', 'Account locked', ip_address)
                raise ValueError("Account ist temporär gesperrt")
            
            # Aktiv-Status prüfen
            if not user['is_active']:
                self.log_action(user['id'], 'LOGIN_FAILED', 'Account deactivated', ip_address)
                raise ValueError("Account ist deaktiviert")
            
            # Passwort prüfen
            if self.verify_password(password, user['password_hash'], user['salt']):
                # Erfolgreiche Anmeldung
                cursor.execute('''
                    UPDATE users SET 
                        last_login = CURRENT_TIMESTAMP,
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE id = ?
                ''', (user['id'],))
                
                conn.commit()
                self.log_action(user['id'], 'LOGIN_SUCCESS', 'Successful login', ip_address)
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            else:
                # Fehlgeschlagene Anmeldung
                failed_attempts = user['failed_login_attempts'] + 1
                locked_until = None
                
                # Account sperren nach 5 Fehlversuchen
                if failed_attempts >= 5:
                    locked_until = (datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat()
                
                cursor.execute('''
                    UPDATE users SET 
                        failed_login_attempts = ?,
                        locked_until = ?
                    WHERE id = ?
                ''', (failed_attempts, locked_until, user['id']))
                
                conn.commit()
                self.log_action(user['id'], 'LOGIN_FAILED', f'Wrong password (attempt {failed_attempts})', ip_address)
                
                return None
                
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Benutzer per ID laden"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def get_user_by_username(self, username):
        """Benutzer per Benutzername laden"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def update_user(self, user_id, **kwargs):
        """Benutzer aktualisieren"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['email', 'role', 'is_active']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f'{field} = ?')
                values.append(value)
        
        if updates:
            values.append(user_id)
            cursor.execute(f'''
                UPDATE users SET {', '.join(updates)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
            self.log_action(user_id, 'USER_UPDATED', f'Updated: {", ".join(updates)}')
        
        conn.close()
    
    def change_password(self, user_id, old_password, new_password):
        """Passwort ändern"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Aktuelles Passwort prüfen
        cursor.execute('''
            SELECT password_hash, salt FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        if not user:
            raise ValueError("Benutzer nicht gefunden")
        
        if not self.verify_password(old_password, user['password_hash'], user['salt']):
            raise ValueError("Aktuelles Passwort ist falsch")
        
        # Neues Passwort setzen
        new_hash, new_salt = self.hash_password(new_password)
        cursor.execute('''
            UPDATE users SET password_hash = ?, salt = ?
            WHERE id = ?
        ''', (new_hash, new_salt, user_id))
        
        conn.commit()
        conn.close()
        
        self.log_action(user_id, 'PASSWORD_CHANGED', 'Password changed successfully')
    
    def create_session(self, user_id, ip_address=None, user_agent=None):
        """Session erstellen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Session-Token generieren
        session_token = secrets.token_urlsafe(32)
        expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
        
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, session_token, ip_address, user_agent, expires_at))
        
        conn.commit()
        conn.close()
        
        return session_token
    
    def validate_session(self, session_token):
        """Session validieren"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.user_id, s.expires_at, u.username, u.role, u.is_active
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.is_active = 1
        ''', (session_token,))
        
        session = cursor.fetchone()
        conn.close()
        
        if not session:
            return None
        
        # Ablaufzeit prüfen
        if datetime.datetime.now() > datetime.datetime.fromisoformat(session['expires_at']):
            self.invalidate_session(session_token)
            return None
        
        # Benutzer aktiv?
        if not session['is_active']:
            return None
        
        return {
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        }
    
    def invalidate_session(self, session_token):
        """Session invalidieren"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_sessions SET is_active = 0
            WHERE session_token = ?
        ''', (session_token,))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        """Alle Benutzer laden (für Admin)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users ORDER BY created_at DESC
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return users
    
    def log_action(self, user_id, action, details=None, ip_address=None):
        """Audit-Log Eintrag erstellen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action, details, ip_address))
        
        conn.commit()
        conn.close()
    
    def get_audit_log(self, user_id=None, limit=100):
        """Audit-Log abrufen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT al.*, u.username
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE al.user_id = ?
                ORDER BY al.timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT al.*, u.username
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.id
                ORDER BY al.timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return logs


class UserAuth:
    def __init__(self, user_db, secret_key):
        self.user_db = user_db
        self.secret_key = secret_key
    
    def require_auth(self, required_role=None):
        """Decorator für Authentifizierung"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Session-Token aus Header oder Cookie
                token = request.headers.get('Authorization')
                if token and token.startswith('Bearer '):
                    token = token[7:]
                elif 'session_token' in request.cookies:
                    token = request.cookies['session_token']
                else:
                    return jsonify({'error': 'Authentication required'}), 401
                
                # Session validieren
                session_data = self.user_db.validate_session(token)
                if not session_data:
                    return jsonify({'error': 'Invalid or expired session'}), 401
                
                # Rolle prüfen
                if required_role and session_data['role'] != required_role and session_data['role'] != 'admin':
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                # Benutzer-Daten zur Anfrage hinzufügen
                request.current_user = session_data
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def generate_jwt(self, user_data):
        """JWT Token generieren"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt(self, token):
        """JWT Token verifizieren"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


if __name__ == "__main__":
    # Test des Benutzer-Systems
    print("🔧 Initialisiere Benutzer-Datenbank...")
    
    user_db = UserDatabase()
    
    print("✅ Benutzer-System initialisiert")
    print("📊 Standard-Admin: admin / admin123")
    
    # Test-Benutzer erstellen
    try:
        user_db.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='user'
        )
        print("✅ Test-Benutzer erstellt: testuser / testpass123")
    except ValueError as e:
        print(f"ℹ️  Test-Benutzer existiert bereits: {e}")
    
    # Authentifizierung testen
    print("\n🔐 Teste Authentifizierung...")
    user = user_db.authenticate_user('admin', 'admin123', '127.0.0.1')
    if user:
        print(f"✅ Login erfolgreich: {user['username']} ({user['role']})")
        
        # Session erstellen
        token = user_db.create_session(user['id'], '127.0.0.1')
        print(f"🎫 Session-Token: {token[:20]}...")
        
        # Session validieren
        session = user_db.validate_session(token)
        if session:
            print(f"✅ Session gültig: {session['username']}")
    
    print("\n📋 Alle Benutzer:")
    users = user_db.get_all_users()
    for user in users:
        print(f"  - {user['username']} ({user['role']}) - {user['email']}")