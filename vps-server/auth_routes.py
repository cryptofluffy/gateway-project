#!/usr/bin/env python3
"""
Authentifizierungs-Routes für VPN Gateway Pro
Erweitert das bestehende Flask-App um Benutzer-Management
"""

from flask import request, jsonify, render_template, redirect, url_for, session, make_response
from functools import wraps
import secrets
from user_management import UserDatabase, UserAuth

class AuthRoutes:
    def __init__(self, app, secret_key=None):
        self.app = app
        self.secret_key = secret_key or secrets.token_hex(32)
        
        # Benutzer-Datenbank initialisieren
        self.user_db = UserDatabase()
        self.auth = UserAuth(self.user_db, self.secret_key)
        
        # Routes registrieren
        self.register_routes()
    
    def register_routes(self):
        """Alle Auth-Routes registrieren"""
        
        # Login-Seite
        @self.app.route('/login')
        def login_page():
            return render_template('login.html')
        
        # Login API
        @self.app.route('/api/auth/login', methods=['POST'])
        def api_login():
            try:
                data = request.get_json()
                username = data.get('username', '').strip()
                password = data.get('password', '')
                remember = data.get('remember', False)
                ip_address = data.get('ip_address', request.remote_addr)
                user_agent = data.get('user_agent', request.headers.get('User-Agent'))
                
                if not username or not password:
                    return jsonify({'error': 'Benutzername und Passwort erforderlich'}), 400
                
                # Authentifizierung
                user = self.user_db.authenticate_user(username, password, ip_address)
                
                if user:
                    # Session erstellen
                    session_token = self.user_db.create_session(
                        user['id'], 
                        ip_address, 
                        user_agent
                    )
                    
                    # Response mit Cookie
                    response = make_response(jsonify({
                        'success': True,
                        'message': 'Anmeldung erfolgreich',
                        'user': user,
                        'session_token': session_token,
                        'redirect_url': '/admin/users' if user['role'] == 'admin' else '/'
                    }))
                    
                    # Session-Cookie setzen
                    cookie_kwargs = {
                        'httponly': True,
                        'secure': request.is_secure,
                        'samesite': 'Lax'
                    }
                    
                    if remember:
                        cookie_kwargs['max_age'] = 30 * 24 * 60 * 60  # 30 Tage
                    
                    response.set_cookie('session_token', session_token, **cookie_kwargs)
                    
                    return response
                else:
                    return jsonify({'error': 'Ungültige Anmeldedaten'}), 401
                    
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.app.logger.error(f"Login error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Logout API
        @self.app.route('/api/auth/logout', methods=['POST', 'GET'])
        def api_logout():
            # Session-Token aus Cookie oder Header
            session_token = request.cookies.get('session_token')
            if not session_token:
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    session_token = auth_header[7:]
            
            if session_token:
                self.user_db.invalidate_session(session_token)
            
            response = make_response(redirect('/login') if request.method == 'GET' 
                                   else jsonify({'success': True, 'message': 'Erfolgreich abgemeldet'}))
            response.set_cookie('session_token', '', expires=0)
            
            return response
        
        # Session-Info API
        @self.app.route('/api/auth/me')
        @self.auth.require_auth()
        def api_current_user():
            user_data = self.user_db.get_user_by_id(request.current_user['user_id'])
            return jsonify({
                'success': True,
                'user': user_data
            })
        
        # Client IP API (für Login-Logs)
        @self.app.route('/api/client-ip')
        def api_client_ip():
            return jsonify({'ip': request.remote_addr})
        
        # Admin-Routes
        @self.app.route('/admin/users')
        @self.auth.require_auth('admin')
        def admin_users_page():
            return render_template('admin_users.html')
        
        # Admin API - Alle Benutzer
        @self.app.route('/api/admin/users')
        @self.auth.require_auth('admin')
        def api_admin_get_users():
            users = self.user_db.get_all_users()
            return jsonify(users)
        
        # Admin API - Benutzer erstellen
        @self.app.route('/api/admin/users', methods=['POST'])
        @self.auth.require_auth('admin')
        def api_admin_create_user():
            try:
                data = request.get_json()
                
                required_fields = ['username', 'email', 'password', 'role']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({'error': f'{field} ist erforderlich'}), 400
                
                user_id = self.user_db.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data['password'],
                    role=data['role']
                )
                
                # Status setzen falls angegeben
                if 'is_active' in data:
                    self.user_db.update_user(user_id, is_active=data['is_active'])
                
                # Audit-Log
                self.user_db.log_action(
                    request.current_user['user_id'],
                    'ADMIN_USER_CREATED',
                    f'Created user: {data["username"]}',
                    request.remote_addr
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Benutzer erfolgreich erstellt',
                    'user_id': user_id
                })
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.app.logger.error(f"Create user error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Admin API - Benutzer aktualisieren
        @self.app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
        @self.auth.require_auth('admin')
        def api_admin_update_user(user_id):
            try:
                data = request.get_json()
                
                # Nicht erlaubte Felder entfernen
                allowed_fields = ['email', 'role', 'is_active']
                update_data = {k: v for k, v in data.items() if k in allowed_fields}
                
                if update_data:
                    self.user_db.update_user(user_id, **update_data)
                    
                    # Audit-Log
                    self.user_db.log_action(
                        request.current_user['user_id'],
                        'ADMIN_USER_UPDATED',
                        f'Updated user {user_id}: {list(update_data.keys())}',
                        request.remote_addr
                    )
                
                return jsonify({
                    'success': True,
                    'message': 'Benutzer erfolgreich aktualisiert'
                })
                
            except Exception as e:
                self.app.logger.error(f"Update user error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Admin API - Benutzer löschen
        @self.app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
        @self.auth.require_auth('admin')
        def api_admin_delete_user(user_id):
            try:
                # Prüfen ob Benutzer existiert
                user = self.user_db.get_user_by_id(user_id)
                if not user:
                    return jsonify({'error': 'Benutzer nicht gefunden'}), 404
                
                # Sich selbst nicht löschen
                if user_id == request.current_user['user_id']:
                    return jsonify({'error': 'Sie können sich nicht selbst löschen'}), 400
                
                # Benutzer deaktivieren statt löschen (Soft Delete)
                self.user_db.update_user(user_id, is_active=False)
                
                # Alle Sessions invalidieren
                # TODO: Implementierung für alle Sessions eines Benutzers
                
                # Audit-Log
                self.user_db.log_action(
                    request.current_user['user_id'],
                    'ADMIN_USER_DELETED',
                    f'Deleted user: {user["username"]}',
                    request.remote_addr
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Benutzer erfolgreich gelöscht'
                })
                
            except Exception as e:
                self.app.logger.error(f"Delete user error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Admin API - Passwort zurücksetzen
        @self.app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
        @self.auth.require_auth('admin')
        def api_admin_reset_password(user_id):
            try:
                data = request.get_json()
                new_password = data.get('new_password')
                
                if not new_password:
                    return jsonify({'error': 'Neues Passwort erforderlich'}), 400
                
                if len(new_password) < 6:
                    return jsonify({'error': 'Passwort muss mindestens 6 Zeichen lang sein'}), 400
                
                # Benutzer existiert?
                user = self.user_db.get_user_by_id(user_id)
                if not user:
                    return jsonify({'error': 'Benutzer nicht gefunden'}), 404
                
                # Passwort direkt setzen (Admin-Berechtigung)
                password_hash, salt = self.user_db.hash_password(new_password)
                
                conn = self.user_db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET password_hash = ?, salt = ?
                    WHERE id = ?
                ''', (password_hash, salt, user_id))
                conn.commit()
                conn.close()
                
                # Audit-Log
                self.user_db.log_action(
                    request.current_user['user_id'],
                    'ADMIN_PASSWORD_RESET',
                    f'Reset password for user: {user["username"]}',
                    request.remote_addr
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Passwort erfolgreich zurückgesetzt'
                })
                
            except Exception as e:
                self.app.logger.error(f"Reset password error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Admin API - Audit-Log
        @self.app.route('/api/admin/audit-log')
        @self.auth.require_auth('admin')
        def api_admin_audit_log():
            try:
                limit = request.args.get('limit', 100, type=int)
                user_id = request.args.get('user_id', type=int)
                
                logs = self.user_db.get_audit_log(user_id, limit)
                
                return jsonify({
                    'success': True,
                    'logs': logs
                })
                
            except Exception as e:
                self.app.logger.error(f"Audit log error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Passwort ändern (für eingeloggte Benutzer)
        @self.app.route('/api/auth/change-password', methods=['POST'])
        @self.auth.require_auth()
        def api_change_password():
            try:
                data = request.get_json()
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                
                if not old_password or not new_password:
                    return jsonify({'error': 'Altes und neues Passwort erforderlich'}), 400
                
                if len(new_password) < 6:
                    return jsonify({'error': 'Neues Passwort muss mindestens 6 Zeichen lang sein'}), 400
                
                self.user_db.change_password(
                    request.current_user['user_id'],
                    old_password,
                    new_password
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Passwort erfolgreich geändert'
                })
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.app.logger.error(f"Change password error: {e}")
                return jsonify({'error': 'Interner Serverfehler'}), 500
        
        # Dashboard-Schutz (Original-Route erweitern)
        original_dashboard = None
        for rule in self.app.url_map.iter_rules():
            if rule.endpoint == 'dashboard' and rule.rule == '/':
                original_dashboard = self.app.view_functions[rule.endpoint]
                break
        
        if original_dashboard:
            @self.app.route('/')
            @self.auth.require_auth()
            def protected_dashboard():
                return original_dashboard()


def init_auth(app):
    """Authentifizierung zur Flask-App hinzufügen"""
    auth_routes = AuthRoutes(app)
    
    # Middleware für Session-Validierung
    @app.before_request
    def validate_session():
        # Pfade die keine Authentifizierung benötigen
        public_paths = ['/login', '/api/auth/login', '/api/client-ip', '/static']
        
        if any(request.path.startswith(path) for path in public_paths):
            return
        
        # Session-Token prüfen
        session_token = request.cookies.get('session_token')
        if not session_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if session_token:
            session_data = auth_routes.user_db.validate_session(session_token)
            if session_data:
                request.current_user = session_data
                return
        
        # Umleitung zu Login für HTML-Requests
        if request.path != '/login' and 'text/html' in request.headers.get('Accept', ''):
            return redirect('/login')
        
        # 401 für API-Requests
        return jsonify({'error': 'Authentication required'}), 401
    
    return auth_routes


if __name__ == "__main__":
    # Test der Auth-Routes
    from flask import Flask
    
    app = Flask(__name__)
    app.secret_key = 'test-secret-key'
    
    # Auth initialisieren
    auth = init_auth(app)
    
    print("✅ Auth-System initialisiert")
    print("🔐 Login: http://localhost:5000/login")
    print("👥 Admin: http://localhost:5000/admin/users")
    
    app.run(debug=True, port=5000)