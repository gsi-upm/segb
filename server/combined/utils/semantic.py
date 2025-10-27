from rdflib import Graph
import json

import logging
import os

logger = logging.getLogger("segb.server.utils.semantic")

logger.info("Loading module utils.semantic...")

# -------- AUX FUNCTIONS FOR APP.PY ----------- # 

def get_graph_from_ttl(data) -> Graph:
    graph = Graph()
    graph.parse(data=data, format="turtle")
    return graph

def get_graph_from_json(data) -> Graph:
    graph = Graph()
    if data:
        graph.parse(data=data, format="json-ld")
    return graph

def convert_graph_to_json_ld(graph: Graph) -> dict:
    graph_namespace = graph.namespaces()
    prefixes = {prefix: str(uri) for prefix, uri in graph_namespace}
    serialized_json_ld = graph.serialize(format="json-ld", context=prefixes, encoding="utf-8")
    json_ld_data = json.loads(serialized_json_ld)
    
    context = json_ld_data.get("@context", {})
    
    if "@graph" not in json_ld_data:
        json_ld_data.pop("@context")
        data = json_ld_data if isinstance(json_ld_data, list) else [json_ld_data]
        json_ld_data = {"@context": context, "@graph": data}
    
    return json_ld_data

def convert_graph_to_turtle(graph: Graph) -> str:
    graph_namespace = graph.namespaces()
    prefixes = {prefix: str(uri) for prefix, uri in graph_namespace}
    serialized_turtle_data = graph.serialize(format="turtle", context=prefixes, encoding="utf-8").decode("utf-8")
    return serialized_turtle_data

# -------- AUX FUNCTIONS FOR MODEL.PY ----------- # 

def update_prefixes (graph_data:dict, json_ld_data:dict) -> dict:
    new_prefixes = json_ld_data.get("@context", None)
    current_prefixes = graph_data.get("@context", {})
    if new_prefixes:
        for key, value in new_prefixes.items():
            if key not in current_prefixes:
                current_prefixes.update({key:value})
    json_ld_data["@context"].update(current_prefixes)
    return json_ld_data


def update_graph (graph_data: dict, json_ld_data:dict) -> dict:
    old_graph = graph_data.get("@graph", [])
    new_graph = old_graph + [json_triple for json_triple in json_ld_data["@graph"]]
    json_ld_data["@graph"] = new_graph
    return json_ld_data

def convert_ttl_info_to_dict(ttl_list) -> dict:
    dict_ttl_list = [json.loads(ttl.to_json()) for ttl in ttl_list]
    return dict_ttl_list