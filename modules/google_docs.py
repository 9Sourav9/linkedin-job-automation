"""
Google Docs integration.
Creates and updates a Google Doc with job listings.
Also uploads tailored resumes to Google Drive.
"""
import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config


def _get_google_credentials() -> Credentials:
    """Obtain valid Google OAuth2 credentials."""
    creds = None

    if os.path.exists(config.GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(
            config.GOOGLE_TOKEN_PATH, config.GOOGLE_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GOOGLE_CREDENTIALS_PATH,
                config.GOOGLE_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(config.GOOGLE_TOKEN_PATH), exist_ok=True)
        with open(config.GOOGLE_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return creds


def _get_services():
    creds = _get_google_credentials()
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return docs_service, drive_service


def create_jobs_doc(jobs: list, doc_title: str = None) -> str:
    """
    Create a Google Doc with all job listings.
    Returns the document URL.
    """
    if not doc_title:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        doc_title = f"LinkedIn Jobs — {date_str}"

    docs_service, drive_service = _get_services()

    # Create document
    doc = docs_service.documents().create(body={"title": doc_title}).execute()
    doc_id = doc["documentId"]
    print(f"[Google Docs] Created document: {doc_title} (ID: {doc_id})")

    # Build content as batch requests
    requests = []
    index = 1  # Track insertion index

    # ── Title ──────────────────────────────────────────────────────
    title_text = f"{doc_title}\n"
    requests.append({"insertText": {"location": {"index": index}, "text": title_text}})
    requests.append({
        "updateParagraphStyle": {
            "range": {"startIndex": index, "endIndex": index + len(title_text)},
            "paragraphStyle": {"namedStyleType": "TITLE"},
            "fields": "namedStyleType",
        }
    })
    index += len(title_text)

    # ── Summary line ───────────────────────────────────────────────
    summary_text = (
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}\n"
        f"Total Jobs: {len(jobs)}\n"
        f"Search Keywords: {', '.join(config.JOB_KEYWORDS)}\n"
        f"Location: {config.JOB_LOCATION or 'Any'}\n"
        f"Date Filter: {config.DATE_FILTER_LABELS.get(config.JOB_DATE_FILTER, 'Any time')}\n\n"
    )
    requests.append({"insertText": {"location": {"index": index}, "text": summary_text}})
    index += len(summary_text)

    # ── Separator ──────────────────────────────────────────────────
    sep = "─" * 60 + "\n\n"
    requests.append({"insertText": {"location": {"index": index}, "text": sep}})
    index += len(sep)

    # ── Job entries ────────────────────────────────────────────────
    for i, job in enumerate(jobs, 1):
        entry = _format_job_entry(i, job)
        requests.append({"insertText": {"location": {"index": index}, "text": entry}})

        # Style the job title (first line of entry)
        title_end = index + len(f"#{i}. {job['title']}\n")
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": index, "endIndex": title_end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        })

        index += len(entry)

    # Send all requests in one batch
    docs_service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"[Google Docs] Document ready: {doc_url}")
    return doc_url


def update_job_status(doc_id: str, job_id: str, status: str, resume_url: str = ""):
    """Update application status for a job in the Google Doc."""
    # This would require tracking paragraph indices, which is complex.
    # For simplicity, we append a status update at the end of the doc.
    docs_service, _ = _get_services()

    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    end_index = content[-1]["endIndex"] - 1 if content else 1

    status_text = f"\n[UPDATE] Job {job_id}: {status}"
    if resume_url:
        status_text += f" | Resume: {resume_url}"
    status_text += "\n"

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {"insertText": {"location": {"index": end_index}, "text": status_text}}
            ]
        },
    ).execute()


def upload_resume_to_drive(resume_path: str, job_title: str, company: str) -> str:
    """Upload tailored resume DOCX to Google Drive. Returns the file URL."""
    _, drive_service = _get_services()

    filename = os.path.basename(resume_path)
    folder_id = _get_or_create_resume_folder(drive_service)

    file_metadata = {
        "name": f"Resume — {job_title} @ {company}.docx",
        "parents": [folder_id],
    }
    media = MediaFileUpload(
        resume_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    uploaded = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    file_url = uploaded.get("webViewLink", "")
    print(f"[Drive] Uploaded resume: {file_url}")
    return file_url


def _get_or_create_resume_folder(drive_service) -> str:
    """Get or create 'LinkedIn Job Applications' folder in Drive."""
    folder_name = "LinkedIn Job Applications"

    # Search for existing folder
    results = (
        drive_service.files()
        .list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)",
        )
        .execute()
    )
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # Create new folder
    folder = (
        drive_service.files()
        .create(
            body={
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        )
        .execute()
    )
    print(f"[Drive] Created folder: {folder_name}")
    return folder["id"]


def _format_job_entry(index: int, job: dict) -> str:
    """Format a single job entry for the Google Doc."""
    easy_apply_tag = "✅ Easy Apply" if job.get("is_easy_apply") else "🔗 External Apply"
    status_emoji = {
        "pending": "⏳",
        "applied": "✅",
        "failed": "❌",
        "skipped": "⏭️",
    }.get(job.get("application_status", "pending"), "⏳")

    entry = (
        f"#{index}. {job['title']}\n"
        f"🏢 Company: {job['company']}\n"
        f"📍 Location: {job['location']} | {job.get('remote_type', '')}\n"
        f"📅 Posted: {job.get('posted_date', 'N/A')}\n"
        f"💼 Type: {job.get('job_type', 'N/A')} | Level: {job.get('seniority_level', 'N/A')}\n"
        f"🏭 Industry: {job.get('industry', 'N/A')}\n"
        f"{easy_apply_tag}\n"
        f"🔗 URL: {job.get('job_url', 'N/A')}\n"
        f"{status_emoji} Status: {job.get('application_status', 'pending').title()}\n"
    )

    if job.get("tailored_resume_path"):
        entry += f"📄 Tailored Resume: {job['tailored_resume_path']}\n"

    if job.get("error_msg"):
        entry += f"⚠️ Error: {job['error_msg']}\n"

    # First 300 chars of JD as preview
    desc = job.get("description", "")
    if desc:
        preview = desc[:300].replace("\n", " ").strip()
        entry += f"\n📋 Description Preview:\n{preview}...\n"

    entry += "\n" + "─" * 50 + "\n\n"
    return entry


def save_jobs_to_json(jobs: list, path: str = "outputs/jobs.json"):
    """Save job listings to a local JSON file as backup."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"[Output] Jobs saved to {path}")
