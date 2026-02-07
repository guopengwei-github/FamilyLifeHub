"""
Sample data generator for FamilyLifeHub
Creates test users and sample data for the last 30 days
"""
import requests
from datetime import date, timedelta
import random
import sys
import io

# Fix UTF-8 encoding on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
API_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key-change-this-in-production"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def create_users():
    """Create sample family members."""
    users = [
        {"name": "Alice", "avatar": None},
        {"name": "Bob", "avatar": None}
    ]

    created_users = []
    for user in users:
        response = requests.post(
            f"{API_URL}/api/v1/users",
            json=user,
            headers=headers
        )
        if response.status_code == 201:
            created_user = response.json()
            print(f"✓ Created user: {created_user['name']} (ID: {created_user['id']})")
            created_users.append(created_user)
        elif response.status_code == 400 and "already exists" in response.json().get("detail", ""):
            # User already exists, fetch it
            users_response = requests.get(f"{API_URL}/api/v1/users")
            all_users = users_response.json()
            existing_user = next((u for u in all_users if u['name'] == user['name']), None)
            if existing_user:
                print(f"ℹ User already exists: {existing_user['name']} (ID: {existing_user['id']})")
                created_users.append(existing_user)
        else:
            print(f"✗ Failed to create user {user['name']}: {response.text}")

    return created_users


def generate_health_data(user_id, days=30):
    """Generate sample health metrics for the last N days."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    current_date = start_date
    while current_date <= end_date:
        # Generate realistic health data with some variation
        sleep_hours = round(random.uniform(6.0, 9.0), 1)
        light_sleep_hours = round(sleep_hours * random.uniform(0.5, 0.65), 1)
        deep_sleep_hours = round(sleep_hours * random.uniform(0.15, 0.25), 1)
        rem_sleep_hours = round(sleep_hours - light_sleep_hours - deep_sleep_hours, 1)

        # Calculate sleep score based on sleep quality
        sleep_score = int(random.randint(60, 95))

        health_data = {
            "user_id": user_id,
            "date": current_date.isoformat(),
            # Basic health metrics
            "sleep_hours": sleep_hours,
            "light_sleep_hours": light_sleep_hours,
            "deep_sleep_hours": deep_sleep_hours,
            "rem_sleep_hours": rem_sleep_hours,
            "resting_heart_rate": random.randint(55, 75),
            "stress_level": random.randint(20, 70),
            "exercise_minutes": random.randint(0, 120),
            # Garmin advanced metrics
            "steps": random.randint(3000, 15000),
            "calories": random.randint(1500, 3000),
            "distance_km": round(random.uniform(3, 15), 1),
            "body_battery": random.randint(40, 100),
            "spo2": round(random.uniform(95, 100), 1),
            "respiration_rate": round(random.uniform(12, 20), 1),
            "resting_hr": random.randint(50, 75),
            "sleep_score": sleep_score
        }

        response = requests.post(
            f"{API_URL}/api/v1/ingest/health",
            json=health_data,
            headers=headers
        )

        if response.status_code in [200, 201]:
            print(f"✓ Added health data for user {user_id} on {current_date}")
        else:
            print(f"✗ Failed to add health data: {response.text}")

        current_date += timedelta(days=1)


def generate_work_data(user_id, days=30):
    """Generate sample work metrics for the last N days."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    categories = ["coding", "browsing", "communication", "productivity"]

    current_date = start_date
    while current_date <= end_date:
        # Generate 3-5 work sessions per day
        num_sessions = random.randint(3, 5)

        for session in range(num_sessions):
            # Spread sessions throughout the day (9 AM to 6 PM)
            hour = random.randint(9, 17)
            minute = random.randint(0, 59)

            work_data = {
                "user_id": user_id,
                "timestamp": f"{current_date.isoformat()}T{hour:02d}:{minute:02d}:00Z",
                "screen_time_minutes": random.randint(30, 120),
                "focus_score": random.randint(50, 95),
                "active_window_category": random.choice(categories)
            }

            response = requests.post(
                f"{API_URL}/api/v1/ingest/work",
                json=work_data,
                headers=headers
            )

            if response.status_code == 201:
                print(f"✓ Added work data for user {user_id} on {current_date} at {hour:02d}:{minute:02d}")
            else:
                print(f"✗ Failed to add work data: {response.text}")

        current_date += timedelta(days=1)


def main():
    """Main function to generate all sample data."""
    print("=" * 60)
    print("FamilyLifeHub Sample Data Generator")
    print("=" * 60)
    print()

    # Check if API is accessible
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code != 200:
            print("✗ API is not accessible. Please start the backend first.")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API. Please start the backend first.")
        return

    print("Step 1: Creating users...")
    users = create_users()
    print()

    if not users:
        print("✗ No users created. Exiting.")
        return

    print("Step 2: Generating health data (last 30 days)...")
    for user in users:
        generate_health_data(user['id'], days=30)
    print()

    print("Step 3: Generating work data (last 30 days)...")
    for user in users:
        generate_work_data(user['id'], days=30)
    print()

    print("=" * 60)
    print("✓ Sample data generation complete!")
    print("=" * 60)
    print()
    print("You can now view the dashboard at: http://localhost:3000")
    print()


if __name__ == "__main__":
    main()
