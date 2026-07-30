"""
main.py - FastAPI Backend Server for TeamPulse
Serves REST APIs for Manager View, Reportee Check-In Portal, and AI Agent Chat.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import database
import agent

app = FastAPI(
    title="TeamPulse AI API",
    description="Team Health, Blocker Tracking, and AI Management Copilot",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on startup
@app.on_event("startup")
def on_startup():
    database.init_db()

# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------
class CheckInRequest(BaseModel):
    user_ldap: str
    mood: str
    status_summary: str
    has_blocker: bool = False
    blocker_details: Optional[str] = ""
    wants_1on1: bool = False
    one_on_one_topics: Optional[str] = ""
    leave_info: Optional[str] = ""
    doc_links: Optional[str] = ""

class AgentChatRequest(BaseModel):
    manager_ldap: str = "malviyarashi"
    message: str

class SyncMomaRequest(BaseModel):
    manager_ldap: str

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.get("/api/users")
def get_all_users():
    """Lists all available users for role-switching in the UI."""
    return database.get_all_users()

@app.get("/api/manager/{manager_ldap}/overview")
def get_manager_team_overview(manager_ldap: str):
    """
    Manager View Endpoint: Returns latest statuses, blockers, leaves,
    and 1:1 requests for all direct reportees.
    """
    team_status = database.get_latest_team_status(manager_ldap)
    return {
        "manager_ldap": manager_ldap,
        "team_count": len(team_status),
        "team": team_status
    }

@app.post("/api/checkin")
def submit_checkin(payload: CheckInRequest):
    """
    Reportee View Endpoint: Allows team members to submit status,
    flag blockers, request 1:1s, and attach docs.
    """
    checkin_id = database.add_checkin(payload.dict())
    return {
        "success": True,
        "message": "Status update and pulse check submitted successfully!",
        "checkin_id": checkin_id
    }

@app.get("/api/user/{user_ldap}/history")
def get_user_history(user_ldap: str):
    """Returns past check-in history for a team member."""
    history = database.get_user_history(user_ldap)
    return {"user_ldap": user_ldap, "history": history}

@app.post("/api/agent/chat")
def chat_with_agent(req: AgentChatRequest):
    """
    AI Agent Endpoint: Manager interacts with the AI Copilot to
    analyze team pulse, blockers, and prepare for 1:1s.
    """
    response = agent.run_agent(req.message, req.manager_ldap)
    return response

@app.post("/api/sync-moma")
def sync_moma_hierarchy(req: SyncMomaRequest):
    """
    Moma/TeamGraph Sync Endpoint:
    In production, connects to Google HR API / Moma TeamGraph to fetch live reportees.
    In local dev, ensures the hierarchy is up-to-date.
    """
    reportees = database.get_reportees_for_manager(req.manager_ldap)
    return {
        "status": "synced",
        "source": "Moma TeamGraph & HR API Bridge",
        "manager": req.manager_ldap,
        "synced_reportees_count": len(reportees),
        "synced_reportees": [r["ldap"] for r in reportees]
    }

# -------------------------------------------------------------
# Static Files & UI Serving
# -------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
