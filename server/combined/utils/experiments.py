from rdflib import Namespace, Graph, URIRef
from rdflib.query import Result
import os
import logging

logger = logging.getLogger("segb.server.utils.experiments")

logger.info("Loading module utils.experiments...")

# -------- AUX FUNCTIONS FOR AMOR EXPERIMENTS QUERIES ----------- # 

def get_experiment(graph: Graph, namespace: str, experiment_id: str):
    '''
    Get the experiment details from the RDF graph
    Args:
        graph (Graph): The RDF graph to query.
        namespace (str): The namespace of the experiment.
        experiment_id (str): The ID of the experiment.
    Returns:
        tuple: A tuple containing the experiment URI and the details.
    '''
    # Define the specific experiment
    ns = Namespace(namespace)
    experiment_uri = ns[experiment_id]
    # Define the SPARQL query
    logger.info(f"Getting experiment details for {experiment_uri}")
    query = f"""
    PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>

    SELECT ?predicate ?object
    WHERE {{
        <{experiment_uri}> a amor-exp:Experiment .
        <{experiment_uri}> ?predicate ?object .
    }}
    """
    # Execute the query
    results = graph.query(query)
    # Return the results
    logger.info(f"Experiment details for {experiment_uri} retrieved successfully.")
    return experiment_uri, results

def get_logged_activities(graph: Graph, namespace: str, experiment_id: str) -> Result:
    '''
    Get the logged activities related to a specific experiment
    Args:
        graph (Graph): The RDF graph to query.
        namespace (str): The namespace of the experiment.
        experiment_id (str): The ID of the experiment.
    Returns:
        Result: The logged activities related to the experiment.
    '''
    # Define the specific experiment
    ns = Namespace(namespace)
    experiment_uri: URIRef = ns[experiment_id]
    # Define the SPARQL query
    logger.info(f"Getting logged activities for {experiment_uri}")
    query = f"""
    PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
    PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>
    
    DESCRIBE ?activity
    WHERE {{
        ?activity a segb:LoggedActivity .
        ?activity amor-exp:isRelatedWithExperiment <{experiment_uri}> .
    }}
    """
    # Execute the query
    results = graph.query(query)
    logger.info(f"Logged activities for {experiment_uri} retrieved successfully.")
    # Return the results
    return results

def get_logged_messages(graph: Graph, namespace: str, experiment_id: str) -> Result:
    '''
    Get the logged messages related to a specific experiment
    Args:
        graph (Graph): The RDF graph to query.
        namespace (str): The namespace of the experiment.
        experiment_id (str): The ID of the experiment.
    Returns:
        Result: The logged messages related to the experiment.
    '''
    # Define the specific experiment
    ns = Namespace(namespace)
    experiment_uri: URIRef = ns[experiment_id]

    logger.info(f"Getting logged messages for {experiment_uri}")
    query = f"""
    PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
    PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>
    PREFIX oro: <http://kb.openrobots.org#>
    
    DESCRIBE ?message
    WHERE {{
        ?activity a segb:LoggedActivity ;
            amor-exp:isRelatedWithExperiment <{experiment_uri}> ;
            oro:hasMessage ?message .
    }}
    """

    results = graph.query(query)
    logger.info(f"Logged messages for {experiment_uri} retrieved successfully.")

    return results

def get_experiment_with_activities(source: Graph, namespace: str, experiment_id: str) -> Graph:
    '''
    Deprecated function: too many SPARQL queries. Recommended to use get_single_experiment_graph instead which uses only one query (more sophisticated).
    Args:
        source (Graph): The RDF graph to query.
        namespace (str): The namespace of the experiment.
        experiment_id (str): The ID of the experiment.
    Returns:
        Graph: A graph containing the experiment details, activities, and messages.
    '''
    # Get the experiment details
    try:
        logger.info(f"Getting experiment details...")
        experiment_uri, experiment_details = get_experiment(source, namespace, experiment_id)
    except Exception as e:
        raise Exception(f"Error getting experiment details: {str(e)}")
    # Get the logged activities related to the experiment
    try:
        logged_activities = get_logged_activities(source, namespace, experiment_id)
    except Exception as e:
        raise Exception(f"Error getting logged activities: {str(e)}")
    # Get the logged messages related to the experiment
    try:
        logged_messages = get_logged_messages(source, namespace, experiment_id)
    except Exception as e:
        raise Exception(f"Error getting logged messages: {str(e)}")
    # Return both experiment details, logged activities, and logged messages in a new graph
    result_graph = Graph()
    # Bind all prefixes from the source graph to the result graph
    for prefix, namespace_uri in source.namespaces():
        result_graph.bind(prefix, namespace_uri)
    # Add the experiment details and logged activities to the result graph
    for row in experiment_details:
        result_graph.add((experiment_uri, row.predicate, row.object))

    for triple in logged_activities:
        subject, predicate, obj = triple
        result_graph.add((subject, predicate, obj))
    
    for triple in logged_messages:
        subject, predicate, obj = triple
        result_graph.add((subject, predicate, obj))
    
    logger.info(f"Experiment details for {experiment_uri} retrieved successfully.")
    logger.debug(f"Resulting graph has {len(result_graph)} triples.")
    return result_graph

def get_experiment_list(graph: Graph) -> dict:
    '''
    Get a list of all experiments in the RDF graph
    Args:
        graph (Graph): The RDF graph to query.
    Returns:
        dict: A dictionary containing the experiment URIs.
    '''
    # Define the SPARQL query
    logger.info("Getting list of experiments...")
    query = """
        PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>
        
        SELECT ?experiment_uri 
        WHERE {
            ?experiment_uri a amor-exp:Experiment .
        }
    """
    result = graph.query(query)
    return result.serialize(format="json", encoding="utf-8")

def get_single_experiment_graph(graph: Graph, namespace: str, experiment_id: str) -> Graph:
    '''
    Get a single experiment graph from the RDF graph including activities and messages
    Args:
        graph (Graph): The RDF graph to query.
        namespace (str): The namespace of the experiment.
        experiment_id (str): The ID of the experiment.
    Returns:
        Graph: A graph containing the experiment details, activities, and messages.
    '''
    # Define the specific experiment
    ns = Namespace(namespace)
    experiment_uri = ns[experiment_id]
    # Define the SPARQL query
    logger.info(f"Getting experiment details for {experiment_uri}")
    query = f"""
    PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
    PREFIX amor-exp: <http://www.gsi.upm.es/ontologies/amor/experiments/ns#>
    PREFIX oro: <http://kb.openrobots.org#>

    CONSTRUCT {{ 
        <{experiment_uri}> ?experiment_predicate ?experiment_object .
        ?activity_uri ?activity_predicate ?activity_object .
        ?msg_uri ?message_predicate ?message_object .
    }}
    WHERE {{
        <{experiment_uri}> a amor-exp:Experiment .
        
        <{experiment_uri}> ?experiment_predicate ?experiment_object .
        
        OPTIONAL {{
            ?activity_uri amor-exp:isRelatedWithExperiment <{experiment_uri}> .

            ?activity_uri ?activity_predicate ?activity_object .
        }}
        OPTIONAL {{
            ?activity amor-exp:isRelatedWithExperiment <{experiment_uri}> ;
                oro:hasMessage ?msg_uri .

            ?msg_uri ?message_predicate ?message_object .
            
        }}
    }}
    """
    # Execute the query
    results = graph.query(query)
    # Return the results
    logger.info(f"Experiment details for {experiment_uri} retrieved successfully.")
    resulting_graph = Graph()
    resulting_graph.bind("segb", Namespace("http://www.gsi.upm.es/ontologies/segb/ns#"))
    resulting_graph.bind("amor-exp", Namespace("http://www.gsi.upm.es/ontologies/amor/experiments/ns#"))
    resulting_graph.bind("oro", Namespace("http://kb.openrobots.org#"))
    for triple in results:
        resulting_graph.add(triple)
    logger.debug(f"Resulting graph has {len(resulting_graph)} triples.")
    return resulting_graph