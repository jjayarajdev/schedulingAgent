"""
External Configuration Loader for ProjectForce Orchestrator

Loads status and category configuration from S3 with in-memory caching.
This allows business users to update configuration without code deployments.

Usage:
    from config_loader import (
        get_schedulable_statuses,
        get_scheduled_statuses,
        get_status_group,
        get_category_bucket,
        get_outdoor_categories,
        resolve_status_alias,
        resolve_category_alias,
    )
"""
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG_BUCKET = os.environ.get('CONFIG_BUCKET', 'pf-syn-config-dev')
CONFIG_PREFIX = os.environ.get('CONFIG_PREFIX', 'orchestrator')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
CACHE_TTL_SECONDS = int(os.environ.get('CONFIG_CACHE_TTL', '300'))  # 5 minutes default

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE STATE
# ═══════════════════════════════════════════════════════════════════════════════

_cache: Dict[str, Any] = {}
_cache_timestamps: Dict[str, float] = {}
_s3_client = None


def _get_s3_client():
    """Get or create S3 client (singleton)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def _is_cache_valid(key: str) -> bool:
    """Check if cached value is still valid."""
    if key not in _cache or key not in _cache_timestamps:
        return False
    age = time.time() - _cache_timestamps[key]
    return age < CACHE_TTL_SECONDS


def _load_config_from_s3(filename: str) -> Dict:
    """Load a config file from S3."""
    s3_key = f"{CONFIG_PREFIX}/{ENVIRONMENT}/{filename}"

    try:
        logger.info(f"[CONFIG] Loading s3://{CONFIG_BUCKET}/{s3_key}")
        response = _get_s3_client().get_object(Bucket=CONFIG_BUCKET, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        config = json.loads(content)
        logger.info(f"[CONFIG] Loaded {filename} (version: {config.get('version', 'unknown')})")
        return config
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"[CONFIG] Failed to load {filename} from S3: {error_code}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[CONFIG] Invalid JSON in {filename}: {e}")
        raise


def _get_config(config_name: str) -> Dict:
    """Get config with caching."""
    cache_key = f"config_{config_name}"

    if _is_cache_valid(cache_key):
        return _cache[cache_key]

    # Load from S3
    config = _load_config_from_s3(f"{config_name}.json")

    # Update cache
    _cache[cache_key] = config
    _cache_timestamps[cache_key] = time.time()

    return config


def invalidate_cache():
    """Force reload of all configs on next access."""
    global _cache, _cache_timestamps
    _cache = {}
    _cache_timestamps = {}
    logger.info("[CONFIG] Cache invalidated")


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

def get_statuses_config() -> Dict:
    """Get the full statuses configuration."""
    return _get_config('statuses')


def get_status_group(group_name: str) -> Set[str]:
    """
    Get statuses for a specific group.

    Args:
        group_name: One of 'schedulable', 'scheduled', 'in_progress', 'completed', 'on_hold', 'cancelled'

    Returns:
        Set of status strings in that group
    """
    config = get_statuses_config()
    group = config.get('status_groups', {}).get(group_name, {})
    return set(group.get('statuses', []))


def get_schedulable_statuses() -> Set[str]:
    """Get statuses that indicate a project can be scheduled."""
    return get_status_group('schedulable')


def get_scheduled_statuses() -> Set[str]:
    """Get statuses that indicate a project has an appointment."""
    return get_status_group('scheduled')


def get_completed_statuses() -> Set[str]:
    """Get statuses that indicate a project is finished."""
    return get_status_group('completed')


def get_on_hold_statuses() -> Set[str]:
    """Get statuses that indicate a project is blocked/waiting."""
    return get_status_group('on_hold')


def resolve_status_alias(user_term: str) -> Optional[str]:
    """
    Resolve a user's status term to a canonical group name.

    Args:
        user_term: What the user said (e.g., "on the books", "ready to go")

    Returns:
        Canonical group name (e.g., "scheduled", "schedulable") or None
    """
    config = get_statuses_config()
    aliases = config.get('aliases', {})
    return aliases.get(user_term.lower())


def get_all_status_groups() -> Dict[str, Set[str]]:
    """Get all status groups as a dict."""
    config = get_statuses_config()
    return {
        name: set(group.get('statuses', []))
        for name, group in config.get('status_groups', {}).items()
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

def get_categories_config() -> Dict:
    """Get the full categories configuration."""
    return _get_config('categories')


def get_category_bucket(bucket_name: str) -> Set[str]:
    """
    Get keywords for a category bucket.

    Args:
        bucket_name: One of 'kitchen', 'appliances', 'flooring', etc.

    Returns:
        Set of keywords that map to this bucket
    """
    config = get_categories_config()
    bucket = config.get('buckets', {}).get(bucket_name, {})
    return set(bucket.get('keywords', []))


def get_all_category_buckets() -> Dict[str, Set[str]]:
    """Get all category buckets as a dict of bucket_name -> keywords."""
    config = get_categories_config()
    return {
        name: set(bucket.get('keywords', []))
        for name, bucket in config.get('buckets', {}).items()
    }


def get_outdoor_categories() -> List[str]:
    """Get list of category buckets that are outdoor projects."""
    config = get_categories_config()
    return config.get('outdoor_buckets', [])


def is_outdoor_category(bucket_name: str) -> bool:
    """Check if a category bucket is for outdoor projects."""
    return bucket_name.lower() in get_outdoor_categories()


def resolve_category_alias(user_term: str) -> Optional[str]:
    """
    Resolve a user's category term to a canonical bucket name.

    Args:
        user_term: What the user said (e.g., "kitchen appliances", "floor project")

    Returns:
        Canonical bucket name (e.g., "kitchen", "flooring") or None
    """
    config = get_categories_config()
    aliases = config.get('aliases', {})
    return aliases.get(user_term.lower())


def find_category_bucket_for_keyword(keyword: str) -> Optional[str]:
    """
    Find which bucket a keyword belongs to.

    Args:
        keyword: A category keyword (e.g., "dishwasher", "carpet")

    Returns:
        Bucket name (e.g., "kitchen", "flooring") or None
    """
    keyword_lower = keyword.lower()
    config = get_categories_config()

    for bucket_name, bucket_config in config.get('buckets', {}).items():
        keywords = {k.lower() for k in bucket_config.get('keywords', [])}
        if keyword_lower in keywords:
            return bucket_name

    return None


def get_category_voice_name(bucket_name: str) -> str:
    """
    Get the voice-friendly name for a category bucket.

    Args:
        bucket_name: Internal bucket name (e.g., "windows_doors")

    Returns:
        Voice-friendly name (e.g., "window and door")
    """
    config = get_categories_config()
    bucket = config.get('buckets', {}).get(bucket_name, {})
    return bucket.get('voice_name', bucket_name)


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK VALUES (used if S3 load fails)
# ═══════════════════════════════════════════════════════════════════════════════

FALLBACK_SCHEDULABLE_STATUSES = {"New", "Ready To Schedule"}
FALLBACK_SCHEDULED_STATUSES = {"Scheduled", "Tentatively Scheduled"}
FALLBACK_CATEGORY_BUCKETS = {
    "kitchen": {"dishwasher", "oven", "range", "microwave", "cooktop"},
    "flooring": {"carpet", "hardwood", "vinyl", "tile", "laminate"},
    "decking": {"deck", "decking", "patio"},
}


def get_schedulable_statuses_safe() -> Set[str]:
    """Get schedulable statuses with fallback if S3 fails."""
    try:
        return get_schedulable_statuses()
    except Exception as e:
        logger.warning(f"[CONFIG] Using fallback schedulable statuses: {e}")
        return FALLBACK_SCHEDULABLE_STATUSES


def get_scheduled_statuses_safe() -> Set[str]:
    """Get scheduled statuses with fallback if S3 fails."""
    try:
        return get_scheduled_statuses()
    except Exception as e:
        logger.warning(f"[CONFIG] Using fallback scheduled statuses: {e}")
        return FALLBACK_SCHEDULED_STATUSES


def get_all_category_buckets_safe() -> Dict[str, Set[str]]:
    """Get category buckets with fallback if S3 fails."""
    try:
        return get_all_category_buckets()
    except Exception as e:
        logger.warning(f"[CONFIG] Using fallback category buckets: {e}")
        return FALLBACK_CATEGORY_BUCKETS
