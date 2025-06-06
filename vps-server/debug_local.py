#!/usr/bin/env python3
"""
Debug-Version für lokale Entwicklung
"""

import os
from flask import Flask, render_template

# Debug: Template-Pfad prüfen
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')

print(f"🔍 Debug-Informationen:")
print(f"Current Dir: {current_dir}")
print(f"Template Dir: {template_dir}")
print(f"Template Dir exists: {os.path.exists(template_dir)}")

if os.path.exists(template_dir):
    print(f"Templates gefunden: {os.listdir(template_dir)}")

app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def test():
    print("📍 Route '/' wurde aufgerufen")
    try:
        # Einfacher Test ohne Daten
        return render_template('dashboard.html', 
                             status={'status': 'active', 'output': 'Test'}, 
                             clients=[],
                             port_forwards={})
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Template Error</h1><p>{e}</p>"

@app.route('/port-forwards')
def port_forwards():
    print("📍 Route '/port-forwards' wurde aufgerufen")
    try:
        # Mock Port-Forwards
        mock_port_forwards = {
            '8080_tcp': {
                'external_port': 8080,
                'internal_ip': '10.0.0.100',
                'internal_port': 80,
                'protocol': 'tcp',
                'created': '2024-01-15T10:30:00'
            },
            '2222_tcp': {
                'external_port': 2222,
                'internal_ip': '10.0.0.101',
                'internal_port': 22,
                'protocol': 'tcp',
                'created': '2024-01-15T11:45:00'
            }
        }
        return render_template('port_forwards.html', port_forwards=mock_port_forwards)
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Template Error</h1><p>{e}</p>"

@app.route('/test')
def simple_test():
    return "<h1>Flask funktioniert!</h1><p>Einfacher HTML-Test</p>"

if __name__ == '__main__':
    print("\n🚀 Debug-Server startet...")
    print("Test-URL: http://localhost:5000/test")
    print("Dashboard: http://localhost:5000/")
    app.run(host='localhost', port=5000, debug=True)