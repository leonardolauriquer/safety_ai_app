"""
NR Update Checker — SafetyAI

Semi-automatic checker for new versions of Normas Regulamentadoras (NRs) on the MTE portal.
Results are cached for 24h in data/nr_update_cache.json to avoid overloading the portal.
Local PDF metadata is persisted in data/nr_versions.json for fast comparisons.
Update history is persisted in data/nr_update_history.json.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).parent
_SRC_DIR = _PACKAGE_DIR.parent
_APP_ROOT = _SRC_DIR.parent
_DATA_DIR = _APP_ROOT / "data"
_NRS_DIR = _DATA_DIR / "nrs"
_CACHE_PATH = _DATA_DIR / "nr_update_cache.json"
_VERSIONS_PATH = _DATA_DIR / "nr_versions.json"
_HISTORY_PATH = _DATA_DIR / "nr_update_history.json"

CACHE_TTL_SECONDS = 24 * 3600
_LAST_MODIFIED_TOLERANCE_SECONDS = 86400

MAIN_NRS_LIST_URL = (
    "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho"
    "/seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs/"
)

NR_27_REVOKED = True
ALL_NRS = list(range(1, 39))

_REQUEST_TIMEOUT = 20
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SafetyAI-NRChecker/1.0; "
        "+https://github.com/safety-ai)"
    )
}


# ---------------------------------------------------------------------------
# Local metadata helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("Falha ao carregar %s: %s", path, exc)
    return default


def _save_json(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as exc:
        logger.error("Falha ao salvar %s: %s", path, exc)
        return False


def _get_local_pdf_path(nr_num: int) -> Path:
    return _NRS_DIR / f"NR-{nr_num:02d}.pdf"


def _get_local_pdf_metadata(nr_num: int) -> Optional[Dict[str, Any]]:
    """Return size and mtime of the local NR PDF, or None if not found."""
    path = _get_local_pdf_path(nr_num)
    if not path.exists():
        return None
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "mtime_str": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%d/%m/%Y %H:%M"
        ),
    }


def load_local_versions() -> Dict[str, Any]:
    return _load_json(_VERSIONS_PATH, {})


def save_local_versions(versions: Dict[str, Any]) -> bool:
    return _save_json(_VERSIONS_PATH, versions)


def update_local_version_for_nr(nr_num: int) -> None:
    """Refresh the local version record for a single NR after download."""
    versions = load_local_versions()
    meta = _get_local_pdf_metadata(nr_num)
    if meta:
        versions[str(nr_num)] = meta
        save_local_versions(versions)


# ---------------------------------------------------------------------------
# Update history helpers
# ---------------------------------------------------------------------------

def load_update_history() -> List[Dict[str, Any]]:
    return _load_json(_HISTORY_PATH, [])


def append_update_history(entry: Dict[str, Any]) -> None:
    """Append one update event to the history file (max 100 entries kept)."""
    history = load_update_history()
    history.insert(0, entry)
    history = history[:100]
    _save_json(_HISTORY_PATH, history)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def get_cached_check_results() -> Optional[Dict[str, Any]]:
    """Return cached check results if still valid (< 24h old), else None."""
    data = _load_json(_CACHE_PATH, {})
    if not data:
        return None
    cached_at = data.get("cached_at", 0)
    if time.time() - cached_at < CACHE_TTL_SECONDS:
        return data
    return None


def save_check_cache(results: List[Dict[str, Any]]) -> None:
    """Persist check results with current timestamp."""
    _save_json(
        _CACHE_PATH,
        {
            "cached_at": time.time(),
            "cached_at_str": datetime.now(tz=timezone.utc).strftime(
                "%d/%m/%Y %H:%M UTC"
            ),
            "results": results,
        },
    )


def invalidate_cache() -> None:
    """Remove cached results so the next check hits the portal."""
    try:
        if _CACHE_PATH.exists():
            _CACHE_PATH.unlink()
    except Exception as exc:
        logger.warning("Falha ao invalidar cache: %s", exc)


# ---------------------------------------------------------------------------
# URL discovery — single-pass: fetch listing page once, extract all NR URLs
# ---------------------------------------------------------------------------

def _discover_all_nr_pdf_urls() -> Dict[int, str]:
    """
    Fetch the MTE NR listing page once and extract PDF (or HTML page) URLs
    for all NRs in a single pass.  Then for HTML pages, fetch each HTML page
    to find the PDF link.

    Returns a dict mapping nr_num → pdf_url.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("BeautifulSoup não disponível — pip install beautifulsoup4")
        return {}

    html_pages: Dict[int, str] = {}
    pdf_urls: Dict[int, str] = {}

    try:
        resp = requests.get(
            MAIN_NRS_LIST_URL, headers=_HEADERS, timeout=_REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        content_core = soup.find("div", id="content-core")
        if not content_core:
            logger.warning("'content-core' não encontrado na página MTE.")
            return {}

        for link in content_core.find_all("a"):
            link_text = link.get_text(strip=True)
            m = re.search(r"NR-?0?(\d{1,2})(\b| -|$)", link_text, re.IGNORECASE)
            if not m:
                continue
            try:
                nr_num = int(m.group(1))
            except ValueError:
                continue
            if nr_num not in range(1, 39):
                continue

            href = link.get("href", "")
            if not href:
                continue
            if not href.startswith("http"):
                href = requests.compat.urljoin(MAIN_NRS_LIST_URL, href)

            if ".pdf" in href.lower() and (
                f"nr-{nr_num}" in href.lower() or f"nr{nr_num}" in href.lower()
            ):
                pdf_urls[nr_num] = href
            elif ".pdf" not in href.lower() and nr_num not in pdf_urls:
                html_pages[nr_num] = href

    except Exception as exc:
        logger.warning("Erro ao carregar página principal MTE: %s", exc)
        return {}

    for nr_num, html_url in html_pages.items():
        if nr_num in pdf_urls:
            continue
        pdf_url = _find_pdf_on_html_page(html_url, nr_num)
        if pdf_url:
            pdf_urls[nr_num] = pdf_url

    logger.info(
        "Descoberta de URLs: %d PDFs diretos + %d via página HTML = %d total",
        len(pdf_urls) - len(html_pages),
        sum(1 for n in html_pages if n in pdf_urls),
        len(pdf_urls),
    )
    return pdf_urls


def _find_pdf_on_html_page(html_url: str, nr_num: int) -> Optional[str]:
    """Visit the NR's HTML page and look for a PDF download link."""
    try:
        from bs4 import BeautifulSoup

        resp = requests.get(html_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE)):
            href = link.get("href", "")
            if not href.startswith("http"):
                href = requests.compat.urljoin(html_url, href)
            link_text = link.get_text(strip=True)
            if (
                f"nr-{nr_num}" in href.lower()
                or f"nr{nr_num}" in href.lower()
                or f"nr-{nr_num}" in link_text.lower()
                or f"nr{nr_num}" in link_text.lower()
            ):
                return href

    except Exception as exc:
        logger.warning("Erro ao buscar PDF na página HTML da NR-%d: %s", nr_num, exc)

    return None


# ---------------------------------------------------------------------------
# Remote metadata via HEAD request
# ---------------------------------------------------------------------------

def _fetch_remote_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Perform a HEAD request and return content-length + last-modified.
    Falls back to GET with stream=True if HEAD returns 405.
    """
    for method in ("HEAD", "GET"):
        try:
            if method == "HEAD":
                resp = requests.head(
                    url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT, allow_redirects=True
                )
            else:
                resp = requests.get(
                    url,
                    headers=_HEADERS,
                    timeout=_REQUEST_TIMEOUT,
                    stream=True,
                    allow_redirects=True,
                )
                resp.close()

            if resp.status_code == 405 and method == "HEAD":
                continue

            resp.raise_for_status()

            size_str = resp.headers.get("Content-Length")
            size = int(size_str) if size_str and size_str.isdigit() else None

            lm_str = resp.headers.get("Last-Modified", "")
            lm_dt: Optional[datetime] = None
            if lm_str:
                try:
                    lm_dt = parsedate_to_datetime(lm_str)
                except Exception:
                    pass

            return {
                "size": size,
                "last_modified": lm_dt.isoformat() if lm_dt else None,
                "last_modified_str": (
                    lm_dt.strftime("%d/%m/%Y %H:%M") if lm_dt else "—"
                ),
                "last_modified_ts": lm_dt.timestamp() if lm_dt else None,
                "url": url,
            }

        except Exception as exc:
            logger.warning("Falha em %s %s: %s", method, url, exc)

    return None


# ---------------------------------------------------------------------------
# Core check logic
# ---------------------------------------------------------------------------

def _is_outdated(local_meta: Dict[str, Any], remote: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Determine whether the remote NR is newer than the local copy.
    Compares BOTH size and Last-Modified; either signal can trigger an update.

    Returns (is_outdated, reason_string).
    """
    local_size = local_meta.get("size")
    remote_size = remote.get("size")
    local_mtime = local_meta.get("mtime")
    remote_lm_ts = remote.get("last_modified_ts")

    size_changed = (
        remote_size is not None
        and local_size is not None
        and remote_size != local_size
    )
    if size_changed:
        return True, f"tamanho diferente ({local_size:,} B → {remote_size:,} B)"

    lm_newer = (
        remote_lm_ts is not None
        and local_mtime is not None
        and remote_lm_ts > local_mtime + _LAST_MODIFIED_TOLERANCE_SECONDS
    )
    if lm_newer:
        local_dt = datetime.fromtimestamp(local_mtime, tz=timezone.utc).strftime("%d/%m/%Y")
        remote_dt = remote.get("last_modified_str", "?")
        return True, f"MTE mais recente ({local_dt} → {remote_dt})"

    if remote_size is None and remote_lm_ts is None:
        return False, "sem dados comparáveis do servidor"

    return False, "OK"


def _check_single_nr(
    nr_num: int,
    local_versions: Dict[str, Any],
    pdf_url: Optional[str],
) -> Dict[str, Any]:
    """
    Check one NR for updates given a pre-discovered pdf_url.
    Returns a result dict.
    """
    result: Dict[str, Any] = {
        "nr": nr_num,
        "nr_label": f"NR-{nr_num:02d}",
        "local_exists": False,
        "pdf_url": pdf_url,
        "local_size": None,
        "local_mtime_str": "—",
        "remote_size": None,
        "remote_last_modified_str": "—",
        "status": "unknown",
        "status_label": "—",
        "reason": "",
    }

    if nr_num == 27 and NR_27_REVOKED:
        result["status"] = "revoked"
        result["status_label"] = "⚠️ Revogada"
        return result

    local_meta = _get_local_pdf_metadata(nr_num)
    if local_meta:
        result["local_exists"] = True
        result["local_size"] = local_meta["size"]
        result["local_mtime_str"] = local_meta["mtime_str"]
        stored = local_versions.get(str(nr_num), {})
        if not stored or stored.get("size") != local_meta["size"]:
            local_versions[str(nr_num)] = local_meta
    else:
        result["status"] = "no_local"
        result["status_label"] = "❌ PDF local ausente"
        return result

    if not pdf_url:
        result["status"] = "no_remote"
        result["status_label"] = "⚠️ URL não encontrada"
        return result

    remote = _fetch_remote_metadata(pdf_url)
    if not remote:
        result["status"] = "no_remote"
        result["status_label"] = "⚠️ Sem resposta do servidor"
        return result

    result["remote_size"] = remote.get("size")
    result["remote_last_modified_str"] = remote.get("last_modified_str", "—")
    result["remote_last_modified"] = remote.get("last_modified")

    outdated, reason = _is_outdated(local_meta, remote)
    result["reason"] = reason

    if outdated:
        result["status"] = "outdated"
        result["status_label"] = "🆕 Nova versão disponível"
    else:
        result["status"] = "updated"
        result["status_label"] = "✅ Atualizada"

    return result


def check_nr_updates(force: bool = False) -> List[Dict[str, Any]]:
    """
    Check all NRs for available updates on the MTE portal.
    Results are cached for 24h unless force=True.
    Returns a list of result dicts (one per NR).
    """
    if not force:
        cached = get_cached_check_results()
        if cached:
            remaining = (CACHE_TTL_SECONDS - (time.time() - cached["cached_at"])) / 3600
            logger.info(
                "Retornando resultados do cache (%.1fh restantes)", remaining
            )
            return cached["results"]

    logger.info("Iniciando verificação de atualizações das NRs no portal MTE...")
    local_versions = load_local_versions()

    logger.info("Descobrindo URLs dos PDFs no portal MTE (passagem única)...")
    pdf_url_map = _discover_all_nr_pdf_urls()

    results: List[Dict[str, Any]] = []
    for nr_num in ALL_NRS:
        logger.info("Verificando NR-%d...", nr_num)
        try:
            result = _check_single_nr(
                nr_num, local_versions, pdf_url_map.get(nr_num)
            )
        except Exception as exc:
            logger.error("Erro ao verificar NR-%d: %s", nr_num, exc)
            result = {
                "nr": nr_num,
                "nr_label": f"NR-{nr_num:02d}",
                "local_exists": False,
                "pdf_url": pdf_url_map.get(nr_num),
                "local_size": None,
                "local_mtime_str": "—",
                "remote_size": None,
                "remote_last_modified_str": "—",
                "status": "error",
                "status_label": f"❌ Erro: {str(exc)[:60]}",
                "reason": str(exc),
            }
        results.append(result)

    save_local_versions(local_versions)
    save_check_cache(results)
    logger.info("Verificação concluída: %d NRs verificadas.", len(results))
    return results


# ---------------------------------------------------------------------------
# Download & reindex (with old-chunk purge)
# ---------------------------------------------------------------------------

def _purge_nr_chunks_from_chroma(nr_num: int, qa_instance: Any) -> int:
    """
    Delete all existing ChromaDB chunks for a given NR (identified by
    source_file = 'NR-XX.pdf' and source = 'MTE-oficial') before reindexing.
    Returns the count of deleted chunks.
    """
    fname = f"NR-{nr_num:02d}.pdf"
    try:
        collection = qa_instance.vector_db._collection
        res = collection.get(
            where={"$and": [{"source": "MTE-oficial"}, {"source_file": fname}]},
            include=["metadatas"],
        )
        ids = res.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            logger.info(
                "NR-%d: %d chunks antigos removidos do ChromaDB antes da reindexação",
                nr_num, len(ids),
            )
        return len(ids)
    except Exception as exc:
        logger.warning(
            "NR-%d: falha ao purgar chunks antigos do ChromaDB: %s", nr_num, exc
        )
        return 0


def download_nr_update(nr_num: int, pdf_url: str) -> Tuple[bool, str]:
    """
    Download the NR PDF from pdf_url and replace the local file atomically.
    Returns (success, message).
    """
    dest = _get_local_pdf_path(nr_num)
    tmp = dest.with_suffix(".pdf.tmp")

    local_before = _get_local_pdf_metadata(nr_num)
    size_before = local_before["size"] if local_before else None

    try:
        resp = requests.get(
            pdf_url,
            headers=_HEADERS,
            timeout=120,
            stream=True,
            allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet" not in content_type.lower():
            return False, f"Tipo de conteúdo inesperado: {content_type}"

        _NRS_DIR.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        size_after = tmp.stat().st_size
        if size_after < 1024:
            tmp.unlink(missing_ok=True)
            return False, f"Arquivo muito pequeno ({size_after} B) — provável página de erro"

        tmp.replace(dest)
        update_local_version_for_nr(nr_num)
        invalidate_cache()

        size_str_before = f"{size_before:,} B" if size_before else "—"
        size_str_after = f"{size_after:,} B"
        msg = (
            f"NR-{nr_num:02d} atualizada: versão anterior {size_str_before} → "
            f"nova versão {size_str_after}"
        )
        logger.info(msg)
        return True, msg

    except Exception as exc:
        tmp.unlink(missing_ok=True)
        msg = f"Falha ao baixar NR-{nr_num:02d}: {exc}"
        logger.error(msg)
        return False, msg


def trigger_reindex_for_nr(nr_num: int, qa_instance: Any) -> Tuple[bool, str]:
    """
    Safely reindex a single NR PDF:
    1. Purge all existing MTE-oficial chunks for this NR from ChromaDB.
    2. Re-ingest the updated PDF via process_document_to_chroma.
    Returns (success, message).
    """
    pdf_path = _get_local_pdf_path(nr_num)
    if not pdf_path.exists():
        return False, f"PDF NR-{nr_num:02d} não encontrado em {pdf_path}"

    fname = pdf_path.name
    try:
        purged = _purge_nr_chunks_from_chroma(nr_num, qa_instance)
        before = qa_instance.vector_db._collection.count()
        qa_instance.process_document_to_chroma(
            file_path=str(pdf_path),
            document_name=fname,
            source="MTE-oficial",
            file_type="application/pdf",
            additional_metadata={
                "nr_number": nr_num,
                "doc_type": "norma_regulamentadora",
                "source": "MTE-oficial",
                "source_file": fname,
                "document_name": fname,
                "source_type": "local_pdf",
            },
        )
        after = qa_instance.vector_db._collection.count()
        added = after - before
        msg = (
            f"NR-{nr_num:02d} reindexada: {purged} chunks removidos, "
            f"+{added} novos chunks no ChromaDB"
        )
        logger.info(msg)
        return True, msg
    except Exception as exc:
        msg = f"Erro ao reindexar NR-{nr_num:02d}: {exc}"
        logger.error(msg)
        return False, msg
