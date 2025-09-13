from promptperfector.logic.logger import log_info, log_debug
import sqlite3
import uuid
import json
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / 'promptperfector.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS flowcharts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            flowchart_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )''')
        conn.commit()

def create_project(name):
    pid = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute('INSERT INTO projects (id, name) VALUES (?, ?)', (pid, name))
        conn.commit()
    log_info(f"Created new project: {pid}, name: {name}")
    return pid

def list_projects():
    with get_connection() as conn:
        return conn.execute('SELECT id, name FROM projects').fetchall()

def get_latest_flowchart(project_id):
    with get_connection() as conn:
        row = conn.execute('''SELECT flowchart_json FROM flowcharts WHERE project_id=? ORDER BY version DESC LIMIT 1''', (project_id,)).fetchone()
        log_debug(f"Loaded latest flowchart for project: {project_id}, found: {bool(row)}")
        return json.loads(row[0]) if row else None

def save_flowchart_version(project_id, flowchart_json):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT MAX(version) FROM flowcharts WHERE project_id=?', (project_id,))
        max_version = c.fetchone()[0] or 0
        new_version = max_version + 1
        fid = str(uuid.uuid4())
        c.execute('''INSERT INTO flowcharts (id, project_id, version, flowchart_json) VALUES (?, ?, ?, ?)''',
                  (fid, project_id, new_version, json.dumps(flowchart_json)))
        conn.commit()
        log_info(f"Saved flowchart version {new_version} for project: {project_id}")
        return new_version

def list_flowchart_versions(project_id):
    with get_connection() as conn:
        versions = conn.execute('''SELECT version, created_at FROM flowcharts WHERE project_id=? ORDER BY version DESC''', (project_id,)).fetchall()
        log_debug(f"Listed {len(versions)} versions for project: {project_id}")
        return versions
