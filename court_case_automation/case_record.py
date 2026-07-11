"""Structured case data extracted from an intake complaint.

In production, `extract_case_record` would run the first 1-3 pages of a
filed complaint through a small LLM prompt (caption block + case number are
always on page 1) instead of being hand-filled. The Hirlinger/WP Company
record below is that manual extraction, kept as a concrete fixture so the
rest of the pipeline (docket lookup, alerting, Salesforce sync) has a real
case to run against.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CaseRecord:
    plaintiffs: str
    defendant: str
    attorneys: str

    filing_court: str
    state_case_number: str
    filed_date: str

    # Populated once/if the case is identified on a docket-monitoring source.
    # Consumer class actions against national companies are frequently
    # removed from state court to federal court under CAFA (28 U.S.C. 1453) -
    # that happened here, which is why both are tracked.
    federal_court: Optional[str] = None
    federal_case_number: Optional[str] = None
    federal_filed_date: Optional[str] = None

    salesforce_case_id: Optional[str] = None


HIRLINGER_V_WP_COMPANY = CaseRecord(
    plaintiffs="Joseph Hirlinger and Guy Ball",
    defendant="WP Company LLC (The Washington Post)",
    attorneys="Keller Grover LLP; Law Offices of Scot D. Bernstein; Don Bivens PLLC",
    filing_court="Superior Court of California, County of San Francisco",
    state_case_number="CGC-23-609585",
    filed_date="2023-10-06",
    federal_court="N.D. Cal.",
    federal_case_number="3:23-cv-05963",
    federal_filed_date="2023-11-17",
)
