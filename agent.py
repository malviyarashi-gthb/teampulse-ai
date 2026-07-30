"""
agent.py - AI Agent Engine for TeamPulse
Equipped with tools to query team health, blocker triage, 1:1 preparation, and sentiment analysis.
"""

import json
from typing import Dict, Any, List
import database

# -------------------------------------------------------------
# 1. TOOL DEFINITIONS (What the Agent can do)
# -------------------------------------------------------------
TOOLS = [
    {
        "name": "get_team_summary",
        "description": "Fetches the full pulse check of all direct reports for a manager including mood, blockers, 1:1 requests, and doc reviews.",
        "parameters": {
            "type": "object",
            "properties": {
                "manager_ldap": {"type": "string", "description": "The LDAP of the manager"}
            },
            "required": ["manager_ldap"]
        }
    },
    {
        "name": "get_critical_blockers",
        "description": "Lists all team members who currently have active blockers and describes what support they need.",
        "parameters": {
            "type": "object",
            "properties": {
                "manager_ldap": {"type": "string", "description": "The LDAP of the manager"}
            },
            "required": ["manager_ldap"]
        }
    },
    {
        "name": "get_1on1_prep",
        "description": "Compiles a comprehensive 1:1 preparation summary for a specific team member including their latest work, blockers, requested talking points, and recent doc links.",
        "parameters": {
            "type": "object",
            "properties": {
                "reportee_ldap": {"type": "string", "description": "The LDAP of the reportee"}
            },
            "required": ["reportee_ldap"]
        }
    },
    {
        "name": "get_leave_and_docs",
        "description": "Retrieves upcoming leave schedules and design/review docs waiting for manager attention.",
        "parameters": {
            "type": "object",
            "properties": {
                "manager_ldap": {"type": "string", "description": "The LDAP of the manager"}
            },
            "required": ["manager_ldap"]
        }
    }
]

# -------------------------------------------------------------
# 2. TOOL IMPLEMENTATIONS (Executing the database queries)
# -------------------------------------------------------------
def execute_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """Executes the specific tool function against the database."""
    if tool_name == "get_team_summary":
        manager_ldap = args.get("manager_ldap", "malviyarashi")
        team = database.get_latest_team_status(manager_ldap)
        return {
            "total_reportees": len(team),
            "reportees": team
        }

    elif tool_name == "get_critical_blockers":
        manager_ldap = args.get("manager_ldap", "malviyarashi")
        team = database.get_latest_team_status(manager_ldap)
        blocked = [r for r in team if r.get("has_blocker") == 1]
        return {
            "blocked_count": len(blocked),
            "blocked_members": [
                {
                    "name": r["name"],
                    "ldap": r["ldap"],
                    "blocker_details": r["blocker_details"],
                    "status_summary": r["status_summary"]
                }
                for r in blocked
            ]
        }

    elif tool_name == "get_1on1_prep":
        reportee_ldap = args.get("reportee_ldap")
        user = database.get_user(reportee_ldap)
        if not user:
            return {"error": f"User {reportee_ldap} not found"}
        history = database.get_user_history(reportee_ldap)
        latest = history[0] if history else None
        return {
            "user": user,
            "latest_checkin": latest,
            "recent_history_count": len(history)
        }

    elif tool_name == "get_leave_and_docs":
        manager_ldap = args.get("manager_ldap", "malviyarashi")
        team = database.get_latest_team_status(manager_ldap)
        leaves = [
            {"name": r["name"], "leave_info": r["leave_info"]}
            for r in team if r.get("leave_info") and r["leave_info"] != "None planned this month."
        ]
        docs = [
            {"name": r["name"], "doc_links": r["doc_links"]}
            for r in team if r.get("doc_links")
        ]
        return {
            "upcoming_leaves": leaves,
            "pending_doc_reviews": docs
        }

    return {"error": f"Unknown tool {tool_name}"}

# -------------------------------------------------------------
# 3. AGENT REASONING ENGINE
# -------------------------------------------------------------
def run_agent(query: str, manager_ldap: str = "malviyarashi") -> Dict[str, Any]:
    """
    Intelligent Agent Loop:
    1. Interprets manager's intent from the query.
    2. Selects and executes relevant tools.
    3. Synthesizes a structured, highly actionable response.
    """
    query_lower = query.lower()
    executed_tools = []
    
    # Reasoning logic for tool dispatch
    if any(k in query_lower for k in ["blocker", "stuck", "blocked", "issue", "problem", "help"]):
        tool_name = "get_critical_blockers"
        tool_args = {"manager_ldap": manager_ldap}
        result = execute_tool(tool_name, tool_args)
        executed_tools.append({"tool": tool_name, "args": tool_args, "result": result})

        # Synthesize response
        if result["blocked_count"] == 0:
            answer = "🎉 **Great news!** None of your direct reports have flagged any active blockers right now. The team is running smoothly."
        else:
            lines = [f"⚠️ **Found {result['blocked_count']} team member(s) facing critical blockers:**\n"]
            for m in result["blocked_members"]:
                lines.append(f"• **{m['name']}** (`{m['ldap']}`):\n  - **Blocker**: {m['blocker_details']}\n  - **Context**: {m['status_summary']}\n  - **Action Needed**: Manager reach-out / escalation recommended.")
            answer = "\n".join(lines)

    elif any(k in query_lower for k in ["1:1", "1 on 1", "one on one", "prep", "talk", "agenda", "meeting"]):
        # Check if a specific person is mentioned
        team = database.get_latest_team_status(manager_ldap)
        target_member = None
        for member in team:
            first_name = member["name"].split()[0].lower()
            if first_name in query_lower or member["ldap"].lower() in query_lower:
                target_member = member
                break

        if target_member:
            tool_name = "get_1on1_prep"
            tool_args = {"reportee_ldap": target_member["ldap"]}
            result = execute_tool(tool_name, tool_args)
            executed_tools.append({"tool": tool_name, "args": tool_args, "result": result})

            latest = result.get("latest_checkin", {})
            topics = latest.get("one_on_one_topics") or "No specific topics submitted."
            blocker = latest.get("blocker_details") if latest.get("has_blocker") else "None"
            docs = latest.get("doc_links") or "None"

            answer = (
                f"📋 **1:1 Prep Brief for {target_member['name']} ({target_member['title']})**\n\n"
                f"• **Current Sentiment / Mood**: {latest.get('mood', 'N/A').capitalize()}\n"
                f"• **Active Focus**: {latest.get('status_summary', 'N/A')}\n"
                f"• **Blockers**: {blocker}\n"
                f"• **Requested Talking Points**: {topics}\n"
                f"• **Docs Needing Your Review**: {docs}\n"
                f"• **Suggested Manager Action**: Acknowledge the requested topics early and check in on their workload balance."
            )
        else:
            # General 1:1 check
            team_with_1on1 = [r for r in team if r.get("wants_1on1") == 1]
            answer = f"📅 **1:1 Requests Overview ({len(team_with_1on1)} pending requests):**\n\n"
            for r in team_with_1on1:
                answer += f"• **{r['name']}**: Requested discussion on: *\"{r.get('one_on_one_topics')}\"*\n"
            answer += "\n💡 *Tip: Ask me 'Prep 1:1 for [Name]' to get a full customized meeting agenda.*"

    elif any(k in query_lower for k in ["leave", "vacation", "off", "doc", "review", "schedule"]):
        tool_name = "get_leave_and_docs"
        tool_args = {"manager_ldap": manager_ldap}
        result = execute_tool(tool_name, tool_args)
        executed_tools.append({"tool": tool_name, "args": tool_args, "result": result})

        lines = ["🏖️ **Upcoming Leaves & 📄 Pending Doc Reviews:**\n"]
        lines.append("**Upcoming Leaves:**")
        for l in result["upcoming_leaves"]:
            lines.append(f"• **{l['name']}**: {l['leave_info']}")
        lines.append("\n**Pending Design / Review Docs:**")
        for d in result["pending_doc_reviews"]:
            lines.append(f"• **{d['name']}**: {d['doc_links']}")
        answer = "\n".join(lines)

    else:
        # Default: Full Team Health Summary
        tool_name = "get_team_summary"
        tool_args = {"manager_ldap": manager_ldap}
        result = execute_tool(tool_name, tool_args)
        executed_tools.append({"tool": tool_name, "args": tool_args, "result": result})

        team = result["reportees"]
        happy_count = sum(1 for r in team if r.get("mood") == "happy")
        blocked_count = sum(1 for r in team if r.get("has_blocker") == 1)
        req_1on1_count = sum(1 for r in team if r.get("wants_1on1") == 1)

        lines = [
            f"📊 **Team Health Executive Summary ({len(team)} Direct Reports)**\n",
            f"• **Sentiment**: {happy_count}/{len(team)} team members feeling great 😄",
            f"• **Blockers**: {blocked_count} active blocker(s) flagged ⚠️",
            f"• **1:1 Requests**: {req_1on1_count} teammate(s) requested discussion 💬\n",
            "**Quick Team Roster Status:**"
        ]
        for r in team:
            mood_icon = "😄" if r.get("mood") == "happy" else ("🛑" if r.get("mood") in ["blocked", "overwhelmed"] else "😐")
            blocker_flag = " [BLOCKED]" if r.get("has_blocker") else ""
            lines.append(f"• {mood_icon} **{r['name']}**{blocker_flag}: {r.get('status_summary', 'No status yet')}")

        lines.append("\n*You can ask me specific questions like: 'Who is blocked?', 'Prep 1:1 for Alex', or 'Show leaves and docs'.*")
        answer = "\n".join(lines)

    return {
        "reply": answer,
        "tools_called": executed_tools
    }
