#!/usr/bin/env python
"""
SoundPulse - Automated MySQL Database Setup Script
Tests MySQL connection, creates 'soundpulse_db' database if missing, and runs Django migrations.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

try:
    import pymysql
except ImportError:
    print("[!] Installing PyMySQL...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "cryptography"])
    import pymysql

def setup_mysql():
    db_name = os.getenv('DB_NAME', 'soundpulse_db')
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))

    print(f"[*] Connecting to MySQL Server at {db_host}:{db_port} as '{db_user}'...")

    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            port=db_port,
            charset='utf8mb4',
            autocommit=True
        )
        print("[+] Connected to MySQL successfully!")

        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"[+] Database '{db_name}' is ready!")

        conn.close()

        # Run Django migrations
        print("[*] Running Django migrations on MySQL...")
        import subprocess
        result = subprocess.run([sys.executable, "manage.py", "migrate"], cwd=BASE_DIR)
        if result.returncode == 0:
            print(f"\n[SUCCESS] MySQL setup complete! SoundPulse is configured with MySQL database '{db_name}'.")
        else:
            print("\n[!] Migrations encountered an issue. Check the output above.")

    except pymysql.MySQLError as e:
        print(f"\n[ERROR] Could not connect to MySQL: {e}")
        print("\n[TIP] Make sure MySQL is running (e.g. Start MySQL in XAMPP or check MySQL Windows service).")

if __name__ == '__main__':
    setup_mysql()

