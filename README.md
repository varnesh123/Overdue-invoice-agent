<p align="center">
  <a href="https://github.com/varnesh123/Overdue-invoice-agent">
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="60" alt="Python" />
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flask/flask-original.svg" width="60" alt="Flask" />
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/sqlite/sqlite-original.svg" width="60" alt="SQLite" />
    <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-plain.svg" width="60" alt="Tailwind CSS" />
  </a>
</p>

<h1 align="center">🧾 Overdue Invoice Follow-up Agent</h1>
<p align="center">
  A smart, human-in-the-loop reminder agent that chases overdue invoices against a <b>mock Zoho Invoice sandbox</b>, escalates tone by age, enforces approval gates, and verifies delivery — with official test-case evidence (TC1–TC4).
</p>

<p align="center">
  <a><img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python"></a>
  <a><img src="https://img.shields.io/badge/Flask-3.0.3-black?logo=flask" alt="Flask"></a>
  <a><img src="https://img.shields.io/badge/SQLite-Lightweight-blueviolet?logo=sqlite" alt="SQLite"></a>
  <a><img src="https://img.shields.io/badge/Tailwind-CSS-06B6D4?logo=tailwindcss" alt="Tailwind CSS"></a>
  <a><img src="https://img.shields.io/badge/License-MIT-green" alt="License"></a>
</p>

---

## 🚀 Demo in One Glance

| Component | What it does |
|-----------|--------------|
| **Mock Zoho Portal** | 4 seeded invoices (Acme Corp, Globex Inc, Stark Design, Wayne Tech) with amounts, due dates, days overdue, and client replies/promises. |
| **Agent Engine** | Collects portal state, applies decision rules, drafts escalation-aware reminders (Gentle → Firm → Urgent), and queues them for human approval. |
| **Human-in-the-Loop** | Approve & Send each draft from the UI — or simulate a network timeout (TC4) to test idempotency. |
| **Verification** | Independent post-send check against portal history to prevent duplicate sends. |
| **Test Suite** | Official test cases TC1–TC4 with traceable evidence and pass/fail status. |

---

## 🛠️ Tech Stack

<p align="center">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="40"/>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flask/flask-original.svg" width="40"/>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/sqlite/sqlite-original.svg" width="40"/>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-plain.svg" width="40"/>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" width="40"/>
</p>

- **Backend:** Python + Flask
- **Database:** SQLite (file-based `invoices.db`)
- **Frontend:** Tailwind CSS (via CDN), vanilla JS
- **Mock Target:** Zoho Invoice sandbox (simulated via `portal_invoices` table)

---

## 📦 Installation & Run

```bash
# 1. Clone the repo
git clone https://github.com/varnesh123/Overdue-invoice-agent.git
cd Overdue-invoice-agent

# 2. Create & activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

> The app auto-initializes the SQLite database and seeds demo invoices on first run. Use the **"Reset Sandbox"** button to restore the default state at any time.

---

## 🧭 How to Use the UI

1. **Trigger the agent** — Pick a base reminder tone (*Polite & Collaborative* or *Direct & Professional*) and click **"Run Agent: 'Chase My Overdue Invoices'"**. This polls the mock portal and generates reminder proposals.
2. **Review proposals** — Each invoice gets an escalated tone & draft message based on how overdue it is:
   - 1–7 days → Gentle Nudge
   - 8–20 days → Firm Follow-up
   - 21+ days → Urgent Final Notice
3. **Human Approval Gate** — Click **"✓ Approve & Send"** on any queued draft. Paid invoices are excluded automatically; disputed invoices are paused for manual review.
4. **Verify** — The agent checks portal send history before retrying, so duplicates are never sent (TC4).
5. **Run Official Tests** — Click **"⚡ Run Official Test Cases (TC1 – TC4)"** to execute the evidence matrix.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/state` | Fetch live portal state, agent logs, and test results. |
| `POST` | `/api/reset` | Reset sandbox to default seeded data. |
| `POST` | `/api/agent/plan` | Run agent: collect, draft reminders, queue for approval. |
| `POST` | `/api/agent/approve_and_send` | Human approve & send a queued reminder (with optional timeout simulation). |
| `POST` | `/api/agent/run_official_tests` | Execute TC1–TC4 test suite. |

---

## ✅ Official Test Cases (TC1 – TC4)

| TC | Scenario | Expected Result | Status |
|----|----------|-----------------|--------|
| **TC1** | Approved overdue reminder → sent once with portal record | Sent once; `portal_sent_count = 1` | ✅ Pass |
| **TC2** | Invoice paid since last run → excluded | Excluded from reminder queue | ✅ Pass |
| **TC3** | Client disputes an amount → reminders paused | Reminders paused; approval blocked | ✅ Pass |
| **TC4** | Send times out → history checked before retry | Duplicate re-send blocked | ✅ Pass |

Run them anytime from the UI or via `POST /api/agent/run_official_tests`.

---

## 🗄️ Database Schema

`invoices.db` contains three tables:

- **`portal_invoices`** — Mock Zoho sandbox state (invoice id, client, amount, due date, days overdue, payment state, client reply, promised date, sent count).
- **`agent_logs`** — Audit trail of every agent run (evidence, decision, draft, approval state, action status, verification status).
- **`test_runs`** — Results of TC1–TC4 test executions with input, expected, actual, and evidence.

---

## 📂 Project Structure

```
Overdue-invoice-agent/
├── app.py                # Flask backend + agent logic + DB init
├── invoices.db           # SQLite database (auto-created/seeded)
├── requirements.txt      # Python dependencies
├── README.md             # You are here
└── templates/
    └── index.html        # Tailwind-powered dashboard UI
```

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request with:

1. A clear description of the change
2. Screenshots (if UI-related)
3. Test results (TC1–TC4 still passing)

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built with ❤️ to automate overdue invoice follow-ups safely and transparently.</b>
</p>