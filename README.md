# TeamPulse AI 🚀
### Team Health, Blocker Triage, 1:1 Prep, and AI Management Copilot

An end-to-end full-stack AI application consisting of an **API**, **SQLite Database**, **Responsive Dual-Role Web UI**, and an **Autonomous AI Reasoning Agent**.

---

## 🌟 Key Features
- **1. Manager Dashboard**: Live pulse on direct reports, active blocker alerts, 1:1 discussion requests, and doc review queue.
- **2. Team Member Check-In Portal**: Weekly status update form with mood picker (😄/😐/🛑/⚡), blocker flagging, 1:1 agenda topics, and upcoming leave plans.
- **3. AI Management Copilot**: Autonomous agent equipped with database tools to triage blockers, summarize team health, and generate 1:1 briefing sheets.
- **4. Zero External Dependencies**: Runs using standard Python's built-in libraries out-of-the-box.

---

## 🚀 Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/teampulse-ai.git
   cd teampulse-ai
   ```

2. **Run the server:**
   ```bash
   python3 server.py
   ```

3. **Open in your browser:**
   Navigate to [http://localhost:8080](http://localhost:8080).

---

## 📂 Project Structure
- `database.py` - SQLite schema, CRUD operations, and initial seed data.
- `agent.py` - AI agent reasoning engine and tool calling definitions.
- `server.py` - Zero-dependency Python standard library HTTP & REST API server.
- `main.py` - FastAPI + Pydantic alternative server.
- `static/index.html` - Dual-role responsive web UI powered by Tailwind CSS.
- `Dockerfile` - Container definition for one-click Cloud Run deployment.
