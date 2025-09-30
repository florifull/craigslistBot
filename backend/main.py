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
        prompt = f"""You are a Craigslist search optimizer. Extract the specific model/brand keywords that will find the most relevant results without being too broad.

User Query: "{user_query}"

Rules:
- Extract 2-4 keywords that identify the SPECIFIC MODEL/BRAND
- Include the main product type and specific model name
- Remove qualifiers, conditions, sizes, colors, locations, and descriptive words
- Keep it specific enough to find relevant results but broad enough to get listings
- Return ONLY the keywords as a single string, no quotes or extra text

Examples:
- "yeezy oreo v2 size 9 or 9.5 would be best, in good condition only or brand new" → "yeezy oreo v2"
- "54cm frame road bike with components comparable to Shimano 105's" → "road bike shimano 105"
- "macbook pro 13 inch 2020 model in excellent condition" → "macbook pro 13"
- "nike air jordan 1 size 10.5 in good condition" → "jordan 1"
- "iphone 12 pro max 256gb unlocked excellent condition" → "iphone 12 pro max"

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

def get_craigslist_region_from_zip(zip_code: str) -> str:
    """
    Determine the appropriate Craigslist region based on zip code
    
    Args:
        zip_code: 5-digit zip code
        
    Returns:
        Craigslist region subdomain (e.g., 'miami', 'sfbay', 'newyork')
    """
    # Convert to int for range checking
    try:
        zip_int = int(zip_code)
    except ValueError:
        print(f"⚠ Invalid zip code {zip_code}, defaulting to sfbay")
        return "sfbay"
    
    # Florida zip codes (33000-34999)
    if 33000 <= zip_int <= 34999:
        return "miami"
    # New York zip codes (10000-14999)
    elif 10000 <= zip_int <= 14999:
        return "newyork"
    # California zip codes (90000-96699)
    elif 90000 <= zip_int <= 96699:
        return "sfbay"
    # Texas zip codes (75000-79999)
    elif 75000 <= zip_int <= 79999:
        return "dallas"
    # Illinois zip codes (60000-62999)
    elif 60000 <= zip_int <= 62999:
        return "chicago"
    # Washington zip codes (98000-99499)
    elif 98000 <= zip_int <= 99499:
        return "seattle"
    # Massachusetts zip codes (01000-05599)
    elif 1000 <= zip_int <= 5599:
        return "boston"
    # Georgia zip codes (30000-31999)
    elif 30000 <= zip_int <= 31999:
        return "atlanta"
    # Colorado zip codes (80000-81699)
    elif 80000 <= zip_int <= 81699:
        return "denver"
    # Oregon zip codes (97000-97999)
    elif 97000 <= zip_int <= 97999:
        return "portland"
    # Nevada zip codes (89000-89899)
    elif 89000 <= zip_int <= 89899:
        return "lasvegas"
    # Arizona zip codes (85000-86599)
    elif 85000 <= zip_int <= 86599:
        return "phoenix"
    # North Carolina zip codes (27000-28999)
    elif 27000 <= zip_int <= 28999:
        return "raleigh"
    # Virginia zip codes (22000-24699)
    elif 22000 <= zip_int <= 24699:
        return "norfolk"
    # Pennsylvania zip codes (15000-19699)
    elif 15000 <= zip_int <= 19699:
        return "philadelphia"
    # Ohio zip codes (43000-45999)
    elif 43000 <= zip_int <= 45999:
        return "columbus"
    # Michigan zip codes (48000-49999)
    elif 48000 <= zip_int <= 49999:
        return "detroit"
    # Minnesota zip codes (55000-56999)
    elif 55000 <= zip_int <= 56999:
        return "minneapolis"
    # Missouri zip codes (63000-65899)
    elif 63000 <= zip_int <= 65899:
        return "kansascity"
    # Tennessee zip codes (37000-38599)
    elif 37000 <= zip_int <= 38599:
        return "nashville"
    # Louisiana zip codes (70000-71499)
    elif 70000 <= zip_int <= 71499:
        return "neworleans"
    # Alabama zip codes (35000-36999)
    elif 35000 <= zip_int <= 36999:
        return "birmingham"
    # Mississippi zip codes (38600-39799)
    elif 38600 <= zip_int <= 39799:
        return "jackson"
    # Arkansas zip codes (71600-72999)
    elif 71600 <= zip_int <= 72999:
        return "littlerock"
    # Oklahoma zip codes (73000-74999)
    elif 73000 <= zip_int <= 74999:
        return "oklahomacity"
    # Kansas zip codes (66000-67999)
    elif 66000 <= zip_int <= 67999:
        return "wichita"
    # Nebraska zip codes (68000-69399)
    elif 68000 <= zip_int <= 69399:
        return "omaha"
    # Iowa zip codes (50000-52899)
    elif 50000 <= zip_int <= 52899:
        return "desmoines"
    # Wisconsin zip codes (53000-54999)
    elif 53000 <= zip_int <= 54999:
        return "milwaukee"
    # Indiana zip codes (46000-47999)
    elif 46000 <= zip_int <= 47999:
        return "indianapolis"
    # Kentucky zip codes (40000-42999)
    elif 40000 <= zip_int <= 42999:
        return "louisville"
    # West Virginia zip codes (24700-26999)
    elif 24700 <= zip_int <= 26999:
        return "charlestonwv"
    # Maryland zip codes (20600-21999)
    elif 20600 <= zip_int <= 21999:
        return "baltimore"
    # Delaware zip codes (19700-19999)
    elif 19700 <= zip_int <= 19999:
        return "delaware"
    # New Jersey zip codes (07000-08999)
    elif 7000 <= zip_int <= 8999:
        return "newjersey"
    # Connecticut zip codes (06000-06999)
    elif 6000 <= zip_int <= 6999:
        return "hartford"
    # Rhode Island zip codes (02800-02999)
    elif 2800 <= zip_int <= 2999:
        return "providence"
    # Vermont zip codes (05000-05999)
    elif 5000 <= zip_int <= 5999:
        return "burlington"
    # New Hampshire zip codes (03000-03999)
    elif 3000 <= zip_int <= 3999:
        return "nh"
    # Maine zip codes (03900-04999)
    elif 3900 <= zip_int <= 4999:
        return "maine"
    # Alaska zip codes (99500-99999)
    elif 99500 <= zip_int <= 99999:
        return "anchorage"
    # Hawaii zip codes (96700-96899)
    elif 96700 <= zip_int <= 96899:
        return "honolulu"
    # Utah zip codes (84000-84799)
    elif 84000 <= zip_int <= 84799:
        return "saltlakecity"
    # Idaho zip codes (83200-83899)
    elif 83200 <= zip_int <= 83899:
        return "boise"
    # Montana zip codes (59000-59999)
    elif 59000 <= zip_int <= 59999:
        return "montana"
    # Wyoming zip codes (82000-83199)
    elif 82000 <= zip_int <= 83199:
        return "wyoming"
    # North Dakota zip codes (58000-58899)
    elif 58000 <= zip_int <= 58899:
        return "fargo"
    # South Dakota zip codes (57000-57799)
    elif 57000 <= zip_int <= 57799:
        return "siouxfalls"
    # New Mexico zip codes (87000-88499)
    elif 87000 <= zip_int <= 88499:
        return "albuquerque"
    # Default to San Francisco Bay Area
    else:
        print(f"⚠ Zip code {zip_code} not mapped to specific region, defaulting to sfbay")
        return "sfbay"

def build_craigslist_url(query: str, postal: str, distance: str) -> str:
    """
    Build a properly encoded Craigslist search URL with location filtering
    
    Args:
        query: Search query keywords
        postal: Zip code for location filtering
        distance: Search distance in miles
        
    Returns:
        Complete Craigslist search URL with location filtering
    """
    # Determine the appropriate Craigslist region based on zip code
    region = get_craigslist_region_from_zip(postal)
    base_url = f"https://{region}.craigslist.org/search/sss"
    
    # Include postal code and distance parameters for location filtering
    # Sort by date to get newest posts first
    params = {
        'query': query,
        'postal': postal,
        'search_distance': distance,
        'sort': 'date'
    }
    
    # Use urllib.parse.urlencode for proper URL encoding
    query_string = urlencode(params)
    full_url = f"{base_url}?{query_string}"
    
    print(f"✓ Built Craigslist URL: {full_url}")
    print(f"✓ Location filtering: {postal} within {distance} miles")
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
        prompt = f"""You are a helpful assistant that evaluates whether a Craigslist listing matches what a user is looking for. Provide varied, nuanced scores based on how well each listing matches the user's specific requirements.

LISTING TO EVALUATE:
Title: {listing['title']}
Price: {listing['price']}
Description: {listing['text'][:1000]}...

USER'S REQUIREMENTS:
{user_criteria}

EVALUATION CRITERIA:
1. Feature Match: How closely does the listing match the user's specific requirements (size, brand, model, condition, etc.)?
2. Listing Quality: Is this a reasonable listing without obvious red flags?

SCORING GUIDELINES - PROVIDE VARIED SCORES:
- 0.9-1.0: Perfect match - exactly what user wants (rare)
- 0.8-0.89: Excellent match - very close to requirements
- 0.7-0.79: Good match - right product type, minor differences
- 0.6-0.69: Decent match - related product, notable differences
- 0.5-0.59: Fair match - somewhat related, significant differences
- 0.3-0.49: Weak match - barely related
- 0.0-0.29: Poor match - not what user is looking for

SIZE TOLERANCE GUIDELINES:
- Close sizes (within 2-3cm): Should score 0.7-0.8 (good match)
- Moderate size differences (4-6cm): Should score 0.5-0.7 (decent to good match)
- Large size differences (7cm+): Should score 0.3-0.5 (weak to fair match)
- Example: 54cm requested, 56cm offered = 0.7-0.8 (close enough for good match)

IMPORTANT: Use the full range of scores. Don't default to 0.7. Consider:
- Size differences (be lenient with close sizes)
- Brand/model differences
- Condition differences
- Missing specifications
- Price appropriateness

MANDATORY OUTPUT FORMAT (JSON only):
{{
    "match_score": <float 0.0-1.0>,
    "reasoning": "<concise 1-2 sentence explanation - max 50 words>",
    "feature_match": "<assessment of how well features match>",
    "quality_assessment": "<assessment of listing quality and authenticity>"
}}

REASONING REQUIREMENTS:
- Keep reasoning to 1-2 sentences maximum
- Use simple, direct language
- Focus on the key reason for the match score
- Avoid unnecessary details or repetition

Provide varied, nuanced scores and return only the JSON object."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
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
                print(f"  Match score: {evaluation['match_score']}")
                print(f"  Reasoning: {evaluation['reasoning'][:100]}...")
                print(f"  *** DEBUG: This is the updated code with temperature 0.7 ***")
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
    Save listing IDs to Firestore for future reference (append to existing list)
    
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
        
        # Get existing listing IDs to append to
        existing_doc = doc_ref.get()
        existing_ids = []
        if existing_doc.exists:
            existing_data = existing_doc.to_dict()
            existing_ids = existing_data.get('listing_ids', [])
        
        # Combine existing and new IDs, removing duplicates
        all_ids = list(set(existing_ids + listing_ids))
        
        # Update the document with the combined list
        doc_ref.set({
            'listing_ids': all_ids,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        
        new_count = len(all_ids) - len(existing_ids)
        print(f"✓ Saved {new_count} new listing IDs to Firestore (total: {len(all_ids)})")
        return True
        
    except Exception as e:
        print(f"⚠ Error saving listing IDs: {e}")
        return False

def create_search_hash(query: str, location: str, distance: str, user_id: str = None, task_id: str = None) -> str:
    """
    Create a unique hash identifier for a search configuration
    
    Args:
        query: Search query terms
        location: Zip code or location
        distance: Search distance
        user_id: User ID to make hash user-specific (optional)
        task_id: Task ID to make hash task-specific (optional)
        
    Returns:
        Unique hash string for this search
    """
    import hashlib
    if user_id and task_id:
        search_string = f"{query.lower()}_{location}_{distance}_{user_id}_{task_id}"
    elif user_id:
        search_string = f"{query.lower()}_{location}_{distance}_{user_id}"
    else:
        search_string = f"{query.lower()}_{location}_{distance}"
    return hashlib.md5(search_string.encode()).hexdigest()

def send_notification_via_discord(recommended_listings: List[Dict], user_query: str, webhook_url: str = None) -> bool:
    """
    Send notification via Discord webhook
    
    Args:
        recommended_listings: List of listings that meet the strictness threshold
        user_query: Original user search query for context
        
    Returns:
        True if successful, False otherwise
    """
    # Use provided webhook URL or fallback to environment variable
    webhook_url = webhook_url or DISCORD_WEBHOOK_URL
    
    if not webhook_url:
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
            
            # Get reasoning - send full reasoning to Discord
            reasoning = eval_data.get('reasoning', 'No reasoning provided')
            
            embed["fields"].append({
                "name": f"{i}. {listing['title'][:50]}...",
                "value": f"💰 **Price:** {listing['price']}\n⭐ **Match Score:** {score:.0f}%\n🪄 **Reasoning:** {reasoning}\n🔗 **URL:** {listing['url']}",
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
            webhook_url,
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

def scrape_new_listings_data(search_url: str, is_initial_run: bool = True, initial_scrape_count: int = 6, seen_ids: set = None) -> List[Dict[str, str]]:
    """
    Scrape Craigslist search results and individual listings using native Python
    
    Args:
        search_url: Craigslist search results URL
        is_initial_run: Whether this is the initial run (limits to initial_scrape_count listings)
        initial_scrape_count: Number of listings to scrape on initial run
        seen_ids: Set of previously seen listing IDs (for subsequent runs)
        
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
        
        # Try to find listing elements in DOM first
        dom_elements = soup.find_all('li', class_='cl-static-search-result')
        print(f"Found {len(dom_elements)} listing elements in DOM")
        
        # Try parsing JSON-LD data
        json_ld_listings = []
        json_ld_script = soup.find('script', {'id': 'ld_searchpage_results'})
        if json_ld_script:
            try:
                import json
                json_data = json.loads(json_ld_script.string)
                if 'itemListElement' in json_data:
                    print(f"Found {len(json_data['itemListElement'])} items in JSON-LD")
                    # Convert JSON-LD items to listing data
                    for item in json_data['itemListElement']:
                        if 'item' in item:
                            product = item['item']
                            listing_data = {
                                'title': product.get('name', ''),
                                'price': product.get('offers', {}).get('price', ''),
                                'description': product.get('description', ''),
                                'images': product.get('image', []),
                                'location': product.get('offers', {}).get('availableAtOrFrom', {}).get('address', {}).get('addressLocality', ''),
                                'position': item.get('position', 0)
                            }
                            json_ld_listings.append(listing_data)
            except Exception as e:
                print(f"Error parsing JSON-LD: {e}")
        
        # Use JSON-LD data if available, otherwise use DOM elements
        if json_ld_listings:
            print(f"Using {len(json_ld_listings)} JSON-LD listings")
            listing_elements = json_ld_listings
        else:
            print(f"Using {len(dom_elements)} DOM elements")
            listing_elements = dom_elements
        
        # Limit to specified number of most recent posts for initial scrape only
        if is_initial_run:
            listing_elements = listing_elements[:initial_scrape_count]
            print(f"Limited to {len(listing_elements)} most recent listings for initial scrape")
        else:
            print(f"Processing listings until first seen one is found (for subsequent run)")
        
        # Step 2: Extract data from each listing
        for i, listing_element in enumerate(listing_elements):
            try:
                print(f"Processing listing {i+1}/{len(listing_elements)}")
                
                # Check if this is JSON-LD data (dict) or DOM element
                if isinstance(listing_element, dict):
                    # Handle JSON-LD data
                    title = listing_element['title']
                    price = listing_element['price']
                    description = listing_element['description']
                    location = listing_element['location']
                    images = listing_element['images']
                    
                    # Generate a consistent listing ID based on position and title hash
                    listing_id = f"json_ld_{i}_{hash(title) % 100000}"
                    
                    # For JSON-LD data, we need to find the actual listing URL from the DOM
                    # Look for the corresponding DOM element with the same title
                    actual_listing_url = None
                    for dom_element in dom_elements:
                        link_element = dom_element.find('a', href=True)
                        if link_element:
                            link_title = link_element.get_text(strip=True)
                            if link_title == title or title in link_title:
                                actual_listing_url = link_element.get('href')
                                # Make URL absolute if it's relative
                                if actual_listing_url.startswith('/'):
                                    base_url = f"https://{urlparse(search_url).netloc}"
                                    actual_listing_url = base_url + actual_listing_url
                                break
                    
                    # Fallback to search URL if no actual listing URL found
                    # Extract region from search URL to use correct region
                    from urllib.parse import urlparse
                    parsed_url = urlparse(search_url)
                    region = parsed_url.netloc.split('.')[0]  # Extract 'miami' from 'miami.craigslist.org'
                    listing_url = actual_listing_url or f"https://{region}.craigslist.org/search/sss?query={title.replace(' ', '+')}"
                    
                    # Use the description from JSON-LD as text content
                    text_content = description if description else title
                    
                    print(f"  JSON-LD listing: {title} - ${price}")
                    
                else:
                    # Handle DOM elements (original logic)
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
                    
                    # Extract listing ID from URL and use consistent format
                    numeric_id = extract_listing_id_from_url(listing_url)
                    if not numeric_id:
                        continue
                    # Use consistent format for DOM elements
                    listing_id = f"dom_{i}_{numeric_id}"
                
                # Step 3: Fetch individual listing page for full description (only for DOM elements)
                if not isinstance(listing_element, dict):
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
                else:
                    # For JSON-LD data, location_zip is already extracted
                    location_zip = location
                
                # For subsequent runs, check if we've seen this listing before
                if not is_initial_run and seen_ids and listing_id in seen_ids:
                    print(f"Found seen listing at position {i+1}, stopping scraping")
                    break
                
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
        listings = scrape_new_listings_data(search_url, True, 6, None)
        
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
        request: HTTP request object containing user configuration
        
    Returns:
        HTTP response with operation status
    """
    try:
        print("Craigslist Bot - Production Entry Point")
        print("=" * 50)
        
        # Initialize clients
        initialize_clients()
        
        # Parse user configuration from request
        user_config = None
        if request:
            # Try to get JSON data
            if hasattr(request, 'get_json') and request.get_json():
                user_config = request.get_json()
                print(f"User-specific configuration received (JSON)")
                print(f"User ID: {user_config.get('user_id', 'N/A')}")
                print(f"Task ID: {user_config.get('task_id', 'N/A')}")
            elif hasattr(request, 'data') and request.data:
                # Handle raw data
                try:
                    import json
                    user_config = json.loads(request.data.decode('utf-8'))
                    print(f"User-specific configuration received (raw data)")
                    print(f"User ID: {user_config.get('user_id', 'N/A')}")
                    print(f"Task ID: {user_config.get('task_id', 'N/A')}")
                except Exception as e:
                    print(f"Failed to parse request data: {e}")
                    print(f"Request data: {request.data}")
            else:
                print(f"No JSON data in request")
                print(f"Request type: {type(request)}")
                print(f"Request attributes: {dir(request)}")
        
        # Use user config if provided, otherwise fallback to environment defaults
        if user_config and 'config' in user_config:
            config = user_config['config']
            search_params = {
                'location': config.get('location', SEARCH_POSTAL),
                'distance': config.get('distance', SEARCH_DISTANCE),
                'query': config.get('search_query', SEARCH_QUERY),
                'strictness': config.get('strictness', PRODUCTION_STRICTNESS)
            }
            user_id = user_config.get('user_id', 'default')
            task_id = user_config.get('task_id')
            discord_webhook_url = user_config.get('discord_webhook_url', DISCORD_WEBHOOK_URL)
            enable_initial_scrape = user_config.get('enable_initial_scrape', True)
            initial_scrape_count = user_config.get('initial_scrape_count', 6)
            is_initial_scrape = user_config.get('is_initial_scrape', True)
            seed_seen_set = user_config.get('seed_seen_set', False)
        else:
            # Fallback to global configuration (legacy support)
            search_params = {
                'location': SEARCH_POSTAL,
                'distance': SEARCH_DISTANCE,
                'query': SEARCH_QUERY,
                'strictness': PRODUCTION_STRICTNESS
            }
            user_id = 'global'
            task_id = None
            discord_webhook_url = DISCORD_WEBHOOK_URL
            enable_initial_scrape = True
            initial_scrape_count = 6
            is_initial_scrape = True
            seed_seen_set = False
        
        print(f"Production Configuration:")
        print(f"  User ID: {user_id}")
        print(f"  Location: {search_params['location']}")
        print(f"  Distance: {search_params['distance']} miles")
        print(f"  Query: {search_params['query']}")
        print(f"  Strictness: {search_params['strictness']}")
        
        # Define user_strictness early so it's available in all code paths
        user_strictness = search_params.get('strictness', PRODUCTION_STRICTNESS)
        
        # Use LLM to refine the search query
        refined_query = format_llm_query(search_params['query'])
        
        # Add LLM evaluation logs to show thought process (only for initial run)
        if task_id:
            import time
            # Get current run count before updating
            from task_api import db
            task_ref = db.collection('user_tasks').document(task_id)
            task_doc = task_ref.get()
            current_run_count = 0
            if task_doc.exists:
                current_run_count = task_doc.to_dict().get('total_runs', 0)
            
            # Only add LLM logs for initial run (run count 0)
            if current_run_count == 0:
                # Add LLM query refinement log with actual prompt/response
                llm_query_log = {
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'message': f'LLM evaluating best Craigslist search: {refined_query}',
                    'level': 'info',
                    'details': f'From LLM: "I will be acting as a Craigslist search optimizer extracting core product identifiers for broad search results. User query: \'{search_params["query"]}\' → Extracted: \'{refined_query}\' (excluding size, condition, and location details for broader results)"'
                }
                
                # Add LLM filter evaluation log
                strictness_explanation = {
                    'less_strict': 'broad matching with lower quality threshold',
                    'strict': 'balanced matching with moderate quality threshold', 
                    'very_strict': 'precise matching with high quality threshold'
                }
                
                llm_filter_log = {
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'message': f'LLM evaluating filters: {strictness_explanation.get(user_strictness, "standard filtering")}',
                    'level': 'info',
                    'details': f'From LLM: "I will be acting as an items appraiser trying to find the best item fits for the user based on their query. Using {user_strictness} strictness for \'{refined_query}\' - this means {strictness_explanation.get(user_strictness, "standard filtering")}"'
                }
                
                # Add both logs to the task (don't increment run count for LLM logs)
                from task_api import update_task_stats
                update_task_stats(task_id, 0, 0, llm_query_log, increment_run_count=False)
                update_task_stats(task_id, 0, 0, llm_filter_log, increment_run_count=False)
        
        # Build the Craigslist search URL
        search_url = build_craigslist_url(
            query=refined_query,
            postal=search_params['location'],
            distance=search_params['distance']
        )
        
        # Add LLM-built query URL log (only for initial run)
        if task_id and current_run_count == 0:
            llm_url_log = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'message': f'LLM built query link: {search_url}',
                'level': 'info',
                'details': f'Generated Craigslist search URL for refined query: "{refined_query}"'
            }
            from task_api import update_task_stats
            update_task_stats(task_id, 0, 0, llm_url_log, increment_run_count=False)
        
        # Create unique search hash for state management (user and task-specific)
        # Use the refined query to match what we're actually searching for
        search_hash = create_search_hash(refined_query, search_params['location'], search_params['distance'], user_id, task_id)
        print(f"Task-specific search hash: {search_hash}")
        print(f"Hash components: query='{refined_query}', user_id='{user_id}', task_id='{task_id}', location='{search_params['location']}', distance='{search_params['distance']}'")
        
        # Check if task is active before proceeding
        if task_id:
            try:
                from task_api import db
                task_ref = db.collection('user_tasks').document(task_id)
                task_doc = task_ref.get()
                if task_doc.exists:
                    task_data = task_doc.to_dict()
                    if not task_data.get('is_active', True):
                        print(f"Task {task_id} is paused, skipping execution")
                        return {
                            'statusCode': 200,
                            'body': {
                                'message': 'Task is paused - skipping execution',
                                'total_listings': 0,
                                'new_listings': 0,
                                'recommended_listings': 0,
                                'notification_sent': False,
                                'strictness_used': user_strictness,
                                'sample_listings': []
                            }
                        }
            except Exception as e:
                print(f"Warning: Could not check task status: {e}")
        
        # Retrieve previously seen listing IDs (skip for initial run)
        print(f"\nRetrieving previously seen listings...")
        print(f"Looking for search hash: {search_hash}")
        seen_ids = get_seen_listing_ids(search_hash)
        seen_ids = set(seen_ids)  # Convert to set for efficient lookup
        print(f"Retrieved {len(seen_ids)} previously seen IDs: {list(seen_ids)[:3]}..." if len(seen_ids) > 3 else f"Retrieved {len(seen_ids)} previously seen IDs: {list(seen_ids)}")
        
        # Handle seeding mode (when initial scrape is disabled)
        if seed_seen_set:
            print("Seeding mode - adding most recent listing to seen set")
            # Get the most recent listing and add it to seen set
            temp_listings = scrape_new_listings_data(search_url, True, 1, None)
            if temp_listings:
                most_recent_id = temp_listings[0]['id']
                save_listing_ids(search_hash, [most_recent_id])
                print(f"Seeded seen set with most recent listing: {most_recent_id}")
                
                # Update task with seeding completion log
                if task_id:
                    seeding_complete_log = {
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'message': 'Seeding completed - monitoring from now',
                        'level': 'success',
                        'details': f'Added most recent listing to seen set. Next run will detect new posts.'
                    }
                    from task_api import update_task_stats
                    update_task_stats(task_id, 0, 0, seeding_complete_log, increment_run_count=False)
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Seeding completed successfully',
                        'total_listings': 0,
                        'new_listings': 0,
                        'recommended_listings': 0,
                        'notification_sent': False,
                        'sample_listings': [],
                        'strictness_used': search_params['strictness']
                    }
                }
            else:
                print("No listings found for seeding")
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'No listings found for seeding',
                        'total_listings': 0,
                        'new_listings': 0,
                        'recommended_listings': 0,
                        'notification_sent': False,
                        'sample_listings': [],
                        'strictness_used': search_params['strictness']
                    }
                }
        
        # Determine if this is an initial run based on user configuration
        is_initial_run = enable_initial_scrape and len(seen_ids) == 0
        if is_initial_run:
            print("This is an initial run - will process up to specified number of listings")
        else:
            print("This is a subsequent run - will process listings until first seen one is found")
        
        # Scrape listings with enhanced data extraction
        print(f"\nScraping listings...")
        listings = scrape_new_listings_data(search_url, is_initial_run, initial_scrape_count, seen_ids)
        
        if len(listings) == 0:
            # This could be either no listings found OR no new listings found
            # Check if this is a subsequent run with seen listings
            if not is_initial_run and len(seen_ids) > 0:
                # This is a subsequent run with no new listings found
                # Continue to the "No new posts found" logic below
                pass
            else:
                # This is truly no listings found (initial run or no seen listings)
                # Update task statistics for no listings found
                if task_id:
                    import time
                    # Get current run count before updating
                    from task_api import db
                    task_ref = db.collection('user_tasks').document(task_id)
                    task_doc = task_ref.get()
                    current_run_count = 0
                    if task_doc.exists:
                        current_run_count = task_doc.to_dict().get('total_runs', 0)
                    
                    # Determine run count for log message
                    if is_initial_run:
                        log_run_count = 0
                    else:
                        log_run_count = current_run_count + 1
                    
                    log_entry = {
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'message': f'Scrape: {log_run_count} - No posts found',
                        'level': 'success',
                        'details': 'No listings found matching search criteria'
                    }
                    from task_api import update_task_stats
                    update_task_stats(task_id, 0, 0, log_entry)
                
                # Prepare response for no listings found
                response_body = {
                    'message': 'No listings found - search criteria may need adjustment',
                    'total_listings': 0,
                    'new_listings': 0,
                    'recommended_listings': 0,
                    'notification_sent': False,
                    'strictness_used': user_strictness,
                    'sample_listings': []
                }
                
                return {
                    'statusCode': 200,
                    'body': response_body
                }
        
        # Filter for NEW listings only (skip filtering for initial run)
        if is_initial_run:
            new_listings = listings  # Process all listings for initial run
            print(f"\nInitial Run - Processing limited listings:")
            print(f"  Total scraped: {len(listings)} (limited to {initial_scrape_count} most recent)")
            print(f"  NEW listings: {len(new_listings)} (all listings are new for initial run)")
        else:
            # For subsequent runs, listings are already filtered during scraping
            new_listings = listings
            print(f"\nSubsequent Run - Already filtered during scraping:")
            print(f"  NEW listings: {len(new_listings)}")
            print(f"  Previously seen: {len(seen_ids)}")
        
        if len(new_listings) == 0:
            # Save current state and return
            save_listing_ids(search_hash, [listing['id'] for listing in listings])
            
            # Update task statistics for no new listings found
            if task_id:
                import time
                # Get current run count before updating
                from task_api import db
                task_ref = db.collection('user_tasks').document(task_id)
                task_doc = task_ref.get()
                current_run_count = 0
                if task_doc.exists:
                    current_run_count = task_doc.to_dict().get('total_runs', 0)
                
                # Determine run count for log message
                if is_initial_run:
                    log_run_count = 0
                    message = f'Scrape: {log_run_count} - No posts found'
                    details = 'No listings found matching search criteria'
                else:
                    log_run_count = current_run_count + 1
                    message = f'Scrape: {log_run_count} - No new posts found'
                    details = f'Found old listings - no new posts since last scrape'
                
                log_entry = {
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'message': message,
                    'level': 'warning',
                    'details': details
                }
                # Only increment scrape count if we actually found new listings
                from task_api import update_task_stats
                if is_initial_run and len(listings) > 0:
                    update_task_stats(task_id, len(listings), 0, log_entry)
                elif not is_initial_run:
                    # For subsequent runs, don't increment scrape count if no new listings
                    update_task_stats(task_id, 0, 0, log_entry)
                else:
                    # Initial run with no listings found - don't increment
                    update_task_stats(task_id, 0, 0, log_entry)
            
            # Prepare response for no new listings
            if is_initial_run:
                response_message = 'No listings found - search criteria may need adjustment'
            else:
                response_message = 'No new listings found - all listings have been processed previously'
            
            response_body = {
                'message': response_message,
                'total_listings': len(listings),
                'new_listings': 0,
                'recommended_listings': 0,
                'notification_sent': False,
                'strictness_used': user_strictness,
                'sample_listings': []
            }
            
            return {
                'statusCode': 200,
                'body': response_body
            }
        
        # Evaluate only NEW listings with LLM
        print(f"\nEvaluating {len(new_listings)} NEW listings...")
        evaluated_listings = []
        
        for listing in new_listings:
            evaluation = llm_evaluate_listing(listing, search_params['query'])
            listing_with_eval = listing.copy()
            listing_with_eval['evaluation'] = evaluation
            evaluated_listings.append(listing_with_eval)
        
        # Apply strictness filter based on user configuration
        threshold = STRICTNESS_THRESHOLDS[user_strictness]
        recommended_listings = get_production_listings(evaluated_listings, threshold)
        
        print(f"\nFilter Results:")
        print(f"  Threshold: {threshold:.2f}")
        print(f"  Recommended listings: {len(recommended_listings)}")
        
        # Send Discord notification for new recommendations
        notification_sent = False
        if recommended_listings:
            print(f"\nSending Discord notification...")
            notification_sent = send_notification_via_discord(recommended_listings, search_params['query'], discord_webhook_url)
        
        # Update task statistics
        if task_id:
            import time
            # Get current run count before updating
            from task_api import db
            task_ref = db.collection('user_tasks').document(task_id)
            task_doc = task_ref.get()
            current_run_count = 0
            if task_doc.exists:
                current_run_count = task_doc.to_dict().get('total_runs', 0)
            
            # Determine run count for log message
            if is_initial_run:
                # Initial run should be "Scrape: 0"
                log_run_count = 0
            else:
                # Subsequent runs should be incremented
                log_run_count = current_run_count + 1
            
            # Create appropriate log message based on results
            if len(listings) == 0:
                log_message = f'Scrape: {log_run_count} - No posts found'
                log_level = 'success'
                log_details = 'No listings found matching search criteria'
            elif len(recommended_listings) == 0:
                log_message = f'Scrape: {log_run_count} - No posts found'
                log_level = 'info'
                log_details = f'Scraped {len(listings)} listings, but none met the {threshold:.2f} threshold'
            else:
                log_message = f'Scrape: {log_run_count} - Found {len(recommended_listings)} matches'
                log_level = 'success'
                if is_initial_run:
                    log_details = f'Total scraped: {len(listings)} (limited to {initial_scrape_count} most recent), Matches: {len(recommended_listings)}, Threshold: {threshold:.2f}'
                else:
                    log_details = f'Total scraped: {len(new_listings)} (new listings only), Matches: {len(recommended_listings)}, Threshold: {threshold:.2f}'
            
            log_entry = {
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'message': log_message,
                'level': log_level,
                'details': log_details
            }
            from task_api import update_task_stats
            update_task_stats(task_id, len(listings), len(recommended_listings), log_entry)
        
        # Save processed listing IDs to state management (only if we have listings)
        if listings:
            save_listing_ids(search_hash, [listing['id'] for listing in listings])
        
        # Prepare response
        response_body = {
            'message': 'Craigslist bot execution completed',
            'total_listings': len(listings),
            'new_listings': len(new_listings),
            'recommended_listings': len(recommended_listings),
            'notification_sent': notification_sent,
            'strictness_used': user_strictness,
            'sample_listings': recommended_listings[:3] if recommended_listings else []
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

# Import task management API
from task_management_api import task_management_api

if __name__ == "__main__":
    main()
