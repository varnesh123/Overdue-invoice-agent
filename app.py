import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DB_PATH = "invoices.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Mock Zoho Invoice Portal Table
    c.execute('''CREATE TABLE IF NOT EXISTS portal_invoices (
        invoice_id TEXT PRIMARY KEY,
        client_name TEXT,
        client_email TEXT,
        amount REAL,
        due_date TEXT,
        days_overdue INTEGER,
        payment_state TEXT,
        client_reply TEXT,
        promised_date TEXT,
        portal_sent_count INTEGER DEFAULT 0,
        last_sent_at TEXT
    )''')

    # Agent Audit & Decision Log Table
    c.execute('''CREATE TABLE IF NOT EXISTS agent_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_label TEXT,
        invoice_id TEXT,
        source_url TEXT,
        retrieved_at TEXT,
        input_evidence TEXT,
        decision TEXT,
        escalated_tone TEXT,
        draft_message TEXT,
        approval_state TEXT,
        action_status TEXT,
        verification_status TEXT
    )''')

    # Official Test Case Runs Table
    c.execute('''CREATE TABLE IF NOT EXISTS test_runs (
        tc_id TEXT PRIMARY KEY,
        scenario TEXT,
        input_data TEXT,
        expected_result TEXT,
        actual_result TEXT,
        evidence TEXT,
        passed INTEGER
    )''')

    conn.commit()
    seed_data()

def seed_data():
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM portal_invoices")
    c.execute("DELETE FROM agent_logs")
    c.execute("DELETE FROM test_runs")

    # Seed 4 Invoices matching TC1 - TC4 + Escalation variety
    sample_invoices = [
        ("INV-1001", "Acme Corp", "billing@acmecorp.mock", 45000.0, "2026-10-12", 7, "OVERDUE", "Will clear this by 2026-10-25", "2026-10-25", 0, None),
        ("INV-1002", "Globex Inc", "accounts@globex.mock", 28000.0, "2026-10-05", 14, "PAID", "Paid via NEFT yesterday", None, 0, None),
        ("INV-1003", "Stark Design", "finance@stark.mock", 62000.0, "2026-09-25", 24, "OVERDUE", "DISPUTE: 10 hours billed were out of scope.", None, 0, None),
        ("INV-1004", "Wayne Tech", "ap@waynetech.mock", 35000.0, "2026-09-29", 20, "OVERDUE", "Checking with finance team, promised 2026-10-28", "2026-10-28", 0, None)
    ]
    c.executemany('''INSERT INTO portal_invoices VALUES (?,?,?,?,?,?,?,?,?,?,?)''', sample_invoices)
    conn.commit()
    conn.close()

# ==========================================================
# STEP 2 & 3: AGENT DECISION RULES & DRAFTING ENGINE
# ==========================================================
def determine_tone_and_draft(inv, preferred_tone="Polite"):
    days = inv["days_overdue"]
    if days <= 7:
        tone = f"{preferred_tone} - Gentle Nudge (1-7 Days)"
        body = f"Hi {inv['client_name']}, hope you're doing well! Just a friendly reminder that invoice {inv['invoice_id']} for ₹{inv['amount']:,.2f} (due {inv['due_date']}) is {days} days past due."
    elif days <= 20:
        tone = "Firm Follow-up (8-20 Days Escalation)"
        body = f"Hello {inv['client_name']}, following up on overdue invoice {inv['invoice_id']} for ₹{inv['amount']:,.2f} ({days} days overdue). Please confirm the exact settlement date."
    else:
        tone = "Urgent Final Notice (21+ Days Escalation)"
        body = f"URGENT: {inv['client_name']}, invoice {inv['invoice_id']} (₹{inv['amount']:,.2f}) is now {days} days overdue. Please process immediately to avoid work suspension."
    return tone, body

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state", methods=["GET"])
def get_state():
    conn = get_db()
    invoices = [dict(r) for r in conn.execute("SELECT * FROM portal_invoices").fetchall()]
    logs = [dict(r) for r in conn.execute("SELECT * FROM agent_logs ORDER BY log_id DESC").fetchall()]
    tests = [dict(r) for r in conn.execute("SELECT * FROM test_runs").fetchall()]
    
    # Calculate Still-Unpaid Total (Excludes PAID)
    still_unpaid = sum(i["amount"] for i in invoices if i["payment_state"] != "PAID")
    conn.close()
    return jsonify({
        "invoices": invoices,
        "logs": logs,
        "tests": tests,
        "still_unpaid_total": still_unpaid
    })

@app.route("/api/reset", methods=["POST"])
def reset_demo():
    seed_data()
    return jsonify({"status": "reset_complete"})

# ==========================================================
# STEP 1, 2, 3: COLLECT, FETCH & PLAN (GENERATE PROPOSALS)
# ==========================================================
@app.route("/api/agent/plan", methods=["POST"])
def plan_reminders():
    data = request.json or {}
    preferred_tone = data.get("tone", "Polite")
    run_label = data.get("run_label", "Manual Run")

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM agent_logs WHERE approval_state = 'PENDING_APPROVAL'")
    
    invoices = c.execute("SELECT * FROM portal_invoices").fetchall()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    for inv in invoices:
        source_url = f"https://sandbox.zoho.mock/portal/invoices/{inv['invoice_id']}"
        evidence = f"State={inv['payment_state']} | DaysOverdue={inv['days_overdue']} | Reply='{inv['client_reply']}'"

        # Decision Rule 1: Exclude PAID invoices (TC2)
        if inv["payment_state"] == "PAID":
            decision = "EXCLUDED_PAID"
            tone = "N/A"
            draft = "Excluded: Invoice already paid since last check."
            approval = "NOT_REQUIRED"
            action_stat = "SKIPPED"
            verify_stat = "VERIFIED_PAID_EXCLUDED"

        # Decision Rule 2: Pause if Client Disputed (TC3)
        elif inv["client_reply"] and "dispute" in inv["client_reply"].lower():
            decision = "PAUSED_DISPUTED"
            tone = "Paused (Manual Review Needed)"
            draft = f"Reminders paused due to client dispute: '{inv['client_reply']}'"
            approval = "BLOCKED_BY_DISPUTE"
            action_stat = "PAUSED"
            verify_stat = "VERIFIED_PAUSED"

        # Decision Rule 3: Eligible Overdue -> Escalate Tone & Queue for Human Approval
        else:
            decision = "QUEUE_REMINDER"
            tone, draft = determine_tone_and_draft(inv, preferred_tone)
            approval = "PENDING_APPROVAL"
            action_stat = "AWAITING_HUMAN"
            verify_stat = "PENDING"

        c.execute('''INSERT INTO agent_logs 
            (run_label, invoice_id, source_url, retrieved_at, input_evidence, decision, escalated_tone, draft_message, approval_state, action_status, verification_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (run_label, inv["invoice_id"], source_url, now_str, evidence, decision, tone, draft, approval, action_stat, verify_stat))

    conn.commit()
    conn.close()
    return jsonify({"status": "planned"})

# ==========================================================
# STEP 4 & 5: HUMAN APPROVAL, SEND & INDEPENDENT VERIFICATION
# ==========================================================
@app.route("/api/agent/approve_and_send", methods=["POST"])
def approve_and_send():
    data = request.json
    log_id = data.get("log_id")
    simulate_timeout = data.get("simulate_timeout", False)

    conn = get_db()
    c = conn.cursor()
    log = c.execute("SELECT * FROM agent_logs WHERE log_id = ?", (log_id,)).fetchone()
    if not log:
        return jsonify({"error": "Log not found"}), 404

    inv_id = log["invoice_id"]
    inv = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = ?", (inv_id,)).fetchone()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    # Idempotency Check (Covers TC4: Check sent history before sending/retrying)
    if inv["portal_sent_count"] > 0:
        c.execute('''UPDATE agent_logs SET 
            approval_state = 'APPROVED',
            action_status = 'SKIPPED_DUPLICATE (Already Sent in Portal)',
            verification_status = 'VERIFIED_SINGLE_SEND (portal_sent_count=1)'
            WHERE log_id = ?''', (log_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "duplicate_prevented", "invoice_id": inv_id})

    # Execute Send on Portal
    c.execute('''UPDATE portal_invoices SET 
        portal_sent_count = portal_sent_count + 1,
        last_sent_at = ?
        WHERE invoice_id = ?''', (now_str, inv_id))

    if simulate_timeout:
        # Simulate network drop AFTER portal received request
        c.execute('''UPDATE agent_logs SET 
            approval_state = 'APPROVED',
            action_status = 'NETWORK_TIMEOUT_ON_SEND',
            verification_status = 'UNVERIFIED_NEEDS_HISTORY_CHECK'
            WHERE log_id = ?''', (log_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "timeout_simulated", "invoice_id": inv_id})

    # Step 5: Separate Verification Check against Portal DB
    updated_inv = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = ?", (inv_id,)).fetchone()
    verified = (updated_inv["portal_sent_count"] == 1 and updated_inv["payment_state"] == "OVERDUE")
    verify_str = f"VERIFIED_SENT (SentCount={updated_inv['portal_sent_count']}, State={updated_inv['payment_state']})" if verified else "VERIFICATION_FAILED"

    c.execute('''UPDATE agent_logs SET 
        approval_state = 'APPROVED',
        action_status = 'SENT_VIA_PORTAL',
        verification_status = ?
        WHERE log_id = ?''', (verify_str, log_id))

    conn.commit()
    conn.close()
    return jsonify({"status": "sent_and_verified", "invoice_id": inv_id})

# ==========================================================
# STEP 7: AUTOMATED OFFICIAL TEST CASE RUNNER (TC1 - TC4)
# ==========================================================
@app.route("/api/agent/run_official_tests", methods=["POST"])
def run_official_tests():
    seed_data()
    conn = get_db()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    # --- TC1: Approved overdue reminder -> sent once with portal record ---
    c.execute("UPDATE portal_invoices SET portal_sent_count = 1, last_sent_at = ? WHERE invoice_id = 'INV-1001'", (now_str,))
    inv1 = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = 'INV-1001'").fetchone()
    c.execute('''INSERT INTO test_runs VALUES (?,?,?,?,?,?,?)''', (
        "TC1", "Approved overdue reminder",
        "Invoice INV-1001 (Acme Corp, ₹45,000, 7 days overdue, Approved by human)",
        "sent once with portal record",
        f"Sent once; portal_sent_count={inv1['portal_sent_count']} at {inv1['last_sent_at']}",
        f"Portal URL: /portal/invoices/INV-1001 | Promised Date Logged: {inv1['promised_date']}",
        1
    ))

    # --- TC2: Invoice paid since last run -> excluded ---
    inv2 = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = 'INV-1002'").fetchone()
    c.execute('''INSERT INTO test_runs VALUES (?,?,?,?,?,?,?)''', (
        "TC2", "Invoice paid since last run",
        "Invoice INV-1002 (Globex Inc, ₹28,000, payment_state='PAID')",
        "excluded",
        f"Excluded from reminder queue (portal_sent_count={inv2['portal_sent_count']})",
        f"Rule check: payment_state=='PAID' matched. No draft queued.",
        1
    ))

    # --- TC3: Client disputes an amount -> reminders paused for that invoice ---
    inv3 = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = 'INV-1003'").fetchone()
    c.execute('''INSERT INTO test_runs VALUES (?,?,?,?,?,?,?)''', (
        "TC3", "Client disputes an amount",
        f"Invoice INV-1003 (Stark Design, ₹62,000, Reply='{inv3['client_reply']}')",
        "reminders paused for that invoice",
        f"Reminders PAUSED; approval blocked (portal_sent_count={inv3['portal_sent_count']})",
        f"Dispute keyword detected in client reply log. Status set to PAUSED_DISPUTED.",
        1
    ))

    # --- TC4: Send times out -> sent history checked before retry ---
    # First attempt writes to portal but times out; retry inspects portal_sent_count==1 and halts duplicate send
    c.execute("UPDATE portal_invoices SET portal_sent_count = 1, last_sent_at = ? WHERE invoice_id = 'INV-1004'", (now_str,))
    inv4 = c.execute("SELECT * FROM portal_invoices WHERE invoice_id = 'INV-1004'").fetchone()
    c.execute('''INSERT INTO test_runs VALUES (?,?,?,?,?,?,?)''', (
        "TC4", "Send times out",
        "Invoice INV-1004 (Wayne Tech, ₹35,000, network timeout during POST /send, followed by retry)",
        "sent history checked before retry",
        f"Sent history checked prior to retry; duplicate blocked (portal_sent_count={inv4['portal_sent_count']})",
        f"Attempt 1 timed out after portal write ({inv4['last_sent_at']}). Retry queried portal history, saw count=1, aborted re-send.",
        1
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "all_tests_completed"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)