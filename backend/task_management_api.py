"""
Task Management API Cloud Function
Handles HTTP requests for task CRUD operations
"""

import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from task_api import create_user_task, get_user_tasks, delete_user_task, toggle_task_active

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/create-task', methods=['POST'])
def create_task_endpoint():
    """Create a new monitoring task"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        result = create_user_task(request_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/user-tasks', methods=['GET'])
def get_tasks_endpoint():
    """Get all tasks for a user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id parameter required'}), 400
        
        tasks = get_user_tasks(user_id)
        return jsonify({'success': True, 'tasks': tasks})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete-task', methods=['DELETE'])
def delete_task_endpoint():
    """Delete a user task"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        task_id = request_data.get('task_id')
        user_id = request_data.get('user_id')
        
        if not task_id or not user_id:
            return jsonify({'success': False, 'message': 'task_id and user_id required'}), 400
        
        success = delete_user_task(task_id, user_id)
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/toggle-task', methods=['PUT'])
def toggle_task_endpoint():
    """Toggle task active status"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        task_id = request_data.get('task_id')
        user_id = request_data.get('user_id')
        is_active = request_data.get('is_active')
        
        if not all([task_id, user_id, is_active is not None]):
            return jsonify({'success': False, 'message': 'task_id, user_id, and is_active required'}), 400
        
        success = toggle_task_active(task_id, user_id, is_active)
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/task-status/<task_id>', methods=['GET', 'OPTIONS'])
def get_task_status_endpoint(task_id):
    """Get real-time status of a specific task"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from task_api import get_task_status
        status = get_task_status(task_id)
        return jsonify({'success': True, 'status': status})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'task-management-api'})

def task_management_api(request):
    """
    Cloud Function entry point for task management API
    """
    # Create a simple request context for Cloud Functions
    from flask import request as flask_request
    
    # Set up the request context manually
    with app.request_context(request.environ):
        return app.full_dispatch_request()

if __name__ == '__main__':
    app.run(debug=True)
