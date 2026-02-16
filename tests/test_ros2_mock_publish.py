import argparse
import os
import unittest
from unittest.mock import patch

from examples.run_simulation import (
    PublishConfig,
    build_publish_config_from_args,
    publish_simulation_result,
    run_simulation,
)


class TestROS2MockPublishing(unittest.TestCase):
    def test_publish_simulation_result_uses_segb_publisher(self) -> None:
        simulation_result = run_simulation()
        config = PublishConfig(
            base_url="http://localhost:8000",
            token="token-123",
            user="ari_logger",
            queue_file="/tmp/segb_queue.jsonl",
            timeout_seconds=7.5,
            verify_tls=False,
        )

        with patch("examples.run_simulation.SEGBPublisher") as publisher_cls:
            publisher = publisher_cls.return_value
            publisher.publish_graph.return_value = {"log_id": "abc-123"}

            report = publish_simulation_result(simulation_result, config=config)

            publisher_cls.assert_called_once_with(
                base_url="http://localhost:8000",
                token="token-123",
                default_user="ari_logger",
                timeout_seconds=7.5,
                verify_tls=False,
                queue_file="/tmp/segb_queue.jsonl",
            )
            publisher.publish_graph.assert_called_once_with(simulation_result.graph, user="ari_logger")
            self.assertTrue(report["published"])
            self.assertEqual(report["publish_response"]["log_id"], "abc-123")

    def test_build_publish_config_from_args_env_fallback(self) -> None:
        args = argparse.Namespace(
            publish_url=None,
            token=None,
            user=None,
            queue_file=None,
            timeout_seconds=None,
            insecure=False,
            no_print_ttl=False,
        )

        with patch.dict(
            os.environ,
            {
                "SEGB_API_URL": "http://localhost:9000",
                "SEGB_API_TOKEN": "token-from-env",
                "SEGB_LOG_USER": "env-user",
                "SEGB_QUEUE_FILE": "/tmp/env_queue.jsonl",
                "SEGB_PUBLISH_TIMEOUT": "12.0",
            },
            clear=False,
        ):
            config = build_publish_config_from_args(args)

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.base_url, "http://localhost:9000")
        self.assertEqual(config.token, "token-from-env")
        self.assertEqual(config.user, "env-user")
        self.assertEqual(config.queue_file, "/tmp/env_queue.jsonl")
        self.assertEqual(config.timeout_seconds, 12.0)
        self.assertTrue(config.verify_tls)

    def test_build_publish_config_uses_default_url_without_args_or_env(self) -> None:
        args = argparse.Namespace(
            publish_url=None,
            token=None,
            user=None,
            queue_file=None,
            timeout_seconds=None,
            insecure=False,
            no_print_ttl=False,
        )
        with patch.dict(os.environ, {}, clear=True):
            config = build_publish_config_from_args(args)
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.base_url, "http://localhost:5000")


if __name__ == "__main__":
    unittest.main()
