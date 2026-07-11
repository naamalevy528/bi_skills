# Handover: Court Case Docket Monitoring

## Mission
Automate this pipeline: a partner law firm files a case → we track docket activity on that case over time → when something changes, someone finds out → (for now) the update, a source link, and a summary of any new documents get posted to Slack.

Hard constraint: **never automate logging into Lexis/Nexis CourtLink.** It's a shared account real attorneys depend on, and Lexis/Nexis's terms generally prohibit scripted/automated access to their web interface. An RPA/browser bot risks account suspension for everyone, not just the automation. Everything in this project is built around that constraint — CourtListener (see below) was chosen specifically because it's a free, API-first alternative with no such restriction, at least for federal cases.

Salesforce is currently **out of scope** — an earlier version of this work built a Salesforce push client speculatively; the user has since said explicitly not to push anything there. Slack is the current target output, for testing.

## What's built (`court_case_automation/`)
- **`case_record.py`** — a `CaseRecord` dataclass plus one fixture, `HIRLINGER_V_WP_COMPANY`. Tracks both the state-court filing (`CGC-23-609585`, SF Superior Court) and the federal case it was removed to under CAFA (`3:23-cv-05963`, N.D. Cal.) — consumer class actions against national companies are commonly removed to federal court this way, so both numbers matter.
- **`courtlistener_client.py`** — a REST client for [CourtListener/RECAP](https://www.courtlistener.com/help/api/rest/) (the Free Law Project's free federal docket database): `search_docket`, `list_docket_entries`, `create_docket_alert`. **This has never been executed against the live API** — see "Where it's stuck" below.
- **`salesforce_client.py`** — a Salesforce REST client (`update_case_fields`, `attach_file`). Built before the Salesforce constraint above was stated. Currently unused and out of scope; the next person should decide whether to delete it or leave it clearly marked as not-in-use.

Not yet built: anything that wires these together (a "check this case, tell me what's new" script), a way to download and summarize an actual document, and anything Slack-related.

## The requested test, and what happened
The ask: prove the system can find a real case, return a source link, and describe the documents in it (dates, titles, ideally a summary).

What I could actually do, in this sandbox:
- Found the case via a general web-search tool (not via `courtlistener_client.py` — that code was never run).
  - Justia docket: https://dockets.justia.com/docket/california/candce/3:2023cv05963/421040
  - PacerMonitor: https://www.pacermonitor.com/public/case/51412299/Hirlinger_et_al_v_WP_Company_LLC
- Found one document this way: **Document 22**, an order dated **June 10, 2024**, signed by Judge Araceli Martinez-Olguin, **granting a Motion to Dismiss with leave to amend**, and vacating a hearing that had been set for June 27, 2024. (https://law.justia.com/cases/federal/district-courts/california/candce/3:2023cv05963/421040/22/)

That's a real result, but it came from AI-summarized search snippets, not from actually calling the CourtListener API or reading a real document — so it doesn't prove the pipeline works, just that the case and at least one document genuinely exist and are publicly findable.

## Where it's stuck
1. **No outbound network access to arbitrary sites from this dev sandbox.** Direct HTTP requests (via Python `requests`, and via the WebFetch tool) return 403 through this environment's proxy — confirmed this isn't CourtListener-specific by testing against `example.com`, which also 403'd. Only a web-search tool worked, and it returns summarized snippets, not raw API/HTML responses.
   - Practical effect: `courtlistener_client.py` has **never been run against the real API** in this environment. It's untested code.
   - Next person needs an environment with normal outbound internet access (a regular dev machine or CI runner) to actually exercise it.
2. **No API credentials configured anywhere.** No `COURTLISTENER_API_TOKEN` in the environment. Public search/read is supposed to work without one; `create_docket_alert` needs one (free CourtListener account).
3. **Unknown whether this specific case has good RECAP coverage.** CourtListener/RECAP only has documents that someone has actually pulled from PACER and uploaded — coverage is crowd-sourced, not universal. It's possible `search_docket("3:23-cv-05963", "cand")` returns the docket shell but few or no actual documents. This needs to be checked live before assuming the pipeline will have much to report on for this case.
4. **No document-download or summarization code exists yet.** `courtlistener_client.py` can list docket entries but has no method to fetch a document's actual text/PDF. Needs something like `get_recap_document(document_id)` / `download_document(...)`, then a real summarization step (e.g., feed extracted text to an LLM prompt) — today's "summary" was a web-search shortcut, not a built pipeline step.
5. **Slack destination undecided** — which channel, and whether posting is automatic or on-demand, hasn't been agreed with the user yet.
6. **No orchestrator wiring `case_record.py` + `courtlistener_client.py` together exists.** A design for one (`monitor.py`) was proposed once but not approved to build — see the architecture appendix below for that design if it's still useful as a starting point.

## Suggested next steps
1. Move to an environment with real network access; get a free CourtListener API token.
2. Actually call `search_docket` / `list_docket_entries` for the Hirlinger federal case and see what RECAP really has — don't assume.
3. Add document download + a real summarization step to `courtlistener_client.py`.
4. Build the missing orchestrator script and a Slack-sending step (confirm channel with the user first — posting to a real channel is a visible action).
5. Decide the fate of `salesforce_client.py` (delete vs. keep-but-unused).
6. Re-verify the "no CourtLink automation" constraint stays respected in whatever gets built next.

## Repo state
- Branch: `claude/court-case-automation-95rvdg` (pushed)
- Files: `case_record.py`, `courtlistener_client.py`, `salesforce_client.py`, this file

## Appendix: original architecture recommendation
The plan below was the original recommendation for the full pipeline (intake → docket alerts → notification → get update/attachment → CRM sync), written before scope narrowed to "docket monitoring + Slack, no CourtLink, no Salesforce for now." Kept here for context on the reasoning, since it lived only in a local planning file that doesn't persist with the repo.

> ### Recommended architecture (original, includes Salesforce — since narrowed)
> **1. Intake:** partner reports case → Salesforce (Web-to-Case or a form tool), via Make.com/n8n. No CourtLink involved.
>
> **2. Docket alert setup:** ask the Lexis/CourtLink rep about API/webhook access first (some enterprise tiers have it). Otherwise, evaluate API-first vendors: **CourtListener/RECAP** (free, federal only — what this repo currently uses), **Docket Alarm** (federal + state, paid), **UniCourt** (state-court strength), **PacerMonitor** (federal, has an API/webhook option).
>
> **3. Update notification:** Gmail API/n8n trigger or a vendor webhook — safe either way, since it's reading your own inbox or receiving a webhook, not touching another party's session.
>
> **4. Get the update + attachment:** fully automatic for API-first vendor cases. For CourtLink-only cases: don't build a bot — make it a ~60-second human checkpoint (notify a person, they log in normally and drop the file in a watched folder/inbox).
>
> **5. Attachment upload + CRM update:** Make.com/n8n watches the drop folder/inbox, uploads the file, updates the case record via API.
>
> This repo currently implements a slice of steps 2-4 (CourtListener lookup) plus a not-currently-used Salesforce client for step 5 — Slack has since replaced Salesforce as the target output for the current testing phase.
