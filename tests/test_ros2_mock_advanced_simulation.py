import unittest

from rdflib import Literal, URIRef
from rdflib.namespace import RDF

from examples.run_advanced_simulation import run_advanced_simulation
from segb_logger.namespaces import EMOML, ONYX, ORO


class TestROS2MockAdvancedSimulation(unittest.TestCase):
    def test_advanced_simulation_logs_exam_anxiety_and_recovery_with_animals(self) -> None:
        result = run_advanced_simulation()
        graph = result.graph
        ari_namespace = result.base_result.ari_namespace

        exam_news_message = URIRef(f"{ari_namespace}message_ari_exam_news_msg_1")
        apology_message = URIRef(f"{ari_namespace}message_ari_apology_msg_1")
        animal_news_message = URIRef(f"{ari_namespace}message_ari_animal_news_msg_1")
        gratitude_message = URIRef(f"{ari_namespace}message_ari_heard_gratitude_1")

        self.assertIn((exam_news_message, RDF.type, ORO.ResponseMessage), graph)
        self.assertIn((apology_message, RDF.type, ORO.ResponseMessage), graph)
        self.assertIn((animal_news_message, RDF.type, ORO.ResponseMessage), graph)
        self.assertIn((gratitude_message, RDF.type, ORO.InitialMessage), graph)

        self.assertIn(
            (
                exam_news_message,
                ORO.hasText,
                Literal(
                    "Here is one headline: many students are anxious because an important exam is coming soon.",
                    lang="en",
                ),
            ),
            graph,
        )
        self.assertIn(
            (
                apology_message,
                ORO.hasText,
                Literal("I am sorry, Maria. That exam news was not a good choice right now.", lang="en"),
            ),
            graph,
        )
        self.assertIn(
            (
                gratitude_message,
                ORO.hasText,
                Literal("Thank you, ARI! That animal news made me very happy.", lang="en"),
            ),
            graph,
        )

        fear_intensities = []
        happiness_intensities = []
        for emotion in graph.subjects(RDF.type, ONYX.Emotion):
            category = graph.value(emotion, ONYX.hasEmotionCategory)
            intensity = graph.value(emotion, ONYX.hasEmotionIntensity)
            if category == EMOML.big6_fear and intensity is not None:
                fear_intensities.append(float(intensity))
            if category == EMOML.big6_happiness and intensity is not None:
                happiness_intensities.append(float(intensity))

        self.assertTrue(any(value >= 0.9 for value in fear_intensities))
        self.assertTrue(any(value >= 0.98 for value in happiness_intensities))


if __name__ == "__main__":
    unittest.main()
