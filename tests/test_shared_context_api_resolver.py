from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

import requests

from segb_logger.shared_context import HTTPSharedContextResolver
from segb_logger.types import SharedEventRequest


class TestHTTPSharedContextResolver(unittest.TestCase):
    def test_returns_shared_context_uri_on_success(self) -> None:
        session = Mock(spec=requests.Session)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"shared_context_uri": "https://example.org/shared-events/ctx_1"}
        session.post.return_value = response

        resolver = HTTPSharedContextResolver(
            base_url="https://segb.example.org",
            token="abc123",
            session=session,
            raise_on_error=True,
        )
        resolved = resolver(
            SharedEventRequest(
                event_kind="human_utterance",
                observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                subject="https://example.org/human/maria",
                text="hello",
                modality="speech",
            )
        )

        self.assertEqual(resolved, "https://example.org/shared-events/ctx_1")
        session.post.assert_called_once()

    def test_returns_none_on_failure_when_not_raising(self) -> None:
        session = Mock(spec=requests.Session)
        session.post.side_effect = requests.RequestException("boom")

        resolver = HTTPSharedContextResolver(
            base_url="https://segb.example.org",
            session=session,
            raise_on_error=False,
        )
        with patch("segb_logger.shared_context.logger.warning") as warning_mock:
            resolved = resolver(
                SharedEventRequest(
                    event_kind="human_utterance",
                    observed_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
                    subject="https://example.org/human/maria",
                    text="hello",
                    modality="speech",
                )
            )

        self.assertIsNone(resolved)
        warning_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
