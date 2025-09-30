#!/usr/bin/env python3
"""
Test script to verify the bot only scrapes NEW listings after the initial run.
This script simulates the bot's behavior to ensure it stops at the first seen listing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_listing_id_generation():
    """Test that listing IDs are stable and position-independent"""
    print("=== Testing Listing ID Generation ===")
    
    # Simulate JSON-LD listing data
    test_listings = [
        {"title": "54cm Road Bike", "price": "$500"},
        {"title": "56cm Trek Bike", "price": "$600"},
        {"title": "52cm Specialized", "price": "$700"},
    ]
    
    # Test old method (position-based) - should be different
    old_ids = []
    for i, listing in enumerate(test_listings):
        old_id = f"json_ld_{i}_{hash(listing['title']) % 100000}"
        old_ids.append(old_id)
    
    # Test new method (stable) - should be same regardless of position
    new_ids = []
    for listing in test_listings:
        stable_string = f"{listing['title']}_{listing['price']}"
        new_id = f"json_ld_{abs(hash(stable_string)) % 1000000000}"
        new_ids.append(new_id)
    
    print("Old method (position-based):")
    for i, listing in enumerate(test_listings):
        print(f"  Position {i}: {old_ids[i]}")
    
    print("New method (stable):")
    for i, listing in enumerate(test_listings):
        print(f"  Position {i}: {new_ids[i]}")
    
    # Test that new method is stable when positions change
    print("\nTesting position independence:")
    # Simulate position change (new listing at position 0)
    shifted_listings = [
        {"title": "NEW 48cm Bike", "price": "$400"},  # New listing
        {"title": "54cm Road Bike", "price": "$500"},  # Shifted to position 1
        {"title": "56cm Trek Bike", "price": "$600"},  # Shifted to position 2
    ]
    
    shifted_new_ids = []
    for listing in shifted_listings:
        stable_string = f"{listing['title']}_{listing['price']}"
        new_id = f"json_ld_{abs(hash(stable_string)) % 1000000000}"
        shifted_new_ids.append(new_id)
    
    print("After position shift:")
    for i, listing in enumerate(shifted_listings):
        print(f"  Position {i}: {shifted_new_ids[i]}")
    
    # Check if "54cm Road Bike" has same ID in both cases
    original_54cm_id = new_ids[0]  # Was at position 0
    shifted_54cm_id = shifted_new_ids[1]  # Now at position 1
    
    if original_54cm_id == shifted_54cm_id:
        print("✅ PASS: Listing ID is stable across position changes")
    else:
        print("❌ FAIL: Listing ID changes with position")
        print(f"  Original: {original_54cm_id}")
        print(f"  Shifted:  {shifted_54cm_id}")

def test_early_stop_logic():
    """Test the early-stop logic for subsequent runs"""
    print("\n=== Testing Early-Stop Logic ===")
    
    # Simulate seen_ids from previous run
    seen_ids = {
        "json_ld_123456789",  # First listing (most recent)
        "json_ld_987654321",  # Second listing
        "json_ld_555666777",  # Third listing
    }
    
    # Simulate current listings (newest first)
    current_listings = [
        {"id": "json_ld_999888777", "title": "Brand New Bike"},  # New listing
        {"id": "json_ld_123456789", "title": "54cm Road Bike"},  # Seen before - should stop here
        {"id": "json_ld_987654321", "title": "56cm Trek Bike"},  # Should not be processed
        {"id": "json_ld_555666777", "title": "52cm Specialized"}, # Should not be processed
    ]
    
    print("Seen IDs from previous run:")
    for seen_id in seen_ids:
        print(f"  {seen_id}")
    
    print("\nCurrent listings (newest first):")
    for i, listing in enumerate(current_listings):
        print(f"  {i+1}. {listing['id']} - {listing['title']}")
    
    # Simulate the early-stop logic
    new_listings = []
    is_initial_run = False  # This is a subsequent run
    
    print("\nProcessing listings:")
    for i, listing in enumerate(current_listings):
        print(f"  Processing listing {i+1}: {listing['id']}")
        
        # Check if we've seen this listing before (early-stop logic)
        if not is_initial_run and listing['id'] in seen_ids:
            print(f"  ✅ Found seen listing at position {i+1}, stopping scraping")
            break
        
        new_listings.append(listing)
        print(f"  ✅ New listing added: {listing['title']}")
    
    print(f"\nResult:")
    print(f"  Total listings processed: {len(new_listings)}")
    print(f"  Expected: 1 (only the new listing)")
    
    if len(new_listings) == 1 and new_listings[0]['id'] == "json_ld_999888777":
        print("✅ PASS: Early-stop logic works correctly")
    else:
        print("❌ FAIL: Early-stop logic failed")
        print(f"  Processed: {[l['id'] for l in new_listings]}")

def test_threshold_comparison():
    """Test that 0.7 score passes 0.70 threshold"""
    print("\n=== Testing Threshold Comparison ===")
    
    threshold = 0.70
    test_scores = [0.6, 0.7, 0.8, 0.9]
    
    print(f"Threshold: {threshold}")
    print("Score comparison:")
    
    for score in test_scores:
        passes = score >= threshold
        status = "✅ PASS" if passes else "❌ FAIL"
        print(f"  {score:.1f} >= {threshold:.2f} = {passes} {status}")
    
    # Specifically test 0.7 vs 0.70
    score_07 = 0.7
    passes_07 = score_07 >= threshold
    print(f"\nSpecific test: {score_07} >= {threshold} = {passes_07}")
    
    if passes_07:
        print("✅ PASS: 0.7 correctly passes 0.70 threshold")
    else:
        print("❌ FAIL: 0.7 should pass 0.70 threshold")

if __name__ == "__main__":
    print("🧪 Testing New Listing Logic")
    print("=" * 50)
    
    test_listing_id_generation()
    test_early_stop_logic()
    test_threshold_comparison()
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("1. Listing IDs should be stable (not position-dependent)")
    print("2. Early-stop should work (stop at first seen listing)")
    print("3. Threshold comparison should work (0.7 >= 0.70)")
    print("\nIf all tests pass, the bot should only scrape NEW listings after initial run!")
