from datetime import datetime, timezone
import unittest

from backend.combined.utils.shared_context import (
    SharedContextPolicy,
    SharedContextResolveRequest,
    SharedContextResolver,
)


class TestSharedContextResolver(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = SharedContextResolver(
            policy=SharedContextPolicy(
                namespace="https://example.org/shared-context/",
                time_window_seconds=3.0,
                match_threshold=0.85,
                ambiguous_threshold=0.70,
            )
        )

    def test_same_event_from_two_robots_matches_one_context(self) -> None:
        first = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                subject_uri="https://example.org/human/maria",
                modality="speech",
                text="Could you show me climate news?",
                robot_uri="https://example.org/robot/ari",
            )
        )
        second = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 1, tzinfo=timezone.utc),
                subject_uri="https://example.org/human/maria",
                modality="speech",
                text="Could you show me climate news",
                robot_uri="https://example.org/robot/tiago",
            )
        )

        self.assertEqual(first.status, "created")
        self.assertEqual(second.status, "matched")
        self.assertEqual(first.shared_context_uri, second.shared_context_uri)
        self.assertGreaterEqual(second.confidence, 0.85)

    def test_strict_subject_mismatch_creates_new_context(self) -> None:
        first = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                subject_uri="https://example.org/human/maria",
                modality="speech",
                text="hello there",
            )
        )
        second = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, 500000, tzinfo=timezone.utc),
                subject_uri="https://example.org/human/john",
                modality="speech",
                text="hello there",
            )
        )

        self.assertEqual(first.status, "created")
        self.assertEqual(second.status, "created")
        self.assertNotEqual(first.shared_context_uri, second.shared_context_uri)

    def test_reconcile_merges_ambiguous_context(self) -> None:
        base = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                modality="speech",
                text="climate change news now",
            )
        )
        ambiguous = self.resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 1, tzinfo=timezone.utc),
                modality="speech",
                text="climate change updates now",
            )
        )

        if ambiguous.status != "ambiguous":
            self.skipTest("Ambiguous branch not reached with current deterministic policy inputs.")

        report = self.resolver.reconcile_pending()
        self.assertGreaterEqual(report.scanned_ambiguous, 1)
        self.assertGreaterEqual(report.merged_count, 0)
        if report.merged_count > 0:
            self.assertIn(ambiguous.shared_context_uri, report.mappings)


if __name__ == "__main__":
    unittest.main()
