"""
User-configurable scheduling API for Craigslist Bot

This module provides dynamic Cloud Scheduler management where each user
can configure their own scraping frequency through the web app.
"""

import json
from google.cloud import scheduler_v1

def create_user_scheduler_job(user_id: str, frequency_minutes: int, user_config: dict):
    """
    Create a Cloud Scheduler job for a specific user
    
    Args:
        user_id: Unique identifier for the user
        frequency_minutes: How often to scrape (in minutes)
        user_config: User's search configuration (query, location, etc.)
    
    Returns:
        job_id: The created scheduler job ID
    """
    # Enforce rate limits
    min_frequency = 2  # 2 minutes minimum for testing
    max_frequency = 10080  # 1 week maximum
    
    if frequency_minutes < min_frequency:
        raise ValueError(f"Minimum frequency is {min_frequency} minutes")
    if frequency_minutes > max_frequency:
        raise ValueError(f"Maximum frequency is {max_frequency} minutes")
    
    # Create scheduler client
    scheduler_client = scheduler_v1.CloudSchedulerClient()
    
    # Convert frequency to cron expression
    cron_schedule = f"*/{frequency_minutes} * * * *"
    
    # Prepare the HTTP request payload
    job_config_payload = {
        "user_id": user_id,
        "config": user_config
    }
    
    # Define the scheduler job
    job = scheduler_v1.Job(
        name=f"projects/heroic-glyph-473602-q8/locations/us-central1/jobs/craigslist-bot-user-{user_id}",
        schedule=cron_schedule,
        time_zone="America/Los_Angeles",
        http_target=scheduler_v1.HttpTarget(
            uri="https://us-central1-heroic-glyph-473602-q8.cloudfunctions.net/craigslist-bot",
            http_method=scheduler_v1.HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body=json.dumps(job_config_payload).encode()
        ),
        retry_config=scheduler_v1.RetryConfig(
            retry_count=3,
            max_retry_duration="600s"
        )
    )
    
    # Create the job
    parent = "projects/heroic-glyph-473602-q8/locations/us-central1"
    created_job = scheduler_client.create_job(parent=parent, job=job)
    
    return created_job.name

def update_user_scheduler_job(user_id: str, frequency_minutes: int, user_config: dict):
    """Update an existing user's scheduler job"""
    try:
        # First delete the old job
        delete_user_scheduler_job(user_id)
        # Create new job with updated settings
        return create_user_scheduler_job(user_id, frequency_minutes, user_config)
    except Exception as e:
        raise Exception(f"Failed to update scheduler job: {str(e)}")

def delete_user_scheduler_job(user_id: str):
    """Delete a user's scheduler job"""
    scheduler_client = scheduler_v1.CloudSchedulerClient()
    
    job_name = f"projects/heroic-glyph-473602-q8/locations/us-central1/jobs/craigslist-bot-user-{user_id}"
    
    try:
        scheduler_client.delete_job(name=job_name)
        return True
    except Exception as e:
        print(f"Failed to delete job {job_name}: {str(e)}")
        return False

def list_user_scheduler_jobs():
    """List all user scheduler jobs"""
    scheduler_client = scheduler_v1.CloudSchedulerClient()
    
    parent = "projects/heroic-glyph-473602-q8/locations/us-central1"
    
    jobs = []
    for job in scheduler_client.list_jobs(parent=parent):
        if job.name.startswith(parent + "/jobs/craigslist-bot-user-"):
            jobs.append({
                "job_name": job.name,
                "schedule": job.schedule,
                "state": job.state
            })
    
    return jobs

# Example usage for web app integration
def configure_user_scraping(user_id: str, email: str, search_query: str, 
                           location: str, distance: str, frequency_minutes: int):
    """
    Complete configuration function for web app integration
    
    Args:
        user_id: User's unique ID (email hash, etc.)
        email: User's email for notifications
        search_query: What they're searching for
        location: ZIP code
        distance: Search radius in miles
        frequency_minutes: How often to check (minimum 60)
    
    Returns:
        dict: Configuration result
    """
    user_config = {
        "email": email,
        "search_query": search_query,
        "location": location,
        "distance": distance,
        "strictness": "very_strict",  # Start conservative
        "notification_method": "discord"
    }
    
    try:
        job_id = create_user_scheduler_job(user_id, frequency_minutes, user_config)
        return {
            "success": True,
            "job_id": job_id,
            "frequency_minutes": frequency_minutes,
            "message": f"Scraping scheduled every {frequency_minutes} minutes"
        }
    except ValueError as e:
        return {
            "success": False,
            "error": "rate_limit_error",
            "message": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": "configuration_error",
            "message": str(e)
        }
