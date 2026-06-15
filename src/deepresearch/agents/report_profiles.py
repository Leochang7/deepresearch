from __future__ import annotations

from enum import StrEnum


class ReportProfile(StrEnum):
    FACTUAL_ANSWER = "factual_answer"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    TECH_RESEARCH = "tech_research"
    RISK_ANALYSIS = "risk_analysis"


PROFILE_SECTIONS: dict[ReportProfile, dict[str, object]] = {
    ReportProfile.FACTUAL_ANSWER: {
        "description": "Direct factual answer with evidence citations.",
        "sections": ["Answer", "Key Evidence", "Limitations", "References"],
    },
    ReportProfile.COMPARISON: {
        "description": "Side-by-side comparison of options with evidence.",
        "sections": [
            "Overview",
            "Comparison Table",
            "Analysis",
            "Recommendation",
            "Limitations",
            "References",
        ],
    },
    ReportProfile.TIMELINE: {
        "description": "Chronological narrative with dated evidence.",
        "sections": [
            "Timeline",
            "Key Developments",
            "Current Status",
            "Limitations",
            "References",
        ],
    },
    ReportProfile.TECH_RESEARCH: {
        "description": "Technical deep-dive with methodological evidence.",
        "sections": [
            "Executive Summary",
            "Background",
            "Technical Analysis",
            "Findings",
            "Limitations",
            "References",
        ],
    },
    ReportProfile.RISK_ANALYSIS: {
        "description": "Risk-focused report with severity assessments.",
        "sections": [
            "Executive Summary",
            "Risk Overview",
            "Risk Details",
            "Mitigation",
            "Limitations",
            "References",
        ],
    },
}


def build_profile_prompt(profile: ReportProfile, base_prompt: str) -> str:
    config = PROFILE_SECTIONS[profile]
    description = str(config["description"])
    sections = config["sections"]
    assert isinstance(sections, list)
    sections_text = ", ".join(str(s) for s in sections)
    profile_block = (
        f"\n\nReport profile: {profile.value}\n"
        f"Description: {description}\n"
        f"Use these sections: {sections_text}\n"
    )
    return base_prompt + profile_block
