# =============================================================================
# app.py — Main Flask Application
# =============================================================================
# Entry point for the Honeytoken Access Monitoring System.
#
# HOW HONEYTOKEN DETECTION WORKS:
#   1. User accesses a resource → INSERT into access_logs
#   2. TRIGGER trg_after_access_log FIRES on that INSERT
#   3. Trigger queries honeytokens table — does the resource_id match?
#   4. If YES → trigger INSERTs a CRITICAL alert into alerts table
#   5. Second TRIGGER trg_after_alert FIRES on that alerts INSERT
#   6. Second trigger recalculates user's risk_score:
#        risk_score = (honeytoken_hits×40) + (failed_logins×10)
#                     + (off_hours_access×20)
#   7. risk_history table is UPDATED with the new score
# =============================================================================

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from functools import wraps
from datetime import datetime, timedelta
from config import Config
from db import fetch_all, fetch_one, execute_query

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY


# =============================================================================
# AUTH DECORATOR
# =============================================================================

def login_required(f):
    """Protects routes — redirects to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# HELPER: Call the log_admin_action stored procedure
# =============================================================================

def log_admin_action(action_type, target, details):
    """
    Calls MySQL stored procedure log_admin_action to record every
    admin activity into the audit_trail table.
    """
    admin_id = session.get("admin_id", 1)
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host     = Config.DB_HOST,
            user     = Config.DB_USER,
            password = Config.DB_PASSWORD,
            database = Config.DB_NAME,
            port     = Config.DB_PORT
        )
        cursor = conn.cursor()
        cursor.callproc("log_admin_action", [admin_id, action_type, target, details])
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[AUDIT ERROR] log_admin_action failed: {e}")


# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.route("/", methods=["GET"])
def index():
    """Redirect root to dashboard or login."""
    if "admin_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Render login page.
    POST: Validate credentials. On success set session and redirect.
    """
    if "admin_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Fetch user by username — parameterized query
        user = fetch_one(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )

        if user and user.get("password_hash") == password:
            session["admin_id"]       = user["user_id"]
            session["admin_username"] = user["username"]
            session["admin_role"]     = user.get("role_id", 1)

            # Record successful login
            execute_query(
                """INSERT INTO login_history
                   (user_id, ip_address, status, user_agent)
                   VALUES (%s, %s, %s, %s)""",
                (user["user_id"], request.remote_addr, "Success",
                 request.headers.get("User-Agent", "Unknown"))
            )
            log_admin_action("LOGIN", f"user:{username}", f"Admin {username} logged in")
            return redirect(url_for("dashboard"))
        else:
            # Record failed login
            if user:
                execute_query(
                    """INSERT INTO login_history
                       (user_id, ip_address, status, user_agent)
                       VALUES (%s, %s, %s, %s)""",
                    (user["user_id"], request.remote_addr, "Failed",
                     request.headers.get("User-Agent", "Unknown"))
                )
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Clear session and redirect to login."""
    username = session.get("admin_username", "unknown")
    log_admin_action("LOGOUT", f"user:{username}", f"Admin {username} logged out")
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# =============================================================================
# DASHBOARD
# =============================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Main SOC dashboard with stat cards, recent alerts,
    risk distribution chart, and alert trend chart.
    """
    # -- Stat cards (safe fetch — never crashes if query returns None) --
    result = fetch_one("SELECT COUNT(*) AS cnt FROM users WHERE is_active = 1")
    total_users = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM alerts")
    total_alerts = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM risk_history WHERE risk_score >= 50")
    high_risk_count = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM honeytokens")
    total_honeytokens = result["cnt"] if result else 0

    # -- Recent 5 alerts --
    recent_alerts = fetch_all(
        """SELECT a.alert_id, u.username, a.severity,
                  a.description, a.created_at, a.status
           FROM alerts a
           JOIN users u ON a.user_id = u.user_id
           ORDER BY a.created_at DESC
           LIMIT 5"""
    )

    # -- Risk distribution for doughnut chart --
    risk_dist = fetch_all(
        """SELECT
             SUM(CASE WHEN risk_score < 20  THEN 1 ELSE 0 END) AS low_count,
             SUM(CASE WHEN risk_score >= 20 AND risk_score < 50 THEN 1 ELSE 0 END) AS med_count,
             SUM(CASE WHEN risk_score >= 50 AND risk_score < 80 THEN 1 ELSE 0 END) AS high_count,
             SUM(CASE WHEN risk_score >= 80 THEN 1 ELSE 0 END) AS crit_count
           FROM risk_history"""
    )
    if risk_dist and risk_dist[0]:
        dist = risk_dist[0]
        # Replace None with 0 for each key
        dist = {k: (v if v is not None else 0) for k, v in dist.items()}
    else:
        dist = {"low_count": 0, "med_count": 0, "high_count": 0, "crit_count": 0}

    # -- Alert trend: last 7 days --
    trend_data = fetch_all(
        """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
           FROM alerts
           WHERE created_at >= CURDATE() - INTERVAL 7 DAY
           GROUP BY DATE(created_at)
           ORDER BY day ASC"""
    )
    trend_labels = []
    trend_values = []
    trend_map = {str(row["day"]): int(row["cnt"]) for row in trend_data}
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        trend_labels.append((datetime.now() - timedelta(days=i)).strftime("%b %d"))
        trend_values.append(trend_map.get(d, 0))

    return render_template(
        "dashboard.html",
        total_users       = total_users,
        total_alerts      = total_alerts,
        high_risk_count   = high_risk_count,
        total_honeytokens = total_honeytokens,
        recent_alerts     = recent_alerts,
        dist              = dist,
        trend_labels      = trend_labels,
        trend_values      = trend_values,
    )


# =============================================================================
# API — STATS (polled by JS every 30s)
# =============================================================================

@app.route("/api/stats")
@login_required
def api_stats():
    """
    GET /api/stats
    Returns live dashboard statistics as JSON.
    Called by main.js dashboardAutoRefresh() every 30 seconds.
    """
    result = fetch_one("SELECT COUNT(*) AS cnt FROM users WHERE is_active = 1")
    total_users = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM alerts")
    total_alerts = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM risk_history WHERE risk_score >= 50")
    high_risk_count = result["cnt"] if result else 0

    result = fetch_one("SELECT COUNT(*) AS cnt FROM honeytokens")
    total_honeytokens = result["cnt"] if result else 0

    recent_alerts = fetch_all(
        """SELECT a.alert_id, u.username, a.severity,
                  a.description, a.created_at
           FROM alerts a
           JOIN users u ON a.user_id = u.user_id
           ORDER BY a.created_at DESC
           LIMIT 5"""
    )
    # Serialize datetime for JSON
    for alert in recent_alerts:
        alert["created_at"] = str(alert["created_at"])

    return jsonify({
        "total_users"      : total_users,
        "total_alerts"     : total_alerts,
        "high_risk_count"  : high_risk_count,
        "total_honeytokens": total_honeytokens,
        "recent_alerts"    : recent_alerts,
    })


# =============================================================================
# USERS
# =============================================================================

@app.route("/users")
@login_required
def users():
    """
    Users management page.
    Shows all users with risk scores, departments, roles.
    Supports search via ?q= query param.
    """
    search_term = request.args.get("q", "").strip()

    if search_term:
        rows = fetch_all(
            """SELECT u.user_id, u.username, u.email, u.is_active,
                      COALESCE(d.department_name, '—') AS department_name,
                      COALESCE(r.role_name, '—') AS role_name,
                      COALESCE(rh.risk_score, 0) AS risk_score,
                      MAX(lh.login_time) AS last_login
               FROM users u
               LEFT JOIN departments d ON u.department_id = d.department_id
               LEFT JOIN roles r ON u.role_id = r.role_id
               LEFT JOIN risk_history rh ON u.user_id = rh.user_id
               LEFT JOIN login_history lh ON u.user_id = lh.user_id
               WHERE u.username LIKE %s OR d.department_name LIKE %s
               GROUP BY u.user_id, u.username, u.email, u.is_active,
                        d.department_name, r.role_name, rh.risk_score
               ORDER BY risk_score DESC""",
            (f"%{search_term}%", f"%{search_term}%")
        )
    else:
        rows = fetch_all(
            """SELECT u.user_id, u.username, u.email, u.is_active,
                      COALESCE(d.department_name, '—') AS department_name,
                      COALESCE(r.role_name, '—') AS role_name,
                      COALESCE(rh.risk_score, 0) AS risk_score,
                      MAX(lh.login_time) AS last_login
               FROM users u
               LEFT JOIN departments d ON u.department_id = d.department_id
               LEFT JOIN roles r ON u.role_id = r.role_id
               LEFT JOIN risk_history rh ON u.user_id = rh.user_id
               LEFT JOIN login_history lh ON u.user_id = lh.user_id
               GROUP BY u.user_id, u.username, u.email, u.is_active,
                        d.department_name, r.role_name, rh.risk_score
               ORDER BY risk_score DESC"""
        )

    return render_template("users.html", users=rows, search_term=search_term)


@app.route("/api/user/<int:user_id>/logs")
@login_required
def user_recent_logs(user_id):
    """
    GET /api/user/<user_id>/logs
    Returns last 3 access logs for a user as JSON.
    Used by JS accordion on the Users page.
    """
    logs = fetch_all(
        """SELECT al.log_id, al.action_type,
                  COALESCE(r.resource_name, '—') AS resource_name,
                  al.ip_address, al.access_time, al.is_suspicious
           FROM access_logs al
           LEFT JOIN resources r ON al.resource_id = r.resource_id
           WHERE al.user_id = %s
           ORDER BY al.access_time DESC
           LIMIT 3""",
        (user_id,)
    )
    for log in logs:
        log["access_time"] = str(log["access_time"])
    return jsonify(logs)


# =============================================================================
# ALERTS
# =============================================================================

@app.route("/alerts")
@login_required
def alerts():
    """
    Alerts monitoring page.
    Supports filtering by severity and date range.
    """
    severity  = request.args.get("severity", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to   = request.args.get("date_to", "").strip()

    base_query = """
        SELECT a.alert_id, u.username,
               COALESCE(r.resource_name, '—') AS resource_name,
               a.is_honeytoken, a.severity, a.created_at,
               a.status, a.description
        FROM alerts a
        JOIN users u ON a.user_id = u.user_id
        LEFT JOIN resources r ON a.resource_id = r.resource_id
        WHERE 1=1
    """
    params = []

    if severity:
        base_query += " AND a.severity = %s"
        params.append(severity)
    if date_from:
        base_query += " AND DATE(a.created_at) >= %s"
        params.append(date_from)
    if date_to:
        base_query += " AND DATE(a.created_at) <= %s"
        params.append(date_to)

    base_query += " ORDER BY a.created_at DESC"

    alert_rows = fetch_all(base_query, tuple(params))

    return render_template(
        "alerts.html",
        alerts    = alert_rows,
        severity  = severity,
        date_from = date_from,
        date_to   = date_to,
    )


# =============================================================================
# ACCESS LOGS
# =============================================================================

@app.route("/logs")
@login_required
def logs():
    """
    Access logs page with pagination (20 rows per page).
    Supports search by username or resource name.
    """
    page        = int(request.args.get("page", 1))
    search_term = request.args.get("q", "").strip()
    per_page    = Config.LOGS_PER_PAGE
    offset      = (page - 1) * per_page

    if search_term:
        log_rows = fetch_all(
            """SELECT al.log_id, u.username,
                      COALESCE(r.resource_name, '—') AS resource_name,
                      al.action_type, al.ip_address,
                      al.access_time, al.is_suspicious
               FROM access_logs al
               JOIN users u ON al.user_id = u.user_id
               LEFT JOIN resources r ON al.resource_id = r.resource_id
               WHERE u.username LIKE %s OR r.resource_name LIKE %s
               ORDER BY al.access_time DESC
               LIMIT %s OFFSET %s""",
            (f"%{search_term}%", f"%{search_term}%", per_page, offset)
        )
        result = fetch_one(
            """SELECT COUNT(*) AS cnt
               FROM access_logs al
               JOIN users u ON al.user_id = u.user_id
               LEFT JOIN resources r ON al.resource_id = r.resource_id
               WHERE u.username LIKE %s OR r.resource_name LIKE %s""",
            (f"%{search_term}%", f"%{search_term}%")
        )
        total = result["cnt"] if result else 0
    else:
        log_rows = fetch_all(
            """SELECT al.log_id, u.username,
                      COALESCE(r.resource_name, '—') AS resource_name,
                      al.action_type, al.ip_address,
                      al.access_time, al.is_suspicious
               FROM access_logs al
               JOIN users u ON al.user_id = u.user_id
               LEFT JOIN resources r ON al.resource_id = r.resource_id
               ORDER BY al.access_time DESC
               LIMIT %s OFFSET %s""",
            (per_page, offset)
        )
        result = fetch_one("SELECT COUNT(*) AS cnt FROM access_logs")
        total = result["cnt"] if result else 0

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "logs.html",
        logs        = log_rows,
        page        = page,
        total_pages = total_pages,
        search_term = search_term,
    )


# =============================================================================
# HONEYTOKENS
# =============================================================================

@app.route("/honeytokens")
@login_required
def honeytokens():
    """
    Honeytoken management page.
    Shows all honeytokens with breach counts.
    """
    tokens = fetch_all(
        """SELECT h.token_id, h.token_name, h.token_type,
                  h.resource_id,
                  COALESCE(r.resource_name, '—') AS resource_name,
                  COALESCE(u.username, '—') AS created_by,
                  h.created_at,
                  COUNT(a.alert_id) AS times_triggered
           FROM honeytokens h
           LEFT JOIN resources r ON h.resource_id = r.resource_id
           LEFT JOIN users u ON h.created_by = u.user_id
           LEFT JOIN alerts a ON a.resource_id = h.resource_id
                              AND a.is_honeytoken = 1
           GROUP BY h.token_id, h.token_name, h.token_type,
                    h.resource_id, r.resource_name, u.username, h.created_at
           ORDER BY h.created_at DESC"""
    )

    resources = fetch_all(
        "SELECT resource_id, resource_name FROM resources ORDER BY resource_name"
    )

    return render_template("honeytokens.html", tokens=tokens, resources=resources)


@app.route("/honeytokens/add", methods=["POST"])
@login_required
def add_honeytoken():
    """
    POST /honeytokens/add
    Inserts a new honeytoken. All inputs are parameterized.
    """
    token_name  = request.form.get("token_name", "").strip()
    token_type  = request.form.get("token_type", "").strip()
    resource_id = request.form.get("resource_id", "").strip()
    description = request.form.get("description", "").strip()
    admin_id    = session.get("admin_id")

    if not all([token_name, token_type, resource_id]):
        flash("All required fields must be filled.", "error")
        return redirect(url_for("honeytokens"))

    new_id = execute_query(
        """INSERT INTO honeytokens
           (token_name, token_type, resource_id, description, created_by)
           VALUES (%s, %s, %s, %s, %s)""",
        (token_name, token_type, int(resource_id), description, admin_id)
    )

    log_admin_action(
        "CREATE",
        f"honeytoken:{new_id}",
        f"Created honeytoken '{token_name}' of type {token_type} on resource {resource_id}"
    )

    flash(f"Honeytoken '{token_name}' created successfully.", "success")
    return redirect(url_for("honeytokens"))


# =============================================================================
# RISK MONITOR
# =============================================================================

@app.route("/risk")
@login_required
def risk():
    """
    Risk Monitor page.
    Shows risk summary cards, bar chart for top-10 users, full risk table.
    """
    risk_rows = fetch_all(
        """SELECT u.username, rh.risk_score,
                  rh.honeytoken_hits, rh.failed_logins,
                  rh.off_hours_access, rh.last_updated
           FROM risk_history rh
           JOIN users u ON rh.user_id = u.user_id
           ORDER BY rh.risk_score DESC"""
    )

    avg_result = fetch_one(
        "SELECT ROUND(AVG(risk_score), 1) AS avg FROM risk_history"
    )
    avg_risk = avg_result["avg"] if avg_result and avg_result["avg"] is not None else 0

    max_risk_user = fetch_one(
        """SELECT u.username, rh.risk_score
           FROM risk_history rh
           JOIN users u ON rh.user_id = u.user_id
           ORDER BY rh.risk_score DESC LIMIT 1"""
    )

    result = fetch_one(
        "SELECT COUNT(*) AS cnt FROM risk_history WHERE risk_score >= 80"
    )
    critical_count = result["cnt"] if result else 0

    top10 = fetch_all(
        """SELECT u.username, rh.risk_score
           FROM risk_history rh
           JOIN users u ON rh.user_id = u.user_id
           ORDER BY rh.risk_score DESC LIMIT 10"""
    )
    chart_labels = [r["username"] for r in top10]
    chart_values = [int(r["risk_score"]) for r in top10]

    return render_template(
        "risk.html",
        risk_rows      = risk_rows,
        avg_risk       = avg_risk,
        max_risk_user  = max_risk_user,
        critical_count = critical_count,
        chart_labels   = chart_labels,
        chart_values   = chart_values,
    )


# =============================================================================
# AUDIT TRAIL
# =============================================================================

@app.route("/audit")
@login_required
def audit():
    """
    Audit Trail page — timeline of all admin actions.
    """
    audit_rows = fetch_all(
        """SELECT at.audit_id, u.username AS admin_username,
                  at.action_type, at.target_entity,
                  at.action_details, at.created_at
           FROM audit_trail at
           JOIN users u ON at.admin_id = u.user_id
           ORDER BY at.created_at DESC
           LIMIT 200"""
    )
    return render_template("audit.html", audit_rows=audit_rows)


# =============================================================================
# LOGIN HISTORY
# =============================================================================

@app.route("/login_history")
@login_required
def login_history():
    """
    Login History page.
    Flags IPs with 3+ failed logins as potential brute-force.
    """
    history = fetch_all(
        """SELECT lh.history_id, u.username, lh.ip_address,
                  lh.login_time, lh.status, lh.user_agent
           FROM login_history lh
           JOIN users u ON lh.user_id = u.user_id
           ORDER BY lh.login_time DESC
           LIMIT 500"""
    )

    # Find brute-force IPs — 3 or more failed logins from same IP
    brute_force_ips = fetch_all(
        """SELECT ip_address, COUNT(*) AS fail_count
           FROM login_history
           WHERE status = 'Failed'
           GROUP BY ip_address
           HAVING fail_count >= 3"""
    )
    bf_ip_set = {row["ip_address"] for row in brute_force_ips}

    return render_template(
        "login_history.html",
        history   = history,
        bf_ip_set = bf_ip_set,
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)