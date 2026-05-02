# =============================================================================
# config.py — Application Configuration
# =============================================================================
# Centralizes all environment-specific settings for the Honeytoken Access
# Monitoring System. Modify DB credentials here before running the app.
# =============================================================================

class Config:
    """
    Central configuration class for the Flask application.
    All database credentials, secret keys, and app settings live here.
    """

    # Flask secret key — used to sign session cookies
    # CHANGE THIS to a long random string in production!
    SECRET_KEY = "h0n3yt0k3n_s3cur3_k3y_ch4ng3_m3_1n_pr0d"

    # ── MySQL Database Credentials ──────────────────────────────────────────
    DB_HOST     = "localhost"
    DB_USER     = "root"
    DB_PASSWORD = "root4321"
    DB_NAME     = "cyber_deception_grid"
    DB_PORT     = 3306

    # ── Session config ──────────────────────────────────────────────────────
    SESSION_PERMANENT = False
    SESSION_TYPE      = "filesystem"

    # ── Pagination ──────────────────────────────────────────────────────────
    LOGS_PER_PAGE = 20