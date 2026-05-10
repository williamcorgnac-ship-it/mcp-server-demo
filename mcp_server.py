import os
import re
from datetime import date
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("second-brain-server")

BRAIN_ROOT = os.environ.get("BRAIN_ROOT", os.path.expanduser("~/@Cerveau"))
INBOX = os.path.join(BRAIN_ROOT, "05-inputs", "a-traiter")
SEARCH_DIRS = [
    os.path.join(BRAIN_ROOT, "05-inputs"),
    os.path.join(BRAIN_ROOT, "03-veille"),
    os.path.join(BRAIN_ROOT, "04-reflexion"),
    os.path.join(BRAIN_ROOT, "02-account-sg"),
    os.path.join(BRAIN_ROOT, "07-toolkit"),
]


@mcp.tool()
def capture_note(note: str) -> dict:
    """
    Capture an idea, observation, or note and save it as a dated file in the inbox.
    Use this when the input starts with '>'.
    """
    os.makedirs(INBOX, exist_ok=True)
    today = date.today().isoformat()
    existing = [f for f in os.listdir(INBOX) if f.startswith(today)]
    index = len(existing) + 1
    filename = f"{today}-{index:02d}.md"
    filepath = os.path.join(INBOX, filename)
    content = f"---\ndate: {today}\n---\n\n{note.strip()}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return {
        "status": "captured",
        "file": filename,
        "path": f"05-inputs/a-traiter/{filename}",
        "preview": note.strip()[:120],
    }


@mcp.tool()
def search_brain(query: str) -> dict:
    """
    Search the second brain for information matching the query.
    Use this when the input starts with '?'. Returns a summary and the exact locations of matches.
    """
    keywords = [w.lower() for w in re.split(r"\s+", query.strip()) if len(w) > 2]
    matches = []

    for search_dir in SEARCH_DIRS:
        if not os.path.isdir(search_dir):
            continue
        for root, _, files in os.walk(search_dir):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    text = open(fpath, encoding="utf-8").read()
                except OSError:
                    continue
                lower_text = text.lower()
                hits = sum(1 for kw in keywords if kw in lower_text)
                if hits == 0:
                    continue
                # Extract first matching line as excerpt
                excerpt = next(
                    (line.strip() for line in text.splitlines()
                     if any(kw in line.lower() for kw in keywords) and line.strip()),
                    ""
                )
                rel_path = os.path.relpath(fpath, BRAIN_ROOT)
                matches.append({"file": rel_path, "score": hits, "excerpt": excerpt[:200]})

    matches.sort(key=lambda m: m["score"], reverse=True)
    top = matches[:5]

    if not top:
        return {"query": query, "results": [], "summary": "Aucun résultat trouvé."}

    summary_lines = [f"- {m['file']}: {m['excerpt']}" for m in top]
    return {
        "query": query,
        "results": top,
        "summary": "\n".join(summary_lines),
    }


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
        "Tu es mon assistant second cerveau. Mes fichiers sont dans le dossier @Cerveau "
        "avec cette structure :\n"
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
