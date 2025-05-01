from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from auth import router as auth_router
from jira_utils import (                 # ← ONLY imports that exist
    create_bug_issue_with_attachments,
    search_issues,
    get_issue_details,
    add_subtasks_to_existing,
    get_priority_and_category_options
)
from slack_utils import send_slack_notification
import os, uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")

@app.get("/")
def root():
    return {"status": "Bug Cutter backend live"}

@app.post("/submit_bug/")
async def submit_bug(
    summary: str = Form(...),
    description: str = Form(...),
    priority: str = Form(None),
    category: str = Form(None),
    assignee: str = Form(None),
    components: str = Form(None),
    subtasks: str = Form(None),
    token: str = Form(...),
    files: list[UploadFile] = File(None),
):
    try:
        subtask_list = [s.strip() for s in (subtasks or "").split("\n") if s.strip()]
        bug_key = await create_bug_issue_with_attachments(
            token, summary, description, priority, category,
            assignee, components, files, subtask_list
        )
        await send_slack_notification(bug_key, summary,
                                      priority or "", category or "")
        return {"success": True, "issue_key": bug_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/options")
async def get_options(token: str):
    try:
        priorities, categories = await get_priority_and_category_options(token)
        return {"priorities": priorities, "categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search_bugs")
async def search_bugs(q: str, token: str):
    try:
        return {"results": await search_issues(token, q)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bug/{issue_id}")
async def get_bug(issue_id: str, token: str):
    try:
        return await get_issue_details(token, issue_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bug/{issue_id}/add_subtask")
async def add_subtask(issue_id: str,
                      token: str = Form(...),
                      subtasks: str = Form(...)):
    try:
        subtask_list = [s.strip() for s in subtasks.split("\n") if s.strip()]
        await add_subtasks_to_existing(token, issue_id, subtask_list)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)))
