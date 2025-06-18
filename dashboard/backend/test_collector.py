import asyncio
import sys
from app.services.collector_client import CollectorApiClient
from app.core.config import settings

async def test_collector():
    # Initialize client with direct URL to collector
    client = CollectorApiClient('http://192.168.141.40:8000')
    
    try:
        # Test connection
        print("Testing connection to collector...")
        connected = await client.test_connection()
        print(f"Connection successful: {connected}")
        
        if not connected:
            return False
        
        # Get events with pagination
        print("Fetching events with pagination...")
        events_data = await client.get_events({"limit": 10, "offset": 0})
        
        events = events_data.get("events", [])
        total = events_data.get("total", 0)
        
        print(f"Retrieved {len(events)} events (out of {total} total)")
        
        if events:
            print("\nSample event:")
            print(events[0])
        
        # Get events summary
        print("\nFetching events summary...")
        summary = await client.get_events_summary()
        
        by_component = summary.get("by_component", {})
        by_level = summary.get("by_level", {})
        total_summary = summary.get("total", 0)
        
        print(f"Events summary: {total_summary} total events")
        print(f"By component: {by_component}")
        print(f"By level: {by_level}")
        
        return True
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_collector()) 