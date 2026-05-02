-- =============================================================================
-- triggers_and_procedures.sql
-- Honeytoken Access Monitoring System — MySQL Security Logic
-- =============================================================================
-- Run this file ONCE against your honeytoken_db database AFTER creating tables.
-- Contains:
--   1. TRIGGER: trg_after_access_log  — detects honeytoken access
--   2. TRIGGER: trg_after_alert       — recalculates user risk score
--   3. STORED PROCEDURE: log_admin_action — records audit trail entries
-- =============================================================================

-- Drop existing objects if re-running (safe for development)
DROP TRIGGER IF EXISTS trg_after_access_log;
DROP TRIGGER IF EXISTS trg_after_alert;
DROP PROCEDURE IF EXISTS log_admin_action;

DELIMITER $$

-- =============================================================================
-- TRIGGER 1: trg_after_access_log
-- =============================================================================
-- Purpose: After any new row is inserted into access_logs, check if the
--          accessed resource is a registered honeytoken. If so, automatically
--          generate a CRITICAL alert in the alerts table.
--
-- Detection Logic:
--   Step 1: NEW.resource_id is the resource just accessed.
--   Step 2: We look up the honeytokens table to see if this resource_id
--           is a registered honeytoken.
--   Step 3: If a match is found (v_token_id is NOT NULL):
--           → Insert a CRITICAL alert into the alerts table
--           → Mark the alert as is_honeytoken = TRUE
--           → The alert description names the honeytoken that was tripped
-- =============================================================================

CREATE TRIGGER trg_after_access_log
AFTER INSERT ON access_logs
FOR EACH ROW
BEGIN
    -- Step 1: Declare a variable to hold the honeytoken ID if found
    DECLARE v_token_id   INT DEFAULT NULL;
    DECLARE v_token_name VARCHAR(255) DEFAULT '';

    -- Step 2: Check if the accessed resource is a honeytoken
    SELECT token_id, token_name
    INTO   v_token_id, v_token_name
    FROM   honeytokens
    WHERE  resource_id = NEW.resource_id
    LIMIT  1;

    -- Step 3: If a honeytoken match was found, insert a CRITICAL alert
    IF v_token_id IS NOT NULL THEN
        INSERT INTO alerts
            (user_id, resource_id, is_honeytoken, severity,
             description, status, created_at)
        VALUES
            (NEW.user_id,           -- The user who triggered the honeytoken
             NEW.resource_id,       -- The honeytoken resource that was accessed
             TRUE,                  -- Mark this as a honeytoken breach
             'CRITICAL',            -- Honeytoken access is always CRITICAL
             CONCAT('HONEYTOKEN BREACH: User accessed honeytoken "',
                    v_token_name, '" (resource_id=',
                    NEW.resource_id, '). IP: ', NEW.ip_address),
             'Open',                -- New alert starts as Open
             NOW());
    END IF;
END$$


-- =============================================================================
-- TRIGGER 2: trg_after_alert
-- =============================================================================
-- Purpose: After any new alert is inserted, recalculate the affected user's
--          risk score in the risk_history table.
--
-- Risk Score Formula:
--   risk_score = (honeytoken_hits × 40) + (failed_logins × 10)
--                + (off_hours_access × 20)
--
-- Explanation:
--   honeytoken_hits  : Most critical — counts CRITICAL alerts for this user
--   failed_logins    : Counts failed login attempts in login_history
--   off_hours_access : Counts access_logs entries outside 08:00–20:00
--
-- Detection Logic:
--   Step 1: Count total honeytoken-triggered CRITICAL alerts for the user
--   Step 2: Count total failed logins for the user
--   Step 3: Count total off-hours access log entries for the user
--   Step 4: Apply formula to get new risk_score (capped at 100)
--   Step 5: INSERT or UPDATE risk_history using ON DUPLICATE KEY UPDATE
-- =============================================================================

CREATE TRIGGER trg_after_alert
AFTER INSERT ON alerts
FOR EACH ROW
BEGIN
    DECLARE v_honeytoken_hits  INT DEFAULT 0;
    DECLARE v_failed_logins    INT DEFAULT 0;
    DECLARE v_off_hours        INT DEFAULT 0;
    DECLARE v_risk_score       INT DEFAULT 0;

    -- Step 1: Count how many CRITICAL honeytoken alerts this user has triggered
    SELECT COUNT(*)
    INTO   v_honeytoken_hits
    FROM   alerts
    WHERE  user_id      = NEW.user_id
      AND  is_honeytoken = TRUE
      AND  severity      = 'CRITICAL';

    -- Step 2: Count failed logins from login_history for this user
    SELECT COUNT(*)
    INTO   v_failed_logins
    FROM   login_history
    WHERE  user_id = NEW.user_id
      AND  status  = 'Failed';

    -- Step 3: Count off-hours access (before 08:00 or after 20:00)
    SELECT COUNT(*)
    INTO   v_off_hours
    FROM   access_logs
    WHERE  user_id = NEW.user_id
      AND  (HOUR(access_time) < 8 OR HOUR(access_time) >= 20);

    -- Step 4: Calculate risk score using the formula; cap at 100
    SET v_risk_score = LEAST(
        (v_honeytoken_hits * 40) + (v_failed_logins * 10) + (v_off_hours * 20),
        100
    );

    -- Step 5: Insert or update risk_history for this user
    INSERT INTO risk_history
        (user_id, risk_score, honeytoken_hits, failed_logins,
         off_hours_access, last_updated)
    VALUES
        (NEW.user_id, v_risk_score, v_honeytoken_hits,
         v_failed_logins, v_off_hours, NOW())
    ON DUPLICATE KEY UPDATE
        risk_score       = v_risk_score,
        honeytoken_hits  = v_honeytoken_hits,
        failed_logins    = v_failed_logins,
        off_hours_access = v_off_hours,
        last_updated     = NOW();
END$$


-- =============================================================================
-- STORED PROCEDURE: log_admin_action
-- =============================================================================
-- Purpose: Records every admin action into the audit_trail table.
--          Called from Flask app.py after every privileged operation.
--
-- Parameters:
--   p_admin_id    INT          — user_id of the admin performing the action
--   p_action_type VARCHAR(50)  — e.g. LOGIN, LOGOUT, CREATE, DELETE, UPDATE
--   p_target      VARCHAR(255) — the affected entity, e.g. "honeytoken:5"
--   p_details     TEXT         — human-readable description of what was done
-- =============================================================================

CREATE PROCEDURE log_admin_action(
    IN p_admin_id    INT,
    IN p_action_type VARCHAR(50),
    IN p_target      VARCHAR(255),
    IN p_details     TEXT
)
BEGIN
    -- Insert the audit record with the current timestamp
    INSERT INTO audit_trail
        (admin_id, action_type, target_entity, action_details, created_at)
    VALUES
        (p_admin_id, p_action_type, p_target, p_details, NOW());
END$$

DELIMITER ;

-- =============================================================================
-- VERIFICATION: Check that triggers and procedure were created
-- =============================================================================
SHOW TRIGGERS LIKE 'access_logs';
SHOW TRIGGERS LIKE 'alerts';
SHOW PROCEDURE STATUS WHERE Name = 'log_admin_action';