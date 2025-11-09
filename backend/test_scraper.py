"""
Test script for dining scraper
"""
from dining_scraper import DiningScraper

def test_scraper():
    """Test the dining scraper"""
    print("Testing UMass Dining Scraper...")
    print("=" * 60)
    
    scraper = DiningScraper()
    
    # Test dining hall
    print("\n1. Testing Berkshire Dining Hall...")
    berkshire = scraper.get_dining_hall_menu("berkshire")
    if berkshire:
        print(f"   ✓ Successfully scraped {berkshire['name']}")
        print(f"   - Location: {berkshire['location']}")
        print(f"   - Type: {berkshire['type']}")
        print(f"   - Dietary options: {', '.join(berkshire.get('dietary_options', []))}")
        
        # Show meal counts
        for meal_type, items in berkshire.get('meals', {}).items():
            if items:
                print(f"   - {meal_type.capitalize()}: {len(items)} items")
    else:
        print("   ✗ Failed to scrape Berkshire")
    
    # Test Grab 'N Go
    print("\n2. Testing Berkshire Grab 'N Go...")
    grab_n_go = scraper.get_grab_n_go_menu("berkshire")
    if grab_n_go:
        print(f"   ✓ Successfully scraped {grab_n_go['name']}")
        print(f"   - Items: {len(grab_n_go.get('items', []))}")
    else:
        print("   ✗ Failed to scrape Grab 'N Go")
    
    # Test get_all_dining_options
    print("\n3. Testing get_all_dining_options...")
    all_options = scraper.get_all_dining_options(meal_period="lunch")
    print(f"   ✓ Found {len(all_options)} dining options")
    for option in all_options[:3]:
        print(f"   - {option['name']} ({option['type']})")
    
    print("\n" + "=" * 60)
    print("Scraper test completed!")

if __name__ == "__main__":
    test_scraper()

