import os
import re
from datetime import date

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("second-brain-server")

SCOPES = ["https://www.googleapis.com/auth/drive"]
SA_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")

# Google Drive folder IDs for @Cerveau — share each with the service account email
FOLDER_IDS = {
    "inbox":         "18_er-3axcXsx63nwslYdOlmUvS-8f9dF",  # 05-inputs/a-traiter
    "03-veille":     "1oOkU8zbmNtFAQH4VrJ0k1yAC__sxdkwo",
    "04-reflexion":  "1vWCfaa36PCveKcaWIPORc26u4fWiLCZT",
    "02-account-sg": "1conmnIN4Vq11KOdOcS1oHCzraWc-OC37",
    "07-toolkit":    "1AbL0qDYzcUGW2upHLR30x_xhs8Y2Rmeq",
}

_drive_service = None


def _drive():
    global _drive_service
    if _drive_service is None:
        creds = service_account.Credentials.from_service_account_file(SA_FILE, scopes=SCOPES)
        _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


@mcp.tool()
def capture_note(note: str) -> dict:
    """
    Capture an idea, observation, or note and save it as a dated file in the inbox (05-inputs/a-traiter/).
    Use this when the input starts with '>'.
    """
    today = date.today().isoformat()
    service = _drive()

    existing = service.files().list(
        q=f"'{FOLDER_IDS['inbox']}' in parents and name contains '{today}' and trashed=false",
        fields="files(id)",
    ).execute()
    index = len(existing.get("files", [])) + 1

    filename = f"{today}-{index:02d}.md"
    content = f"---\ndate: {today}\n---\n\n{note.strip()}\n"

    media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain", resumable=False)
    created = service.files().create(
        body={"name": filename, "parents": [FOLDER_IDS["inbox"]]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    return {
        "status": "captured",
        "file": created["name"],
        "path": f"05-inputs/a-traiter/{created['name']}",
        "link": created.get("webViewLink", ""),
        "preview": note.strip()[:120],
    }


@mcp.tool()
def search_brain(query: str) -> dict:
    """
    Search the second brain for information matching the query.
    Use this when the input starts with '?'. Returns a summary and exact file locations.
    Note: only searches direct children of each brain folder (not recursive sub-folders).
    """
    keywords = [w for w in re.split(r"\s+", query.strip()) if len(w) > 2]
    if not keywords:
        return {"query": query, "results": [], "summary": "Requête trop courte."}

    service = _drive()

    folder_filter = " or ".join(f"'{fid}' in parents" for fid in FOLDER_IDS.values())
    # Drive API fullText search supports AND logic; cap at 3 terms to stay under query limits
    text_filter = " and ".join(f"fullText contains '{kw}'" for kw in keywords[:3])
    q = f"({folder_filter}) and ({text_filter}) and trashed=false"

    results = service.files().list(
        q=q,
        fields="files(id,name,parents,webViewLink,modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=5,
    ).execute()

    id_to_folder = {v: k for k, v in FOLDER_IDS.items()}
    matches = []
    for f in results.get("files", []):
        parent_id = (f.get("parents") or [None])[0]
        matches.append({
            "file": f["name"],
            "folder": id_to_folder.get(parent_id, "unknown"),
            "link": f.get("webViewLink", ""),
            "modified": (f.get("modifiedTime") or "")[:10],
        })

    if not matches:
        return {"query": query, "results": [], "summary": "Aucun résultat trouvé."}

    summary = "\n".join(
        f"- [{m['file']}]({m['link']}) ({m['folder']}, {m['modified']})" for m in matches
    )
    return {"query": query, "results": matches, "summary": summary}


@mcp.resource("brain://structure")
def brain_structure() -> str:
    """Returns the folder structure of the second brain."""
    return (
        "Structure du second cerveau (@Cerveau/) :\n"
        "  05-inputs/a-traiter/  → inbox (captures)\n"
        "  03-veille/            → signaux et synthèses de veille\n"
        "  04-reflexion/         → frameworks et synthèses hebdo\n"
        "  02-account-sg/        → dossiers professionnels\n"
        "  07-toolkit/           → prompts et artefacts\n"
    )


@mcp.prompt()
def mobile_session_start() -> str:
    """Startup prompt for mobile second brain sessions."""
    return (
        "Tu es mon assistant second cerveau. Mes fichiers sont sur Google Drive "
        "dans le dossier @Cerveau avec cette structure :\n"
        "  - 05-inputs/a-traiter/ → inbox (captures)\n"
        "  - 03-veille/ → signaux et synthèses de veille\n"
        "  - 04-reflexion/ → frameworks et synthèses hebdo\n"
        "  - 02-account-sg/ → dossiers professionnels\n"
        "  - 07-toolkit/ → prompts et artefacts\n\n"
        "Règles :\n"
        "  - '>' au début = capture → appelle capture_note\n"
        "  - '?' au début = recherche → appelle search_brain, réponds en 5 lignes max\n\n"
        "Confirme que tu es prêt."
    )


if __name__ == "__main__":
    mcp.run("stdio")
