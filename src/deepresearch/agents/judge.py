from __future__ import annotations

from dataclasses import dataclass, field

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.red_agent import RedAgent
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport


@dataclass
class JudgeConfig:
    max_rounds: int = 3
    target_score: float = 0.85
    min_score_delta: float = 0.03
    oscillation_window: int = 2


@dataclass
class RoundResult:
    round_num: int
    pre_fix_score: float
    post_fix_score: float
    issues_count: int
    actions_count: int
    issue_signatures: set[str] = field(default_factory=set)
    rejected_actions: int = 0


@dataclass
class JudgeResult:
    report: ResearchReport
    rounds: list[RoundResult]
    final_score: float
    termination_reason: str


class Judge:
    def __init__(
        self,
        config: JudgeConfig | None = None,
        *,
        red_agent: RedAgent | None = None,
        blue_agent: BlueAgent | None = None,
    ) -> None:
        self._config = config or JudgeConfig()
        self._red = red_agent
        self._blue = blue_agent
        self._history: list[RoundResult] = []

    @property
    def history(self) -> list[RoundResult]:
        return self._history.copy()

    def record_round(self, result: RoundResult) -> None:
        self._history.append(result)

    async def run(
        self,
        report: ResearchReport,
        evidence: list[EvidenceItem],
    ) -> JudgeResult:
        if self._red is None or self._blue is None:
            raise ValueError("Judge.run requires red_agent and blue_agent")

        self._history.clear()
        current_report = report.model_copy(deep=True)
        current_review = await self._red.review(current_report, evidence)

        if current_review.score >= self._config.target_score:
            return JudgeResult(
                report=current_report,
                rounds=[],
                final_score=current_review.score,
                termination_reason=(
                    f"target score reached: {current_review.score:.2f}"
                ),
            )

        termination_reason = ""
        for round_num in range(1, self._config.max_rounds + 1):
            fix_result = await self._blue.fix(
                current_report,
                current_review.issues,
                evidence,
            )
            revised_review = await self._red.review(fix_result.report, evidence)
            round_result = RoundResult(
                round_num=round_num,
                pre_fix_score=current_review.score,
                post_fix_score=revised_review.score,
                issues_count=len(current_review.issues),
                actions_count=len(fix_result.actions),
                issue_signatures={issue.signature for issue in revised_review.issues},
                rejected_actions=len(fix_result.rejected_actions),
            )
            self.record_round(round_result)
            current_report = fix_result.report
            current_review = revised_review

            should_continue, termination_reason = self.should_continue()
            if not should_continue:
                break

        return JudgeResult(
            report=current_report,
            rounds=self.history,
            final_score=current_review.score,
            termination_reason=termination_reason,
        )

    def should_continue(self) -> tuple[bool, str]:
        if not self._history:
            return True, "no rounds completed"

        latest = self._history[-1]
        if latest.post_fix_score >= self._config.target_score:
            return False, f"target score reached: {latest.post_fix_score:.2f}"
        if len(self._history) >= self._config.max_rounds:
            return False, f"max rounds ({self._config.max_rounds}) reached"
        if self._check_issue_oscillation():
            return False, "issue oscillation detected"
        if self._check_convergence():
            return False, "score converged for two consecutive rounds"
        return True, "improvement possible"

    def _check_convergence(self) -> bool:
        if len(self._history) < 2:
            return False
        recent = self._history[-2:]
        return all(
            result.post_fix_score - result.pre_fix_score
            < self._config.min_score_delta
            for result in recent
        )

    def _check_issue_oscillation(self) -> bool:
        window = self._config.oscillation_window
        if window <= 1 or len(self._history) < window:
            return False
        recent = self._history[-window:]
        common = set(recent[0].issue_signatures)
        for result in recent[1:]:
            common.intersection_update(result.issue_signatures)
        return bool(common)

    def final_report(self) -> dict:
        if not self._history:
            return {"rounds": 0, "final_score": 0.0, "termination_reason": "no rounds"}

        latest = self._history[-1]
        _, reason = self.should_continue()
        return {
            "rounds": len(self._history),
            "final_score": latest.post_fix_score,
            "termination_reason": reason,
            "history": [
                {
                    "round": result.round_num,
                    "pre_fix_score": result.pre_fix_score,
                    "post_fix_score": result.post_fix_score,
                    "issues": result.issues_count,
                    "actions": result.actions_count,
                    "rejected_actions": result.rejected_actions,
                }
                for result in self._history
            ],
        }
