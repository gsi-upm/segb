import unittest
from collections import Counter

from rdflib import Literal, URIRef
from rdflib.namespace import PROV, RDF

from examples.run_simulation import run_basic_simulation
from segb_logger.namespaces import EMOML, ONYX, ORO, SCHEMA, SEGB


class TestROS2MockSimulation(unittest.TestCase):
    def test_basic_simulation_logs_entry_engagement_and_emotion_shift(self) -> None:
        result = run_basic_simulation()
        graph = result.graph

        ari_entry_detection_activity = URIRef(f"{result.ari_namespace}activity_ari_human_detection_1")
        tiago_entry_detection_activity = URIRef(f"{result.tiago_namespace}activity_tiago_human_detection_1")
        ari_listening_activity = URIRef(f"{result.ari_namespace}activity_ari_listening_1")
        tiago_listening_activity = URIRef(f"{result.tiago_namespace}activity_tiago_listening_1")
        ari_decision_activity = URIRef(f"{result.ari_namespace}activity_ari_decision_1")
        tiago_engagement_activity = URIRef(f"{result.tiago_namespace}activity_tiago_engagement_check_1")
        ari_emotion_from_speech = URIRef(f"{result.ari_namespace}activity_ari_emotion_from_speech_1")
        ari_emotion_from_face_before = URIRef(f"{result.ari_namespace}activity_ari_emotion_from_face_before_1")
        ari_emotion_from_face_after = URIRef(f"{result.ari_namespace}activity_ari_emotion_from_face_after_1")

        self.assertIn((result.human_uri, RDF.type, ORO.Human), graph)

        # Step 1: Maria enters and both robots detect her.
        self.assertIn((result.entry_shared_event_uri, RDF.type, PROV.Entity), graph)
        self.assertIn((result.entry_shared_event_uri, RDF.type, SCHEMA.Event), graph)
        self.assertIn((ari_entry_detection_activity, SCHEMA.about, result.entry_shared_event_uri), graph)
        self.assertIn((tiago_entry_detection_activity, SCHEMA.about, result.entry_shared_event_uri), graph)
        self.assertIn((ari_entry_detection_activity, RDF.type, ORO.DetectedHumanEvent), graph)
        self.assertIn((tiago_entry_detection_activity, RDF.type, ORO.DetectedHumanEvent), graph)

        # Shared speech event observed by both robots.
        self.assertIn((result.shared_event_uri, RDF.type, PROV.Entity), graph)
        self.assertIn((result.shared_event_uri, RDF.type, SCHEMA.Event), graph)
        self.assertIn((ari_listening_activity, SCHEMA.about, result.shared_event_uri), graph)
        self.assertIn((tiago_listening_activity, SCHEMA.about, result.shared_event_uri), graph)
        self.assertIn((result.ari_observation_uri, PROV.specializationOf, result.shared_event_uri), graph)
        self.assertIn((result.tiago_observation_uri, PROV.specializationOf, result.shared_event_uri), graph)

        self.assertIn((ari_decision_activity, SEGB.triggeredByActivity, ari_listening_activity), graph)
        self.assertIn((ari_decision_activity, SEGB.triggeredByEntity, result.ari_observation_uri), graph)
        self.assertIn((ari_decision_activity, SEGB.producedEntityResult, result.ari_response_uri), graph)
        self.assertIn((tiago_engagement_activity, SEGB.triggeredByActivity, tiago_listening_activity), graph)
        self.assertIn((tiago_engagement_activity, SEGB.triggeredByEntity, result.tiago_observation_uri), graph)

        response_messages = list(graph.subjects(RDF.type, ORO.ResponseMessage))
        self.assertEqual(response_messages, [result.ari_response_uri])
        self.assertTrue(str(result.ari_response_uri).startswith(result.ari_namespace))
        self.assertTrue(all(str(uri).startswith(result.ari_namespace) for uri in response_messages))

        # Step 5: ARI gives emotional support.
        self.assertIn(
            (
                result.ari_response_uri,
                ORO.hasText,
                Literal("Maria, siento que estes triste. Estoy contigo y todo va a estar bien.", lang="en"),
            ),
            graph,
        )

        # Steps 3 and 6: sadness from speech+face, then happiness after response.
        self.assertIn((ari_emotion_from_speech, RDF.type, ONYX.EmotionAnalysis), graph)
        self.assertIn((ari_emotion_from_face_before, RDF.type, ONYX.EmotionAnalysis), graph)
        self.assertIn((ari_emotion_from_face_after, RDF.type, ONYX.EmotionAnalysis), graph)

        emotion_categories = Counter(graph.objects(None, ONYX.hasEmotionCategory))
        self.assertEqual(emotion_categories[EMOML.big6_sadness], 2)
        self.assertEqual(emotion_categories[EMOML.big6_happiness], 1)


if __name__ == "__main__":
    unittest.main()
