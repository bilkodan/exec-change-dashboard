import re
import time
import html
import hashlib
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

from Db import init_db, insert_change

SEC_HEADERS = {
    "User-Agent": "ExecChangeDashboard monitor@execchanges.io",
    "Accept-Encoding": "gzip, deflate",
}

# ── Name-origin classifiers ───────────────────────────────────────────────────

INDIAN_SURNAMES = {
    "patel", "shah", "gupta", "sharma", "singh", "kumar", "mehta", "joshi",
    "nair", "iyer", "rao", "reddy", "naidu", "pillai", "menon", "krishnan",
    "bose", "ghosh", "chatterjee", "banerjee", "mukherjee", "agarwal",
    "malhotra", "kapoor", "chopra", "verma", "mishra", "shukla", "pandey",
    "tiwari", "srivastava", "khanna", "arora", "bhatia", "sethi", "mahajan",
    "bajaj", "mittal", "goel", "jain", "saxena", "trivedi", "pathak",
    "narayanan", "subramanian", "venkataraman", "krishnamurthy", "balakrishnan",
    "chandrasekaran", "natarajan", "ramachandran", "srinivasan", "venkatesh",
    "subramaniam", "bhattacharya", "chakraborty", "dasgupta", "mitra",
    "dey", "roy", "sen", "biswas", "das", "basu", "lahiri", "sarkar",
    "chaudhary", "desai", "gandhi", "sheth", "parikh", "parekh", "bhatt",
    "vyas", "dave", "raval", "modi", "solanki", "chauhan", "prajapati",
    "murthy", "gowda", "hegde", "shetty", "kamath", "bhat", "pai",
    "varma", "nambiar", "panicker", "unnithan", "kannan", "raman",
    "pichai", "nadella", "goyal", "taneja", "khosla", "banga", "anand",
    "agrawal", "mistry", "premji", "nilekani", "venkatesan", "sethuraman",
    "rajan", "sundaram", "parthasarathy", "rajagopalan", "krishnaswamy",
}

INDIAN_FIRST_NAMES = {
    "aarav", "aditya", "ajay", "amit", "amitabh", "anand", "aniket", "anil",
    "anish", "ankur", "anuj", "anup", "arjun", "arpit", "arun", "arvind",
    "ashish", "ashok", "ashwin", "atul", "bharat", "chetan", "deepak",
    "devesh", "dilip", "dinesh", "gaurav", "girish", "gopal", "harish",
    "hemant", "indra", "jagdish", "jayesh", "jigar", "jitendra", "kamal",
    "kapil", "karan", "kartik", "kiran", "krishna", "lalit", "madhur",
    "mahesh", "manoj", "manish", "milind", "mukesh", "naresh", "naveen",
    "nikhil", "nilesh", "nitin", "paresh", "parth", "pawan", "piyush",
    "pradeep", "prakash", "pranav", "prasad", "prashant", "praveen",
    "puneet", "rahul", "raj", "rajeev", "rajesh", "rakesh", "ram", "ramesh",
    "ravi", "ritesh", "rohit", "sachin", "sandeep", "sanjay", "sanjeev",
    "saurabh", "shailesh", "shekhar", "shivam", "shyam", "siddharth",
    "subhash", "suhas", "sunil", "suresh", "sushil", "tarun", "umesh",
    "uday", "varun", "vikas", "vikram", "vinay", "vineet", "vinod",
    "vishal", "vivek", "yogesh", "satya", "sundar", "venkat", "murali",
    "mani", "karthik", "krish", "priya", "divya", "deepa", "kavita",
    "lakshmi", "meena", "nisha", "pooja", "radha", "rekha", "seema",
    "sunita", "usha", "jyoti", "smita", "sneha", "swati", "anita",
}

US_FIRST_NAMES = {
    "aaron", "adam", "alan", "alex", "alexander", "alfred", "allen",
    "andrew", "andy", "anthony", "arthur", "austin", "barry", "benjamin",
    "bill", "billy", "bob", "bobby", "brad", "bradley", "brandon", "brian",
    "bruce", "bryan", "carl", "charles", "charlie", "chris", "christian",
    "christopher", "chuck", "clarence", "clark", "clay", "clifford", "clint",
    "clinton", "cody", "cole", "colin", "corey", "cory", "craig", "curtis",
    "dale", "dan", "daniel", "danny", "darrell", "david", "dean", "dennis",
    "derek", "donald", "doug", "douglas", "drew", "duane", "dustin", "dylan",
    "ed", "edward", "eric", "ethan", "evan", "floyd", "frank", "fred",
    "gary", "gene", "george", "gerald", "glen", "greg", "gregory", "harold",
    "harry", "henry", "howard", "hunter", "jack", "jacob", "james", "jason",
    "jeff", "jeffrey", "jeremy", "jerry", "jesse", "jim", "jimmy", "joe",
    "joel", "john", "johnny", "jon", "jonathan", "joseph", "josh", "joshua",
    "justin", "karl", "keith", "ken", "kenneth", "kevin", "kyle", "lance",
    "larry", "lee", "leon", "lewis", "logan", "louis", "luke", "mark",
    "martin", "marvin", "matt", "matthew", "michael", "mike", "mitchell",
    "nathan", "nicholas", "nick", "noah", "paul", "peter", "philip",
    "phillip", "randy", "raymond", "richard", "rick", "rob", "robert",
    "roger", "ron", "ronald", "ross", "ryan", "sam", "samuel", "scott",
    "sean", "seth", "shawn", "stanley", "stephen", "steve", "steven",
    "thomas", "timothy", "todd", "tom", "tony", "travis", "troy", "tyler",
    "victor", "vincent", "walter", "wayne", "william", "zachary",
    "amy", "barbara", "betty", "carol", "catherine", "cheryl", "christine",
    "cynthia", "deborah", "diana", "donna", "dorothy", "elizabeth", "emily",
    "frances", "helen", "jennifer", "jessica", "joyce", "judith", "karen",
    "kathleen", "kelly", "laura", "linda", "lisa", "margaret", "mary",
    "melissa", "nancy", "patricia", "ruth", "sandra", "sarah", "sharon",
    "shirley", "stephanie", "susan", "virginia",
}

ANGLO_SURNAME_SUFFIXES = ("son", "man", "berg", "stein", "ton", "ford", "wood", "field", "worth")


def _parts(name: str):
    parts = name.strip().lower().split()
    return (parts[0] if parts else ""), (parts[-1] if len(parts) > 1 else "")


def classify_indian(name: str) -> float:
    first, last = _parts(name)
    score = 0.7 if last in INDIAN_SURNAMES else 0.0
    if first in INDIAN_FIRST_NAMES:
        score += 0.3
    return min(score, 1.0)


def classify_us(name: str) -> float:
    first, last = _parts(name)
    if last in INDIAN_SURNAMES:
        return 0.0
    score = 0.5 if first in US_FIRST_NAMES else 0.0
    score += 0.3 if len(last) > 2 else 0.0
    if any(last.endswith(s) for s in ANGLO_SURNAME_SUFFIXES):
        score += 0.2
    return min(score, 1.0)


def compute_signal(outgoing_us: float, incoming_indian: float) -> dict:
    score = round(outgoing_us * incoming_indian, 3)
    if score >= 0.5:
        return {"signal_score": score, "trade_signal": "WATCH", "position_size": round(score * 10_000)}
    if score >= 0.2:
        return {"signal_score": score, "trade_signal": "MONITOR", "position_size": 0}
    return {"signal_score": score, "trade_signal": "NONE", "position_size": 0}


# ── SEC EDGAR fetching ────────────────────────────────────────────────────────

EDGAR_RSS = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=8-K&dateb=&owner=include&count=40"
    "&search_text=&output=atom"
)

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"


def _get(url: str, **kwargs) -> requests.Response:
    time.sleep(0.15)  # stay well under SEC's 10 req/s limit
    return requests.get(url, headers=SEC_HEADERS, timeout=30, **kwargs)


def fetch_efts_filings(since_date: str) -> list[dict]:
    """Search EDGAR full-text for 8-K filings mentioning Item 5.02 and CEO."""
    params = {
        "q": '"Item 5.02" "Chief Executive Officer"',
        "forms": "8-K",
        "dateRange": "custom",
        "startdt": since_date,
    }
    resp = _get(EFTS_URL, params=params)
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        src = hit.get("_source", {})
        accession = src.get("accession_no", "")
        if not accession:
            continue
        results.append({
            "accession_no": accession,
            "company": src.get("entity_name", "Unknown"),
            "filed_at": src.get("file_date", ""),
        })
    return results


def accession_to_urls(accession_no: str):
    """Return (cik, index_url) derived from an accession number."""
    # accession format: 0001234567-24-000001
    parts = accession_no.split("-")
    if len(parts) != 3:
        return None, None
    cik = str(int(parts[0]))  # strip leading zeros
    path = accession_no.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{path}/"
    return cik, index_url


def get_primary_doc_url(index_url: str) -> str | None:
    """Parse EDGAR filing index page to find the primary 8-K document URL."""
    resp = _get(index_url)
    if not resp.ok:
        return None
    # Each document row has href="/Archives/edgar/data/.../filename.htm"
    candidates = re.findall(
        r'href="(/Archives/edgar/data/[^"]+\.(?:htm|txt))"',
        resp.text, re.IGNORECASE,
    )
    for c in candidates:
        low = c.lower()
        if re.search(r"ex[-_]?\d|exhibit", low):
            continue
        return "https://www.sec.gov" + c
    return ("https://www.sec.gov" + candidates[0]) if candidates else None


def strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


# ── CEO name extraction ───────────────────────────────────────────────────────

_CEO = (
    r"(?:Chief\s+Executive\s+Officer"
    r"|President\s+(?:and\s+)?(?:Chief\s+Executive\s+Officer|CEO)"
    r"|\bCEO\b)"
)

_NAME = r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})"

_APPOINT = [
    re.compile(
        r"(?:appointed|named|elected|designated)\s+" + _NAME +
        r"\s+(?:as|to(?:\s+serve\s+as)?|to\s+the\s+position\s+of)\s+" + _CEO,
        re.IGNORECASE,
    ),
    re.compile(
        _NAME + r"\s+(?:has\s+been|was|will\s+be)\s+(?:appointed|named|elected)\s+(?:as\s+)?" + _CEO,
        re.IGNORECASE,
    ),
    re.compile(
        _NAME + r"\s+(?:will\s+(?:join\s+as|become|serve\s+as)|becomes?|assumes?)\s+(?:the\s+role\s+of\s+|)?" + _CEO,
        re.IGNORECASE,
    ),
]

_DEPART = [
    re.compile(
        _NAME + r"\s+(?:has\s+)?(?:resigned?|retires?|steps?\s+down|is\s+departing|departed?)[^.]{0,60}" + _CEO,
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:resignation|retirement|departure|stepping\s+down)\s+of\s+" + _NAME + r"[^.]{0,60}" + _CEO,
        re.IGNORECASE,
    ),
    re.compile(
        _NAME + r"[^.]{0,40}" + _CEO + r"[^.]{0,40}(?:resigned?|retires?|steps?\s+down|departed?)",
        re.IGNORECASE,
    ),
]


def extract_ceo_names(text: str):
    incoming = outgoing = None
    for pat in _APPOINT:
        m = pat.search(text)
        if m:
            incoming = m.group(1).strip()
            break
    for pat in _DEPART:
        m = pat.search(text)
        if m:
            outgoing = m.group(1).strip()
            break
    return incoming, outgoing


def extract_ticker(text: str) -> str:
    m = re.search(r"\((?:NYSE|NASDAQ|AMEX|OTC):\s*([A-Z]{1,5})\)", text)
    if m:
        return m.group(1)
    m = re.search(r"ticker\s+symbol[:\s]+([A-Z]{1,5})", text, re.IGNORECASE)
    return m.group(1) if m else ""


# ── Worker loop ───────────────────────────────────────────────────────────────

_seen: set[str] = set()


def process_once(since_date: str):
    try:
        filings = fetch_efts_filings(since_date)
    except Exception as exc:
        print(f"[EFTS] {exc}")
        return

    for f in filings:
        acc = f["accession_no"]
        if acc in _seen:
            continue
        _seen.add(acc)

        try:
            cik, index_url = accession_to_urls(acc)
            if not index_url:
                continue

            doc_url = get_primary_doc_url(index_url)
            if not doc_url:
                continue

            raw = _get(doc_url)
            if not raw.ok:
                continue
            text = strip_html(raw.text)

            incoming, outgoing = extract_ceo_names(text)
            if not incoming:
                continue

            outgoing_us = classify_us(outgoing) if outgoing else 0.0
            incoming_indian = classify_indian(incoming)
            sig = compute_signal(outgoing_us, incoming_indian)

            row = {
                "id": hashlib.md5(acc.encode()).hexdigest()[:16],
                "company": f["company"],
                "ticker": extract_ticker(text),
                "role": "CEO",
                "outgoing": outgoing or "—",
                "incoming": incoming,
                "filed_at": f["filed_at"],
                "outgoing_us": outgoing_us,
                "incoming_indian": incoming_indian,
                "incoming_asian": incoming_indian,
                "price": 0.0,
                "price_change_1d": 0.0,
                **sig,
            }
            insert_change(row)

            alert = "  *** US → INDIAN CEO ***" if sig["trade_signal"] == "WATCH" else ""
            print(
                f"[+] {f['company']} | OUT={outgoing or '?'} | IN={incoming}"
                f" | us={outgoing_us:.2f} ind={incoming_indian:.2f}{alert}"
            )

        except Exception as exc:
            print(f"[-] {acc}: {exc}")


def run_worker():
    print("[Worker] Exec Change Monitor starting…")
    init_db()
    # On first run look back 7 days to seed the database
    lookback_days = 7
    while True:
        since = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        print(f"\n[{datetime.utcnow():%Y-%m-%d %H:%M:%S}] Polling SEC EDGAR (since {since})…")
        process_once(since)
        lookback_days = 1  # subsequent runs only look back 1 day
        time.sleep(300)    # poll every 5 minutes


if __name__ == "__main__":
    run_worker()
