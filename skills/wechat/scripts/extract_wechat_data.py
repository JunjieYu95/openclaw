#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
WeChat Data Extractor

Now that we confirmed databases are readable, this script:
1. Identifies which databases contain what data
2. Extracts contacts, messages, and Moments
3. Outputs structured data for summarization

Usage:
    uv run extract_wechat_data.py --list-tables
    uv run extract_wechat_data.py --contacts
    uv run extract_wechat_data.py --messages [--limit 50]
    uv run extract_wechat_data.py --moments [--limit 20]
    uv run extract_wechat_data.py --all
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# WeChat data location
WECHAT_CONTAINER = Path.home() / "Library/Containers/com.tencent.xinWeChat"
WECHAT_GROUP = Path.home() / "Library/Group Containers/group.com.tencent.xinWeChat"


def find_databases() -> list[Path]:
    """Find all WeChat databases."""
    databases = []

    for base in [WECHAT_CONTAINER, WECHAT_GROUP]:
        if base.exists():
            for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
                databases.extend(base.rglob(pattern))

    return sorted(set(databases), key=lambda x: x.stat().st_size, reverse=True)


def get_db_tables(db_path: Path) -> list[str]:
    """Get all tables in a database."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except:
        return []


def analyze_all_databases():
    """Analyze all databases and categorize them."""
    print("=" * 60)
    print("Analyzing WeChat Databases")
    print("=" * 60)

    databases = find_databases()

    categorized = {
        "contacts": [],
        "messages": [],
        "moments_sns": [],
        "media": [],
        "settings": [],
        "other": [],
    }

    for db_path in databases:
        tables = get_db_tables(db_path)
        tables_lower = [t.lower() for t in tables]

        # Categorize based on table names
        if any("contact" in t or "friend" in t for t in tables_lower):
            categorized["contacts"].append((db_path, tables))
        if any("message" in t or "msg" in t or "chat" in t for t in tables_lower):
            categorized["messages"].append((db_path, tables))
        if any("sns" in t or "moment" in t or "timeline" in t or "pyq" in t for t in tables_lower):
            categorized["moments_sns"].append((db_path, tables))
        if any("media" in t or "image" in t or "video" in t or "voice" in t for t in tables_lower):
            categorized["media"].append((db_path, tables))
        if any("setting" in t or "config" in t or "preference" in t for t in tables_lower):
            categorized["settings"].append((db_path, tables))

        # If not categorized, add to other
        categorized_elsewhere = False
        for cat, items in categorized.items():
            if cat != "other" and any(db_path == item[0] for item in items):
                categorized_elsewhere = True
                break
        if not categorized_elsewhere:
            categorized["other"].append((db_path, tables))

    # Print summary
    for category, items in categorized.items():
        if items:
            print(f"\n{category.upper()} ({len(items)} databases):")
            for db_path, tables in items[:5]:
                print(f"  {db_path.name}")
                print(f"    Tables: {tables[:5]}{'...' if len(tables) > 5 else ''}")

    return categorized


def list_all_tables():
    """List all tables across all databases."""
    print("=" * 60)
    print("All Tables in WeChat Databases")
    print("=" * 60)

    databases = find_databases()
    all_tables = {}

    for db_path in databases:
        tables = get_db_tables(db_path)
        for table in tables:
            if table not in all_tables:
                all_tables[table] = []
            all_tables[table].append(db_path)

    # Sort by frequency
    sorted_tables = sorted(all_tables.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"\nUnique tables found: {len(all_tables)}")
    print("\nMost common tables:")
    for table, dbs in sorted_tables[:30]:
        print(f"  {table}: in {len(dbs)} database(s)")

    # Look for interesting tables
    print("\n" + "-" * 40)
    print("Tables likely containing user data:")
    keywords = ['contact', 'friend', 'message', 'msg', 'chat', 'sns', 'moment',
                'timeline', 'user', 'account', 'session', 'conversation']

    for table, dbs in sorted_tables:
        if any(kw in table.lower() for kw in keywords):
            print(f"  {table}")
            # Show sample DB and schema
            try:
                conn = sqlite3.connect(str(dbs[0]))
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info([{table}])")
                columns = [row[1] for row in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                count = cursor.fetchone()[0]
                conn.close()
                print(f"    Rows: {count}, Columns: {columns[:6]}...")
            except Exception as e:
                print(f"    Error: {e}")


def extract_from_table(db_path: Path, table: str, limit: int = 50) -> list[dict]:
    """Extract data from a specific table."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM [{table}] LIMIT {limit}")
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(dict(row))

        conn.close()
        return result
    except Exception as e:
        print(f"Error extracting from {table}: {e}")
        return []


def find_and_extract_contacts(limit: int = 100) -> list[dict]:
    """Find and extract contacts."""
    print("\n" + "=" * 60)
    print("Extracting Contacts")
    print("=" * 60)

    databases = find_databases()
    contacts = []

    for db_path in databases:
        tables = get_db_tables(db_path)

        for table in tables:
            if any(kw in table.lower() for kw in ['contact', 'friend', 'wccontact']):
                print(f"\nFound contact table: {table} in {db_path.name}")

                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Get column names
                    cursor.execute(f"PRAGMA table_info([{table}])")
                    columns = [row[1] for row in cursor.fetchall()]
                    print(f"  Columns: {columns}")

                    # Extract data
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT {limit}")
                    rows = cursor.fetchall()

                    for row in rows:
                        contact = dict(row)
                        contacts.append(contact)

                    print(f"  Extracted: {len(rows)} contacts")
                    conn.close()

                except Exception as e:
                    print(f"  Error: {e}")

    # Print sample
    if contacts:
        print(f"\nTotal contacts found: {len(contacts)}")
        print("\nSample contact fields:")
        sample = contacts[0]
        for key, value in list(sample.items())[:10]:
            val_str = str(value)[:50] if value else "None"
            print(f"  {key}: {val_str}")

    return contacts


def find_and_extract_messages(limit: int = 50) -> list[dict]:
    """Find and extract messages."""
    print("\n" + "=" * 60)
    print("Extracting Messages")
    print("=" * 60)

    databases = find_databases()
    messages = []

    for db_path in databases:
        tables = get_db_tables(db_path)

        for table in tables:
            if any(kw in table.lower() for kw in ['message', 'msg', 'chat']):
                if 'revoke' in table.lower() or 'delete' in table.lower():
                    continue

                print(f"\nFound message table: {table} in {db_path.name}")

                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Get columns
                    cursor.execute(f"PRAGMA table_info([{table}])")
                    columns = [row[1] for row in cursor.fetchall()]
                    print(f"  Columns: {columns[:8]}...")

                    # Try to get recent messages
                    time_col = None
                    for col in columns:
                        if any(t in col.lower() for t in ['time', 'date', 'create']):
                            time_col = col
                            break

                    if time_col:
                        cursor.execute(f"SELECT * FROM [{table}] ORDER BY [{time_col}] DESC LIMIT {limit}")
                    else:
                        cursor.execute(f"SELECT * FROM [{table}] LIMIT {limit}")

                    rows = cursor.fetchall()

                    for row in rows:
                        messages.append(dict(row))

                    print(f"  Extracted: {len(rows)} messages")
                    conn.close()

                    if messages:
                        break  # Found messages, stop searching

                except Exception as e:
                    print(f"  Error: {e}")

    # Print sample
    if messages:
        print(f"\nTotal messages found: {len(messages)}")
        print("\nSample message:")
        sample = messages[0]
        for key, value in list(sample.items())[:10]:
            val_str = str(value)[:60] if value else "None"
            print(f"  {key}: {val_str}")

    return messages


def find_and_extract_moments(limit: int = 20) -> list[dict]:
    """Find and extract Moments (朋友圈/SNS) data."""
    print("\n" + "=" * 60)
    print("Extracting Moments (朋友圈)")
    print("=" * 60)

    databases = find_databases()
    moments = []

    # Keywords that might indicate Moments data
    moment_keywords = ['sns', 'moment', 'timeline', 'pyq', 'friendcircle', 'feed']

    for db_path in databases:
        tables = get_db_tables(db_path)

        for table in tables:
            if any(kw in table.lower() for kw in moment_keywords):
                print(f"\nFound potential Moments table: {table} in {db_path.name}")

                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Get columns
                    cursor.execute(f"PRAGMA table_info([{table}])")
                    columns = [row[1] for row in cursor.fetchall()]
                    print(f"  Columns: {columns}")

                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    count = cursor.fetchone()[0]
                    print(f"  Total rows: {count}")

                    # Extract data
                    cursor.execute(f"SELECT * FROM [{table}] LIMIT {limit}")
                    rows = cursor.fetchall()

                    for row in rows:
                        moments.append({
                            "source_table": table,
                            "source_db": db_path.name,
                            "data": dict(row)
                        })

                    print(f"  Extracted: {len(rows)} entries")
                    conn.close()

                except Exception as e:
                    print(f"  Error: {e}")

    # Also search for tables with content-like columns
    print("\n" + "-" * 40)
    print("Searching for tables with content/post data...")

    for db_path in databases:
        tables = get_db_tables(db_path)

        for table in tables:
            if table in [m.get("source_table") for m in moments]:
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info([{table}])")
                columns = [row[1].lower() for row in cursor.fetchall()]

                # Look for tables with content + time columns
                has_content = any(c in columns for c in ['content', 'text', 'body', 'description'])
                has_time = any('time' in c or 'date' in c for c in columns)
                has_user = any(c in columns for c in ['user', 'from', 'sender', 'author', 'username'])

                if has_content and (has_time or has_user):
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        print(f"\n  Potential content table: {table}")
                        print(f"    Rows: {count}")
                        print(f"    Columns: {columns[:8]}")

                        # Extract sample
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT * FROM [{table}] LIMIT 5")
                        for row in cursor.fetchall():
                            moments.append({
                                "source_table": table,
                                "source_db": db_path.name,
                                "data": dict(row)
                            })

                conn.close()

            except:
                continue

    # Print summary
    if moments:
        print(f"\n" + "=" * 40)
        print(f"Total Moments/content entries found: {len(moments)}")

        # Group by source
        by_source = {}
        for m in moments:
            key = f"{m['source_db']}/{m['source_table']}"
            if key not in by_source:
                by_source[key] = 0
            by_source[key] += 1

        print("\nBy source:")
        for source, count in by_source.items():
            print(f"  {source}: {count} entries")

        # Print sample entry
        if moments:
            print("\nSample entry:")
            sample = moments[0]['data']
            for key, value in list(sample.items())[:10]:
                val_str = str(value)[:80] if value else "None"
                print(f"  {key}: {val_str}")
    else:
        print("\nNo Moments data found in standard locations.")
        print("Moments might be stored with different naming or in encrypted tables.")

    return moments


def export_data(data: list[dict], output_file: str):
    """Export data to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nExported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract WeChat data from local databases"
    )
    parser.add_argument("--list-tables", "-t", action="store_true",
                        help="List all tables across all databases")
    parser.add_argument("--analyze", "-a", action="store_true",
                        help="Analyze and categorize databases")
    parser.add_argument("--contacts", "-c", action="store_true",
                        help="Extract contacts")
    parser.add_argument("--messages", "-m", action="store_true",
                        help="Extract messages")
    parser.add_argument("--moments", "-M", action="store_true",
                        help="Extract Moments (朋友圈)")
    parser.add_argument("--all", action="store_true",
                        help="Extract all data types")
    parser.add_argument("--limit", "-l", type=int, default=50,
                        help="Limit number of records (default: 50)")
    parser.add_argument("--output", "-o", type=str,
                        help="Output JSON file")

    args = parser.parse_args()

    print("=" * 60)
    print("WeChat Data Extractor")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Default to analyze if no specific option
    if not any([args.list_tables, args.analyze, args.contacts,
                args.messages, args.moments, args.all]):
        args.analyze = True

    results = {}

    if args.list_tables:
        list_all_tables()

    if args.analyze:
        categorized = analyze_all_databases()
        results['categorized'] = {k: len(v) for k, v in categorized.items()}

    if args.contacts or args.all:
        results['contacts'] = find_and_extract_contacts(args.limit)

    if args.messages or args.all:
        results['messages'] = find_and_extract_messages(args.limit)

    if args.moments or args.all:
        results['moments'] = find_and_extract_moments(args.limit)

    if args.output and results:
        export_data(results, args.output)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
