import os

from flask import Flask, render_template, request, redirect, session, url_for
from cs50 import SQL
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Connect directly to the SQLite database file
db = SQL("sqlite:///golf.db")

def init_db():
    """Create tables if they do not exist (for fresh databases)."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            loft REAL,
            notes TEXT,
            bag_order INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS shots (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            club_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            distance REAL NOT NULL,
            result TEXT,
            context TEXT,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
        """
    )


# Make sure tables exist (safe to run even if they already do)
init_db()


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Basic checks
        if not username or not password or not confirmation:
            return "Must provide username and password (twice)", 400
        if password != confirmation:
            return "Passwords do not match", 400

        # Hash the password
        hash_value = generate_password_hash(password)

        # Try to insert; fail if username is taken
        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username,
                hash_value,
            )
        except Exception:
            # Most likely UNIQUE constraint on username
            return "Username already taken", 400

        # Log the user in immediately (optional but nice)
        row = db.execute("SELECT id FROM users WHERE username = ?", username)[0]
        session["user_id"] = row["id"]
        session["username"] = username

        return redirect("/")

    # GET: show registration form
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Clear any old session
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Must provide username and password", 400

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return "Invalid username or password", 400

        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


CLUB_ORDER = {
    "driver": 10,
    "mini-driver": 15,
    "3 wood": 20,
    "4 wood": 30,
    "5 wood": 40,
    "7 wood": 50,
    "9 wood": 60,
    "11 wood": 70,

    "2 hybrid": 80,
    "3 hybrid": 90,
    "4 hybrid": 100,

    "2 iron": 110,
    "3 iron": 120,
    "4 iron": 130,
    "5 iron": 140,
    "6 iron": 150,
    "7 iron": 160,
    "8 iron": 170,
    "9 iron": 180,

    "pw": 200,
    "gw": 210,
    "aw": 220,
    "sw": 230,
    "lw": 240,

    "putter": 300,
}

# Determine custom lofts for wedges


def determine_bag_order(name, loft_value):
    """
    Decide bag_order based on club name and (optionally) loft.
    Priority:
      1) Exact name match in CLUB_ORDER
      2) Wedge loft ranges:
         - 44–47.9  -> 205
         - 48–51.9  -> 215
         - 52–55.9  -> 225
         - 56–59.9  -> 235
         - 60+      -> 245
      3) Default -> 999
    """
    key = name.strip().lower()

    # Direct name match (Driver, 3 wood, PW, SW, etc.)
    if key in CLUB_ORDER:
        return CLUB_ORDER[key]

    # Loft-based ranges for wedges (if we have a numeric loft)
    if loft_value is not None:
        try:
            loft_num = float(loft_value)
        except (TypeError, ValueError):
            loft_num = None

        if loft_num is not None:
            if 44 <= loft_num < 48:
                return 205      # 44–47.9
            elif 48 <= loft_num < 52:
                return 215      # 48–51.9
            elif 52 <= loft_num < 56:
                return 225      # 52–55.9
            elif 56 <= loft_num < 60:
                return 235      # 56–59.9
            elif loft_num >= 60:
                return 245      # 60+

    # Fallback: unknown club -> bottom of list
    return 999


@app.route("/")
@login_required
def index():
    """Show home page"""
    return render_template("index.html")

@app.route("/clubs", methods=["GET", "POST"])
@login_required
def clubs():
    """Show clubs and allow adding a new one"""
    if request.method == "POST":
        # Read form data
        name = request.form.get("name")
        loft = request.form.get("loft")
        notes = request.form.get("notes")

        # Validation: name is required
        if not name:
            return "Must provide club name", 400

        # Loft is optional; if empty, store NULL
        if loft == "":
            loft_value = None
        else:
            try:
                loft_value = float(loft)
            except ValueError:
                return "Loft must be a number", 400

        # Use helper to determine bag_order (name + loft ranges)
        bag_order = determine_bag_order(name, loft_value)
        user_id = session["user_id"]

        # Insert into database
        db.execute(
            "INSERT INTO clubs (name, loft, notes, bag_order, user_id) VALUES (?, ?, ?, ?, ?)",
            name,
            loft_value,
            notes,
            bag_order,
            user_id,
        )

        # Redirect to /clubs so refresh doesn't resubmit the form
        return redirect("/clubs")

    # GET request: just show the page
    user_id = session["user_id"]

    clubs = db.execute("SELECT id, name, loft, notes, bag_order FROM clubs WHERE user_id = ? "
                       "ORDER BY COALESCE(bag_order, 999), name",
                       user_id,
                       )
    return render_template("clubs.html", clubs=clubs)


@app.route("/clubs/<int:club_id>/edit", methods=["GET", "POST"])
def edit_club(club_id):
    """Edit an existing club"""

    # Fetch the club
    rows = db.execute(
        "SELECT id, name, loft, notes FROM clubs WHERE id = ?",
        club_id,
    )
    if len(rows) != 1:
        return "Club not found", 404

    club = rows[0]

    if request.method == "POST":
        name = request.form.get("name")
        loft = request.form.get("loft")
        notes = request.form.get("notes")

        if not name:
            return "Must provide club name", 400

        if loft == "":
            loft_value = None
        else:
            try:
                loft_value = float(loft)
            except ValueError:
                return "Loft must be a number", 400

        # Recalculate bag_order from the new name
        key = name.strip().lower()
        bag_order = CLUB_ORDER.get(key, 999)

        db.execute(
            "UPDATE clubs "
            "SET name = ?, loft = ?, notes = ?, bag_order = ? "
            "WHERE id = ?",
            name,
            loft_value,
            notes,
            bag_order,
            club_id,
        )

        return redirect("/clubs")

    # GET: show edit form
    return render_template("edit_club.html", club=club)


@app.route("/clubs/<int:club_id>/delete", methods=["POST"])
def delete_club(club_id):
    """Delete a club and all its shots"""
    # First delete shots that reference this club
    db.execute("DELETE FROM shots WHERE club_id = ?", club_id)
    # Then delete the club itself
    db.execute("DELETE FROM clubs WHERE id = ?", club_id)
    return redirect("/clubs")


@app.route("/shots", methods=["GET", "POST"])
@login_required
def shots():
    """Log new shots and list shots (optionally filtered by date)."""

    user_id = session["user_id"]

    # ----- Handle new shot submission -----
    if request.method == "POST":
        date_str = request.form.get("date")
        club_id = request.form.get("club_id")
        distance_str = request.form.get("distance")
        result = request.form.get("result") or None
        context = request.form.get("context") or None

        # Default date to today if left empty
        if not date_str:
            date_str = date.today().isoformat()

        # Basic validation
        if not club_id or not distance_str:
            return redirect("/shots")

        try:
            distance_value = float(distance_str)
        except ValueError:
            return redirect("/shots")

        db.execute(
            """
            INSERT INTO shots (club_id, date, distance, result, context)
            VALUES (?, ?, ?, ?, ?)
            """,
            club_id,
            date_str,
            distance_value,
            result,
            context,
        )

        return redirect("/shots")

    # ----- GET: show form + table -----

    # Optional ?date=YYYY-MM-DD in the query string
    selected_date = request.args.get("date")

    # Clubs for the dropdown (only this user's clubs)
    clubs = db.execute(
        """
        SELECT id, name, notes
        FROM clubs
        WHERE user_id = ?
        ORDER BY COALESCE(bag_order, 999), name
        """,
        user_id,
    )

    # Build the shot list query
    base_query = """
        SELECT shots.id,
               shots.date,
               shots.distance,
               shots.result,
               shots.context,
               clubs.name  AS club_name,
               clubs.notes AS club_notes,
               COALESCE(clubs.bag_order, 999) AS bag_order
        FROM shots
        JOIN clubs ON shots.club_id = clubs.id
        WHERE clubs.user_id = ?
    """
    params = [user_id]

    if selected_date:
        base_query += " AND shots.date = ?\n"
        params.append(selected_date)

    base_query += """
        ORDER BY bag_order,
                 shots.date DESC,
                 shots.id DESC
    """

    rows = db.execute(base_query, *params)

    return render_template(
        "shots.html",
        shots=rows,
        clubs=clubs,
        selected_date=selected_date,
    )


@app.route("/shots/<int:shot_id>/delete", methods=["POST"])
@login_required
def delete_shot(shot_id):
    user_id = session["user_id"]

    # Only delete if the shot belongs to a club owned by this user
    db.execute(
        """
        DELETE FROM shots
        WHERE id = ?
          AND club_id IN (SELECT id FROM clubs WHERE user_id = ?)
        """,
        shot_id,
        user_id,
    )

    return redirect("/shots")


@app.route("/stats")
@login_required
def stats():
    """Show average distance, miss pattern per club, and spray chart (optionally filtered by date)"""

    selected_date = request.args.get("date")  # e.g. "2025-12-07" or None
    user_id = session["user_id"]

    # Average distance + shot count per club
    club_query = """
        SELECT clubs.id,
               clubs.name,
               clubs.notes,
               ROUND(AVG(shots.distance), 1) AS avg_distance,
               COUNT(*) AS shot_count
        FROM shots
        JOIN clubs ON shots.club_id = clubs.id
        WHERE clubs.user_id = ?
    """
    club_params = [user_id]
    if selected_date:
        club_query += " AND shots.date = ?\n"
        club_params.append(selected_date)

    club_query += """
        GROUP BY clubs.id, clubs.name, clubs.notes
        HAVING COUNT(*) > 0
        ORDER BY COALESCE(clubs.bag_order, 999), clubs.name
    """
    club_stats = db.execute(club_query, *club_params)

    # Miss distribution per club (for percentages)
    miss_query = """
        SELECT clubs.id,
               LOWER(TRIM(COALESCE(shots.result, ''))) AS result,
               COUNT(*) AS count
        FROM shots
        JOIN clubs ON shots.club_id = clubs.id
        WHERE clubs.user_id = ?
    """
    miss_params = [user_id]
    if selected_date:
        miss_query += """
          AND shots.date = ?
          AND shots.result IS NOT NULL
          AND TRIM(shots.result) != ''
        """
        miss_params.append(selected_date)
    else:
        miss_query += """
          AND shots.result IS NOT NULL
          AND TRIM(shots.result) != ''
        """

    miss_query += """
        GROUP BY clubs.id, result
    """
    miss_rows = db.execute(miss_query, *miss_params)

    miss_counts = {}
    for row in miss_rows:
        cid = row["id"]
        r = row["result"]
        count = row["count"]

        if cid not in miss_counts:
            miss_counts[cid] = {
                "left": 0,
                "center_left": 0,
                "center": 0,
                "center_right": 0,
                "right": 0,
                "other": 0,
            }

        if "left" in r or "hook" in r or "pull" in r:
            miss_counts[cid]["left"] += count
        elif "draw" in r:
            miss_counts[cid]["center_left"] += count
        elif "right" in r or "slice" in r or "push" in r:
            miss_counts[cid]["right"] += count
        elif "cut" in r or "fade" in r:
            miss_counts[cid]["center_right"] += count
        elif "center" in r or "straight" in r or "pure" in r:
            miss_counts[cid]["center"] += count
        else:
            miss_counts[cid]["other"] += count

    # Attach percentages to each club row
    for row in club_stats:
        cid = row["id"]
        total = row["shot_count"]
        counts = miss_counts.get(
            cid,
            {
                "left": 0,
                "center_left": 0,
                "center": 0,
                "center_right": 0,
                "right": 0,
                "other": 0,
            },
        )

        if total > 0:
            row["left_pct"] = round(100 * counts["left"] / total, 1)
            row["center_left_pct"] = round(100 * counts["center_left"] / total, 1)
            row["center_pct"] = round(100 * counts["center"] / total, 1)
            row["center_right_pct"] = round(100 * counts["center_right"] / total, 1)
            row["right_pct"] = round(100 * counts["right"] / total, 1)
            row["other_pct"] = round(100 * counts["other"] / total, 1)
        else:
            row["left_pct"] = row["center_left_pct"] = row["center_pct"] = 0.0
            row["center_right_pct"] = row["right_pct"] = row["other_pct"] = 0.0

    # 4) Dispersion chart data

    # Map club id -> label (name + notes)
    club_labels = {}
    for row in club_stats:
        label = row["name"]
        if row["notes"]:
            label = f"{label} – {row['notes']}"
        club_labels[row["id"]] = label

    # Assign each club a color
    palette = [
        "#ef4444",  # red
        "#3b82f6",  # blue
        "#22c55e",  # green
        "#f97316",  # orange
        "#a855f7",  # purple
        "#14b8a6",  # teal
        "#eab308",  # yellow
        "#6b7280",  # gray
    ]
    club_colors = {}
    for idx, row in enumerate(club_stats):
        club_colors[row["id"]] = palette[idx % len(palette)]

    # Pull all individual shots (for dots), scoped to this user (and date if set)
    raw_query = """
        SELECT shots.id,
               shots.distance,
               LOWER(TRIM(COALESCE(shots.result, ''))) AS result,
               clubs.id AS club_id
        FROM shots
        JOIN clubs ON shots.club_id = clubs.id
        WHERE clubs.user_id = ?
    """
    raw_params = [user_id]
    if selected_date:
        raw_query += " AND shots.date = ?"
        raw_params.append(selected_date)

    raw_shots = db.execute(raw_query, *raw_params)

    # Determine chart max distance (round up to next 50 yards)
    range_ticks = []
    if raw_shots:
        raw_max = max(
            (s["distance"] for s in raw_shots if s["distance"] is not None),
            default=0,
        )
        if raw_max <= 0:
            chart_max = 50
        else:
            chart_max = ((int(raw_max) + 49) // 50) * 50
    else:
        raw_max = 0
        chart_max = 50

    step = 50
    current = step
    while current <= chart_max:
        norm_tick = current / chart_max if chart_max > 0 else 0
        y_tick = 5 + norm_tick * 90
        range_ticks.append({"value": current, "y": round(y_tick, 1)})
        current += step

    # Build dispersion dots
    spray_shots = []
    for s in raw_shots:
        dist = s["distance"] or 0.0
        r = s["result"]
        cid = s["club_id"]

        norm = dist / chart_max if chart_max > 0 else 0
        dot_offset = 3.9
        y = 5 + norm * 90 - dot_offset
        if y < 5:
            y = 5
        if y > 95:
            y = 95

        if "left" in r or "hook" in r or "pull" in r:
            lane = -2
        elif "draw" in r:
            lane = -1
        elif "right" in r or "slice" in r or "push" in r:
            lane = 2
        elif "cut" in r or "fade" in r:
            lane = 1
        elif "center" in r or "straight" in r or "pure" in r:
            lane = 0
        else:
            lane = 0

        x = 50 + lane * 10
        x = max(5, min(95, x))

        spray_shots.append(
            {
                "x": round(x, 1),
                "y": round(y, 1),
                "color": club_colors.get(cid, "#6b7280"),
                "label": club_labels.get(cid, "Unknown club"),
                "distance": round(dist, 1),
                "result_raw": r or "",
            }
        )

    spray_legend = []
    for row in club_stats:
        spray_legend.append(
            {
                "label": club_labels[row["id"]],
                "color": club_colors[row["id"]],
            }
        )

    return render_template(
        "stats.html",
        stats=club_stats,
        spray_shots=spray_shots,
        spray_legend=spray_legend,
        range_ticks=range_ticks,
        selected_date=selected_date,
    )


if __name__ == "__main__":
    app.run(debug=True)
