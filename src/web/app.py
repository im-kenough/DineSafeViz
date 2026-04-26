import os

import psycopg2
from flask import Flask, render_template

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "dinesafe"),
    "user": os.environ.get("DB_USER", "dinesafe"),
    "password": os.environ.get("DB_PASSWORD", "dinesafe"),
}


@app.route("/")
def index():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT inspection_date, establishment_name, severity "
        "FROM inspections ORDER BY inspection_date DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    inspections = []
    for date, name, severity in rows:
        if severity:
            violation = f"Yes — {severity}"
        else:
            violation = "No"
        inspections.append({"date": date, "name": name, "violation": violation})

    return render_template("index.html", inspections=inspections)
