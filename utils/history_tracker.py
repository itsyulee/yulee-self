# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.


"""
Author: Routo
NeuraSelf-UwU - https://github.com/routo-loop/neura-self
"""

import json
import os
import time
import sqlite3
from datetime import datetime
import calendar

HISTORY_FILE = 'data/neura_history.db'
LEGACY_HISTORY_FILE = 'data/history.json'

def get_db():
    conn = sqlite3.connect(HISTORY_FILE, check_same_thread=False)
    conn.execute('pragma journal_mode=wal')
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            hunts INTEGER DEFAULT 0,
            battles INTEGER DEFAULT 0,
            commands INTEGER DEFAULT 0,
            captchas INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS cash_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            amount INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS command_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            log_type TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def migrate_legacy_json():
    if not os.path.exists(LEGACY_HISTORY_FILE):
        return
        
    try:
        with open(LEGACY_HISTORY_FILE, 'r') as f:
            data = json.load(f)
            
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM sessions')
        if c.fetchone()[0] > 0:
            conn.close()
            return

        for sess in data.get('sessions', []):
            st = sess.get('stats', {})
            c.execute('''
                INSERT INTO sessions (date, start_time, end_time, hunts, battles, commands, captchas)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sess.get('date', datetime.now().strftime("%Y-%m-%d")),
                sess.get('start_time', datetime.now().strftime("%H:%M:%S")),
                sess.get('end_time'),
                st.get('hunts', 0),
                st.get('battles', 0),
                st.get('commands', 0),
                st.get('captchas', 0)
            ))
            
        for cash in data.get('cash_history', []):
            c.execute('INSERT INTO cash_history (timestamp, amount) VALUES (?, ?)', 
                     (cash.get('timestamp'), cash.get('amount', 0)))
                     
        conn.commit()
        conn.close()
        
        os.rename(LEGACY_HISTORY_FILE, LEGACY_HISTORY_FILE + '.bak')
        print("Successfully migrated legacy history.json to SQLite")
    except Exception as e:
        print(f"Failed to migrate legacy history: {e}")


init_db()
migrate_legacy_json()

def load_history():
    return {} 

def start_session(history_data=None):
    conn = get_db()
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")

    c.execute('UPDATE sessions SET end_time = ? WHERE end_time IS NULL', (time_str,))
    
    c.execute('''
        INSERT INTO sessions (date, start_time)
        VALUES (?, ?)
    ''', (date_str, time_str))
    
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": session_id, "date": date_str, "start_time": time_str, "stats": {"hunts": 0, "battles": 0, "commands": 0, "captchas": 0}}

def end_session(history_data=None):
    conn = get_db()
    c = conn.cursor()
    time_str = datetime.now().strftime("%H:%M:%S")
    c.execute('UPDATE sessions SET end_time = ? WHERE end_time IS NULL', (time_str,))
    conn.commit()
    conn.close()

def _ensure_active_session(c):
    date_str = datetime.now().strftime("%Y-%m-%d")
    c.execute('SELECT id FROM sessions WHERE end_time IS NULL ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    if not row:
        time_str = datetime.now().strftime("%H:%M:%S")
        c.execute('INSERT INTO sessions (date, start_time) VALUES (?, ?)', (date_str, time_str))
        return c.lastrowid
    return row[0]

def track_command(history_data=None, cmd_type=None):
    if not cmd_type: return
    conn = get_db()
    c = conn.cursor()
    sess_id = _ensure_active_session(c)
    
    c.execute('UPDATE sessions SET commands = commands + 1 WHERE id = ?', (sess_id,))
    
    if cmd_type == 'hunt':
        c.execute('UPDATE sessions SET hunts = hunts + 1 WHERE id = ?', (sess_id,))
    elif cmd_type == 'battle':
        c.execute('UPDATE sessions SET battles = battles + 1 WHERE id = ?', (sess_id,))
    elif cmd_type == 'captcha':
        c.execute('UPDATE sessions SET captchas = captchas + 1 WHERE id = ?', (sess_id,))
        
    conn.commit()
    conn.close()

def track_cash(history_data=None, amount=0):
    conn = get_db()
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO cash_history (timestamp, amount) VALUES (?, ?)', (timestamp, amount))
    
    c.execute('SELECT COUNT(*) FROM cash_history')
    count = c.fetchone()[0]
    if count > 100:
        c.execute('DELETE FROM cash_history WHERE id NOT IN (SELECT id FROM cash_history ORDER BY id DESC LIMIT 100)')
        
    conn.commit()
    conn.close()

def get_session_stats(history_data=None):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT hunts, battles, commands, captchas FROM sessions ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"hunts": row[0], "battles": row[1], "commands": row[2], "captchas": row[3]}
    return {"hunts": 0, "battles": 0, "commands": 0, "captchas": 0}

def get_all_time_stats(history_data=None):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT SUM(hunts), SUM(battles), SUM(commands), SUM(captchas), COUNT(id) FROM sessions')
    row = c.fetchone()
    conn.close()
    
    if row and row[4] > 0:
        return {
            "all_time_hunts": row[0] or 0,
            "all_time_battles": row[1] or 0,
            "all_time_commands": row[2] or 0,
            "all_time_captchas": row[3] or 0,
            "total_sessions": row[4]
        }
    return {
        "all_time_hunts": 0,
        "all_time_battles": 0,
        "all_time_commands": 0,
        "all_time_captchas": 0,
        "total_sessions": 0
    }

def get_analytics_data(start_date=None, end_date=None):
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT id, date, start_time, end_time, hunts, battles, commands, captchas FROM sessions'
    params = []
    
    if start_date and end_date:
        query += ' WHERE date >= ? AND date <= ?'
        params.extend([start_date, end_date])
    elif start_date:
        query += ' WHERE date >= ?'
        params.append(start_date)
        
    query += ' ORDER BY id ASC'
    
    c.execute(query, params)
    sessions = []
    for row in c.fetchall():
        sess_id, date_str, start_str, end_str, hunts, battles, commands, captchas = row
        # Convert "YYYY-MM-DD" + "HH:MM:SS" into a Unix timestamp so JS new Date(ts * 1000) works
        start_unix = None
        if date_str and start_str:
            try:
                dt_str = f"{date_str} {start_str}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                start_unix = int(calendar.timegm(dt.timetuple()))
            except Exception:
                start_unix = None
        end_unix = None
        if date_str and end_str:
            try:
                # end_time might be just HH:MM:SS; if it's less than start, it's next day (edge case ignored)
                dt_str = f"{date_str} {end_str}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                end_unix = int(calendar.timegm(dt.timetuple()))
            except Exception:
                end_unix = None
        sessions.append({
            "id": sess_id,
            "date": date_str,
            "start_time": start_unix,
            "end_time": end_unix,
            "stats": {
                "hunts": hunts,
                "battles": battles,
                "commands": commands,
                "captchas": captchas
            }
        })
        
    cash_history = []
    c.execute('SELECT timestamp, amount FROM cash_history ORDER BY id ASC')
    for row in c.fetchall():
        cash_history.append({"timestamp": row[0], "amount": row[1]})
        
    totals = get_all_time_stats()
    conn.close()
    
    return {
        "sessions": sessions,
        "cash_history": cash_history,
        "totals": totals
    }
