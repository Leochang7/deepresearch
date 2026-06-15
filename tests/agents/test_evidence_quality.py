from deepresearch.agents.evidence_quality import DefaultEvidenceQualityChecker
from deepresearch.schemas.evidence import EvidenceItem


def _item(**kwargs) -> EvidenceItem:
    defaults = dict(
        evidence_id="E1",
        task_id="t1",
        claim="The earth orbits the sun",
        quote="The earth orbits the sun in approximately 365 days",
        citation="Astronomy 101",
        source_url="https://example.com",
        confidence=0.8,
    )
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


def test_low_confidence_rejected():
    checker = DefaultEvidenceQualityChecker(min_confidence=0.3)
    passes, reason = checker.check(
        _item(confidence=0.1),
        "The earth orbits the sun in approximately 365 days",
    )
    assert not passes
    assert "confidence" in reason


def test_quote_not_in_source_rejected():
    checker = DefaultEvidenceQualityChecker()
    passes, reason = checker.check(
        _item(),
        "Completely unrelated content about cooking",
    )
    assert not passes
    assert "quote not found" in reason


def test_low_overlap_rejected():
    checker = DefaultEvidenceQualityChecker(min_token_overlap=0.3)
    passes, reason = checker.check(
        _item(
            claim="The stock market crashed in 1929",
            quote="The water cycle involves evaporation and precipitation",
        ),
        "The water cycle involves evaporation and precipitation",
    )
    assert not passes
    assert "overlap" in reason


def test_high_quality_passes():
    checker = DefaultEvidenceQualityChecker()
    passes, reason = checker.check(
        _item(),
        "The earth orbits the sun in approximately 365 days",
    )
    assert passes
    assert reason == ""


def test_empty_quote_rejected():
    checker = DefaultEvidenceQualityChecker()
    passes, _reason = checker.check(
        _item(quote=""),
        "some source content",
    )
    assert not passes


def test_min_confidence_boundary():
    checker = DefaultEvidenceQualityChecker(min_confidence=0.3)
    passes, _ = checker.check(
        _item(confidence=0.3),
        "The earth orbits the sun in approximately 365 days",
    )
    assert passes


def test_substring_match_supports_chinese_text_without_spaces():
    checker = DefaultEvidenceQualityChecker(min_token_overlap=0.5)
    passes, reason = checker.check(
        _item(claim="地球绕太阳公转", quote="地球绕太阳公转约365天。"),
        "地球绕太阳公转约365天。",
    )
    assert passes
    assert reason == ""
