"""
Craigslist Bot - Technical Assessment
A serverless Python bot for scraping Craigslist, filtering with LLM, and Discord notifications.

Architecture:
- Native Python scraping (requests + BeautifulSoup)
- Google Cloud Firestore for state management
- OpenAI API for LLM filtering
- Discord webhooks for notifications
- GCP Cloud Functions for deployment

Configuration: Environment-driven with reasonable production defaults
"""

import os
import re
import json
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration placeholders for environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Discord webhook configuration
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Craigslist search configuration  
SEARCH_QUERY = os.getenv('SEARCH_QUERY', '54cm road bike shimano 105')
SEARCH_POSTAL = os.getenv('SEARCH_POSTAL', '94105')
SEARCH_DISTANCE = os.getenv('SEARCH_DISTANCE', '15')

# Production deployment configuration
PRODUCTION_STRICTNESS = os.getenv('PRODUCTION_STRICTNESS', 'very_strict')  # Default to very_strict for production

# Strictness threshold mapping
STRICTNESS_THRESHOLDS = {
    'less_strict': 0.50,
    'strict': 0.70,
    'very_strict': 0.85
}

# Initialize clients
firestore_client = None
openai_client = None

def initialize_clients():
    """Initialize all external service clients"""
    global firestore_client, openai_client
    
    # Initialize OpenAI client
    if OPENAI_API_KEY:
        try:
            # Initialize with only the mandatory api_key argument to avoid HTTP conflicts
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            print("✓ OpenAI client initialized")
        except Exception as e:
            print(f"⚠ Error initializing OpenAI client: {e}")
            # Try alternative initialization without explicit api_key
            try:
                os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
                openai_client = OpenAI()
                print("✓ OpenAI client initialized (alternative method)")
            except Exception as e2:
                print(f"⚠ Alternative OpenAI initialization also failed: {e2}")
                openai_client = None
    else:
        print("⚠ OPENAI_API_KEY not set")
        openai_client = None
    
    # Discord webhook configuration check
    if DISCORD_WEBHOOK_URL:
        print("✓ Discord webhook configuration available")
    else:
        print("⚠ Discord webhook URL not configured")
    
    # Initialize Firestore client
    try:
        firestore_client = firestore.Client()
        print("✓ Firestore client initialized")
    except Exception as e:
        print(f"⚠ Error initializing Firestore client: {e}")
        print("Firestore requires proper GCP authentication for production deployment")
        firestore_client = None


def format_llm_query(user_query: str) -> str:
    """
    Use OpenAI to extract the most essential keywords for Craigslist search
    
    Args:
        user_query: The user's original search query
        
    Returns:
        Clean, extracted keywords as a single string
    """
    if not openai_client:
        print("⚠ OpenAI client not available, using original query")
        return user_query
    
    try:
        prompt = f"""You are a Craigslist search optimizer. Extract only the 3-5 most critical keywords from this user query that would be suitable for a literal Craigslist search.

User Query: "{user_query}"

Rules:
- Extract only the most essential keywords
- Remove unnecessary words like "with", "comparable to", "within", "miles"
- Keep specific model names, sizes, and key descriptors
- Return ONLY the keywords as a single string, no quotes or extra text

Example: "54cm frame road bike with components comparable to Shimano 105's" → "54cm road bike shimano 105"

Keywords:"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1
        )
        
        keywords = response.choices[0].message.content.strip()
        print(f"✓ LLM extracted keywords: '{keywords}'")
        return keywords
        
    except Exception as e:
        print(f"⚠ LLM query formatting failed: {e}")
        print("Using original query as fallback")
        return user_query

def build_craigslist_url(query: str, postal: str, distance: str) -> str:
    """
    Build a properly encoded Craigslist search URL
    
    Args:
        query: Search query keywords
        postal: Zip code
        distance: Search distance in miles
        
    Returns:
        Complete Craigslist search URL
    """
    base_url = "https://sfbay.craigslist.org/search/bia"
    
    params = {
        'query': query,
        'postal': postal,
        'search_distance': distance
    }
    
    # Use urllib.parse.urlencode for proper URL encoding
    query_string = urlencode(params)
    full_url = f"{base_url}?{query_string}"
    
    print(f"✓ Built Craigslist URL: {full_url}")
    return full_url

def llm_evaluate_listing(listing: Dict, user_criteria: str) -> Dict:
    """
    Use LLM to evaluate a listing against user criteria as a generic expert appraiser
    
    Args:
        listing: Dictionary containing listing data (id, url, title, text, price, location_zip)
        user_criteria: Original user search criteria/requirements
        
    Returns:
        Dictionary with evaluation results including match_score, is_recommended, reasoning
    """
    if not openai_client:
        print("⚠ OpenAI client not available, skipping LLM evaluation")
        return {
            'match_score': 0.5,
            'reasoning': 'LLM evaluation unavailable',
            'feature_match': 'Unknown',
            'quality_assessment': 'Unknown'
        }
    
    try:
        prompt = f"""You are a professional item appraiser and expert buyer for specialized goods. Your task is to rigorously compare a classified ad against a user's detailed requirements and assess the listing's authenticity and quality.

LISTING TO EVALUATE:
Title: {listing['title']}
Price: {listing['price']}
Description: {listing['text'][:1000]}...

USER'S REQUIREMENTS:
{user_criteria}

EVALUATION CRITERIA:
1. Feature Match: Does the listing text mention or strongly imply the requested key features, size, or quality levels outlined in the user's criteria?
2. Listing Quality/Authenticity: Does the description suggest a legitimate, high-quality sale (detailed information, no obvious red flags, reasonable price)?

MANDATORY OUTPUT FORMAT (JSON only):
{{
    "match_score": <float 0.0-1.0>,
    "reasoning": "<brief explanation of decision>",
    "feature_match": "<assessment of how well features match>",
    "quality_assessment": "<assessment of listing quality and authenticity>"
}}

Evaluate strictly and return only the JSON object."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON object in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_text = response_text[json_start:json_end]
                evaluation = json.loads(json_text)
                
                # Validate required fields
                required_fields = ['match_score', 'reasoning', 'feature_match', 'quality_assessment']
                for field in required_fields:
                    if field not in evaluation:
                        evaluation[field] = 'Unknown'
                
                print(f"✓ LLM evaluation completed for listing {listing['id']}")
                return evaluation
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠ Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response_text}")
            return {
                'match_score': 0.5,
                'reasoning': 'Failed to parse LLM response',
                'feature_match': 'Unknown',
                'quality_assessment': 'Unknown'
            }
        
    except Exception as e:
        print(f"⚠ LLM evaluation failed: {e}")
        return {
            'match_score': 0.5,
            'reasoning': f'Evaluation error: {str(e)}',
            'feature_match': 'Unknown',
            'quality_assessment': 'Unknown'
        }

def get_seen_listing_ids(search_hash: str) -> List[str]:
    """
    Retrieve all previously seen listing IDs from Firestore for a specific search
    
    Args:
        search_hash: Unique identifier for the search query/location
        
    Returns:
        List of listing IDs that have been seen before
    """
    if not firestore_client:
        print("⚠ Firestore client not available - requiring proper GCP authentication")
        return []
    
    try:
        # Collection: 'seen_listings'
        # Document: search_hash
        # Fields: 'listing_ids' (array of strings)
        
        doc_ref = firestore_client.collection('seen_listings').document(search_hash)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            seen_ids = data.get('listing_ids', [])
            print(f"✓ Retrieved {len(seen_ids)} previously seen listing IDs")
            return seen_ids
        else:
            print("✓ No previously seen listings found for this search")
            return []
            
    except Exception as e:
        print(f"⚠ Error retrieving seen listings: {e}")
        return []

def save_listing_ids(search_hash: str, listing_ids: List[str]) -> bool:
    """
    Save listing IDs to Firestore for future reference
    
    Args:
        search_hash: Unique identifier for the search query/location
        listing_ids: List of listing IDs to mark as seen
        
    Returns:
        True if successful, False otherwise
    """
    if not firestore_client:
        print("⚠ Firestore client not available - requiring proper GCP authentication")
        return False
    
    if not listing_ids:
        print("⚠ No listing IDs to save")
        return True
    
    try:
        # Collection: 'seen_listings'
        # Document: search_hash
        # Fields: 'listing_ids' (array of strings), 'last_updated' (timestamp)
        
        doc_ref = firestore_client.collection('seen_listings').document(search_hash)
        doc_ref.set({
            'listing_ids': listing_ids,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        
        print(f"✓ Saved {len(listing_ids)} listing IDs to Firestore")
        return True
        
    except Exception as e:
        print(f"⚠ Error saving listing IDs: {e}")
        return False

def create_search_hash(query: str, location: str, distance: str) -> str:
    """
    Create a unique hash identifier for a search configuration
    
    Args:
        query: Search query terms
        location: Zip code or location
        distance: Search distance
        
    Returns:
        Unique hash string for this search
    """
    import hashlib
    search_string = f"{query.lower()}_{location}_{distance}"
    return hashlib.md5(search_string.encode()).hexdigest()

def send_notification_via_discord(recommended_listings: List[Dict], user_query: str) -> bool:
    """
    Send notification via Discord webhook
    
    Args:
        recommended_listings: List of listings that meet the strictness threshold
        user_query: Original user search query for context
        
    Returns:
        True if successful, False otherwise
    """
    if not DISCORD_WEBHOOK_URL:
        print("⚠ Discord webhook URL not configured, skipping notification")
        return False
    
    if not recommended_listings:
        print("✓ No recommended listings to notify about")
        return True
    
    try:
        # Build Discord message with rich formatting
        embed = {
            "title": f"🚴 New Craigslist Matches Found!",
            "description": f"**Query:** {user_query}\n**Matches:** {len(recommended_listings)} listings",
            "color": 0x00ff00,  # Green color
            "fields": []
        }
        
        # Add each recommended listing as a field
        for i, listing in enumerate(recommended_listings[:10], 1):  # Limit to 10 for Discord
            eval_data = listing['evaluation']
            score = eval_data['match_score'] * 100  # Convert to percentage
            
            embed["fields"].append({
                "name": f"{i}. {listing['title'][:50]}...",
                "value": f"💰 **Price:** {listing['price']}\n⭐ **Match Score:** {score:.0f}%\n🔗 **URL:** {listing['url']}",
                "inline": False
            })
        
        if len(recommended_listings) > 10:
            embed["fields"].append({
                "name": "Additional Matches",
                "value": f"+ {len(recommended_listings) - 10} more listings found",
                "inline": False
            })
        
        embed["footer"] = {
            "text": "CraigslistBot • Automated Listing Monitor"
        }
        
        embed["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        
        # Prepare Discord webhook payload
        payload = {
            "content": f"🔔 **New listing alerts for '{user_query}'**",
            "embeds": [embed]
        }
        
        # Send to Discord webhook
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 204:  # Discord success response
            print(f"✓ Discord notification sent successfully")
            print(f"  Matches included: {len(recommended_listings)}")
            print(f"  Query: {user_query}")
            return True
        else:
            print(f"⚠ Discord webhook failed: HTTP {response.status_code}")
            if response.text:
                print(f"  Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"⚠ Discord notification failed: {e}")
        return False

def get_production_listings(recommended_listings: List[Dict], threshold: float) -> List[Dict]:
    """
    Filter listings by strictness threshold for production deployment
    
    Args:
        recommended_listings: List of evaluated listings
        threshold: Minimum match score threshold
        
    Returns:
        List of listings meeting the threshold
    """
    return [listing for listing in recommended_listings 
            if listing['evaluation']['match_score'] >= threshold]

def extract_listing_id_from_url(url: str) -> Optional[str]:
    """
    Extract listing ID from Craigslist URL
    Expected format: https://sfbay.craigslist.org/pen/bia/d/listing-title/1234567890.html
    """
    try:
        # Extract the numeric ID from the URL
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)
        
        # Alternative pattern for some Craigslist URLs
        match = re.search(r'/d/([^/]+)/(\d+)\.html', url)
        if match:
            return match.group(2)
            
        return None
    except Exception as e:
        print(f"Error extracting ID from URL {url}: {e}")
        return None

def scrape_new_listings_data(search_url: str) -> List[Dict[str, str]]:
    """
    Scrape Craigslist search results and individual listings using native Python
    
    Args:
        search_url: Craigslist search results URL
        
    Returns:
        List of dictionaries with keys: id, url, title, text
    """
    listings = []
    
    try:
        print(f"Scraping search results from: {search_url}")
        
        # Step 1: Fetch the search results page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        search_response = requests.get(search_url, headers=headers, timeout=10)
        search_response.raise_for_status()
        
        # Parse the search results page
        soup = BeautifulSoup(search_response.content, 'html.parser')
        
        # Find all listing elements (Craigslist now uses <li class="cl-static-search-result">)
        listing_elements = soup.find_all('li', class_='cl-static-search-result')
        print(f"Found {len(listing_elements)} listing elements")
        
        # Step 2: Extract data from each listing
        for i, listing_element in enumerate(listing_elements):
            try:
                print(f"Processing listing {i+1}/{len(listing_elements)}")
                
                # Extract listing URL - look for the main link in the listing
                link_element = listing_element.find('a', href=True)
                if not link_element:
                    continue
                
                listing_url = link_element.get('href')
                if not listing_url:
                    continue
                
                # Make URL absolute if it's relative
                if listing_url.startswith('/'):
                    base_url = f"https://{urlparse(search_url).netloc}"
                    listing_url = base_url + listing_url
                
                # Extract title from the link text
                title = link_element.get_text(strip=True)
                
                # Extract listing ID from URL
                listing_id = extract_listing_id_from_url(listing_url)
                if not listing_id:
                    continue
                
                # Step 3: Fetch individual listing page for full description
                print(f"  Fetching full description from: {listing_url}")
                listing_response = requests.get(listing_url, headers=headers, timeout=10)
                listing_response.raise_for_status()
                
                listing_soup = BeautifulSoup(listing_response.content, 'html.parser')
                
                # Extract full description text
                description_element = listing_soup.find('section', {'id': 'postingbody'})
                if description_element:
                    # Remove the "QR Code Link to This Post" element
                    qr_element = description_element.find('div', class_='print-information')
                    if qr_element:
                        qr_element.decompose()
                    
                    text_content = description_element.get_text(strip=True)
                else:
                    text_content = ""
                
                # Extract price
                price = ""
                price_element = listing_soup.find('span', class_='price')
                if price_element:
                    price = price_element.get_text(strip=True)
                else:
                    # Try alternative price selectors
                    price_element = listing_soup.find('span', class_='priceinfo')
                    if price_element:
                        price = price_element.get_text(strip=True)
                
                # Extract location/zip
                location_zip = ""
                # Look for location in various places
                location_element = listing_soup.find('div', class_='mapAndAttrs')
                if location_element:
                    location_text = location_element.get_text(strip=True)
                    # Extract zip code pattern
                    zip_match = re.search(r'\b\d{5}\b', location_text)
                    if zip_match:
                        location_zip = zip_match.group()
                
                # If no zip found, try other location elements
                if not location_zip:
                    location_element = listing_soup.find('div', class_='postingtitle')
                    if location_element:
                        location_text = location_element.get_text(strip=True)
                        zip_match = re.search(r'\b\d{5}\b', location_text)
                        if zip_match:
                            location_zip = zip_match.group()
                
                # Create listing dictionary
                listing_info = {
                    'id': listing_id,
                    'url': listing_url,
                    'title': title,
                    'text': text_content,
                    'price': price,
                    'location_zip': location_zip
                }
                
                listings.append(listing_info)
                
                # Add a small delay to be respectful to the server
                time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error processing listing {i+1}: {e}")
                continue
    
    except Exception as e:
        print(f"Error in scrape_new_listings_data: {e}")
    
    print(f"Successfully scraped {len(listings)} listings")
    return listings



def main():
    """Development/testing function - use craigslist_bot_entry_point() for production"""
    print("Craigslist Bot - Development Mode")
    print("For production deployment, use craigslist_bot_entry_point()")
    print("=" * 50)
    
    # Initialize clients
    initialize_clients()
    
    # Use environment-driven configuration
    search_params = {
        'location': SEARCH_POSTAL,
        'distance': SEARCH_DISTANCE, 
        'query': SEARCH_QUERY,
        'strictness': PRODUCTION_STRICTNESS
    }
    
    # Use LLM to refine the search query
    refined_query = format_llm_query(search_params['query'])
    
    # Build the Craigslist search URL
    search_url = build_craigslist_url(
        query=refined_query,
        postal=search_params['location'],
        distance=search_params['distance']
    )
    
    # Create unique search hash for state management
    search_hash = create_search_hash(search_params['query'], search_params['location'], search_params['distance'])
    print(f"Search hash: {search_hash}")
    
    # Retrieve previously seen listing IDs
    print(f"\nRetrieving previously seen listings...")
    seen_ids = get_seen_listing_ids(search_hash)
    
    # Scrape listings with enhanced data extraction
    print(f"\nScraping listings with enhanced data extraction...")
    
    try:
        listings = scrape_new_listings_data(search_url)
        
        print(f"\nScraping completed. Found {len(listings)} listings")
        
        if len(listings) == 0:
            print("\n⚠ No listings found. This could be due to:")
            print("  - No listings matching the search criteria")
            print("  - Network/API issues")
            print("  - Changes in Craigslist HTML structure")
            return
        
        # Filter for NEW listings only
        new_listings = []
        for listing in listings:
            if listing['id'] not in seen_ids:
                new_listings.append(listing)
        
        print(f"\nListings filtering:")
        print(f"  Total scraped: {len(listings)}")
        print(f"  Previously seen: {len(seen_ids)}")
        print(f"  NEW listings: {len(new_listings)}")
        
        if len(new_listings) == 0:
            print("\n✓ No new listings found - all listings have been seen before!")
            print("This demonstrates effective state management.")
            return
        
        # Evaluate only NEW listings with LLM (reduced processing)
        print(f"\nEvaluating {len(new_listings)} NEW listings with LLM expert appraiser...")
        evaluated_listings = []
        
        for i, listing in enumerate(new_listings):
            print(f"Evaluating listing {i+1}/{len(new_listings)}: {listing['title'][:50]}...")
            
            # Get LLM evaluation
            evaluation = llm_evaluate_listing(listing, search_params['query'])
            
            # Add evaluation to listing data
            listing_with_eval = listing.copy()
            listing_with_eval['evaluation'] = evaluation
            evaluated_listings.append(listing_with_eval)
        
        # Comprehensive Testing: Test all three strictness levels
        print(f"\n" + "="*80)
        print("COMPREHENSIVE STRICTNESS TESTING")
        print("="*80)
        
        # Sort listings by match score (highest first) for consistent testing
        sorted_listings = sorted(evaluated_listings, key=lambda x: x['evaluation']['match_score'], reverse=True)
        
        # Test 1: Less Strict (≥0.50)
        threshold_less = STRICTNESS_THRESHOLDS['less_strict']
        matches_less = [l for l in sorted_listings if l['evaluation']['match_score'] >= threshold_less]
        
        print(f"\nTest 1 (Less Strict ≥{threshold_less:.2f}):")
        print(f"Total matches found: {len(matches_less)}")
        
        # Test 2: Strict (≥0.70)
        threshold_strict = STRICTNESS_THRESHOLDS['strict']
        matches_strict = [l for l in sorted_listings if l['evaluation']['match_score'] >= threshold_strict]
        
        print(f"\nTest 2 (Strict ≥{threshold_strict:.2f}):")
        print(f"Total matches found: {len(matches_strict)}")
        
        # Test 3: Very Strict (≥0.85)
        threshold_very = STRICTNESS_THRESHOLDS['very_strict']
        matches_very = [l for l in sorted_listings if l['evaluation']['match_score'] >= threshold_very]
        
        print(f"\nTest 3 (Very Strict ≥{threshold_very:.2f}):")
        print(f"Total matches found: {len(matches_very)}")
        
        # Display top matches for very strict test
        if len(matches_very) > 0:
            print(f"\nHigh-quality matches (Very Strict ≥{threshold_very:.2f}):")
            print("-" * 80)
            for i, listing in enumerate(matches_very[:2]):  # Show top 2 matches
                eval_data = listing['evaluation']
                print(f"\nTop Match {i+1}:")
                print(f"  ID: {listing['id']}")
                print(f"  Title: {listing['title'][:80]}...")
                print(f"  Price: {listing['price']}")
                print(f"  Score: {eval_data['match_score']:.2f}")
                print(f"  Reasoning: {eval_data['reasoning']}")
                print(f"  URL: {listing['url']}")
        elif len(matches_strict) > 0:
            print(f"\nNo very strict matches (≥{threshold_very:.2f}), but here are the best strict matches (≥{threshold_strict:.2f}):")
            print("-" * 80)
            for i, listing in enumerate(matches_strict[:2]):
                eval_data = listing['evaluation']
                print(f"\nBest Match {i+1}:")
                print(f"  ID: {listing['id']}")
                print(f"  Title: {listing['title'][:80]}...")
                print(f"  Price: {listing['price']}")
                print(f"  Score: {eval_data['match_score']:.2f}")
                print(f"  Reasoning: {eval_data['reasoning']}")
        
        print(f"\n" + "="*80)
        print("SUMMARY:")
        print(f"Less Strict (≥{threshold_less:.2f}): {len(matches_less)} matches")
        print(f"Strict (≥{threshold_strict:.2f}): {len(matches_strict)} matches")
        print(f"Very Strict (≥{threshold_very:.2f}): {len(matches_very)} matches")
        print("="*80)
        
        # Save all processed listing IDs to Firestore for future reference
        print(f"\nSaving processed listing IDs to state management...")
        all_listing_ids = [listing['id'] for listing in listings]  # All IDs, not just new ones
        save_success = save_listing_ids(search_hash, all_listing_ids)
        
        if save_success:
            print(f"✓ State management updated: {len(all_listing_ids)} listing IDs saved")
        else:
            print(f"⚠ State management update failed")
            
    except Exception as e:
        print(f"Error in main: {e}")

def craigslist_bot_entry_point(request=None):
    """
    Serverless entry point for GCP Cloud Functions deployment
    
    Args:
        request: HTTP request object (required for Cloud Functions but not used)
        
    Returns:
        HTTP response with operation status
    """
    try:
        print("Craigslist Bot - Production Entry Point")
        print(f"Strictness Level: {PRODUCTION_STRICTNESS}")
        print("=" * 50)
        
        # Initialize clients
        initialize_clients()
        
        # Use production configuration
        search_params = {
            'location': SEARCH_POSTAL,
            'distance': SEARCH_DISTANCE,
            'query': SEARCH_QUERY,
            'strictness': PRODUCTION_STRICTNESS
        }
        
        print(f"Production Configuration:")
        print(f"  Location: {search_params['location']}")
        print(f"  Distance: {search_params['distance']} miles")
        print(f"  Query: {search_params['query']}")
        print(f"  Strictness: {search_params['strictness']}")
        
        # Use LLM to refine the search query
        refined_query = format_llm_query(search_params['query'])
        
        # Build the Craigslist search URL
        search_url = build_craigslist_url(
            query=refined_query,
            postal=search_params['location'],
            distance=search_params['distance']
        )
        
        # Create unique search hash for state management
        search_hash = create_search_hash(search_params['query'], search_params['location'], search_params['distance'])
        print(f"Search hash: {search_hash}")
        
        # Retrieve previously seen listing IDs
        print(f"\nRetrieving previously seen listings...")
        seen_ids = get_seen_listing_ids(search_hash)
        
        # Scrape listings with enhanced data extraction
        print(f"\nScraping listings...")
        listings = scrape_new_listings_data(search_url)
        
        if len(listings) == 0:
            return {
                'statusCode': 200,
                'body': 'No listings found - search criteria may need adjustment'
            }
        
        # Filter for NEW listings only
        new_listings = [listing for listing in listings if listing['id'] not in seen_ids]
        
        print(f"\nState Check:")
        print(f"  Total scraped: {len(listings)}")
        print(f"  Previously seen: {len(seen_ids)}")
        print(f"  NEW listings: {len(new_listings)}")
        
        if len(new_listings) == 0:
            # Save current state and return
            save_listing_ids(search_hash, [listing['id'] for listing in listings])
            
            return {
                'statusCode': 200,
                'body': 'No new listings found - all listings have been processed previously'
            }
        
        # Evaluate only NEW listings with LLM
        print(f"\nEvaluating {len(new_listings)} NEW listings...")
        evaluated_listings = []
        
        for listing in new_listings:
            evaluation = llm_evaluate_listing(listing, search_params['query'])
            listing_with_eval = listing.copy()
            listing_with_eval['evaluation'] = evaluation
            evaluated_listings.append(listing_with_eval)
        
        # Apply production strictness filter
        threshold = STRICTNESS_THRESHOLDS[PRODUCTION_STRICTNESS]
        recommended_listings = get_production_listings(evaluated_listings, threshold)
        
        print(f"\nFilter Results:")
        print(f"  Threshold: {threshold:.2f}")
        print(f"  Recommended listings: {len(recommended_listings)}")
        
        # Send Discord notification for new recommendations
        notification_sent = False
        if recommended_listings:
            print(f"\nSending Discord notification...")
            notification_sent = send_notification_via_discord(recommended_listings, search_params['query'])
        
        # Save processed listing IDs to state management
        save_listing_ids(search_hash, [listing['id'] for listing in listings])
        
        # Prepare response
        response_body = {
            'message': 'Craigslist bot execution completed',
            'total_listings': len(listings),
            'new_listings': len(new_listings),
            'recommended_listings': len(recommended_listings),
            'notification_sent': notification_sent,
            'strictness_used': PRODUCTION_STRICTNESS
        }
        
        return {
            'statusCode': 200,
            'body': response_body
        }
        
    except Exception as e:
        error_msg = f"Craigslist bot execution failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 500,
            'body': {'error': error_msg}
        }

if __name__ == "__main__":
    main()
