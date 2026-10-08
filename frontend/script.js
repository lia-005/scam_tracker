/* CivicShield AI - frontend logic (vanilla JS, no build step) */
"use strict";

const $ = (id) => document.getElementById(id);
const state = { docText: "", docName: "", ran: { scam: null, doc: null, trust: null } };

/* ---------- static UI labels (so headings follow the chosen language) ---------- */
const I18N = {
  English: {
    riskScore: "Risk score", why: "Why", redFlags: "Red flags", nextSteps: "What to do next", issuedBy: "Issued by",
    benefits: "Benefits", eligibility: "Eligibility", docsRequired: "Documents required", deadlines: "Deadlines",
    howToApply: "How to apply", fees: "Fees / payments", links: "Official links", claim: "Message claims",
    official: "Official document says", severity: "Severity", supported: "Supported by the document",
    recommended: "Recommended action", scamAnalysis: "Scam analysis", safeRec: "Safe recommendation",
    notStated: "Not stated", noHistory: "No analyses yet.", noTranslate: "Translation needs Gemma (API key). Showing English.",
    level: { High: "High", Medium: "Medium", Low: "Low" },
    verdict: { "Possible Claim Mismatch": "Possible Claim Mismatch", Consistent: "Consistent", "Cannot Verify": "Cannot Verify" },
  },
  Hindi: {
    riskScore: "जोखिम स्कोर", why: "कारण", redFlags: "खतरे के संकेत", nextSteps: "आगे क्या करें", issuedBy: "जारीकर्ता",
    benefits: "लाभ", eligibility: "पात्रता", docsRequired: "ज़रूरी दस्तावेज़", deadlines: "अंतिम तिथियाँ",
    howToApply: "आवेदन कैसे करें", fees: "शुल्क / भुगतान", links: "आधिकारिक लिंक", claim: "संदेश का दावा",
    official: "आधिकारिक दस्तावेज़ क्या कहता है", severity: "गंभीरता", supported: "दस्तावेज़ से पुष्ट",
    recommended: "सुझाई गई कार्रवाई", scamAnalysis: "स्कैम विश्लेषण", safeRec: "सुरक्षित सुझाव",
    notStated: "उल्लेख नहीं", noHistory: "अभी कोई विश्लेषण नहीं।", noTranslate: "अनुवाद के लिए Gemma (API key) चाहिए। अंग्रेज़ी दिखाई जा रही है।",
    level: { High: "उच्च", Medium: "मध्यम", Low: "कम" },
    verdict: { "Possible Claim Mismatch": "संभावित दावा-विसंगति", Consistent: "संगत", "Cannot Verify": "सत्यापित नहीं हो सका" },
  },
  Bengali: {
    riskScore: "ঝুঁকির স্কোর", why: "কারণ", redFlags: "সতর্কতার চিহ্ন", nextSteps: "এরপর কী করবেন", issuedBy: "প্রকাশক",
    benefits: "সুবিধা", eligibility: "যোগ্যতা", docsRequired: "প্রয়োজনীয় নথি", deadlines: "শেষ তারিখ",
    howToApply: "আবেদন করার ধাপ", fees: "ফি / পেমেন্ট", links: "সরকারি লিংক", claim: "বার্তার দাবি",
    official: "সরকারি নথি কী বলছে", severity: "গুরুত্ব", supported: "নথি দ্বারা সমর্থিত",
    recommended: "প্রস্তাবিত পদক্ষেপ", scamAnalysis: "স্ক্যাম বিশ্লেষণ", safeRec: "নিরাপদ পরামর্শ",
    notStated: "উল্লেখ নেই", noHistory: "এখনও কোনো বিশ্লেষণ নেই।", noTranslate: "অনুবাদের জন্য Gemma (API key) দরকার। ইংরেজি দেখানো হচ্ছে।",
    level: { High: "উচ্চ", Medium: "মাঝারি", Low: "নিম্ন" },
    verdict: { "Possible Claim Mismatch": "সম্ভাব্য দাবির অমিল", Consistent: "সামঞ্জস্যপূর্ণ", "Cannot Verify": "যাচাই করা যায়নি" },
  },
};
const L = () => I18N[$("language").value] || I18N.English;

/* ---------- examples ---------- */
const EX_SCAM = "Pay Rs 500 to activate your scholarship immediately at http://scholarship-india.xyz/pay or it will expire today.";
const EX_DOC = `NATIONAL MERIT SCHOLARSHIP SCHEME 2026-27
Ministry of Education, Government of India (SAMPLE NOTICE FOR DEMO ONLY)

Benefits
- Rs. 12,000 per year, credited directly to the student's bank account

Eligibility
- Indian citizen studying in a recognised college
- Family income below Rs. 4,50,000 per year

Documents Required
- Aadhaar card
- Income certificate
- Class 12 marksheet

How to Apply
1. Register on the official portal https://scholarships.gov.in
2. Fill in the application form and upload documents
3. Submit and note down the application ID

Important Dates
- Last date to apply: 30 November 2026

Fees
No fee is charged at any stage of application, verification or disbursement. Applications are free of cost.`;

/* ---------- helpers ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const list = (items, tag = "ul", cls = "") =>
  items && items.length ? `<${tag} class="${cls}">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</${tag}>` : `<p class="muted">${esc(L().notStated)}</p>`;
const levelColor = { High: "#c62828", Medium: "#e08a00", Low: "#2e9d57" };

async function api(path, options = {}) {
  const res = await fetch(path, options);
  let data = {};
  try { data = await res.json(); } catch { /* non-JSON error */ }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
const postJSON = (path, payload) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

async function run(button, target, fn) {
  button.disabled = true; $("loader").hidden = false;
  try { target.innerHTML = await fn(); }
  catch (e) { target.innerHTML = `<div class="err">⚠️ ${esc(e.message)}</div>`; }
  finally { button.disabled = false; $("loader").hidden = true; }
}
const translatedNote = (r) => (r && r._translated === false ? `<p class="hint">${esc(L().noTranslate)}</p>` : "");

/* ---------- renderers ---------- */
function renderScam(r) {
  const lv = r.risk_level, color = levelColor[lv] || "#666";
  return `${translatedNote(r)}
  <div class="card">
    <div class="result-head">
      <div class="gauge" style="background:conic-gradient(${color} ${r.risk_score * 3.6}deg,#e6ebf3 0deg)">
        <div class="gauge-inner"><b>${esc(r.risk_score)}</b><span>/ 100</span></div>
      </div>
      <div>
        <span class="badge ${esc(lv)}">${esc(L().level[lv] || lv)}</span>
        <h3 style="margin-top:8px">${esc(r.scam_type)}</h3>
        <p style="margin:0">${esc(r.explanation)}</p>
      </div>
    </div>
  </div>
  <div class="grid2">
    <div class="card"><h3>🚩 ${esc(L().redFlags)}</h3>${list(r.red_flags, "ul", "flags")}</div>
    <div class="card"><h3>💡 ${esc(L().nextSteps)}</h3>${list(r.safe_actions, "ul", "actions")}</div>
  </div>`;
}

function renderDoc(r) {
  const t = L();
  return `${translatedNote(r)}
  <div class="card">
    <h3>${esc(r.title || "Document")}</h3>
    <p class="muted">${esc(t.issuedBy)}: ${esc(r.issuing_authority || t.notStated)}</p>
    <p>${esc(r.summary)}</p>
  </div>
  <div class="grid2">
    <div class="card">
      <h3>🎁 ${esc(t.benefits)}</h3>${list(r.benefits)}
      <h3>✔️ ${esc(t.eligibility)}</h3>${list(r.eligibility)}
      <h3>📄 ${esc(t.docsRequired)}</h3>${list(r.required_documents)}
    </div>
    <div class="card">
      <h3>📅 ${esc(t.deadlines)}</h3>${list(r.deadlines)}
      <h3>🪜 ${esc(t.howToApply)}</h3>${list(r.application_steps, "ol")}
      <h3>💰 ${esc(t.fees)}</h3><p>${esc(r.fees_or_payments || t.notStated)}</p>
      ${r.official_links && r.official_links.length ? `<h3>🔗 ${esc(t.links)}</h3>${list(r.official_links)}` : ""}
    </div>
  </div>`;
}

function renderTrust(out) {
  const t = L(), tb = out.trustbridge, sc = out.scam, rec = out.recommendation;
  const mismatch = tb.verdict === "Possible Claim Mismatch";
  const cls = mismatch || sc.risk_level === "High" ? "danger" : sc.risk_level === "Medium" ? "warn" : "ok";
  const rows = (tb.mismatches || []).map((m) =>
    `<tr><td>${esc(m.claim)}</td><td>${esc(m.official_says)}</td><td><span class="badge ${esc(m.severity)}">${esc(m.severity)}</span></td></tr>`).join("");
  return `${translatedNote(out)}
  <div class="banner ${cls}">${esc(rec.headline)}</div>
  <div class="card">
    <h3>🔐 TrustBridge: <span class="badge ${mismatch ? "High" : tb.verdict === "Consistent" ? "Low" : "Medium"}">${esc(t.verdict[tb.verdict] || tb.verdict)}</span></h3>
    <p>${esc(tb.explanation)}</p>
    ${rows ? `<table><thead><tr><th>${esc(t.claim)}</th><th>${esc(t.official)}</th><th>${esc(t.severity)}</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
    ${tb.confirmed_claims && tb.confirmed_claims.length ? `<h3>✅ ${esc(t.supported)}</h3>${list(tb.confirmed_claims)}` : ""}
    <div class="note"><strong>${esc(t.recommended)}:</strong> ${esc(tb.recommendation)}</div>
  </div>
  <h3 style="margin:18px 0 8px">🛡️ ${esc(t.scamAnalysis)}</h3>
  ${renderScam(sc).replace(translatedNote(sc), "")}
  <div class="card"><h3>✅ ${esc(t.safeRec)}</h3>${list(rec.steps, "ul", "actions")}<p class="muted">${esc(rec.report_to)}</p></div>`;
}

/* ---------- actions ---------- */
function doScam() {
  const message = $("scamInput").value.trim();
  if (!message) return ($("scamResult").innerHTML = `<div class="err">Please paste a message first.</div>`);
  const lang = $("language").value;
  state.ran.scam = doScam;
  return run($("scamBtn"), $("scamResult"), async () => renderScam(await postJSON("/api/analyze-message", { message, language: lang })));
}

async function extractFrom(file) {
  const fd = new FormData(); fd.append("file", file);
  return api("/api/extract-text", { method: "POST", body: fd });
}

function doDoc() {
  const file = $("docFile").files[0], lang = $("language").value;
  if (!file && !state.docText) return ($("docResult").innerHTML = `<div class="err">Please choose a file first.</div>`);
  state.ran.doc = doDoc;
  return run($("docBtn"), $("docResult"), async () => {
    if (file && file.name !== state.docName) {
      const ex = await extractFrom(file);
      state.docText = ex.text; state.docName = ex.filename; updateLoadedHint();
    }
    return renderDoc(await postJSON("/api/explain-document", { text: state.docText, language: lang }));
  });
}

function doTrust() {
  const message = $("tbMessage").value.trim(), lang = $("language").value;
  const src = document.querySelector("input[name=tbSrc]:checked").value;
  state.ran.trust = doTrust;
  return run($("tbBtn"), $("tbResult"), async () => {
    let docText = "";
    if (src === "loaded") docText = state.docText;
    else if (src === "paste") docText = $("tbPaste").value;
    else if ($("tbFile").files[0]) docText = (await extractFrom($("tbFile").files[0])).text;
    if (!message || !docText.trim()) throw new Error("Please provide both a message and an official document.");
    return renderTrust(await postJSON("/api/trustbridge", { message, doc_text: docText, language: lang }));
  });
}

async function loadHistory() {
  const rows = await api("/api/history");
  $("historyList").innerHTML = rows.length
    ? `<table><thead><tr><th>Time</th><th>Type</th><th>Input</th><th>Risk</th><th>Verdict</th></tr></thead><tbody>${rows.map((r) =>
        `<tr><td>${esc(r.time)}</td><td>${esc(r.type)}</td><td>${esc(r.input)}</td><td>${esc(r.risk ?? "-")}</td><td>${esc(r.verdict ?? "-")}</td></tr>`).join("")}</tbody></table>`
    : `<p class="muted">${esc(L().noHistory)}</p>`;
}

function updateLoadedHint() {
  $("tbLoaded").textContent = state.docText ? `Using: ${state.docName}` : "No document loaded yet. Upload one in the Document Explainer tab.";
}

/* ---------- wiring ---------- */
function showTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  if (name === "history") loadHistory().catch(() => {});
  if (name === "trust") updateLoadedHint();
}

document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
$("scamBtn").addEventListener("click", doScam);
$("docBtn").addEventListener("click", doDoc);
$("tbBtn").addEventListener("click", doTrust);
$("clearHistory").addEventListener("click", async () => { await api("/api/history", { method: "DELETE" }); loadHistory(); });

document.querySelectorAll("input[name=tbSrc]").forEach((r) => r.addEventListener("change", () => {
  const v = document.querySelector("input[name=tbSrc]:checked").value;
  $("tbLoaded").hidden = v !== "loaded"; $("tbFile").hidden = v !== "upload"; $("tbPaste").hidden = v !== "paste";
}));

document.querySelectorAll("[data-example]").forEach((b) => b.addEventListener("click", () => {
  if (b.dataset.example === "scam") $("scamInput").value = EX_SCAM;
  else {
    $("tbMessage").value = EX_SCAM;
    document.querySelector("input[name=tbSrc][value=paste]").checked = true;
    $("tbPaste").value = EX_DOC; $("tbLoaded").hidden = true; $("tbFile").hidden = true; $("tbPaste").hidden = false;
  }
}));

// Re-run the active tab's last analysis when the language changes
$("language").addEventListener("change", () => {
  const active = document.querySelector(".tab.active").dataset.tab;
  const fn = state.ran[active];
  if (fn) fn();
  if (active === "history") loadHistory();
});

(async function init() {
  try {
    const s = await api("/api/status");
    $("statusBar").textContent = `Engine: ${s.engine}`;
    if (!s.ai_enabled) {
      $("statusBar").classList.add("warn");
      $("statusBar").textContent += " — rules-only mode. Add GOOGLE_API_KEY in .env for full AI analysis and translation.";
    }
    $("helpline").textContent = s.helpline; $("portal").textContent = s.portal;
  } catch { $("statusBar").textContent = "Cannot reach the backend. Start it with: python app.py"; $("statusBar").classList.add("warn"); }
  updateLoadedHint();
})();
