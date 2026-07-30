"""
database.py - SQLite Database Layer for TeamPulse
Handles team hierarchy, status check-ins, blockers, leave requests, and doc reviews.
"""

import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "teampulse.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    return conn

def init_db():
    """Initializes tables and seeds sample team hierarchy if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users table (Team hierarchy)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            ldap TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            title TEXT NOT NULL,
            manager_ldap TEXT,
            avatar_url TEXT
        )
    """)

    # 2. Check-ins table (Reportee status submissions)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_ldap TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            mood TEXT NOT NULL,          -- 'happy', 'neutral', 'blocked', 'overwhelmed'
            status_summary TEXT NOT NULL, -- What they are currently working on
            has_blocker INTEGER DEFAULT 0, -- 1 if blocked, 0 if not
            blocker_details TEXT,         -- Details about the blocker & help needed
            wants_1on1 INTEGER DEFAULT 0,  -- 1 if wants to talk / 1:1 requested
            one_on_one_topics TEXT,       -- Topics to discuss in 1:1
            leave_info TEXT,              -- Upcoming leave dates / plans
            doc_links TEXT,               -- Docs requiring review (URLs / titles)
            FOREIGN KEY (user_ldap) REFERENCES users(ldap)
        )
    """)

    # Seed default team if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_sample_data(cursor)

    conn.commit()
    conn.close()

def seed_sample_data(cursor):
    """Populates realistic Google-style team hierarchy and initial status updates."""
    # Manager
    cursor.execute("""
        INSERT INTO users (ldap, name, role, title, manager_ldap, avatar_url)
        VALUES ('malviyarashi', 'Rashi Malviya', 'manager', 'Engineering Manager', NULL, 'https://api.dicebear.com/7.x/bottts/svg?seed=Rashi')
    """)

    # Reportees
    reportees = [
        ('alex_chen', 'Alex Chen', 'reportee', 'Software Engineer (Backend)', 'malviyarashi', 'https://api.dicebear.com/7.x/bottts/svg?seed=Alex'),
        ('sarah_jenkins', 'Sarah Jenkins', 'reportee', 'Senior SWE (Frontend)', 'malviyarashi', 'https://api.dicebear.com/7.x/bottts/svg?seed=Sarah'),
        ('rahul_sharma', 'Rahul Sharma', 'reportee', 'SWE III (Infra & Cloud)', 'malviyarashi', 'https://api.dicebear.com/7.x/bottts/svg?seed=Rahul'),
        ('maya_patel', 'Maya Patel', 'reportee', 'Software Engineer (ML)', 'malviyarashi', 'https://api.dicebear.com/7.x/bottts/svg?seed=Maya')
    ]

    for ldap, name, role, title, mgr, avatar in reportees:
        cursor.execute("""
            INSERT INTO users (ldap, name, role, title, manager_ldap, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ldap, name, role, title, mgr, avatar))

    # Add realistic initial check-ins
    initial_checkins = [
        (
            'alex_chen',
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            'blocked',
            'Implementing the gRPC stubby service for cross-datacenter sync.',
            1,
            'Waiting on security review & permissions from SecOps team (b/19827364). Work is stalled until ACL is approved.',
            1,
            'Need guidance on escalating the security approval before Q3 feature freeze.',
            'Taking off next Friday (Aug 8) for a personal trip.',
            'https://docs.google.com/document/d/sample-grpc-design - gRPC Architecture Doc (needs quick TL sign-off)'
        ),
        (
            'sarah_jenkins',
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            'happy',
            'Finished redesigning the Manager Dashboard UI components and responsive layout.',
            0,
            '',
            0,
            '',
            'None planned this month.',
            'https://docs.google.com/document/d/sample-ui-mocks - UI UX Review Deck'
        ),
        (
            'rahul_sharma',
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            'overwhelmed',
            'Debugging latency spike in Spanner read queries under peak load testing.',
            1,
            'Hit unexpected Spanner lock contention; might need another engineer or DBA consultation.',
            1,
            'Discuss workload balance and whether we should push the stress testing deadline by 1 week.',
            'Planning Diwali leave in November (Nov 1-5).',
            ''
        ),
        (
            'maya_patel',
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            'happy',
            'Tuned the Gemini prompt embeddings pipeline; latency dropped by 35%!',
            0,
            '',
            0,
            '',
            'Out of office Monday morning for dentist appointment.',
            'https://docs.google.com/document/d/sample-gemini-eval - Eval Benchmarks Doc'
        )
    ]

    for c in initial_checkins:
        cursor.execute("""
            INSERT INTO checkins (user_ldap, timestamp, mood, status_summary, has_blocker, blocker_details, wants_1on1, one_on_one_topics, leave_info, doc_links)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def get_user(ldap: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE ldap = ?", (ldap,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_reportees_for_manager(manager_ldap: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE manager_ldap = ?", (manager_ldap,))
    reportees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reportees

def add_checkin(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checkins (
            user_ldap, timestamp, mood, status_summary,
            has_blocker, blocker_details, wants_1on1,
            one_on_one_topics, leave_info, doc_links
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['user_ldap'],
        datetime.now().strftime('%Y-%m-%d %H:%M'),
        data.get('mood', 'neutral'),
        data.get('status_summary', ''),
        1 if data.get('has_blocker') else 0,
        data.get('blocker_details', ''),
        1 if data.get('wants_1on1') else 0,
        data.get('one_on_one_topics', ''),
        data.get('leave_info', ''),
        data.get('doc_links', '')
    ))
    conn.commit()
    checkin_id = cursor.lastrowid
    conn.close()
    return checkin_id

def get_latest_team_status(manager_ldap: str):
    """Retrieves the latest check-in for each direct report of the manager."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.ldap, u.name, u.title, u.avatar_url,
               c.id as checkin_id, c.timestamp, c.mood, c.status_summary,
               c.has_blocker, c.blocker_details, c.wants_1on1, c.one_on_one_topics,
               c.leave_info, c.doc_links
        FROM users u
        LEFT JOIN checkins c ON u.ldap = c.user_ldap
        AND c.id = (
            SELECT MAX(id) FROM checkins WHERE user_ldap = u.ldap
        )
        WHERE u.manager_ldap = ?
        ORDER BY c.has_blocker DESC, c.wants_1on1 DESC, u.name ASC
    """, (manager_ldap,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_user_history(user_ldap: str):
    """Gets all historical check-ins for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM checkins WHERE user_ldap = ? ORDER BY id DESC
    """, (user_ldap,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
