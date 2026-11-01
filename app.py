from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import requests
import socket
import ipaddress
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Session state simulation (In-memory storage for hackathon prototype)
# Maps a simple session token to its collected sources and metadata
SESSION_STORAGE = {}

@app.get("/")
def home():
    return "InfoGap AI backend is running."

def safe_search_fallback(query):
    """
    Performs a real web fallback query using a privacy-respecting endpoint
    to ensure zero hardcoded fake or mock URLs are returned.
    """
    try:
        # Utilizing DuckDuckGo html interface as a real fallback search engine mechanism
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        res = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0 InfoGapAI/1.0"}, timeout=8)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        links = []
        for a in soup.find_all("a", class_="result__url"):
            href = a.get("href", "").strip()
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https") and "duckduckgo.com" not in parsed.hostname:
                links.append(href)
            if len(links) >= 3:
                break
        return links
    except Exception:
        return []

def rule_based_intelligence_engine(sources, question):
    """
    Analyzes aggregate text corpora dynamically to discover linguistic gaps,
    chronological variance, and potential multi-source discrepancies.
    """
    gaps = []
    conflicts = []
    outdated = []
    
    combined_text = " ".join([s["content"] for s in sources]).lower()
    
    # 1. Evaluate explicit missing parameters or uncertainties
    gap_indicators = ["unknown", "unspecified", "tbd", "pending", "undisclosed", "subject to change", "not determined"]
    for indicator in gap_indicators:
        if indicator in combined_text:
            gaps.append(f"Potential information gap detected matching expression profile: '{indicator}'.")
            
    if not gaps:
        gaps.append("No explicit missing markers spotted, but qualitative details around execution remain unverified.")

    # 2. Check for potential contextual contradictions across documents
    conflict_matrices = [
        ("increase", "decrease", "Varying vectors of performance or directional adjustments noted."),
        ("approved", "pending", "Status alignment conflict (Approved vs. Pending) identified."),
        ("mandatory", "optional", "Compliance definition variants (Mandatory vs. Optional) detected."),
        ("free", "paid", "Financial structure discrepancies (Free vs. Premium/Paid) identified.")
    ]
    for w1, w2, desc in conflict_matrices:
        if w1 in combined_text and w2 in combined_text:
            conflicts.append({
                "description": desc,
                "word1": w1,
                "word2": w2
            })

    # 3. Analyze time horizons / structural age
    current_year = datetime.now().year
    extracted_years = [int(y) for y in re.findall(r'\b(20\d{2})\b', combined_text)]
    if extracted_years:
        oldest_horizon = min(extracted_years)
        if oldest_horizon < current_year - 1:
            outdated.append(f"Data references chronological milestones back to {oldest_horizon}. Structural relevance may be diminished.")
    else:
        outdated.append("No definitive calendar years detected in webpage body text.")

    # 4. Formulate evidence-based output parameters
    summary = f"Synthesized analysis over {len(sources)} active source documentation structures. "
    if conflicts or len(gaps) > 1:
        summary += "Noticeable structural divergence or semantic variances exist between verified endpoints. Exercising checklist validation protocols is highly recommended."
    else:
        summary += "The current source documentation presents aligned topical context, though deep regulatory compliance definitions are pending physical proof."

    # Build prioritized verification targets
    next_steps = [
        "Cross-reference source content extracts directly with primary authoritative domains.",
        "Verify if administrative policy modifications occurred after the webpage's visible snapshot date."
    ]
    if conflicts:
        next_steps.append("Manually cross-examine the contrasting terminology detected in independent excerpts.")

    return {
        "summary": summary,
        "gaps": gaps,
        "conflicts": conflicts,
        "outdated": outdated,
        "verification_checklist": next_steps
    }

@app.post("/analyze")
def analyze():
    data = request.json or {}
    question = data.get("question", "").strip()
    urls = [u.strip() for u in data.get("urls", []) if u.strip()]
    
    if not question:
        return jsonify(error="A baseline research question is required."), 400
        
    is_discovered = False
    # If zero manual links are input, trigger safe discovery search flow
    if not urls:
        urls = safe_search_fallback(question)
        is_discovered = True
        if not urls:
            return jsonify(error="No manual URLs provided and real-time fallback search could not identify valid public listings. Please supply explicit links manually."), 400

    processed_sources = []
    
    for index, url in enumerate(urls, start=1):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            continue
            
        try:
            # SSRF Protection: Ensure target hostname resolves to globally routable IPs
            resolved_ips = socket.getaddrinfo(parsed.hostname, None)
            is_safe = True
            for item in resolved_ips:
                ip_addr = ipaddress.ip_address(item[4][0])
                if not ip_addr.is_global:
                    is_safe = False
                    break
            if not is_safe:
                continue

            # Fetch payload safely with strict size constraints and timeouts
            res = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 InfoGapAI/1.0"},
                timeout=10,
                stream=True
            )
            res.raise_for_status()
            
            if "text/html" not in res.headers.get("Content-Type", "").lower():
                continue

            # Limit reading payload to 1MB to prevent memory exhaustion attacks
            html_raw = res.raw.read(1000000)
            soup = BeautifulSoup(html_raw, "html.parser")
            
            for script_tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                script_tag.decompose()
                
            page_title = soup.title.get_text(" ", strip=True) if soup.title else f"Source Reference {index}"
            page_body = soup.get_text(" ", strip=True)[:2500] # Safe substring allocation
            
            # Simple chronological sniffing regex
            date_match = re.search(r'\b(19|20)\d{2}[-/.]\d{2}[-/.]\d{2}\b|\b\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b', soup.get_text(), re.IGNORECASE)
            extracted_date = date_match.group(0) if date_match else "No update marker detected"

            processed_sources.append({
                "id": index,
                "website": url,
                "title": page_title,
                "content": page_body,
                "date": extracted_date
            })
        except Exception:
            continue

    if not processed_sources:
        return jsonify(error="Could not securely process text or extract content from any available target surfaces. Verify your inputs or network connectivity."), 400

    analysis_results = rule_based_intelligence_engine(processed_sources, question)
    
    # Generate unique session identifier to lock chat timeline integrity
    session_id = str(int(datetime.now().timestamp()))
    SESSION_STORAGE[session_id] = {
        "sources": processed_sources,
        "question": question
    }

    return jsonify({
        "status": "success",
        "sessionId": session_id,
        "discovered": is_discovered,
        "sources": processed_sources,
        "analysis": analysis_results
    })

@app.post("/chat")
def chat():
    data = request.json or {}
    session_id = data.get("sessionId", "")
    user_msg = data.get("message", "").strip().lower()
    
    if not session_id or session_id not in SESSION_STORAGE:
        return jsonify(error="Active research session context lost. Please restart your query analysis loop."), 400
        
    if politicians_check := [x for x in ["mock", "test_insult"] if x in user_msg]: # Placeholder sandbox rule protection
        return jsonify(reply="Query blocked due to contextual filters."), 400

    session_data = SESSION_STORAGE[session_id]
    sources = session_data["sources"]
    
    # Locate context match within the extracted source array
    matched_reply = None
    matched_source_id = None
    
    # Simple semantic rule parser looking for keyword matching in the extracted chunks
    words = [w for w in user_msg.split() if len(w) > 3]
    for src in sources:
        text_pool = src["content"].lower()
        matches = [w for w in words if w in text_pool]
        if len(matches) >= 2: # Found matching density context point
            # Extract sentence around the match safely
            sentences = src["content"].split(".")
            for s in sentences:
                if any(m in s.lower() for m in matches):
                    matched_reply = s.strip() + "."
                    matched_source_id = src["id"]
                    break
            if matched_reply:
                break

    if matched_reply:
        full_reply = f"{matched_reply} [Source {matched_source_id}]"
        return jsonify(reply=full_reply)
    else:
        return jsonify(reply="I could not find this information in the reviewed sources.")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
