import os
import json
import logging
import re
from rdflib import RDF, Graph, Literal

# logging
logging_level = os.getenv("PREFIXES_LOG_LEVEL", "INFO").upper()
log_file = os.getenv("SERVER_LOG_FILE_PREFIXES", "prefixes.log")

# Ensure the logs directory exists
os.makedirs('/logs', exist_ok=True) 
file_handler = logging.FileHandler(
    filename=f'/logs/{log_file}',
    mode='a',
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s -> %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger = logging.getLogger("prefixes_logger")
logger.setLevel(getattr(logging, logging_level, logging.INFO))
logger.addHandler(file_handler)


PREFIX_FILE = os.getenv("PREFIX_FILE_PATH", "prefixes.json")


def clean_prefixes_with_numbers(ttl_string):
    """
    Processes a TTL string and removes digits from prefix names,
    keeping the URI of each prefix untouched.

    Example:
    @prefix ex1: <http://example.org/> .
    becomes:
    @prefix ex: <http://example.org/> .
    """
    # Regex to match prefix declarations with numbers in the name
    prefix_pattern = re.compile(r'^@prefix\s+([a-zA-Z_]+[0-9]+):\s+<([^>]+)>\s+\.')

    new_lines = []
    replacements = {}

    for line in ttl_string.splitlines():
        match = prefix_pattern.match(line)
        if match:
            original_prefix = match.group(1)
            uri = match.group(2)
            new_prefix = re.sub(r'\d+', '', original_prefix)
            # Store the replacement mapping
            replacements[original_prefix] = new_prefix
            new_line = f"@prefix {new_prefix}: <{uri}> ."
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    # Reconstruct the modified TTL with updated prefixes
    modified_ttl = "\n".join(new_lines)

    # Replace all uses of the old prefix in the body of the TTL
    for old, new in replacements.items():
        modified_ttl = re.sub(rf'\b{old}:', f'{new}:', modified_ttl)

    return modified_ttl



def save_prefixes(new_prefixes: dict):
    """Save new prefixes to the JSON file, merging with existing ones."""
    existing = {}
    if os.path.exists(PREFIX_FILE):
        with open(PREFIX_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Update existing prefixes with new ones
    existing.update(new_prefixes)

    with open(PREFIX_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

 
    logger.info(f"Saved prefixes: {new_prefixes}")
    logger.info(f"Total stored prefixes: {existing}")

def load_prefixes() -> dict:
    """Load prefixes from the JSON file."""
    if not os.path.exists(PREFIX_FILE):
        return {}
    with open(PREFIX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# saving prefixes
def extract_prefixes(ttl_text: str) -> dict:
    prefix_pattern = r"@prefix\s+([a-zA-Z0-9\-_]+):\s+<([^>]+)>"
    matches = re.findall(prefix_pattern, ttl_text)
    prefix_dict = {match[0]: match[1] for match in matches}
    logger.info(f"Extracted prefixes: {prefix_dict}")
    return prefix_dict


def extract_classes(ttl_text: str) -> list:
    """Extracts classes from TTL content by finding objects of 'a' (rdf:type) statements."""
    class_pattern = re.compile(r'\s+a\s+([\w\-]+:[\w\-]+)\s*[,;.]')
    return sorted(set(class_pattern.findall(ttl_text)))

def extract_properties(ttl_text: str) -> list:
    """Extracts properties (predicates) from TTL content."""
    property_pattern = re.compile(r'^\s*([\w\-]+:[\w\-]+)\s+', re.MULTILINE)
    return sorted(set(property_pattern.findall(ttl_text)))

def save_prefixes_and_entities(prefixes: dict, ttl_text: str, output_path="/logs/for_RAG.json"):
    """Save prefixes, classes, properties, and abstract patterns into one JSON file for prompt usage."""
    classes = extract_classes(ttl_text)
    properties = extract_properties(ttl_text)

    g = Graph()
    patterns = {}

    try:
        g.parse(data=ttl_text, format="turtle")
    except Exception as e:
        logger.error(f"Failed to parse TTL for extracting patterns: {e}")
    else:
        # Step 1: Map each subject to its rdf:type
        subject_classes = {}
        for s, _, o in g.triples((None, RDF.type, None)):
            subject_classes.setdefault(s, set()).add(o)

        # Step 2: For each triple, add predicate to the subject's class pattern
        for s, p, o in g:
            if p == RDF.type:
                continue  # Skip rdf:type itself here
            for cls in subject_classes.get(s, []):
                patterns.setdefault(str(cls), set()).add(str(p))

            # Also capture predicate -> datatype mapping if literal with datatype
            if isinstance(o, Literal) and o.datatype:
                patterns.setdefault(str(p), set()).add(str(o.datatype))

    # Convertir URIs a prefijos
    def to_prefixed(uri):
        for prefix, ns in g.namespaces():
            if uri.startswith(str(ns)):
                return f"{prefix}:{uri[len(str(ns)):]}"
        return uri

    patterns_prefixed = {
        to_prefixed(k): sorted([to_prefixed(v) for v in vs])
        for k, vs in patterns.items()
    }

    data = {
        "prefixes": prefixes,
        "classes": sorted(classes),
        "properties": sorted(properties),
        "patterns": patterns_prefixed
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved RAG data (prefixes + classes + properties + patterns) to {output_path}")

