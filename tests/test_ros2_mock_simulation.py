import unittest

from rdflib import URIRef
from rdflib.namespace import PROV, RDF

from examples.run_simulation import run_simulation
from segb_logger.namespaces import AMOR_EXP, ORO, SEGB


class TestROS2MockSimulation(unittest.TestCase):
    def test_tutorial_simulation_generates_shared_event_and_single_response(self) -> None:
        result = run_simulation()
        graph = result.graph

        ari_listening_activity = URIRef(f"{result.ari_namespace}activity/ari_listening_1")
        tiago_listening_activity = URIRef(f"{result.tiago_namespace}activity/tiago_listening_1")
        ari_decision_activity = URIRef(f"{result.ari_namespace}activity/ari_decision_1")

        self.assertIn((result.human_uri, RDF.type, ORO.Human), graph)
        self.assertIn((ari_decision_activity, AMOR_EXP.isRelatedWithExperiment, result.experiment_uri), graph)
        self.assertIn((tiago_listening_activity, AMOR_EXP.isRelatedWithExperiment, result.experiment_uri), graph)

        self.assertIn((result.shared_event_uri, RDF.type, PROV.Entity), graph)
        self.assertIn((result.shared_event_uri, RDF.type, SEGB.Trigger), graph)
        self.assertIn((ari_listening_activity, SEGB.triggeredByEntity, result.shared_event_uri), graph)
        self.assertIn((tiago_listening_activity, SEGB.triggeredByEntity, result.shared_event_uri), graph)
        self.assertIn((result.ari_observation_uri, PROV.specializationOf, result.shared_event_uri), graph)
        self.assertIn((result.tiago_observation_uri, PROV.specializationOf, result.shared_event_uri), graph)

        self.assertIn((ari_decision_activity, SEGB.triggeredByActivity, ari_listening_activity), graph)
        self.assertIn((ari_decision_activity, SEGB.producedEntityResult, result.ari_response_uri), graph)

        response_messages = list(graph.subjects(RDF.type, ORO.ResponseMessage))
        self.assertEqual(response_messages, [result.ari_response_uri])
        self.assertTrue(str(result.ari_response_uri).startswith(result.ari_namespace))


if __name__ == "__main__":
    unittest.main()
