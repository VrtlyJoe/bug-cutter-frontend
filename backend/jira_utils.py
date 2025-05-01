# backend/jira_utils.py  ── COMPLETE FILE
import requests
from typing import List
from fastapi import UploadFile

JIRA_API_BASE = "https://api.atlassian.com/ex/jira"
CLOUD_ID_ENDPOINT = "https://api.atlassian.com/oauth/token/accessible-resources"
PROJECT_KEY = "VT"

BUG_CATEGORY_FIELD_ID: str | None = None


# ── user info helper (needed by FE & Slack) ──────────────────────────────
def get_current_user(token: str) -> dict:
    r = requests.get(
        "https://api.atlassian.com/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    d = r.json()
    return {
        "account_id": d.get("account_id"),
        "email": d.get("email"),
        "name": d.get("name"),
    }


async def get_cloud_id(token: str) -> str:
    r = requests.get(CLOUD_ID_ENDPOINT, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()[0]["id"]


# ── issue creation (attachments + subtasks) ─────────────────────────────
async def create_bug_issue_with_attachments(
    token: str,
    summary: str,
    description: str,
    priority: str,
    category: str,
    assignee: str,
    components: str,
    files: List[UploadFile],
    subtasks: List[str] | None = None,
) -> str:
    subtasks = subtasks or []
    cloud_id = await get_cloud_id(token)
    api_url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue"
    hdr = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    fields = {
        "project": {"key": PROJECT_KEY},
        "summary": summary or "Untitled bug",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description or "—"}],
                }
            ],
        },
        "issuetype": {"name": "Bug"},
    }
    if priority:
        fields["priority"] = {"name": priority}
    if category and BUG_CATEGORY_FIELD_ID:
        fields[BUG_CATEGORY_FIELD_ID] = {"value": category}
    if assignee:
        fields["assignee"] = {"accountId": assignee}
    if components:
        fields["components"] = [
            {"name": c.strip()} for c in components.split(",") if c.strip()
        ]

    print("📦 Payload to Jira:", fields)
    create_r = requests.post(api_url, headers=hdr, json={"fields": fields})
    print("🔎 Jira create status:", create_r.status_code)
    create_r.raise_for_status()
    key = create_r.json()["key"]

    if files:
        await upload_attachments(token, cloud_id, key, files)
    for sub in subtasks:
        await create_subtask(token, cloud_id, key, sub.strip())

    return key


async def upload_attachments(
    token: str, cloud_id: str, issue_key: str, files: List[UploadFile]
):
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue/{issue_key}/attachments"
    hdr = {"Authorization": f"Bearer {token}", "X-Atlassian-Token": "no-check"}
    for f in files:
        data = await f.read()
        r = requests.post(
            url,
            headers=hdr,
            files={"file": (f.filename, data, f.content_type or "application/octet-stream")},
        )
        r.raise_for_status()


async def create_subtask(
    token: str, cloud_id: str, parent_key: str, summary: str
) -> None:
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue"
    hdr = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    r = requests.post(
        url,
        headers=hdr,
        json={
            "fields": {
                "project": {"key": PROJECT_KEY},
                "parent": {"key": parent_key},
                "summary": summary,
                "issuetype": {"name": "Sub-task"},
            }
        },
    )
    r.raise_for_status()


# ── dynamic options (priority + categories) ────────────────────────────
async def get_priority_and_category_options(token: str):
    global BUG_CATEGORY_FIELD_ID
    cloud_id = await get_cloud_id(token)
    hdr = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    pr = requests.get(f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/priority", headers=hdr)
    pr.raise_for_status()
    priorities = [p["name"] for p in pr.json()]
    if "Lowest" not in priorities:
        priorities.append("Lowest")

    fr = requests.get(f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/field", headers=hdr)
    fr.raise_for_status()
    category_options = []
    BUG_CATEGORY_FIELD_ID = None
    for f in fr.json():
        if f.get("name", "").lower() == "bug category":
            BUG_CATEGORY_FIELD_ID = f["id"]
            allowed = f.get("allowedValues") or []
            category_options = [o["value"] for o in allowed] if allowed else [
                "Web UI",
                "App",
                "Back End",
                "Admin",
                "Other",
            ]
            break
    return priorities, category_options


# ── searches / details helpers (unchanged) ─────────────────────────────
async def search_issues(token: str, query: str):
    cloud_id = await get_cloud_id(token)
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/search"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "jql": f'summary ~ "{query}" AND project="{PROJECT_KEY}" order by updated DESC',
            "maxResults": 10,
        },
    )
    r.raise_for_status()
    return [{"key": i["key"], "summary": i["fields"]["summary"]} for i in r.json()["issues"]]


async def get_issue_details(token: str, issue_id: str):
    cloud_id = await get_cloud_id(token)
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/issue/{issue_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    d = r.json()
    return {
        "key": d["key"],
        "summary": d["fields"]["summary"],
        "description": d["fields"].get("description", ""),
        "subtasks": [
            st["key"] + " – " + st["fields"]["summary"] for st in d["fields"]["subtasks"]
        ],
    }


async def add_subtasks_to_existing(token: str, issue_id: str, summaries: List[str]):
    cloud_id = await get_cloud_id(token)
    for s in summaries:
        await create_subtask(token, cloud_id, issue_id, s.strip())


async def search_users(token: str, query: str):
    cloud_id = await get_cloud_id(token)
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/user/search"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={"query": query, "maxResults": 10},
    )
    r.raise_for_status()
    return [
        {
            "displayName": u["displayName"],
            "accountId": u["accountId"],
            "email": u.get("emailAddress", ""),
        }
        for u in r.json()
    ]


async def get_project_components(token: str):
    cloud_id = await get_cloud_id(token)
    url = f"{JIRA_API_BASE}/{cloud_id}/rest/api/3/project/{PROJECT_KEY}/components"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return [c["name"] for c in r.json()]
