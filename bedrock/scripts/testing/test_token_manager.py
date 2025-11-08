#!/usr/bin/env python3
"""
Test script for TokenManager module
Tests token retrieval, caching, and authentication
"""
import os
import sys
import time

# Add lambda/shared to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lambda', 'shared'))

# Set environment variables
os.environ['TOKEN_SECRET_NAME'] = 'projectforce/api/dev/credentials'
os.environ['AWS_REGION'] = 'us-east-1'

from token_manager import get_bearer_token, get_token_manager

def test_token_retrieval():
    """Test 1: Basic token retrieval"""
    print("=" * 60)
    print("Test 1: Basic Token Retrieval")
    print("=" * 60)

    try:
        token = get_bearer_token()
        print(f"✅ Token retrieved successfully")
        print(f"   Token length: {len(token)} characters")
        print(f"   Token preview: {token[:60]}...")
        return True
    except Exception as e:
        print(f"❌ Token retrieval failed: {e}")
        return False

def test_token_caching():
    """Test 2: Token caching"""
    print("\n" + "=" * 60)
    print("Test 2: Token Caching")
    print("=" * 60)

    try:
        # First call
        print("Fetching token (should hit Secrets Manager)...")
        start_time = time.time()
        token1 = get_bearer_token()
        time1 = time.time() - start_time
        print(f"   First call took: {time1:.3f} seconds")

        # Second call (should be cached)
        print("\nFetching token again (should use cache)...")
        start_time = time.time()
        token2 = get_bearer_token()
        time2 = time.time() - start_time
        print(f"   Second call took: {time2:.3f} seconds")

        if token1 == token2:
            print(f"✅ Token caching works (tokens match)")
            print(f"   Cache speedup: {time1/time2:.1f}x faster")
            return True
        else:
            print(f"❌ Token caching failed (tokens don't match)")
            return False

    except Exception as e:
        print(f"❌ Caching test failed: {e}")
        return False

def test_token_info():
    """Test 3: Token manager info"""
    print("\n" + "=" * 60)
    print("Test 3: Token Manager Info")
    print("=" * 60)

    try:
        manager = get_token_manager()
        print(f"Secret Name: {manager.secret_name}")
        print(f"Region: {manager.region}")
        print(f"Cache TTL: {manager.cache_ttl} seconds")
        print(f"Cache Valid: {manager._is_cache_valid()}")

        if manager._cache_expiry:
            from datetime import datetime
            expiry = datetime.fromtimestamp(manager._cache_expiry)
            print(f"Cache Expiry: {expiry}")

        print("✅ Token manager info retrieved")
        return True
    except Exception as e:
        print(f"❌ Info test failed: {e}")
        return False

def test_force_refresh():
    """Test 4: Force refresh"""
    print("\n" + "=" * 60)
    print("Test 4: Force Token Refresh")
    print("=" * 60)

    try:
        # Get cached token
        token1 = get_bearer_token()
        print(f"Cached token: {token1[:60]}...")

        # Force refresh
        print("\nForcing token refresh...")
        token2 = get_bearer_token(force_refresh=True)
        print(f"Refreshed token: {token2[:60]}...")

        print("✅ Force refresh completed")
        print(f"   Tokens {'match (same session)' if token1 == token2 else 'differ (new session)'}")
        return True
    except Exception as e:
        print(f"❌ Force refresh test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("ProjectForce Token Manager - Test Suite")
    print("=" * 60)
    print(f"Secret: {os.environ['TOKEN_SECRET_NAME']}")
    print(f"Region: {os.environ['AWS_REGION']}")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(("Token Retrieval", test_token_retrieval()))
    results.append(("Token Caching", test_token_caching()))
    results.append(("Token Manager Info", test_token_info()))
    results.append(("Force Refresh", test_force_refresh()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)

    print("\n" + "=" * 60)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print("=" * 60 + "\n")

    return passed_tests == total_tests

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
