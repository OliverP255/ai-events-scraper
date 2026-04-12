#!/usr/bin/env python3
"""Offline eval: classify mock events via local LLM (no database)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402

from ai_events.enterprise_llm import BATCH_SIZE, _classify_batch  # noqa: E402
from ai_events.models import RawEvent  # noqa: E402

MOCKS: list[tuple[str, str, str]] = [
    ("e01", "CIO roundtable: GenAI governance for regulated firms", "Invitation-only dinner in London for CIOs and chief risk officers on EU AI Act compliance and model risk."),
    ("e02", "Enterprise LLM deployment summit", "Two-day B2B conference for IT leaders on production LLMs, evaluation, and vendor selection."),
    ("e03", "Executive breakfast: AI transformation roadmap", "Fortune 500 strategy officers and MDs; case studies on org design around copilots."),
    ("e04", "Law firm partners briefing: RAG for matter search", "AmLaw 200 knowledge management leaders; enterprise search and privilege-aware retrieval."),
    ("e05", "MLOps at scale — director track", "Hands-off business tracks for engineering directors and heads of data on reliable model deployment."),
    ("e06", "NED board briefing: understanding AI strategy", "Non-executive directors; no code, governance and oversight of enterprise AI investments."),
    ("e07", "PE operating partners dinner: AI in portfolio value creation", "Private equity professionals; operational AI in portco GTM and back office."),
    ("e08", "CHRO forum: workforce planning with predictive analytics", "Senior HR leaders at large employers; AI-supported talent analytics."),
    ("e09", "CISO briefing: securing enterprise GenAI", "Security leaders on data leakage, policy, and tooling for sanctioned LLM use."),
    ("e10", "Retail leadership day: demand forecasting and CV", "VP+ retail operators; applied ML in supply chain and stores."),
    ("e11", "Insurance CIO council: claims automation", "UK insurers; NLP and automation in regulated claims workflows."),
    ("e12", "Pharma R&D leadership: AI in clinical development", "Enterprise pharma; translational AI for trial design and safety."),
    ("e13", "Banking transformation: LLMs in regulated service", "Retail banking VPs+ on compliant assistant rollouts and human oversight."),
    ("e14", "Manufacturing 4.0 for plant and ops directors", "Industrial firms; predictive maintenance and computer vision on the line."),
    ("e15", "AI art night for beginners — Midjourney fun", "Social evening for hobbyists; no business audience."),
    ("e16", "PhD seminar: new transformer architectures", "University CS department; researchers and grad students."),
    ("e17", "48-hour student hackathon — build anything", "Undergrads and developers; prizes for best app."),
    ("e18", "Prompt to profit: side income with ChatGPT", "No prior experience; earn from home using AI tools."),
    ("e19", "Kids coding camp: Python 101", "Ages 8–12; school holiday programme."),
    ("e20", "Creator stream: viral TikToks with AI voices", "Consumer creators; monetization tips."),
    ("e21", "Call for papers — NeurIPS workshop", "Academic submissions; peer review."),
    ("e22", "K8s networking deep dive meetup", "SREs and platform engineers; CNI and service mesh, no AI content."),
    ("e23", "Consumer dating app founders social", "B2C founders mixer; growth hacks."),
    ("e24", "Wellness retreat with optional ‘AI journaling’", "Weekend retreat; yoga primary audience."),
    ("e25", "Free webinar: faceless YouTube automation", "Beginners building income channels with AI clips."),
    ("e26", "University STEM careers fair", "Students meeting employers; general tech stalls."),
    ("e27", "Open source night: contributing to Rust crates", "Developers only; FOSS."),
    ("e28", "Pop-up: AI tarot readings", "Novelty stall at market weekend."),
    ("e29", "VC pitch day: AI startup demos", "Founders pitching; investors; early-stage B2B and B2C mix."),
    ("e30", "Digital transformation networking — broad IT", "General IT managers; one optional AI breakout, mostly cloud and ERP."),
    ("e31", "London Tech Week expo pass", "Mass-market expo ticket; consumer and business mixed."),
    ("e32", "All-hands: enterprise assistant launch (employees)", "Internal only for Acme Corp staff on new sanctioned copilot."),
]

# Expected labels for offline accuracy (human rubric aligned with enterprise_llm system prompt).
_GOLD: dict[str, int] = {
    **{f"e{i:02d}": 1 for i in range(1, 15)},
    **{f"e{i:02d}": 0 for i in range(15, 29)},
    "e29": 1,
    "e30": 0,
    "e31": 0,
    "e32": 1,
}


def _raw(key: str, title: str, desc: str) -> RawEvent:
    return RawEvent(
        source="mock",
        url=f"https://mock.invalid/{key}",
        title=title,
        description=desc,
        starts_at=datetime(2026, 7, 1, 9, 0, 0),
        ends_at=None,
        venue="London",
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={"mock_id": key},
    )


def main() -> int:
    model = os.environ.get("ENTERPRISE_LLM_MODEL", "llama3.2:1b")
    os.environ["ENTERPRISE_LLM_MODEL"] = model
    print(f"model={model} batch_size={BATCH_SIZE} events={len(MOCKS)}", file=sys.stderr)

    events = [_raw(k, t, d) for k, t, d in MOCKS]
    rows: list[dict[str, object]] = []
    with httpx.Client() as client:
        for start in range(0, len(events), BATCH_SIZE):
            batch = events[start : start + BATCH_SIZE]
            labels = _classify_batch(client, batch)
            if labels is None:
                print(f"batch {start // BATCH_SIZE} FAILED (no labels)", file=sys.stderr)
                for ev in batch:
                    rows.append(
                        {
                            "mock_id": ev.extra.get("mock_id"),
                            "title": ev.title,
                            "label": None,
                            "error": "batch_failed",
                        }
                    )
                continue
            for ev, lab in zip(batch, labels, strict=True):
                rows.append(
                    {
                        "mock_id": ev.extra.get("mock_id"),
                        "title": ev.title,
                        "label": int(lab),
                    }
                )

    print(json.dumps({"model": model, "results": rows}, indent=2))
    n_ok = sum(1 for r in rows if r.get("label") is not None)
    print(f"\nclassified {n_ok}/{len(rows)}", file=sys.stderr)

    correct = 0
    wrong: list[str] = []
    scored = 0
    for r in rows:
        mid = str(r.get("mock_id"))
        lab = r.get("label")
        if lab is None or mid not in _GOLD:
            continue
        scored += 1
        if int(lab) == _GOLD[mid]:
            correct += 1
        else:
            wrong.append(f"{mid}: got {lab} expected {_GOLD[mid]}")
    if scored < len(_GOLD):
        print(
            f"accuracy: only {scored}/{len(_GOLD)} labeled (batches failed or partial)",
            file=sys.stderr,
        )
    if wrong:
        print(f"accuracy {correct}/{scored} on labeled ({100.0 * correct / max(scored, 1):.1f}%)", file=sys.stderr)
        for line in wrong:
            print(f"  mismatch: {line}", file=sys.stderr)
    elif scored == len(_GOLD):
        print(f"accuracy {correct}/{len(_GOLD)} (100%)", file=sys.stderr)

    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
