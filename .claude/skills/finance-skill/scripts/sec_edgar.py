#!/usr/bin/env python3
"""
SEC EDGAR client with caching and parsing.

Usage:
    from sec_edgar import get_latest_filing, get_financial_statements

    # Get latest 10-K for Apple
    filing = get_latest_filing("0000320193", "10-K")
    # → {"form": "10-K", "filed": "2025-10-31", "accession": "0000320193-25-000079", ...}

    # Get parsed financial statements
    financials = get_financial_statements("0000320193", filing["accession"])
    # → {"income_statement": [...], "balance_sheet": [...]}
"""

import venv  # Auto-setup venv before other imports
import env  # Load .env before other imports

import os
import re
import urllib.request
from cache import cached_request, set_cached, get_cached, SSL_CONTEXT

BASE_URL = "https://data.sec.gov"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

# Common CIKs for reference
CIKS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "TSLA": "0001318605",
    "META": "0001326801",
    "NVDA": "0001045810",
    "BRK-B": "0001067983",
    "JPM": "0000019617",
}


def _get_user_agent() -> str:
    """Get User-Agent from environment."""
    user_agent = os.environ.get("SEC_EDGAR_USER_AGENT")
    if not user_agent:
        raise Exception("SEC_EDGAR_USER_AGENT environment variable not set. "
                        "Set it to 'YourName your_email@example.com'")
    return user_agent


def _normalize_cik(cik: str) -> str:
    """Normalize CIK to 10-digit zero-padded format."""
    # Handle ticker symbols
    if cik.upper() in CIKS:
        return CIKS[cik.upper()]
    # Remove leading zeros and re-pad
    return cik.lstrip("0").zfill(10)


def _accession_no_dashes(accession: str) -> str:
    """Convert accession number to no-dashes format for URLs."""
    return accession.replace("-", "")


def request(endpoint: str) -> dict:
    """
    Make a cached request to SEC EDGAR API.

    Args:
        endpoint: API endpoint (e.g., "submissions/CIK0000320193.json")

    Returns:
        Parsed JSON response
    """
    url = f"{BASE_URL}/{endpoint}"
    cache_key = f"sec-edgar/{endpoint.replace('/', '_')}"
    headers = {"User-Agent": _get_user_agent()}
    return cached_request(url, cache_key, headers=headers)


def get_submissions(cik: str) -> dict:
    """
    Get company submissions (info + filing history).

    Args:
        cik: Company CIK (e.g., "0000320193") or ticker (e.g., "AAPL")

    Returns:
        dict with company info and filings
    """
    cik = _normalize_cik(cik)
    return request(f"submissions/CIK{cik}.json")


def get_company_facts(cik: str) -> dict:
    """
    Get all XBRL financial facts for a company.

    Args:
        cik: Company CIK or ticker

    Returns:
        dict with all reported financial facts
    """
    cik = _normalize_cik(cik)
    return request(f"api/xbrl/companyfacts/CIK{cik}.json")


def get_latest_filing(cik: str, form_type: str) -> dict | None:
    """
    Get the most recent filing of a specific type.

    Args:
        cik: Company CIK or ticker
        form_type: Form type (e.g., "10-K", "10-Q", "8-K")

    Returns:
        dict with filing metadata or None if not found
    """
    submissions = get_submissions(cik)
    filings = submissions["filings"]["recent"]

    for i, form in enumerate(filings["form"]):
        if form == form_type:
            return {
                "form": form,
                "filed": filings["filingDate"][i],
                "accession": filings["accessionNumber"][i],
                "primary_document": filings["primaryDocument"][i],
                "report_date": filings["reportDate"][i],
                "company": submissions.get("name", ""),
                "cik": submissions.get("cik", ""),
            }
    return None


def get_filings(cik: str, form_type: str = None, limit: int = 10) -> list[dict]:
    """
    Get recent filings, optionally filtered by form type.

    Args:
        cik: Company CIK or ticker
        form_type: Optional form type filter
        limit: Maximum number of filings to return

    Returns:
        List of filing metadata dicts
    """
    submissions = get_submissions(cik)
    filings = submissions["filings"]["recent"]
    results = []

    for i, form in enumerate(filings["form"]):
        if form_type and form != form_type:
            continue
        results.append({
            "form": form,
            "filed": filings["filingDate"][i],
            "accession": filings["accessionNumber"][i],
            "primary_document": filings["primaryDocument"][i],
            "report_date": filings["reportDate"][i],
        })
        if len(results) >= limit:
            break

    return results


def get_filing_url(cik: str, accession: str, filename: str = None) -> str:
    """
    Build URL for a filing document.

    Args:
        cik: Company CIK or ticker symbol
        accession: Accession number
        filename: Optional specific file, defaults to filing index

    Returns:
        URL string
    """
    cik_raw = _normalize_cik(cik).lstrip("0")
    acc_no_dash = _accession_no_dashes(accession)
    if filename:
        return f"{ARCHIVES_URL}/{cik_raw}/{acc_no_dash}/{filename}"
    return f"{ARCHIVES_URL}/{cik_raw}/{acc_no_dash}/"


def _fetch_xml(url: str) -> str:
    """Fetch XML content (not JSON, so can't use cached_request directly)."""
    cache_key = f"sec-edgar/xml_{url.replace('/', '_').replace(':', '_')}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    req = urllib.request.Request(url, headers={"User-Agent": _get_user_agent()})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
        content = response.read().decode()

    set_cached(cache_key, content)
    return content


def get_filing_sections(cik: str, accession: str) -> list[dict]:
    """
    Get list of sections/reports in a filing from FilingSummary.xml.

    Args:
        cik: Company CIK
        accession: Accession number

    Returns:
        List of section dicts with name and filename
    """
    url = get_filing_url(cik, accession, "FilingSummary.xml")
    xml = _fetch_xml(url)

    sections = []
    for match in re.finditer(r'<Report[^>]*>.*?</Report>', xml, re.DOTALL):
        report = match.group()
        name = re.search(r'<ShortName>(.*?)</ShortName>', report)
        html_file = re.search(r'<HtmlFileName>(.*?)</HtmlFileName>', report)
        if name and html_file:
            sections.append({
                "name": name.group(1),
                "file": html_file.group(1),
            })

    return sections


def _parse_html_table(html: str) -> list[list[str]]:
    """Extract table data from HTML, returning rows of cells."""
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

    rows = []
    for row_match in re.finditer(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL):
        cells = []
        for cell_match in re.finditer(r'<t[dh][^>]*>(.*?)</t[dh]>', row_match.group(1), re.DOTALL):
            text = re.sub(r'<[^>]+>', '', cell_match.group(1))
            text = re.sub(r'\s+', ' ', text).strip()
            text = text.replace('&#160;', '').replace('&nbsp;', '')
            if text:
                cells.append(text)
        if cells:
            rows.append(cells)

    return rows


def _fetch_section_html(cik: str, accession: str, filename: str) -> str:
    """Fetch and cache section HTML."""
    url = get_filing_url(cik, accession, filename)
    cache_key = f"sec-edgar/section_{_normalize_cik(cik)}_{_accession_no_dashes(accession)}_{filename}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    req = urllib.request.Request(url, headers={"User-Agent": _get_user_agent()})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
        content = response.read().decode()

    set_cached(cache_key, content)
    return content


def get_financial_statements(cik: str, accession: str) -> dict:
    """
    Extract financial statements from a 10-K or 10-Q filing.

    Args:
        cik: Company CIK
        accession: Accession number

    Returns:
        dict with income_statement, balance_sheet, cash_flow as parsed tables
    """
    sections = get_filing_sections(cik, accession)

    # Map section names to our keys
    section_map = {
        "CONSOLIDATED STATEMENTS OF OPERATIONS": "income_statement",
        "CONSOLIDATED BALANCE SHEETS": "balance_sheet",
        "CONSOLIDATED STATEMENTS OF CASH FLOWS": "cash_flow",
    }

    results = {}
    for section in sections:
        for pattern, key in section_map.items():
            if pattern in section["name"].upper():
                html = _fetch_section_html(cik, accession, section["file"])
                results[key] = _parse_html_table(html)
                break

    return results


def format_financials(financials: dict) -> str:
    """Format financial statements for display."""
    output = []
    for key, rows in financials.items():
        output.append(f"\n{'='*60}")
        output.append(key.upper().replace('_', ' '))
        output.append('='*60)
        for row in rows[:30]:  # Limit rows for display
            output.append(" | ".join(row))
    return "\n".join(output)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: sec_edgar.py <ticker|cik> [form_type]")
        print("Example: sec_edgar.py AAPL 10-K")
        sys.exit(1)

    cik = sys.argv[1]
    form_type = sys.argv[2] if len(sys.argv) > 2 else "10-K"

    print(f"Fetching latest {form_type} for {cik}...")
    filing = get_latest_filing(cik, form_type)

    if not filing:
        print(f"No {form_type} found")
        sys.exit(1)

    print(f"\nFiling: {filing['form']}")
    print(f"Filed: {filing['filed']}")
    print(f"Report Date: {filing['report_date']}")
    print(f"Accession: {filing['accession']}")

    if form_type in ("10-K", "10-Q"):
        print("\nFetching financial statements...")
        financials = get_financial_statements(cik, filing["accession"])
        print(format_financials(financials))
