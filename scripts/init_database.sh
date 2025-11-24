#!/bin/bash

################################################################################
# Database Initialization Script
#
# This script initializes the PostgreSQL database with Alembic migrations
#
# Usage: ./init_database.sh
#
# Prerequisites:
# - PostgreSQL database created (Aurora or local)
# - Database URL configured in environment or .env file
# - Python backend dependencies installed
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Database Initialization Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")/../backend"

################################################################################
# Step 1: Check Prerequisites
################################################################################

echo -e "${YELLOW}Step 1: Checking Prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check if backend dependencies are installed
if ! python3 -c "import alembic" &> /dev/null; then
    echo -e "${YELLOW}⚠ Alembic not installed, installing dependencies...${NC}"
    pip install -r requirements.txt
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    if [ -f .env ]; then
        echo "Loading DATABASE_URL from .env file..."
        export $(grep DATABASE_URL .env | xargs)
    else
        echo -e "${RED}✗ DATABASE_URL not set${NC}"
        echo "Please set DATABASE_URL environment variable or create .env file"
        echo ""
        echo "Example:"
        echo "  export DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/dbname'"
        exit 1
    fi
fi

echo -e "${GREEN}✓ DATABASE_URL configured${NC}"
echo ""

################################################################################
# Step 2: Initialize Alembic (if not already done)
################################################################################

echo -e "${YELLOW}Step 2: Initializing Alembic...${NC}"

if [ ! -d "alembic" ]; then
    echo "Creating Alembic directory..."
    alembic init alembic

    # Update alembic.ini with database URL
    echo "Configuring alembic.ini..."
    sed -i.bak "s|sqlalchemy.url = .*|# sqlalchemy.url = set_via_env_variable|" alembic.ini

    # Update alembic/env.py to use our database config
    cat > alembic/env.py << 'ENVPY'
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, metadata
from app.core.config import get_settings
import app.models  # Import all models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = metadata

# Get database URL from settings
settings = get_settings()
database_url = settings.database_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn,
                    target_metadata=target_metadata
                )
            )

            async with connection.begin() as transaction:
                await connection.run_sync(lambda _: context.run_migrations())

    import asyncio
    asyncio.run(do_run_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
ENVPY

    echo -e "${GREEN}✓ Alembic initialized${NC}"
else
    echo -e "${GREEN}✓ Alembic already initialized${NC}"
fi

echo ""

################################################################################
# Step 3: Create Initial Migration
################################################################################

echo -e "${YELLOW}Step 3: Creating Database Migration...${NC}"

# Create migration
alembic revision --autogenerate -m "Initial schema: sessions, messages, appointments, customers"

echo -e "${GREEN}✓ Migration created${NC}"
echo ""

################################################################################
# Step 4: Apply Migration
################################################################################

echo -e "${YELLOW}Step 4: Applying Migration to Database...${NC}"

# Apply migrations
alembic upgrade head

echo -e "${GREEN}✓ Migration applied${NC}"
echo ""

################################################################################
# Step 5: Verify Tables Created
################################################################################

echo -e "${YELLOW}Step 5: Verifying Database Schema...${NC}"

# Use Python to verify tables
python3 << 'PYCHECK'
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check_tables():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        return tables

tables = asyncio.run(check_tables())

print(f"\n✓ Found {len(tables)} tables:")
for table in tables:
    print(f"  - {table}")

expected_tables = ['sessions', 'messages', 'conversation_summaries', 'appointments', 'customers']
missing = [t for t in expected_tables if t not in tables]

if missing:
    print(f"\n⚠ Missing tables: {', '.join(missing)}")
else:
    print("\n✓ All expected tables created")
PYCHECK

echo ""

################################################################################
# Step 6: Summary
################################################################################

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Database Initialization Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}Database Tables:${NC}"
echo "  1. sessions - Conversation sessions"
echo "  2. messages - Chat messages"
echo "  3. conversation_summaries - Conversation analytics"
echo "  4. appointments - Scheduled appointments"
echo "  5. customers - Customer profiles"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update Lambda functions to use real database (set USE_MOCK_API=false)"
echo "2. Configure PF360 API credentials in AWS Secrets Manager"
echo "3. Test end-to-end with real data"
echo ""
echo -e "${BLUE}To rollback last migration:${NC}"
echo "  alembic downgrade -1"
echo ""
echo -e "${BLUE}To view current migration:${NC}"
echo "  alembic current"
echo ""
echo -e "${GREEN}All done! 🎉${NC}"
