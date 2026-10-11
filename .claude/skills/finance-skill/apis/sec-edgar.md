# SEC EDGAR API

SEC filings data. No API key required, just a User-Agent header.

**Rate Limit:** 10 requests/second, no daily limit.

## Python Module

Use `scripts/sec_edgar.py` for all SEC EDGAR access:

```python
from sec_edgar import get_latest_filing, get_financial_statements, get_filings

# Get latest 10-K
filing = get_latest_filing("AAPL", "10-K")
# → {"form": "10-K", "filed": "2025-10-31", "accession": "...", ...}

# Get parsed financial statements
financials = get_financial_statements("AAPL", filing["accession"])
# → {"income_statement": [...], "balance_sheet": [...], "cash_flow": [...]}

# List recent filings
filings = get_filings("AAPL", form_type="8-K", limit=10)
```

### CLI Usage

```bash
SEC_EDGAR_USER_AGENT="Name email@example.com" python3 sec_edgar.py AAPL 10-K
```

## Environment Variable

```
SEC_EDGAR_USER_AGENT=YourName your_email@example.com
```

Required for all SEC EDGAR requests.

## Filing Types

| Form | Description | Frequency |
|------|-------------|-----------|
| 10-K | Annual report | Yearly |
| 10-Q | Quarterly report | Quarterly |
| 8-K | Current report (material events) | As needed |
| 4 | Insider transactions | Within 2 days |
| 13-F | Institutional holdings | Quarterly |
| DEF 14A | Proxy statement | Annually |

## 10-K Sections

| Item | Description |
|------|-------------|
| 1 | Business |
| 1A | Risk Factors |
| 7 | MD&A (Management Discussion) |
| 8 | Financial Statements |

### Extracting Narrative Sections (Item 1A, MD&A, etc.)

The `get_financial_statements()` function uses `FilingSummary.xml` which only indexes XBRL financial tables. For narrative sections like Risk Factors or MD&A, fetch the primary HTML document directly:

```python
from sec_edgar import get_latest_filing, get_filing_url
import urllib.request
import re

# Get filing metadata
filing = get_latest_filing("TSLA", "10-K")
# filing["primary_document"] → "tsla-20241231.htm"

# Build URL and fetch
cik_raw = filing["cik"].lstrip("0")
acc_no_dash = filing["accession"].replace("-", "")
url = f"https://www.sec.gov/Archives/edgar/data/{cik_raw}/{acc_no_dash}/{filing['primary_document']}"

req = urllib.request.Request(url, headers={"User-Agent": os.environ["SEC_EDGAR_USER_AGENT"]})
with urllib.request.urlopen(req, timeout=60) as resp:
    html = resp.read().decode()

# Extract Item 1A (Risk Factors) - runs until Item 1B
match = re.search(r'Item\s+1A.*?Risk\s+Factors(.*?)Item\s+1B', html, re.DOTALL | re.I)
if match:
    text = re.sub(r'<[^>]+>', ' ', match.group(1))  # Strip HTML tags
    text = re.sub(r'\s+', ' ', text).strip()
```

**Section patterns:**
- Item 1A → Item 1B (Risk Factors)
- Item 7 → Item 7A (MD&A)
- Item 1 → Item 1A (Business)

## Common CIKs

The module accepts ticker symbols directly:

- AAPL → 0000320193
- MSFT → 0000789019
- GOOGL → 0001652044
- AMZN → 0001018724
- TSLA → 0001318605

## Raw API Reference

Base URL: `https://data.sec.gov`

### Endpoints

**Company Submissions:**
```
https://data.sec.gov/submissions/CIK{10-digit-cik}.json
```

**Company Facts (XBRL):**
```
https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-cik}.json
```

**Filing Documents:**
```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/{filename}
```
