"""
Task Management API for Craigslist Bot
Handles user task creation, management, and scheduling
"""

import os
import json
import time
from typing import Dict, List, Optional
from google.cloud import firestore
from google.cloud import scheduler_v1
from google.protobuf import duration_pb2
import requests

# Initialize Firestore client
db = firestore.Client()

# Cloud Scheduler client
scheduler_client = scheduler_v1.CloudSchedulerClient()

# Environment variables
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'heroic-glyph-473602-q8')
REGION = os.getenv('GCP_REGION', 'us-central1')
CLOUD_FUNCTION_URL = os.getenv('CLOUD_FUNCTION_URL', 
    'https://us-central1-heroic-glyph-473602-q8.cloudfunctions.net/craigslist-bot-entry-point')

def create_user_task(request_data: Dict) -> Dict:
    """
    Create a new monitoring task for a user
    
    Args:
        request_data: Dictionary containing task configuration
        
    Returns:
        Dictionary with success status and task details
    """
    try:
        user_id = request_data.get('user_id')
        user_email = request_data.get('user_email', '')
        config = request_data.get('config', {})
        discord_webhook_url = request_data.get('discord_webhook_url')
        frequency_minutes = request_data.get('frequency_minutes', 120)
        task_name = request_data.get('task_name', 'Untitled Task')
        immediate_scraping = request_data.get('immediate_scraping', True)
        enable_initial_scrape = request_data.get('enable_initial_scrape', True)
        initial_scrape_count = request_data.get('initial_scrape_count', 6)
        
        if not user_id or not config or not discord_webhook_url:
            return {
                'success': False,
                'message': 'Missing required fields: user_id, config, discord_webhook_url'
            }
        
        # Generate task ID
        task_id = f"{user_id}_{int(time.time())}"
        
        # Create task document
        current_time = time.time()
        initial_cooldown = current_time + (frequency_minutes * 60)
        task_doc = {
            'id': task_id,
            'user_id': user_id,
            'user_email': user_email,
            'name': task_name,
            'description': config.get('search_query', ''),
            'location': config.get('location', ''),
            'distance': config.get('distance', 15),
            'frequency_minutes': frequency_minutes,
            'discord_webhook_url': discord_webhook_url,
            'strictness': config.get('strictness', 'strict'),
            'enable_initial_scrape': enable_initial_scrape,
            'initial_scrape_count': initial_scrape_count,
            'is_active': True,
            'search_hash': None,  # Will be set by main.py on first run
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(current_time)),
            'last_run': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(current_time)),  # Set initial last_run to now
            'next_cooldown': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(initial_cooldown)),  # Set initial cooldown
            'total_runs': 0,
            'total_scrapes': 0,
            'total_matches': 0,
            'logs': [
                {
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'message': 'Task created successfully',
                    'level': 'success',
                    'details': f'Task "{task_name}" created with {frequency_minutes} minute frequency'
                }
            ]
        }
        
        # Save to Firestore
        db.collection('user_tasks').document(task_id).set(task_doc)
        
        # Create Cloud Scheduler job
        job_name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/craigslist-bot-{task_id}"
        parent = f"projects/{PROJECT_ID}/locations/{REGION}"
        
        # Construct payload for Cloud Function
        function_payload = {
            "user_id": user_id,
            "task_id": task_id,
            "config": config,
            "discord_webhook_url": discord_webhook_url,
            "enable_initial_scrape": enable_initial_scrape,
            "initial_scrape_count": initial_scrape_count
        }
        
        # Cloud Scheduler cron format: "*/X * * * *" for every X minutes
        # Support frequencies as low as 2 minutes for testing
        min_frequency = 2  # 2 minutes minimum for testing
        if frequency_minutes < min_frequency:
            frequency_minutes = min_frequency
        
        # Generate cron schedule based on frequency
        if frequency_minutes < 60:
            # For frequencies less than 1 hour, use minute-based schedule
            cron_schedule = f"*/{frequency_minutes} * * * *"
        elif frequency_minutes == 60:
            # Exactly 1 hour
            cron_schedule = "0 * * * *"
        elif frequency_minutes < 1440:  # Less than 24 hours
            # For frequencies less than 24 hours, use hour-based schedule
            hours = frequency_minutes // 60
            cron_schedule = f"0 */{hours} * * *"
        else:
            # 24 hours or more - use daily schedule
            days = frequency_minutes // 1440
            if days == 1:
                cron_schedule = "0 0 * * *"  # Daily at midnight
            else:
                cron_schedule = f"0 0 */{days} * *"  # Every N days at midnight
        
        job = scheduler_v1.Job(
            name=job_name,
            description=f"Craigslist Bot for task {task_name}",
            schedule=cron_schedule,
            time_zone="America/Los_Angeles",
            http_target=scheduler_v1.HttpTarget(
                uri=CLOUD_FUNCTION_URL,
                http_method=scheduler_v1.HttpMethod.POST,
                headers={"Content-Type": "application/json"},
                body=json.dumps(function_payload).encode('utf-8')
            )
        )
        
        # Create the scheduler job
        response = scheduler_client.create_job(parent=parent, job=job)
        
        # If immediate scraping is enabled, pause the scheduler job temporarily
        # to prevent duplicate runs, then resume it after the initial scrape
        if immediate_scraping and enable_initial_scrape:
            print(f"Pausing scheduler job temporarily to prevent duplicate initial run")
            try:
                # Pause the job immediately after creation
                scheduler_client.pause_job(name=job_name)
                print(f"Scheduler job paused successfully")
            except Exception as e:
                print(f"Warning: Could not pause scheduler job: {e}")
        
        # Perform immediate scraping if requested (async)
        initial_scraping_results = None
        if immediate_scraping and enable_initial_scrape:
            print(f"Starting immediate scraping for task {task_id}")
            
            # Add log entry for immediate scraping start
            # For initial scrape, use run count 0
            scraping_log = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'message': 'Scrape: 0 - Starting immediate scraping',
                'level': 'info',
                'details': f'Searching for: {config.get("search_query", "")}'
            }
            
            # Update task with initial scraping log immediately
            task_ref = db.collection('user_tasks').document(task_id)
            task_ref.update({
                'logs': firestore.ArrayUnion([scraping_log])
            })
            
            # Start scraping in background (don't wait for completion)
            import threading
            def background_scraping():
                # Get task_ref inside the function scope
                task_ref = db.collection('user_tasks').document(task_id)
                import time  # Import time module for timestamp generation
                try:
                    # Call the deployed Cloud Function
                    import requests
                    
                    function_url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/craigslist-bot-entry-point"
                    print(f"Calling deployed function: {function_url}")
                    
                    # Add initial scrape configuration to payload
                    scraping_payload = function_payload.copy()
                    scraping_payload['is_initial_scrape'] = True
                    scraping_payload['initial_scrape_count'] = initial_scrape_count
                    
                    response = requests.post(function_url, json=scraping_payload, timeout=300)
                    print(f"Function response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                    else:
                        result = {
                            'statusCode': response.status_code,
                            'body': {'error': f'Function call failed: {response.text}'}
                        }
                    
                    print(f"Immediate scraping result: {result}")
                    
                    # Parse results for initial scraping
                    if isinstance(result, dict) and result.get('statusCode') == 200:
                        body = result.get('body', {})
                        if isinstance(body, dict):
                            initial_scraping_results = {
                                'totalListings': body.get('total_listings', 0),
                                'matchesFound': body.get('recommended_listings', 0),
                                'sampleListings': body.get('sample_listings', [])
                            }
                            print(f"Initial scraping successful: {initial_scraping_results}")
                            
                            # Add success log with appropriate message
                            if initial_scraping_results["totalListings"] == 0:
                                success_log = {
                                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                    'message': 'Scrape: 0 - No posts found',
                                    'level': 'success',
                                    'details': 'No listings found matching search criteria'
                                }
                            elif initial_scraping_results["matchesFound"] == 0:
                                success_log = {
                                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                    'message': f'Scrape: {initial_scraping_results["totalListings"]} - No posts found',
                                    'level': 'success',
                                    'details': f'Scraped {initial_scraping_results["totalListings"]} listings, but none met the threshold'
                                }
                            else:
                                success_log = {
                                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                    'message': f'Scrape: {initial_scraping_results["totalListings"]} - Found {initial_scraping_results["matchesFound"]} matches',
                                    'level': 'success',
                                    'details': f'Total scraped: {initial_scraping_results["totalListings"]}, Matches: {initial_scraping_results["matchesFound"]}'
                                }
                            
                            # Note: Log entry will be added by the main bot function via update_task_stats
                            # No need to add duplicate log here
                            
                            # Resume the scheduler job after successful initial scraping
                            # Add a delay to ensure the initial scrape is fully processed
                            import time
                            time.sleep(5)  # Wait 5 seconds before resuming scheduler
                            try:
                                print(f"Resuming scheduler job after successful initial scrape")
                                scheduler_client.resume_job(name=job_name)
                                print(f"Scheduler job resumed successfully")
                            except Exception as e:
                                print(f"Warning: Could not resume scheduler job: {e}")
                        else:
                            success_log = {
                                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                'message': 'Scrape: 0 - Failed - invalid response body',
                                'level': 'error',
                                'details': str(body)
                            }
                            # Note: Log entry will be added by the main bot function via update_task_stats
                            # No need to add duplicate log here
                            
                            # Resume the scheduler job even after failed initial scraping
                            # Add a delay to ensure the initial scrape is fully processed
                            import time
                            time.sleep(5)  # Wait 5 seconds before resuming scheduler
                            try:
                                print(f"Resuming scheduler job after failed initial scrape")
                                scheduler_client.resume_job(name=job_name)
                                print(f"Scheduler job resumed successfully")
                            except Exception as e:
                                print(f"Warning: Could not resume scheduler job: {e}")
                    else:
                        # If scraping failed, still return structure
                        initial_scraping_results = {
                            'totalListings': 0,
                            'matchesFound': 0,
                            'sampleListings': []
                        }
                        print(f"Initial scraping failed - invalid result: {result}")
                        success_log = {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'message': 'Scrape: 0 - Failed - invalid response',
                            'level': 'error',
                            'details': str(result)
                        }
                        # Note: Log entry will be added by the main bot function via update_task_stats
                        # No need to add duplicate log here
                        
                        # Resume the scheduler job after failed initial scraping
                        # Add a delay to ensure the initial scrape is fully processed
                        import time
                        time.sleep(5)  # Wait 5 seconds before resuming scheduler
                        try:
                            print(f"Resuming scheduler job after failed initial scrape")
                            scheduler_client.resume_job(name=job_name)
                            print(f"Scheduler job resumed successfully")
                        except Exception as e:
                            print(f"Warning: Could not resume scheduler job: {e}")
                except Exception as e:
                    print(f"Initial scraping failed with exception: {e}")
                    import traceback
                    traceback.print_exc()
                    initial_scraping_results = {
                        'totalListings': 0,
                        'matchesFound': 0,
                        'sampleListings': []
                    }
                    success_log = {
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'message': 'Scrape: 0 - Failed with exception',
                        'level': 'error',
                        'details': str(e)
                    }
                    # Note: Log entry will be added by the main bot function via update_task_stats
                    # No need to add duplicate log here
                    
                    # Resume the scheduler job after initial scraping is complete
                    # Add a delay to ensure the initial scrape is fully processed
                    import time
                    time.sleep(5)  # Wait 5 seconds before resuming scheduler
                    try:
                        print(f"Resuming scheduler job after initial scrape completion")
                        scheduler_client.resume_job(name=job_name)
                        print(f"Scheduler job resumed successfully")
                    except Exception as e:
                        print(f"Warning: Could not resume scheduler job: {e}")
            
            # Start background scraping thread
            scraping_thread = threading.Thread(target=background_scraping)
            scraping_thread.daemon = True
            scraping_thread.start()
        elif immediate_scraping and not enable_initial_scrape:
            # If initial scrape is disabled, seed the seen set with the most recent listing
            print(f"Initial scrape disabled - seeding seen set for task {task_id}")
            
            # Add log entry for seeding
            seeding_log = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'message': 'Seeding seen set - monitoring from now',
                'level': 'info',
                'details': 'Initial scrape disabled - only new posts will be detected'
            }
            
            # Update task with seeding log
            task_ref = db.collection('user_tasks').document(task_id)
            task_ref.update({
                'logs': firestore.ArrayUnion([seeding_log])
            })
            
            # Start seeding in background
            import threading
            def background_seeding():
                try:
                    # Call the deployed Cloud Function with seeding flag
                    import requests
                    
                    function_url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/craigslist-bot-entry-point"
                    print(f"Calling deployed function for seeding: {function_url}")
                    
                    # Add seeding configuration to payload
                    seeding_payload = function_payload.copy()
                    seeding_payload['is_initial_scrape'] = False
                    seeding_payload['seed_seen_set'] = True
                    
                    response = requests.post(function_url, json=seeding_payload, timeout=300)
                    print(f"Seeding response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"Seeding completed successfully: {result}")
                    else:
                        print(f"Seeding failed: {response.text}")
                        
                except Exception as e:
                    print(f"Seeding failed with exception: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Start the background thread
            seeding_thread = threading.Thread(target=background_seeding)
            seeding_thread.daemon = True
            seeding_thread.start()
        
        return {
            'success': True,
            'taskId': task_id,
            'message': 'Task created successfully',
            'initialScrapingResults': initial_scraping_results
        }
        
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'success': False,
            'message': f'Failed to create task: {str(e)}'
        }

def get_user_tasks(user_id: str) -> List[Dict]:
    """
    Get all tasks for a user
    
    Args:
        user_id: User ID to fetch tasks for
        
    Returns:
        List of task dictionaries
    """
    try:
        tasks_ref = db.collection('user_tasks')
        query = tasks_ref.where('user_id', '==', user_id)
        docs = query.stream()
        
        tasks = []
        for doc in docs:
            task_data = doc.to_dict()
            # Timestamps are already in ISO format, no conversion needed
            tasks.append(task_data)
        
        return tasks
        
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def delete_user_task(task_id: str, user_id: str) -> bool:
    """
    Delete a user task and its scheduler job
    
    Args:
        task_id: Task ID to delete
        user_id: User ID (for verification)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify task belongs to user
        task_ref = db.collection('user_tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return False
            
        task_data = task_doc.to_dict()
        if task_data.get('user_id') != user_id:
            return False
        
        # Delete from Firestore
        task_ref.delete()
        
        # Delete Cloud Scheduler job
        job_name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/craigslist-bot-{task_id}"
        try:
            scheduler_client.delete_job(name=job_name)
        except Exception as e:
            print(f"Failed to delete scheduler job: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error deleting task: {e}")
        return False

def update_task_stats(task_id: str, total_scrapes: int, total_matches: int, log_entry: Dict = None, increment_run_count: bool = True) -> bool:
    """
    Update task statistics after a scraping run
    
    Args:
        task_id: Task ID to update
        total_scrapes: Total number of listings scraped
        total_matches: Total number of matches found
        log_entry: Optional log entry to add
        increment_run_count: Whether to increment the run count (default: True)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        task_ref = db.collection('user_tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            print(f"Task {task_id} not found")
            return False
        
        # Get current stats
        task_data = task_doc.to_dict()
        current_runs = task_data.get('total_runs', 0)
        current_scrapes = task_data.get('total_scrapes', 0)
        current_matches = task_data.get('total_matches', 0)
        
        # Calculate next cooldown time
        current_time = time.time()
        next_cooldown_timestamp = current_time + (task_data.get('frequency_minutes', 60) * 60)
        next_cooldown_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(next_cooldown_timestamp))
        
        # Update stats
        updates = {
            'total_runs': current_runs + (1 if increment_run_count else 0),  # Conditionally increment run count
            'total_scrapes': current_scrapes + total_scrapes,
            'total_matches': current_matches + total_matches,
            'last_run': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(current_time)),
            'next_cooldown': next_cooldown_iso
        }
        
        # Add log entry if provided
        if log_entry:
            updates['logs'] = firestore.ArrayUnion([log_entry])
        
        task_ref.update(updates)
        new_run_count = current_runs + (1 if increment_run_count else 0)
        print(f"Updated task {task_id}: Run {new_run_count}, +{total_scrapes} scrapes, +{total_matches} matches")
        return True
        
    except Exception as e:
        print(f"Error updating task stats: {e}")
        return False

def get_task_status(task_id: str) -> Dict:
    """
    Get real-time status of a task
    
    Args:
        task_id: Task ID to check
        
    Returns:
        Dictionary with task status information
    """
    try:
        task_ref = db.collection('user_tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return {'status': 'not_found'}
        
        task_data = task_doc.to_dict()
        logs = task_data.get('logs', [])
        
        if not logs:
            return {'status': 'idle'}
        
        # Get the most recent log entry
        latest_log = logs[-1]
        latest_timestamp = latest_log.get('timestamp', '')
        
        # Check if this is a very recent log (within last 2 minutes) to detect new runs
        current_time = time.time()
        try:
            # Parse ISO timestamp
            log_time = time.mktime(time.strptime(latest_timestamp, '%Y-%m-%dT%H:%M:%SZ'))
            time_diff = current_time - log_time
            
            # If log is very recent (within 2 minutes), it might be a new run
            is_recent = time_diff < 120  # 2 minutes
        except:
            is_recent = False
        
        # Determine status based on latest log
        message = latest_log.get('message', '').lower()
        
        if 'scraping' in message and 'starting' in message:
            return {'status': 'running', 'message': latest_log.get('message', '')}
        elif 'completed' in message or 'found' in message or 'no posts' in message:
            # If it's a recent completion, it might indicate a new run just finished
            if is_recent:
                return {'status': 'completed', 'message': latest_log.get('message', ''), 'recent': True}
            else:
                return {'status': 'completed', 'message': latest_log.get('message', '')}
        elif 'failed' in message:
            return {'status': 'failed', 'message': latest_log.get('message', '')}
        else:
            return {'status': 'idle', 'message': latest_log.get('message', '')}
        
    except Exception as e:
        print(f"Error getting task status: {e}")
        return {'status': 'error', 'message': str(e)}

def toggle_task_active(task_id: str, user_id: str, is_active: bool) -> bool:
    """
    Toggle task active status
    
    Args:
        task_id: Task ID to toggle
        user_id: User ID (for verification)
        is_active: New active status
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify task belongs to user
        task_ref = db.collection('user_tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return False
            
        task_data = task_doc.to_dict()
        if task_data.get('user_id') != user_id:
            return False
        
        # Update task status
        updates = {'is_active': is_active}
        
        # If unpausing, check if we should run immediately
        if is_active:
            current_time = time.time()
            next_cooldown = task_data.get('next_cooldown', current_time)
            
            # If cooldown has passed, run immediately
            if current_time >= next_cooldown:
                print(f"Cooldown has passed, running task {task_id} immediately")
                # Trigger immediate run
                import threading
                def immediate_run():
                    try:
                        import requests
                        function_payload = {
                            "user_id": task_data.get('user_id'),
                            "task_id": task_id,
                            "config": {
                                "search_query": task_data.get('description', ''),
                                "location": task_data.get('location', ''),
                                "distance": task_data.get('distance', 15),
                                "strictness": task_data.get('strictness', 'strict')
                            },
                            "discord_webhook_url": task_data.get('discord_webhook_url')
                        }
                        
                        function_url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/craigslist-bot-entry-point"
                        response = requests.post(function_url, json=function_payload, timeout=300)
                        print(f"Immediate run response: {response.status_code}")
                    except Exception as e:
                        print(f"Immediate run failed: {e}")
                
                # Start immediate run in background
                run_thread = threading.Thread(target=immediate_run)
                run_thread.daemon = True
                run_thread.start()
        
        task_ref.update(updates)
        
        # Update Cloud Scheduler job
        job_name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/craigslist-bot-{task_id}"
        try:
            if is_active:
                # Resume job - enable the scheduler job
                scheduler_client.resume_job(name=job_name)
                print(f"Resumed scheduler job: {job_name}")
            else:
                # Pause job - disable the scheduler job
                scheduler_client.pause_job(name=job_name)
                print(f"Paused scheduler job: {job_name}")
        except Exception as e:
            print(f"Failed to update scheduler job: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error toggling task: {e}")
        return False
