#!/usr/bin/env python3
"""
Test Discord webhook functionality
"""

from main import send_notification_via_discord

def test_discord():
    print("=== Discord Webhook Test ===")
    
    test_listings = [{
        'title': '54cm Cannondale CAAD8 Road Bike - Perfect Match!',
        'price': '$895',
        'url': 'https://sfbay.craigslist.org/sfc/bik/d/san-francisco-54cm-cannondale-caad8/7855175150.html',
        'evaluation': {'match_score': 0.98}
    }, {
        'title': '54cm Novara Carema Carbon Road Bike Shimano 105',
        'price': '$520',
        'url': 'https://sfbay.craigslist.org/sfc/bik/d/san-francisco-54cm-novara-carema-carbon/7862084694.html',
        'evaluation': {'match_score': 0.96}
    }, {
        'title': '54cm Trek Lexa SLX Road Bike Shimano Components',
        'price': '$550',
        'url': 'https://sfbay.craigslist.org/eby/bik/d/oakland-54cm-trek-lexa-slx-road-hybrid/7881930891.html',
        'evaluation': {'match_score': 0.92}
    }]
    
    print('Sending test Discord webhook...')
    result = send_notification_via_discord(test_listings, '54cm road bike shimano 105')
    
    if result:
        print('✅ Discord webhook test successful!')
        print('Check your Discord channel for the notification.')
    else:
        print('❌ Discord webhook test failed')
        print('Check your webhook URL in .env file')

if __name__ == '__main__':
    test_discord()
