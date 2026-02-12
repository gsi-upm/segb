from datetime import datetime, timezone
import unittest

from rdflib import Graph, URIRef
from rdflib.namespace import PROV, RDF

from segb_logger import (
    ActivityKind,
    EmotionScore,
    ModelUsage,
    RobotStateSnapshot,
    SemanticSEGBLogger,
    SharedEventPolicy,
)
from segb_logger.namespaces import AMOR, MLS, OA, ONYX, ORO, SCHEMA, SEGB


class TestSemanticSEGBLogger(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = SemanticSEGBLogger(
            base_namespace="http://example.org/segb/robots/ari1/",
            robot_id="ari1",
            robot_name="ARI",
        )

    def test_activity_links_and_model_config(self) -> None:
        listening = self.logger.log_activity(
            activity_id="listen_1",
            activity_types=["oro:ListeningEvent"],
            started_at=datetime.now(timezone.utc),
        )

        model = self.logger.register_ml_model("decision_model", label="Decision model")
        decision = self.logger.log_activity(
            activity_id="decision_1",
            activity_types=["oro:DecisionMakingAction"],
            triggered_by_activity=listening,
            model_usages=[
                ModelUsage(
                    model=model,
                    parameters={"temperature": 0.1, "max_tokens": 128},
                    software_label="llm-runtime",
                    software_version="1.2.3",
                )
            ],
        )

        graph = self.logger.graph
        self.assertIn((decision, SEGB.triggeredByActivity, listening), graph)
        self.assertIn((decision, SEGB.usedMLModel, model), graph)
        self.assertIn((decision, RDF.type, ORO.DecisionMakingAction), graph)

        settings = list(graph.objects(decision, MLS.hasInput))
        self.assertGreater(len(settings), 0)
        for setting in settings:
            self.assertIn((setting, RDF.type, MLS.HyperParameterSetting), graph)

    def test_activity_single_trigger_activity_is_logged(self) -> None:
        source_activity = self.logger.log_activity(
            activity_id="source_activity",
            activity_types=["oro:ListeningEvent"],
            started_at=datetime.now(timezone.utc),
        )
        source_entity = self.logger.log_message(
            "source",
            message_id="source_message",
            generated_by_activity=source_activity,
            message_types=["oro:InitialMessage"],
        )

        target_activity = self.logger.log_activity(
            activity_id="target_activity",
            activity_types=["oro:DecisionMakingAction"],
            triggered_by_activity=source_activity,
            triggered_by_entity=source_entity,
            triggered_by_entities=[source_entity],
        )
        graph = self.logger.graph

        self.assertEqual(
            len(list(graph.objects(target_activity, SEGB.triggeredByActivity))),
            1,
        )
        self.assertEqual(
            len(list(graph.objects(target_activity, SEGB.triggeredByEntity))),
            1,
        )

    def test_activity_kind_maps_to_controlled_rdf_type(self) -> None:
        activity = self.logger.log_activity(
            activity_id="listen_by_kind",
            activity_kind=ActivityKind.LISTENING,
            started_at=datetime.now(timezone.utc),
        )
        self.assertIn((activity, RDF.type, ORO.ListeningEvent), self.logger.graph)

    def test_strict_activity_types_rejects_legacy_activity_types(self) -> None:
        strict_logger = SemanticSEGBLogger(
            base_namespace="http://example.org/segb/robots/ari1/",
            robot_id="ari1",
            strict_activity_types=True,
        )

        with self.assertRaises(ValueError):
            strict_logger.log_activity(
                activity_id="strict_invalid",
                activity_types=["oro:ListeningEvent"],
            )

    def test_strict_activity_types_accepts_kind_plus_extra_types(self) -> None:
        strict_logger = SemanticSEGBLogger(
            base_namespace="http://example.org/segb/robots/ari1/",
            robot_id="ari1",
            strict_activity_types=True,
        )
        activity = strict_logger.log_activity(
            activity_id="strict_ok",
            activity_kind=ActivityKind.DECISION,
            extra_types=["oro:CoordinationAction"],
        )

        graph = strict_logger.graph
        self.assertIn((activity, RDF.type, ORO.DecisionMakingAction), graph)
        self.assertIn((activity, RDF.type, strict_logger.resolve_term("oro:CoordinationAction")), graph)

    def test_emotions_and_robot_state(self) -> None:
        emotion_activity = self.logger.log_activity(
            activity_id="emotion_1",
            activity_types=["oro:EmotionRecognitionEvent"],
            started_at=datetime.now(timezone.utc),
        )
        msg = self.logger.log_message(
            "I am worried about climate change.",
            message_id="msg_1",
            generated_by_activity=emotion_activity,
            message_types=["oro:InitialMessage"],
        )
        human = self.logger.register_human("maria", first_name="Maria")

        annotation = self.logger.log_emotion_annotation(
            source_activity=emotion_activity,
            targets=[human, msg],
            emotions=[
                EmotionScore(category="emoml:big6_fear", intensity=0.2, confidence=0.8),
                EmotionScore(category="emoml:big6_sadness", intensity=0.6, confidence=0.9),
            ],
        )

        state = self.logger.log_robot_state(
            RobotStateSnapshot(
                timestamp=datetime.now(timezone.utc),
                battery_level=75.0,
                autonomy_mode="interactive",
                mission_phase="dialogue",
                cpu_load=29.5,
                memory_load=34.8,
                network_status="connected",
            ),
            source_activity=emotion_activity,
        )

        graph = self.logger.graph
        self.assertIn((annotation, RDF.type, AMOR.EmotionAnnotation), graph)
        self.assertIn((annotation, OA.hasTarget, human), graph)
        self.assertIn((annotation, OA.hasTarget, msg), graph)
        self.assertIn((emotion_activity, ONYX.usesEmotionModel, self.logger.resolve_term("emoml:big6")), graph)
        self.assertIn((emotion_activity, SEGB.producedEntityResult, state), graph)
        self.assertIn((state, PROV.wasAttributedTo, self.logger.robot_uri), graph)
        self.assertGreater(len(list(graph.objects(annotation, ONYX.hasEmotion))), 0)
        self.assertGreater(len(list(graph.objects(state, SCHEMA.additionalProperty))), 0)

    def test_cross_robot_links_in_shared_graph(self) -> None:
        shared_graph = Graph()
        ari = SemanticSEGBLogger(
            base_namespace="https://gsi.upm.es/segb/robots/ari/v1/",
            robot_id="ari1",
            graph=shared_graph,
        )
        tiago = SemanticSEGBLogger(
            base_namespace="https://gsi.upm.es/segb/robots/tiago/v1/",
            robot_id="tiago1",
            graph=shared_graph,
        )

        listening = ari.log_activity(
            activity_id="listening_1",
            activity_types=["oro:ListeningEvent"],
            started_at=datetime.now(timezone.utc),
        )
        msg = ari.log_message(
            "Need climate headlines",
            message_id="msg_1",
            generated_by_activity=listening,
            message_types=["oro:InitialMessage"],
        )

        coordination = tiago.log_activity(
            activity_id="coordination_1",
            activity_types=["oro:DecisionMakingAction"],
            started_at=datetime.now(timezone.utc),
            triggered_by_entities=[msg],
            used_entities=[msg],
        )
        ari_decision = ari.log_activity(
            activity_id="decision_1",
            activity_types=["oro:DecisionMakingAction"],
            started_at=datetime.now(timezone.utc),
            triggered_by_activity=coordination,
            triggered_by_entities=[msg],
        )
        ari.link_influence(ari_decision, coordination)

        self.assertIn((coordination, SEGB.triggeredByEntity, msg), shared_graph)
        self.assertIn((coordination, PROV.wasInfluencedBy, msg), shared_graph)
        self.assertIn((ari_decision, SEGB.triggeredByActivity, coordination), shared_graph)
        self.assertIn((ari_decision, PROV.wasInfluencedBy, coordination), shared_graph)
        self.assertIn((listening, SEGB.producedEntityResult, msg), shared_graph)
        self.assertTrue(str(coordination).startswith("https://gsi.upm.es/segb/robots/tiago/v1/"))
        self.assertTrue(str(ari_decision).startswith("https://gsi.upm.es/segb/robots/ari/v1/"))

    def test_shared_event_resolution_and_observation_linking(self) -> None:
        human = self.logger.register_human("maria", first_name="Maria")
        observed_at = datetime(2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc)

        event_uri_1 = self.logger.resolve_shared_event(
            event_kind="human_utterance",
            observed_at=observed_at,
            subject=human,
            text="Hello world",
            modality="speech",
            time_bucket_seconds=2,
        )
        event_uri_2 = self.logger.resolve_shared_event(
            event_kind="human_utterance",
            observed_at=datetime(2026, 1, 1, 10, 0, 1, 900000, tzinfo=timezone.utc),
            subject=human,
            text=" hello   world ",
            modality="speech",
            time_bucket_seconds=2,
        )

        self.assertEqual(event_uri_1, event_uri_2)

        listening = self.logger.log_activity(
            activity_id="listening_shared_event",
            activity_types=["oro:ListeningEvent"],
            started_at=observed_at,
            triggered_by_entities=[event_uri_1],
        )
        msg = self.logger.log_message(
            "hello world",
            message_id="msg_shared_event",
            generated_by_activity=listening,
            message_types=["oro:InitialMessage"],
        )
        self.logger.link_observation_to_shared_event(msg, event_uri_1, confidence=0.91)

        graph = self.logger.graph
        self.assertIn((event_uri_1, RDF.type, PROV.Entity), graph)
        self.assertIn((event_uri_1, RDF.type, SEGB.Trigger), graph)
        self.assertIn((listening, SEGB.triggeredByEntity, event_uri_1), graph)
        self.assertIn((msg, PROV.specializationOf, event_uri_1), graph)
        self.assertGreater(len(list(graph.objects(msg, self.logger.resolve_term("schema:confidence")))), 0)

    def test_get_shared_event_uri_uses_policy_fallback(self) -> None:
        human = self.logger.register_human("maria_policy", first_name="Maria")
        policy = SharedEventPolicy(
            namespace="https://gsi.upm.es/segb/shared-events/",
            time_bucket_seconds=2,
        )
        event_uri_1 = self.logger.get_shared_event_uri(
            event_kind="human_utterance",
            observed_at=datetime(2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc),
            subject=human,
            text="Hello world",
            modality="speech",
            policy=policy,
        )
        event_uri_2 = self.logger.get_shared_event_uri(
            event_kind="human_utterance",
            observed_at=datetime(2026, 1, 1, 10, 0, 1, 700000, tzinfo=timezone.utc),
            subject=human,
            text=" hello   world ",
            modality="speech",
            policy=policy,
        )

        self.assertEqual(event_uri_1, event_uri_2)
        self.assertTrue(str(event_uri_1).startswith("https://gsi.upm.es/segb/shared-events/"))

    def test_get_shared_event_uri_can_use_external_resolver(self) -> None:
        human = self.logger.register_human("maria_resolver", first_name="Maria")

        def resolver(request):  # type: ignore[no-untyped-def]
            self.assertEqual(request.event_kind, "human_utterance")
            self.assertEqual(request.subject, human)
            return "https://resolver.gsi.upm.es/shared-events/event_123"

        event_uri = self.logger.get_shared_event_uri(
            event_kind="human_utterance",
            observed_at=datetime(2026, 1, 1, 10, 0, 1, tzinfo=timezone.utc),
            subject=human,
            text="hello world",
            modality="speech",
            resolver=resolver,
        )

        graph = self.logger.graph
        resolved = URIRef("https://resolver.gsi.upm.es/shared-events/event_123")
        self.assertEqual(event_uri, resolved)
        self.assertIn((resolved, RDF.type, PROV.Entity), graph)
        self.assertIn((resolved, RDF.type, SEGB.Trigger), graph)


if __name__ == "__main__":
    unittest.main()
