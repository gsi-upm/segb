"""Namespace constants used by the SEGB semantic logger package."""

from rdflib import Namespace
from rdflib.namespace import FOAF, OWL, PROV, RDF, RDFS, XSD

SEGB = Namespace("http://www.gsi.upm.es/ontologies/segb/ns#")
AMOR = Namespace("http://www.gsi.upm.es/ontologies/amor/ns#")
AMOR_EXP = Namespace("http://www.gsi.upm.es/ontologies/amor/experiments/ns#")
MLS = Namespace("http://www.w3.org/ns/mls#")
ORO = Namespace("http://kb.openrobots.org#")
ONYX = Namespace("http://www.gsi.upm.es/ontologies/onyx/ns#")
EMOML = Namespace("http://www.gsi.upm.es/ontologies/onyx/vocabularies/emotionml/ns#")
OA = Namespace("http://www.w3.org/ns/oa#")
SCHEMA = Namespace("http://schema.org/")

DEFAULT_PREFIXES = {
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
    "prov": PROV,
    "foaf": FOAF,
    "schema": SCHEMA,
    "oa": OA,
    "segb": SEGB,
    "amor": AMOR,
    "amor-exp": AMOR_EXP,
    "mls": MLS,
    "oro": ORO,
    "onyx": ONYX,
    "emoml": EMOML,
}
