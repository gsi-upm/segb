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
        resolver = SharedContextResolver(
            policy=SharedContextPolicy(
                namespace="https://example.org/shared-context/",
                time_window_seconds=3.0,
                match_threshold=0.75,
                ambiguous_threshold=0.60,
                close_score_margin=0.03,
            )
        )
        # Seed one canonical active context that later observations can be compared against.
        base_result = resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                modality="speech",
                text="climate change news now",
            )
        )
        self.assertEqual(base_result.status, "created")

        # Create an ambiguous context near the base one (plausible but not strong enough to match).
        _ = resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 1, tzinfo=timezone.utc),
                modality="speech",
                text="climate change updates now",
            )
        )
        # Third observation is intentionally ambiguous at resolve-time, but should be merged by reconcile.
        ambiguous_result = resolver.resolve(
            SharedContextResolveRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 1, 200000, tzinfo=timezone.utc),
                modality="speech",
                text="climate change news now",
            )
        )
        self.assertEqual(ambiguous_result.status, "ambiguous")

        report = resolver.reconcile_pending()
        self.assertEqual(report.scanned_ambiguous, 2)
        self.assertEqual(report.merged_count, 1)
        self.assertIn(ambiguous_result.shared_context_uri, report.mappings)


if __name__ == "__main__":
    unittest.main()
