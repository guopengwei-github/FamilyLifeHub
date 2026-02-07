"""
Debug script to inspect Garmin API raw data structure.
This helps identify the correct field names for sleep data.
"""
import os
import sys
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from garminconnect import Garmin
import json

def debug_garmin_api():
    """Debug Garmin API to see actual data structure returned."""

    # Get credentials from database
    from app.core.database import SessionLocal
    from app.models import GarminConnection
    from app.core.security import decrypt_token

    db = SessionLocal()
    conn = db.query(GarminConnection).filter(GarminConnection.user_id == 1).first()
    db.close()

    if not conn:
        print("No Garmin connection found for user 1")
        return

    username = decrypt_token(conn.garmin_username)
    password = decrypt_token(conn.garmin_password)
    mfa_token = decrypt_token(conn.garmin_mfa_token) if conn.garmin_mfa_token else None
    is_cn = conn.is_cn == 1

    print(f"Connecting to {'Garmin China' if is_cn else 'Garmin International'}...")
    print(f"Username: {username[:3]}***")

    try:
        garmin = Garmin(username, password, is_cn=is_cn)
        if mfa_token:
            garmin.login_with_mfa(mfa_token)
        else:
            garmin.login()
        print("Login successful!\n")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    target_date = date.today()
    date_str = target_date.strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"Fetching data for {date_str}")
    print("=" * 60)

    # 1. Get daily summary
    print("\n【1. Daily Summary - sleep related fields】")
    summary = garmin.get_user_summary(date_str)

    sleep_fields = [k for k in summary.keys() if 'sleep' in k.lower() or 'Sleep' in k]
    print(f"Sleep-related keys in summary: {sleep_fields}")

    for key in sleep_fields:
        print(f"  {key}: {summary[key]}")

    # Check if expected fields exist
    print("\nChecking expected sleep fields:")
    for field in ['sleepSeconds', 'totalSleepSeconds', 'sleepTimeSeconds']:
        if field in summary:
            print(f"  {field}: {summary[field]}")
        else:
            print(f"  {field}: NOT FOUND")

    # 2. Get sleep data
    print("\n【2. Sleep Data - full structure】")
    sleep_data = garmin.get_sleep_data(date_str)

    print(f"Top-level keys in sleep_data: {list(sleep_data.keys())}")

    # Look for sleep duration fields
    print("\nLooking for sleep duration fields:")
    duration_fields = [
        'dailySleepSeconds', 'totalSleepSeconds', 'sleepTimeSeconds',
        'sleepSeconds', 'duration', 'sleepDuration'
    ]
    for field in duration_fields:
        if field in sleep_data:
            print(f"  {field}: {sleep_data[field]}")
        else:
            print(f"  {field}: NOT FOUND")

    # Check sleepStages structure
    print("\nSleep stages structure:")
    if 'sleepStages' in sleep_data:
        stages = sleep_data['sleepStages']
        print(f"  Keys in sleepStages: {list(stages.keys()) if isinstance(stages, dict) else 'not a dict'}")
        if isinstance(stages, dict):
            for key in stages:
                print(f"    {key}: {stages[key]}")

    # Print full sleep_data for inspection (truncated)
    print("\n【Full sleep_data JSON (for inspection)】")
    print(json.dumps(sleep_data, indent=2, ensure_ascii=False)[:3000] + "...")

    # 3. Also check other potential endpoints
    print("\n【3. Checking other sleep endpoints】")

    try:
        sleep_summary = garmin.get_sleep_summary(date_str)
        print(f"get_sleep_summary keys: {list(sleep_summary.keys()) if isinstance(sleep_summary, dict) else 'not a dict'}")
        # Look for duration in sleep summary
        if isinstance(sleep_summary, dict):
            for key, value in sleep_summary.items():
                if 'sleep' in key.lower() and isinstance(value, (int, float)):
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"  get_sleep_summary failed: {e}")

    try:
        # Check daily stats
        daily = garmin.get_daily_stats(date_str)
        print(f"\nget_daily_stats keys: {list(daily.keys()) if isinstance(daily, dict) else 'not a dict'}")
        # Look for sleep in daily stats
        if isinstance(daily, dict):
            for key, value in daily.items():
                if 'sleep' in key.lower():
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"  get_daily_stats failed: {e}")

if __name__ == "__main__":
    debug_garmin_api()
