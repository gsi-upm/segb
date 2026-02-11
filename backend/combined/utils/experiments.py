"""Helpers for extracting experiment-focused subgraphs from RDF data."""

from __future__ import annotations

from rdflib import Graph, Namespace, URIRef

AMOR_EXP_NS = Namespace("http://www.gsi.upm.es/ontologies/amor/experiments/ns#")
SEGB_NS = Namespace("http://www.gsi.upm.es/ontologies/segb/ns#")
ORO_NS = Namespace("http://kb.openrobots.org#")


def get_experiment_list(graph: Graph) -> bytes:
    """Returns all experiment URIs as SPARQL JSON bytes."""
    query = """
    PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>
    SELECT ?experiment_uri WHERE { ?experiment_uri a amor-exp:Experiment . }
    """
    return graph.query(query).serialize(format="json", encoding="utf-8")


def get_single_experiment_graph(graph: Graph, namespace: str, experiment_id: str) -> Graph:
    """Builds one subgraph containing experiment, activities and linked messages."""
    experiment_uri = Namespace(namespace)[experiment_id]
    query = f"""
    PREFIX segb: <{SEGB_NS}>
    PREFIX amor-exp: <{AMOR_EXP_NS}>
    PREFIX oro: <{ORO_NS}>

    CONSTRUCT {{
        <{experiment_uri}> ?experiment_predicate ?experiment_object .
        ?activity_uri ?activity_predicate ?activity_object .
        ?message_uri ?message_predicate ?message_object .
    }}
    WHERE {{
        <{experiment_uri}> a amor-exp:Experiment ;
                           ?experiment_predicate ?experiment_object .

        OPTIONAL {{
            ?activity_uri amor-exp:isRelatedWithExperiment <{experiment_uri}> ;
                          ?activity_predicate ?activity_object .
        }}

        OPTIONAL {{
            ?activity_uri oro:hasMessage ?message_uri .
            ?message_uri ?message_predicate ?message_object .
        }}
    }}
    """

    result = graph.query(query)
    output = Graph()
    output.bind("segb", SEGB_NS)
    output.bind("amor-exp", AMOR_EXP_NS)
    output.bind("oro", ORO_NS)

    for triple in result:
        output.add(triple)

    return output


# Backward-compatible aliases kept for external callers.
def get_experiment_with_activities(source: Graph, namespace: str, experiment_id: str) -> Graph:
    return get_single_experiment_graph(source, namespace, experiment_id)


def get_experiment(graph: Graph, namespace: str, experiment_id: str):
    experiment_uri = Namespace(namespace)[experiment_id]
    query = f"""
    PREFIX amor-exp: <{AMOR_EXP_NS}>
    SELECT ?predicate ?object
    WHERE {{
      <{experiment_uri}> a amor-exp:Experiment ;
                         ?predicate ?object .
    }}
    """
    return experiment_uri, graph.query(query)


def get_logged_activities(graph: Graph, namespace: str, experiment_id: str):
    experiment_uri: URIRef = Namespace(namespace)[experiment_id]
    query = f"""
    PREFIX segb: <{SEGB_NS}>
    PREFIX amor-exp: <{AMOR_EXP_NS}>
    DESCRIBE ?activity
    WHERE {{
      ?activity a segb:LoggedActivity ;
                amor-exp:isRelatedWithExperiment <{experiment_uri}> .
    }}
    """
    return graph.query(query)


def get_logged_messages(graph: Graph, namespace: str, experiment_id: str):
    experiment_uri: URIRef = Namespace(namespace)[experiment_id]
    query = f"""
    PREFIX amor-exp: <{AMOR_EXP_NS}>
    PREFIX oro: <{ORO_NS}>
    DESCRIBE ?message
    WHERE {{
      ?activity amor-exp:isRelatedWithExperiment <{experiment_uri}> ;
                oro:hasMessage ?message .
    }}
    """
    return graph.query(query)
