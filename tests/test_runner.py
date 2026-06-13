import unittest

from hyperagents.core.runner import (
    CandidateResult,
    CandidateState,
    RunState,
    RunResult,
    Runner,
    candidate_state_from_metadata,
    ensure_run_success,
)


class RunnerTests(unittest.TestCase):
    def test_candidate_state_success(self):
        self.assertEqual(
            candidate_state_from_metadata(
                parent_agent_success=True,
                run_eval=True,
                run_full_eval=True,
                valid_parent=True,
            ),
            CandidateState.ACCEPTED,
        )

    def test_candidate_state_failed_patch_or_compile(self):
        self.assertEqual(
            candidate_state_from_metadata(
                parent_agent_success=False,
                run_eval=False,
                run_full_eval=False,
                valid_parent=False,
            ),
            CandidateState.FAILED,
        )

    def test_candidate_state_rejected_eval(self):
        self.assertEqual(
            candidate_state_from_metadata(
                parent_agent_success=True,
                run_eval=True,
                run_full_eval=True,
                valid_parent=False,
            ),
            CandidateState.REJECTED,
        )

    def test_runner_executes_generations_and_updates_archive(self):
        archive = ["initial"]
        parent_calls = []
        generation_calls = []
        post_generation_calls = []

        def parent_selector(archive_state):
            parent_calls.append(list(archive_state))
            return archive_state[-1]

        def generation_executor(generation, parent_id):
            generation_calls.append((generation, parent_id))
            return CandidateResult(
                candidate_id=generation,
                generation=generation,
                parent_id=parent_id,
                state=CandidateState.ACCEPTED,
                valid_parent=True,
                metadata={"parent_agent_success": True, "run_eval": True, "run_full_eval": True},
            )

        def post_generation(result):
            post_generation_calls.append(result.candidate_id)

        runner = Runner(
            config={"run_id": "test-run"},
            archive=archive,
            sandbox=None,
            domains=["paper_review"],
            meta_agent=None,
            events=None,
            parent_selector=parent_selector,
            generation_executor=generation_executor,
            post_generation_hook=post_generation,
        )

        run_result = runner.run(start_generation=1, max_generation=2)

        self.assertEqual(run_result.status, RunState.COMPLETED)
        self.assertEqual(generation_calls, [(1, "initial"), (2, 1)])
        self.assertEqual(parent_calls, [["initial"], ["initial", 1], ["initial", 1, 2]])
        self.assertEqual(post_generation_calls, [1, 2])
        self.assertEqual(runner.archive, ["initial", 1, 2])
        self.assertEqual(run_result.best_candidate_id, 2)

    def test_runner_reports_failure_summary(self):
        def parent_selector(_archive_state):
            return "initial"

        def generation_executor(_generation, _parent_id):
            raise RuntimeError("compile failed")

        runner = Runner(
            config={"run_id": "failure-run"},
            archive=["initial"],
            sandbox=None,
            domains=["paper_review"],
            meta_agent=None,
            events=None,
            parent_selector=parent_selector,
            generation_executor=generation_executor,
        )

        run_result = runner.run(start_generation=1, max_generation=1)

        self.assertEqual(run_result.status, RunState.FAILED)
        self.assertEqual(run_result.failure_summary, "compile failed")
        self.assertEqual(run_result.candidate_results, [])

    def test_ensure_run_success_raises_for_failed_runs(self):
        run_result = RunResult(
            run_id="failure-run",
            status=RunState.FAILED,
            best_candidate_id=None,
            final_archive_size=1,
            candidate_results=[],
            failure_summary="docker failed",
        )

        with self.assertRaisesRegex(RuntimeError, "docker failed"):
            ensure_run_success(run_result)


if __name__ == "__main__":
    unittest.main()
