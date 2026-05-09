"""Search-operator and dork-template guidance for DorXNG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_FILE_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "log", "zip", "tar", "gz"]
OBJECTIVE_ALIASES = {
    "files": "files",
    "file": "files",
    "documents": "files",
    "docs": "files",
    "archives": "archives",
    "backups": "archives",
    "backup": "archives",
    "directories": "directories",
    "indexes": "directories",
    "index": "directories",
    "code": "code",
    "source": "code",
    "config": "code",
    "broad": "broad",
    "all": "broad",
}


@dataclass(frozen=True)
class DorkTemplate:
    name: str
    query: str
    purpose: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "query": self.query, "purpose": self.purpose}


def _clean_target(target: str | None) -> str:
    if not target:
        return ""
    cleaned = target.strip()
    for prefix in ("https://", "http://"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    return cleaned.strip("/")


def _site_prefix(target: str | None) -> str:
    cleaned = _clean_target(target)
    return f"site:{cleaned} " if cleaned else ""


def _normalize_objective(objective: str) -> str:
    return OBJECTIVE_ALIASES.get(objective.strip().lower(), "broad")


def _normalize_file_types(file_types: Iterable[str] | None) -> list[str]:
    if not file_types:
        return DEFAULT_FILE_TYPES[:]
    normalized: list[str] = []
    for file_type in file_types:
        cleaned = file_type.strip().lower().lstrip(".")
        if cleaned and cleaned.replace("+", "p").replace("-", "p").isalnum() and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized or DEFAULT_FILE_TYPES[:]


def _or_terms(prefix: str, values: Iterable[str]) -> str:
    return " OR ".join(f"{prefix}:{value}" for value in values)


def suggest_dorks(target: str | None = None, objective: str = "broad", file_types: Iterable[str] | None = None) -> dict[str, Any]:
    """Build operator guidance and DorXNG query templates.

    The templates focus on file discovery, directory listings, public source/code
    references, and broad inventory queries.  They intentionally avoid templates
    centered on credential harvesting or personal targeting.
    """
    site = _site_prefix(target)
    cleaned_target = _clean_target(target)
    normalized_objective = _normalize_objective(objective)
    types = _normalize_file_types(file_types)
    doc_types = [item for item in types if item in {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv", "txt"}]
    archive_types = [item for item in types if item in {"zip", "tar", "gz", "tgz", "bz2", "7z", "rar", "bak", "old"}]
    if not doc_types:
        doc_types = ["pdf", "doc", "docx", "xls", "xlsx", "csv"]
    if not archive_types:
        archive_types = ["zip", "tar", "gz", "bak", "old"]

    templates_by_objective: dict[str, list[DorkTemplate]] = {
        "files": [
            DorkTemplate("document file types", f"{site}({_or_terms('filetype', doc_types)})", "Find indexed documents and spreadsheets."),
            DorkTemplate("PDF-only inventory", f"{site}filetype:pdf", "Find PDF documents."),
            DorkTemplate("spreadsheets", f"{site}(filetype:xls OR filetype:xlsx OR filetype:csv)", "Find spreadsheet-like files."),
            DorkTemplate("presentation files", f"{site}(filetype:ppt OR filetype:pptx)", "Find slide decks and presentation material."),
        ],
        "archives": [
            DorkTemplate("archive file types", f"{site}({_or_terms('filetype', archive_types)})", "Find indexed compressed archives and backup-like file extensions."),
            DorkTemplate("backup names", f"{site}inurl:backup OR inurl:archive OR inurl:old", "Find URLs whose paths suggest backups or archived content."),
            DorkTemplate("dated archives", f"{site}(inurl:2023 OR inurl:2024 OR inurl:2025 OR inurl:2026) (filetype:zip OR filetype:tar OR filetype:gz)", "Find date-stamped archives."),
        ],
        "directories": [
            DorkTemplate("directory listings", f"{site}intitle:\"index of\"", "Find indexed directory listing pages."),
            DorkTemplate("directory listings with parent", f"{site}intitle:\"index of\" \"parent directory\"", "Find directory listings with common parent-directory text."),
            DorkTemplate("upload directories", f"{site}intitle:\"index of\" (uploads OR files OR downloads OR docs)", "Find exposed file/download directories."),
        ],
        "code": [
            DorkTemplate("source-ish extensions", f"{site}(filetype:js OR filetype:py OR filetype:rb OR filetype:go OR filetype:java)", "Find indexed source-code-like files."),
            DorkTemplate("repository paths", f"{site}(inurl:.git OR inurl:src OR inurl:repo OR inurl:source)", "Find URLs whose paths suggest repositories or source trees."),
            DorkTemplate("configuration filenames", f"{site}(inurl:config OR inurl:settings OR inurl:properties OR inurl:yaml OR inurl:yml)", "Find configuration-related URLs for review."),
        ],
    }
    broad = [template for group in ("files", "archives", "directories", "code") for template in templates_by_objective[group]]
    selected = broad if normalized_objective == "broad" else templates_by_objective[normalized_objective]

    return {
        "target": cleaned_target or None,
        "objective": normalized_objective,
        "operators": [
            {"operator": "site:", "usage": "Restrict results to a domain, subdomain, or URL prefix.", "example": "site:example.com filetype:pdf"},
            {"operator": "filetype:/ext:", "usage": "Find indexed files by extension; support varies by upstream engine.", "example": "site:example.com filetype:xlsx"},
            {"operator": "intitle:", "usage": "Require a term in the page title.", "example": "site:example.com intitle:\"index of\""},
            {"operator": "inurl:", "usage": "Require a term in the URL path or host.", "example": "site:example.com inurl:downloads"},
            {"operator": "intext:", "usage": "Require a term in page text.", "example": "site:example.com intext:\"quarterly report\""},
            {"operator": "quotes", "usage": "Match an exact phrase.", "example": "site:example.com \"release notes\""},
            {"operator": "minus", "usage": "Exclude noisy terms.", "example": "site:example.com filetype:pdf -manual"},
            {"operator": "OR", "usage": "Combine alternatives. Use parentheses for readability when an engine supports them.", "example": "site:example.com (filetype:pdf OR filetype:docx)"},
            {"operator": "!engine", "usage": "SearXNG/DorXNG engine bang to prefer an upstream engine or category.", "example": "!google site:example.com filetype:pdf"},
        ],
        "workflow": [
            "Start broad with site: plus one operator family.",
            "Store deep searches with dorxng_search_and_store so you can regex-filter the SQLite database afterward.",
            "Pivot on recurring path names, titles, file extensions, and hostnames found in the first pass.",
            "Use negative terms to remove repeated marketing, documentation, or unrelated mirrors.",
            "Run several passes; DorXNG results can vary by upstream engine and Tor circuit.",
        ],
        "templates": [template.as_dict() for template in selected],
        "sources": [
            "DorXNG README: supports advanced search operators through multiple upstream providers; examples include site:example.com intext:example and SearXNG bangs.",
            "SearXNG Search API: q is passed to external search services, so upstream engine syntax such as site:github.com is valid.",
            "SearXNG search syntax: ! prefixes select engines/categories.",
            "Google Search docs: site:, quoted phrases, exclusions, and other operators refine searches.",
        ],
    }
