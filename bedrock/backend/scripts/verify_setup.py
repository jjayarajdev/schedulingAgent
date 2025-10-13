"""
Verification script to test all infrastructure components.

Tests:
1. Configuration loading
2. Database connection
3. Redis connection
4. AWS Bedrock access

Run with: uv run python scripts/verify_setup.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_config() -> bool:
    """Verify configuration loading."""
    print("\n" + "=" * 60)
    print("1. VERIFYING CONFIGURATION")
    print("=" * 60)

    try:
        from app.core.config import get_settings

        settings = get_settings()

        print(f"✅ Configuration loaded successfully")
        print(f"   App name: {settings.app_name}")
        print(f"   Environment: {settings.environment}")
        print(f"   AWS Region: {settings.aws_region}")
        print(f"   Bedrock Model: {settings.bedrock_model_id}")
        print(f"   Intent Threshold: {settings.intent_confidence_threshold}")
        print(f"   Max Tokens: {settings.max_tokens}")

        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


async def verify_database() -> bool:
    """Verify database connection."""
    print("\n" + "=" * 60)
    print("2. VERIFYING DATABASE CONNECTION")
    print("=" * 60)

    try:
        from app.core.database import check_db_health, engine
        from app.core.config import get_settings

        settings = get_settings()

        # Hide credentials in URL
        safe_url = settings.database_url.split("@")[0] + "@***"
        print(f"   Database URL: {safe_url}")

        # Check connection
        is_healthy = await check_db_health()

        if is_healthy:
            print(f"✅ Database connection successful")

            # Get database version
            async with engine.connect() as conn:
                result = await conn.scalar("SELECT version()")
                print(f"   PostgreSQL version: {result.split(',')[0]}")

            return True
        else:
            print(f"❌ Database connection failed")
            return False

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        print(f"   Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
        return False


async def verify_redis() -> bool:
    """Verify Redis connection."""
    print("\n" + "=" * 60)
    print("3. VERIFYING REDIS CONNECTION")
    print("=" * 60)

    try:
        from app.core.redis import check_redis_health, redis_client, session_manager
        from app.core.config import get_settings

        settings = get_settings()

        # Hide credentials in URL
        safe_url = settings.redis_url.split("@")[0] if "@" in settings.redis_url else settings.redis_url
        print(f"   Redis URL: {safe_url}")

        # Check connection
        is_healthy = await check_redis_health()

        if is_healthy:
            print(f"✅ Redis connection successful")

            # Get Redis info
            info = await redis_client.info()
            print(f"   Redis version: {info.get('redis_version', 'unknown')}")
            print(f"   Used memory: {info.get('used_memory_human', 'unknown')}")

            # Test session management
            test_session_id = "test-session-123"
            test_data = {"test": "data", "timestamp": "2025-10-12"}

            await session_manager.set(test_session_id, test_data, ttl=60)
            retrieved = await session_manager.get(test_session_id)

            if retrieved == test_data:
                print(f"✅ Session management working")
            else:
                print(f"⚠️  Session management issue: data mismatch")

            # Cleanup
            await session_manager.delete(test_session_id)

            return True
        else:
            print(f"❌ Redis connection failed")
            return False

    except Exception as e:
        print(f"❌ Redis verification failed: {e}")
        print(f"   Make sure Redis is running and REDIS_URL is correct in .env")
        return False


async def verify_bedrock() -> bool:
    """Verify AWS Bedrock access."""
    print("\n" + "=" * 60)
    print("4. VERIFYING AWS BEDROCK ACCESS")
    print("=" * 60)

    try:
        from app.core.bedrock import check_bedrock_health, claude_client
        from app.core.config import get_settings

        settings = get_settings()

        print(f"   AWS Region: {settings.aws_region}")
        print(f"   Model ID: {settings.bedrock_model_id}")

        # Check Bedrock access
        print(f"   Testing Bedrock invocation (this may take a few seconds)...")

        is_healthy = await check_bedrock_health()

        if is_healthy:
            print(f"✅ Bedrock access successful")
            print(f"✅ Model {settings.bedrock_model_id} is accessible")

            # Test simple invocation
            response = await claude_client.invoke(
                prompt="What is 2+2? Answer with just the number.",
                max_tokens=10,
                temperature=0.0,
            )
            print(f"   Test response: '{response.strip()}'")

            return True
        else:
            print(f"❌ Bedrock access failed")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Bedrock verification failed: {error_str}")

        if "AccessDeniedException" in error_str or "access" in error_str.lower():
            print(f"\n   ⚠️  BEDROCK MODEL ACCESS NOT APPROVED YET")
            print(f"   → Go to AWS Console → Bedrock → Model access")
            print(f"   → Request access to: {settings.bedrock_model_id}")
            print(f"   → Wait 24-48 hours for approval")
            print(f"   → Check email for approval notification")
        elif "credentials" in error_str.lower():
            print(f"\n   ⚠️  AWS CREDENTIALS ISSUE")
            print(f"   → Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            print(f"   → Or configure AWS credentials via `aws configure`")
        else:
            print(f"\n   ⚠️  Check AWS credentials and Bedrock model access")

        return False


async def verify_imports() -> bool:
    """Verify all critical imports."""
    print("\n" + "=" * 60)
    print("0. VERIFYING PACKAGE IMPORTS")
    print("=" * 60)

    imports = {
        "FastAPI": "fastapi",
        "SQLAlchemy": "sqlalchemy",
        "Redis": "redis",
        "Boto3": "boto3",
        "LangGraph": "langgraph",
        "LangChain": "langchain",
        "Pydantic": "pydantic",
        "Structlog": "structlog",
        "Tenacity": "tenacity",
        "Httpx": "httpx",
    }

    all_ok = True
    for name, module in imports.items():
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name}: {e}")
            all_ok = False

    return all_ok


async def main() -> None:
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("BACKEND INFRASTRUCTURE VERIFICATION")
    print("=" * 60)
    print("Testing all infrastructure components...")

    results = {
        "Imports": await verify_imports(),
        "Configuration": await verify_config(),
        "Database": await verify_database(),
        "Redis": await verify_redis(),
        "Bedrock": await verify_bedrock(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for component, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{component:20s} {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 All verification tests passed!")
        print("✅ Backend infrastructure is ready for Phase 2 implementation")
    else:
        print(f"\n⚠️  {failed} verification test(s) failed")
        print("   Fix the issues above before proceeding to Phase 2")

        if not results["Bedrock"]:
            print("\n   📝 NOTE: Bedrock model access approval can take 24-48 hours")
            print("   You can continue with development and test Bedrock later")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
