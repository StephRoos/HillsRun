import sqlite3

DB_PATH = "hillsrun.db"


def _get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY,
            activity_name TEXT,
            activity_type TEXT,
            start_time TEXT,
            distance REAL,
            duration REAL,
            calories INTEGER,
            average_hr INTEGER,
            max_hr INTEGER,
            average_speed REAL,
            elevation_gain REAL,
            elevation_loss REAL
        )
    """)
    conn.commit()
    conn.close()


def save_activities(activities: list[dict]):
    conn = _get_connection()
    for a in activities:
        activity_type = a.get("activityType", {})
        if isinstance(activity_type, dict):
            activity_type = activity_type.get("typeKey", "unknown")

        conn.execute(
            """
            INSERT OR REPLACE INTO activities
            (activity_id, activity_name, activity_type, start_time, distance,
             duration, calories, average_hr, max_hr, average_speed,
             elevation_gain, elevation_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                a.get("activityId"),
                a.get("activityName"),
                activity_type,
                a.get("startTimeLocal"),
                a.get("distance"),
                a.get("duration"),
                a.get("calories"),
                a.get("averageHR"),
                a.get("maxHR"),
                a.get("averageSpeed"),
                a.get("elevationGain"),
                a.get("elevationLoss"),
            ),
        )
    conn.commit()
    conn.close()


def get_all_activities() -> list[dict]:
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM activities ORDER BY start_time DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_activity_date() -> str | None:
    conn = _get_connection()
    result = conn.execute(
        "SELECT MAX(start_time) FROM activities"
    ).fetchone()
    conn.close()
    if result and result[0]:
        return result[0]
    return None


def get_activity_stats() -> dict:
    conn = _get_connection()
    result = conn.execute("""
        SELECT
            COUNT(*) as total_activities,
            COALESCE(SUM(distance), 0) as total_distance,
            COALESCE(SUM(duration), 0) as total_duration,
            COALESCE(AVG(average_hr), 0) as avg_hr
        FROM activities
    """).fetchone()
    conn.close()
    return {
        "total_activities": result[0],
        "total_distance": result[1],
        "total_duration": result[2],
        "avg_hr": result[3],
    }
