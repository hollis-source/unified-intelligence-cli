#!/usr/bin/env python3
"""
Cache Management Utility - Clear LLM response cache.

Usage:
    python scripts/clear_cache.py          # Clear all cached responses
    python scripts/clear_cache.py --stats  # Show cache statistics
    python scripts/clear_cache.py --help   # Show this help

Clean Architecture: Utility script for operational tasks.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.agent.llm_cache import LLMResponseCache, CacheConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_cache() -> None:
    """Clear all cached LLM responses."""
    cache = LLMResponseCache()

    if not cache.enabled:
        logger.error("❌ Cache is not enabled (Redis not available or disabled)")
        logger.info("   To enable cache:")
        logger.info("   1. Ensure Redis is running: sudo systemctl start redis")
        logger.info("   2. Check Redis connection: redis-cli ping")
        sys.exit(1)

    # Get stats before clearing
    stats = cache.get_stats()
    cached_count = stats.get("cached_responses", 0)

    if cached_count == 0:
        logger.info("✓ Cache is already empty (0 entries)")
        return

    # Clear cache
    logger.info(f"🗑️  Clearing {cached_count} cached responses...")
    success = cache.clear_all()

    if success:
        logger.info(f"✅ Cache cleared successfully ({cached_count} entries removed)")
    else:
        logger.error("❌ Failed to clear cache")
        sys.exit(1)


def show_stats() -> None:
    """Show cache statistics."""
    cache = LLMResponseCache()

    if not cache.enabled:
        logger.error("❌ Cache is not enabled (Redis not available or disabled)")
        sys.exit(1)

    stats = cache.get_stats()

    logger.info("📊 Cache Statistics:")
    logger.info(f"   Backend: {stats.get('backend', 'unknown')}")
    logger.info(f"   Host: {stats.get('host', 'unknown')}")
    logger.info(f"   Cached Responses: {stats.get('cached_responses', 0)}")
    logger.info(f"   TTL: {stats.get('ttl_seconds', 0)} seconds ({stats.get('ttl_seconds', 0) / 3600:.1f} hours)")

    # Hit rate
    hits = stats.get('keyspace_hits', 0)
    misses = stats.get('keyspace_misses', 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0

    logger.info(f"   Cache Hits: {hits}")
    logger.info(f"   Cache Misses: {misses}")
    logger.info(f"   Hit Rate: {hit_rate:.1f}%")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage LLM response cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/clear_cache.py          # Clear all cached responses
  python scripts/clear_cache.py --stats  # Show cache statistics

Cache Details:
  - Backend: Redis (localhost:6379 by default)
  - Key Prefix: llm_cache:*
  - TTL: 4 hours (14400 seconds)
  - Use --no-cache flag to bypass cache for specific runs

Clean Architecture:
  This utility is part of the adapter layer (infrastructure concern).
  Cache clearing does not affect business logic or entities.
        """
    )

    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Show cache statistics instead of clearing'
    )

    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        clear_cache()


if __name__ == "__main__":
    main()
