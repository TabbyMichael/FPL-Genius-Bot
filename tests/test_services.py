#!/usr/bin/env python3
"""
Simple test script for FPL Bot services
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.fpl_api import FPLAPI
from services.health_check import get_health_report

async def test_fpl_api():
    """Test FPL API connectivity"""
    print("Testing FPL API connectivity...")
    async with FPLAPI() as api:
        data = await api.get_bootstrap_data()
        if data:
            print(f"✓ FPL API connection successful")
            print(f"  Elements: {len(data.get('elements', []))}")
            print(f"  Teams: {len(data.get('teams', []))}")
            print(f"  Events: {len(data.get('events', []))}")
            return True
        else:
            print("✗ FPL API connection failed")
            return False

async def test_health_check():
    """Test health check service"""
    print("\nTesting health check service...")
    report = await get_health_report()
    print(report)
    return "API Connectivity: ✓" in report and "Database Connectivity: ✓" in report

async def main():
    """Main test function"""
    print("FPL Bot Service Tests")
    print("=" * 30)
    
    # Test FPL API
    api_success = await test_fpl_api()
    
    # Test health check
    health_success = await test_health_check()
    
    print("\n" + "=" * 30)
    print("Test Results")
    print("=" * 30)
    print(f"FPL API: {'PASS' if api_success else 'FAIL'}")
    print(f"Health Check: {'PASS' if health_success else 'FAIL'}")
    
    if api_success and health_success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))