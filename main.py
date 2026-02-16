"""Main entry point for Garmin Connect sync application."""

import asyncio
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from src.config import Config
from src.sync_manager import SyncManager
from src.utils.logging_config import setup_logging


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string

    Returns:
        Date object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD") from e


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Synchronize Garmin Connect data to PostgreSQL"
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.yaml"),
        help="Path to configuration file (default: config/config.yaml)",
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["daily_health", "activities", "body_composition", "advanced_metrics", "wellness"],
        help="Specific categories to sync (default: all configured categories)",
    )

    parser.add_argument(
        "--mode",
        choices=["incremental", "full"],
        help="Sync mode: incremental or full (default: from config)",
    )

    parser.add_argument(
        "--days-back",
        type=int,
        help="Number of days to go back for full sync (default: from config)",
    )

    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date for sync in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date for sync in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full sync (shortcut for --mode full)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level from config",
    )

    return parser.parse_args()


async def async_main():
    """Async main function."""
    args = parse_args()

    # Load configuration
    try:
        if args.config.exists():
            config = Config.from_yaml(args.config)
        else:
            print(f"Warning: Config file not found at {args.config}, using environment variables")
            config = Config.from_env()

        # Validate configuration
        config.validate()

    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Setup logging
    log_level = args.log_level or config.logging.level
    log_file = None
    if config.logging.log_to_file:
        log_file = config.logging.log_dir / f"garmin_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    setup_logging(
        log_level=log_level,
        log_file=log_file,
        log_to_console=config.logging.log_to_console,
    )

    # Override config with command line args
    if args.full:
        args.mode = "full"

    # Initialize sync manager
    sync_manager = SyncManager(config)

    try:
        await sync_manager.initialize()

        # Perform sync
        report = await sync_manager.sync(
            categories=args.categories,
            mode=args.mode,
            days_back=args.days_back,
            start_date=args.start_date,
            end_date=args.end_date,
            dry_run=args.dry_run,
        )

        # Print report
        print("\n" + "=" * 60)
        print("SYNC REPORT")
        print("=" * 60)

        if report.get("dry_run"):
            print("MODE: DRY RUN")
        else:
            print(f"MODE: {report['mode']}")
            print(f"TOTAL RECORDS: {report['total_records']}")

        print("\nCATEGORIES:")
        for category, info in report["categories"].items():
            if report.get("dry_run"):
                print(f"  {category}:")
                print(f"    Date range: {info['start_date']} to {info['end_date']}")
                print(f"    Days: {info['days']}")
            else:
                status = info["status"].upper()
                print(f"  {category}: {info['records']} records - {status}")
                if info.get("error"):
                    print(f"    Error: {info['error']}")

        if report.get("errors"):
            print("\nERRORS:")
            for error in report["errors"]:
                print(f"  - {error}")

        print("=" * 60)

        # Return exit code based on errors
        return 0 if not report.get("errors") else 1

    except KeyboardInterrupt:
        print("\nSync interrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await sync_manager.cleanup()


def main():
    """Entry point."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
