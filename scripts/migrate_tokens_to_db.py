"""One-shot migration: read Garmin tokens from filesystem and store encrypted in DB.

Usage:
    GARMIN_TOKEN_KEY=<key> POSTGRES_PASSWORD=<pwd> python scripts/migrate_tokens_to_db.py [--tokens-dir ~/.garminconnect] [--user-id 1]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DatabaseConfig
from src.database import Database
from src.token_manager import TokenManager


async def main():
    parser = argparse.ArgumentParser(description="Migrate Garmin tokens from filesystem to DB")
    parser.add_argument("--tokens-dir", default=os.environ.get("GARMIN_TOKENS_DIR", str(Path.home() / ".garminconnect")))
    parser.add_argument("--user-id", type=int, default=None, help="garmin_user.user_id to store tokens for (default: first user)")
    args = parser.parse_args()

    tokens_dir = Path(args.tokens_dir)
    if not tokens_dir.exists():
        print(f"Tokens directory not found: {tokens_dir}")
        sys.exit(1)

    # Load garth tokens as JSON blob
    import garth
    client = garth.Client()
    client.load(str(tokens_dir))
    token_data = client.dumps()
    print(f"Loaded tokens from {tokens_dir} ({len(token_data)} bytes)")

    # Encrypt
    tm = TokenManager()
    encrypted = tm.encrypt(token_data)
    print(f"Encrypted tokens: {len(encrypted)} bytes")

    # Store in DB
    db_config = DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "garmin_connect"),
        user=os.environ.get("POSTGRES_USER", "garmin"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )
    db = Database(db_config)
    await db.connect()

    try:
        user_id = args.user_id
        if user_id is None:
            user_id = await db.query_first_user()
            if user_id is None:
                print("No users found in database")
                sys.exit(1)

        await db.store_encrypted_tokens(user_id, encrypted)
        print(f"Stored encrypted tokens for user_id={user_id}")

        # Verify round-trip
        stored = await db.get_encrypted_tokens(user_id)
        decrypted = tm.decrypt(stored)
        assert decrypted == token_data, "Round-trip verification failed!"
        print("Round-trip verification OK")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
