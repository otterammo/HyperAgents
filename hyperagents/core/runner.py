from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RunState(str, Enum):
    PENDING = "run.pending"
    INITIALIZED = "run.initialized"
    RUNNING = "run.running"
    COMPLETED = "run.completed"
    FAILED = "run.failed"


class CandidateState(str, Enum):
    CREATED = "candidate.created"
    PATCHED = "candidate.patched"
    COMPILED = "candidate.compiled"
    STAGED_EVALUATED = "candidate.staged_evaluated"
    FULL_EVALUATED = "candidate.full_evaluated"
    ACCEPTED = "candidate.accepted"
    REJECTED = "candidate.rejected"
    FAILED = "candidate.failed"


@dataclass
class CandidateResult:
    candidate_id: Any
    generation: int
    parent_id: Any | None
    state: CandidateState
    valid_parent: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    run_id: str
    status: RunState
    best_candidate_id: Any | None
    final_archive_size: int
    candidate_results: list[CandidateResult]
    failure_summary: str | None = None


def ensure_run_success(run_result: RunResult) -> RunResult:
    if run_result.status == RunState.FAILED:
        raise RuntimeError(
            run_result.failure_summary or f"Run {run_result.run_id} failed"
        )
    return run_result


def candidate_state_from_metadata(
    *,
    parent_agent_success: bool,
    run_eval: bool,
    run_full_eval: bool = False,
    valid_parent: bool = False,
) -> CandidateState:
    if not parent_agent_success or not run_eval:
        return CandidateState.FAILED
    if run_full_eval:
        return CandidateState.ACCEPTED if valid_parent else CandidateState.REJECTED
    return CandidateState.STAGED_EVALUATED if valid_parent else CandidateState.REJECTED


class Runner:
    def __init__(
        self,
        config: dict[str, Any],
        archive: list[Any],
        sandbox: Any,
        domains: list[str],
        meta_agent: Any,
        events: Any,
        *,
        parent_selector: Callable[[list[Any]], Any],
        generation_executor: Callable[[int, Any | None], CandidateResult],
        archive_recorder: Callable[[list[Any], CandidateResult], list[Any]] | None = None,
        post_generation_hook: Callable[[CandidateResult], None] | None = None,
        parent_failure_handler: Callable[[Any | None, CandidateResult], None] | None = None,
    ) -> None:
        self.config = config
        self.archive = archive
        self.sandbox = sandbox
        self.domains = domains
        self.meta_agent = meta_agent
        self.events = events
        self.parent_selector = parent_selector
        self.generation_executor = generation_executor
        self.archive_recorder = archive_recorder or self._default_archive_recorder
        self.post_generation_hook = post_generation_hook
        self.parent_failure_handler = parent_failure_handler
        self.state = RunState.PENDING
        self.run_id = str(config.get("run_id", "unknown-run"))

    def initialize_run(self) -> str:
        self.state = RunState.INITIALIZED
        return self.run_id

    def run_generation(self, generation: int, parent_id: Any | None) -> CandidateResult:
        if self.state == RunState.PENDING:
            self.initialize_run()
        self.state = RunState.RUNNING
        return self.generation_executor(generation, parent_id)

    def run(
        self,
        *,
        start_generation: int,
        max_generation: int,
        parent_id: Any | None = None,
    ) -> RunResult:
        if self.state == RunState.PENDING:
            self.initialize_run()

        candidate_results: list[CandidateResult] = []
        failure_summary: str | None = None
        current_parent = parent_id

        try:
            if current_parent is None:
                current_parent = self.parent_selector(self.archive)

            for generation in range(start_generation, max_generation + 1):
                result = self.run_generation(generation, current_parent)
                candidate_results.append(result)
                self.archive = self.archive_recorder(self.archive, result)

                if self.parent_failure_handler is not None:
                    self.parent_failure_handler(current_parent, result)

                if self.post_generation_hook is not None:
                    self.post_generation_hook(result)

                current_parent = self.parent_selector(self.archive)

            self.state = RunState.COMPLETED
        except Exception as exc:
            self.state = RunState.FAILED
            failure_summary = str(exc)

        best_candidate_id = self._best_candidate_id(candidate_results)
        return RunResult(
            run_id=self.run_id,
            status=self.state,
            best_candidate_id=best_candidate_id,
            final_archive_size=len(self.archive),
            candidate_results=candidate_results,
            failure_summary=failure_summary,
        )

    @staticmethod
    def _default_archive_recorder(archive: list[Any], result: CandidateResult) -> list[Any]:
        archive.append(result.candidate_id)
        return archive

    @staticmethod
    def _best_candidate_id(candidate_results: list[CandidateResult]) -> Any | None:
        for state in (
            CandidateState.ACCEPTED,
            CandidateState.FULL_EVALUATED,
            CandidateState.STAGED_EVALUATED,
            CandidateState.REJECTED,
        ):
            for result in reversed(candidate_results):
                if result.state == state:
                    return result.candidate_id
        return candidate_results[-1].candidate_id if candidate_results else None
