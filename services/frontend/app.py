#!/usr/bin/env python3
"""
CIVA Frontend Server
Serves HTML dashboards and integrates with backend APIs
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configuration
BEHAVIOR_AGENT_URL = os.getenv('BEHAVIOR_AGENT_URL', 'http://localhost:8002')
ORCHESTRATOR_URL = os.getenv('ORCHESTRATOR_URL', 'http://localhost:8003')
DECEPTION_AGENT_URL = os.getenv('DECEPTION_AGENT_URL', 'http://localhost:8004')
THREAT_INTEL_URL = os.getenv('THREAT_INTEL_URL', 'http://localhost:8005')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')

FRONTEND_DIR = Path(__file__).parent.parent.parent / 'figma frontend' / 'stitch'

# Routes
@app.route('/')
def command_center():
    """Main command center dashboard"""
    return render_template_from_folder('civa_main_command_center')

@app.route('/sentinel')
def sentinel():
    """Sentinel behavior analytics"""
    return render_template_from_folder('civa_sentinel')

@app.route('/deception')
def deception():
    """Deception dashboard"""
    return render_template_from_folder('deception_dashboard')

@app.route('/threat-intel')
def threat_intel():
    """Threat intelligence forensics"""
    return render_template_from_folder('threat_intel_forensics_archive')

@app.route('/audit-logs')
def audit_logs():
    """Audit logs"""
    return render_template_from_folder('audit_logs')

@app.route('/admin')
def admin():
    """Global admin dashboard"""
    return render_template_from_folder('global_admin_dashboard')

@app.route('/settings')
def settings():
    """System settings"""
    return render_template_from_folder('system_settings')

@app.route('/orchestrator')
def orchestrator():
    """Active deception orchestrator"""
    return render_template_from_folder('orchestrator_active_deception')

@app.route('/analytics')
def analytics():
    """Behavior analytics"""
    return render_template_from_folder('sentinel_behavior_analytics')

# API Proxy Routes
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        behavior_health = requests.get(f'{BEHAVIOR_AGENT_URL}/health', timeout=2).json()
        orchestrator_health = requests.get(f'{ORCHESTRATOR_URL}/health', timeout=2).json()
        return jsonify({
            'status': 'healthy',
            'services': {
                'behavior_agent': behavior_health.get('status', 'unknown'),
                'orchestrator': orchestrator_health.get('status', 'unknown'),
                'frontend': 'healthy'
            }
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

@app.route('/api/score', methods=['POST'])
def score():
    """Proxy to behavior agent scoring endpoint"""
    try:
        data = request.json
        response = requests.post(f'{BEHAVIOR_AGENT_URL}/score', json=data, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decide', methods=['POST'])
def decide():
    """Proxy to orchestrator decision endpoint"""
    try:
        data = request.json
        response = requests.post(f'{ORCHESTRATOR_URL}/decide', json=data, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def metrics():
    """Proxy Prometheus metrics"""
    try:
        query = request.args.get('query', 'behavior_agent_risk_score')
        response = requests.get(
            f'{PROMETHEUS_URL}/api/v1/query',
            params={'query': query},
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session data from orchestrator"""
    try:
        response = requests.get(f'{ORCHESTRATOR_URL}/session/{session_id}', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper function
def render_template_from_folder(folder_name):
    """Serve HTML from figma frontend folder"""
    html_file = FRONTEND_DIR / folder_name / 'code.html'
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return f"<h1>Dashboard not found: {folder_name}</h1>", 404

@app.route('/list-dashboards')
def list_dashboards():
    """List all available dashboards"""
    dashboards = [
        {'name': 'Command Center', 'url': '/', 'icon': '🎛️'},
        {'name': 'Sentinel Analytics', 'url': '/sentinel', 'icon': '🔍'},
        {'name': 'Deception Dashboard', 'url': '/deception', 'icon': '🪤'},
        {'name': 'Threat Intelligence', 'url': '/threat-intel', 'icon': '📊'},
        {'name': 'Audit Logs', 'url': '/audit-logs', 'icon': '📋'},
        {'name': 'Admin Dashboard', 'url': '/admin', 'icon': '⚙️'},
        {'name': 'System Settings', 'url': '/settings', 'icon': '🔧'},
        {'name': 'Orchestrator', 'url': '/orchestrator', 'icon': '⚙️'},
        {'name': 'Analytics', 'url': '/analytics', 'icon': '📈'},
    ]
    return jsonify(dashboards)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
