"""
Test script for bus schedule PDF parser
"""
import os
import json
from dotenv import load_dotenv
from bus_schedule_parser import BusScheduleParser

load_dotenv()

def test_bus_parser():
    """Test the bus schedule parser"""
    print("Testing Bus Schedule PDF Parser...")
    print("=" * 60)
    
    # Check if PDF URLs are set
    pdf_urls_config = os.getenv("BUS_SCHEDULE_PDF_URLS")
    pdf_url_single = os.getenv("BUS_SCHEDULE_PDF_URL")
    
    if not pdf_urls_config and not pdf_url_single:
        print("⚠️  Warning: BUS_SCHEDULE_PDF_URLS or BUS_SCHEDULE_PDF_URL not set in .env file")
        print("   Add this to your .env file:")
        print('   BUS_SCHEDULE_PDF_URLS={"30": "https://example.com/route-30.pdf", "31": "https://example.com/route-31.pdf"}')
        return
    
    if pdf_urls_config:
        try:
            urls = json.loads(pdf_urls_config)
            print(f"✓ PDF URLs configured for {len(urls)} routes: {', '.join(urls.keys())}")
        except json.JSONDecodeError:
            print("⚠️  Warning: BUS_SCHEDULE_PDF_URLS is not valid JSON")
            return
    else:
        print(f"✓ Single PDF URL configured: {pdf_url_single[:50]}...")
    
    # Initialize parser
    parser = BusScheduleParser()
    
    # Test PDF parsing
    print("\nParsing PDF schedule...")
    try:
        schedule_data = parser.parse_pdf(use_cache=True)
        
        if "error" in schedule_data:
            print(f"❌ Error: {schedule_data['error']}")
            return
        
        schedules = schedule_data.get("schedules", {})
        print(f"✓ Parsed {len(schedules)} routes from PDF")
        
        # Show sample routes
        print("\nSample routes found:")
        for i, (route_num, route_data) in enumerate(list(schedules.items())[:5]):
            stops = route_data.get("stops", [])
            print(f"  {route_num}: {len(stops)} stops - {', '.join(stops[:3])}")
        
        # Test route lookup with route-specific PDFs
        print("\nTesting route lookup...")
        test_routes = list(parser.pdf_urls.keys())
        if "_default" in test_routes:
            test_routes.remove("_default")
        
        # Test a few common routes
        test_routes = test_routes[:3] if test_routes else ["30", "31", "B43"]
        
        for route_num in test_routes:
            routes = parser.find_route(route_number=route_num)
            if routes:
                print(f"  ✓ Route {route_num}: Found")
            else:
                print(f"  ✗ Route {route_num}: Not found")
        
        # Test next bus times
        print("\nTesting next bus times...")
        next_times = parser.get_next_bus_times(route_number="30", stop="Campus Center")
        if "error" not in next_times:
            print(f"  ✓ Next buses: {', '.join(next_times.get('next_times', [])[:5])}")
        else:
            print(f"  ⚠️  {next_times.get('error', 'Unknown error')}")
        
        print("\n✓ Bus schedule parser is working!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bus_parser()

