"""Offline checks for the pymongo/idna/python-dotenv/pygments security slice.

No Docker, MongoDB, test.env or test/testing_utils.py is used. MongoEngine and
BSON are exercised without any database connection; this does NOT replace real
MongoDB CRUD integration tests. The version-floor tests inspect the installed
environment, not uv.lock.
"""

import errno
import importlib
import importlib.util
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from importlib import metadata
from pathlib import Path
from types import ModuleType

import bson
import idna
import idna.core
import pytest
from bson import ObjectId
from bson.dbref import DBRef
from mongoengine.base.common import _document_registry
from packaging.version import Version
from rdflib import Graph as RdfGraph
from rdflib.compare import isomorphic

SERVER_DIR = Path(__file__).resolve().parents[1] / "server"

TURTLE = """
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:agent1 ex:says "synthetic message"@en ;
    ex:count 3 ;
    ex:knows ex:agent2 ;
    ex:detail [ ex:note "blank node note" ] .
ex:agent2 ex:score "2.5"^^xsd:decimal .
"""

# Minimum versions that carry the fixes for the advisories in this slice.
FIXED_FLOORS = {
    "pymongo": "4.18.2",
    "idna": "3.15",
    "python-dotenv": "1.2.2",
    "pygments": "2.20.0",
}


@pytest.mark.parametrize("name,floor", sorted(FIXED_FLOORS.items()))
def test_installed_version_meets_security_floor(name, floor):
    assert Version(metadata.version(name)) >= Version(floor)


@pytest.mark.parametrize("name,floor", sorted(FIXED_FLOORS.items()))
def test_security_floor_comparison_rejects_prereleases(name, floor):
    # PEP 440: a pre-release sorts below its final release.
    assert Version(floor + "rc1") < Version(floor)
    assert Version(floor + ".dev0") < Version(floor)
    assert Version(floor) >= Version(floor)


# ---------------- isolated loading of server/model.py ---------------- #

def _is_server_module(name):
    return name in ("main", "model", "utils") or name.startswith("utils.")


@contextmanager
def isolated_model(model_file=SERVER_DIR / "model.py"):
    """Load the real server/utils and model.py, then restore global state.

    Restores sys.modules entries for main/model/utils/utils.*, sys.path and the
    MongoEngine global document registry (same dict object, same contents),
    also when loading or the body fails.
    """
    registry_snapshot = dict(_document_registry)
    modules_snapshot = {n: m for n, m in sys.modules.items() if _is_server_module(n)}
    path_snapshot = list(sys.path)
    try:
        for name in modules_snapshot:
            del sys.modules[name]
        sys.path.insert(0, str(SERVER_DIR))
        importlib.invalidate_caches()
        semantic = importlib.import_module("utils.semantic")
        assert Path(semantic.__file__).resolve() == SERVER_DIR / "utils" / "semantic.py"
        spec = importlib.util.spec_from_file_location("model_driver_unit", model_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = path_snapshot
        for name in [n for n in sys.modules if _is_server_module(n)]:
            del sys.modules[name]
        sys.modules.update(modules_snapshot)
        _document_registry.clear()
        _document_registry.update(registry_snapshot)


@pytest.fixture
def model():
    with isolated_model() as module:
        yield module


@pytest.fixture
def semantic(model):
    return model.utils.semantic


def global_state():
    modules = {n: m for n, m in sys.modules.items() if _is_server_module(n)}
    return modules, dict(_document_registry), list(sys.path)


def same_state(before, after):
    modules_b, registry_b, path_b = before
    modules_a, registry_a, path_a = after
    return (
        modules_a.keys() == modules_b.keys()
        and all(modules_a[k] is modules_b[k] for k in modules_b)
        and registry_a.keys() == registry_b.keys()
        and all(registry_a[k] is registry_b[k] for k in registry_b)
        and path_a == path_b
    )


@pytest.fixture
def preexisting_globals(monkeypatch):
    """Foreign modules and registry entries that must survive loading."""
    for name in ("main", "model", "utils", "utils.semantic"):
        fake = ModuleType(name)
        fake.__file__ = "/nonexistent/foreign/%s.py" % name
        monkeypatch.setitem(sys.modules, name, fake)
    for name in ("Graph", "Log", "Insertion", "Deletion", "ForeignDoc"):
        monkeypatch.setitem(_document_registry, name, object())


def test_isolation_uses_real_local_semantic_and_restores_preexisting_state(preexisting_globals):
    before = global_state()
    foreign_utils = sys.modules["utils"]
    with isolated_model() as module:
        assert module.utils is not foreign_utils
        assert Path(module.utils.semantic.__file__).resolve() == SERVER_DIR / "utils" / "semantic.py"
        assert _document_registry["Log"] is module.Log
        assert _document_registry["ForeignDoc"] is before[1]["ForeignDoc"]
    assert sys.modules["utils"] is foreign_utils
    assert same_state(before, global_state())


def test_isolation_restores_state_when_body_fails(preexisting_globals):
    before = global_state()
    with pytest.raises(RuntimeError, match="synthetic body"):
        with isolated_model():
            raise RuntimeError("synthetic body failure")
    assert same_state(before, global_state())


def test_isolation_restores_state_when_loading_fails(preexisting_globals, tmp_path):
    broken = tmp_path / "broken_model.py"
    broken.write_text(
        "import utils.semantic\n"
        "from mongoengine import Document, StringField\n"
        "class Leaked(Document):\n"
        "    name = StringField()\n"
        "raise RuntimeError('synthetic load failure')\n"
    )
    before = global_state()
    with pytest.raises(RuntimeError, match="synthetic load failure"):
        with isolated_model(broken):
            pass  # pragma: no cover - never reached
    assert "Leaked" not in _document_registry
    assert same_state(before, global_state())


def test_isolation_without_preexisting_state_leaves_no_trace():
    before = global_state()
    with isolated_model():
        assert "Log" in _document_registry
    assert same_state(before, global_state())


def test_nested_loads_keep_original_references_valid(model):
    log = model.Log(_id=ObjectId(), origin_ip="192.0.2.10", action_type="insertion", action=ObjectId())
    insertion = model.Insertion(_id=ObjectId(), log=log, ttl_content="synthetic")
    insertion.validate()
    outer_registry = dict(_document_registry)

    with isolated_model() as inner:
        assert inner.Log is not model.Log
        assert _document_registry["Log"] is inner.Log
    assert all(_document_registry[k] is v for k, v in outer_registry.items())
    assert _document_registry["Log"] is model.Log
    insertion.validate()  # reference to the original Log still resolves


# ---------------- MongoEngine / BSON, offline, real native bson ---------------- #

WHEN = datetime(2025, 1, 2, 3, 4, 5, 123000)  # BSON keeps milliseconds


def bson_round_trip(document):
    return bson.decode(bson.encode(document.to_mongo()))


def reconstructed(document, names):
    """Read fields from _data; attribute access on a reference would hit the DB."""
    values = {}
    for name in names:
        value = document._data.get(name)
        values[name] = value.id if isinstance(value, DBRef) else value
    return values


def assert_reconstructed(cls, son, expected):
    """_from_son() must restore exactly the expected fields, offline."""
    restored = cls._from_son(son)
    assert reconstructed(restored, expected) == expected
    assert restored.to_mongo().to_dict() == son
    return restored


def test_bson_native_extension_is_active():
    assert bson.has_c()


def test_graph_round_trip_preserves_rdf_and_fields(model, semantic):
    original = semantic.get_graph_from_ttl(TURTLE)
    json_ld = semantic.convert_graph_to_json_ld(original)
    graph = model.Graph(_id="0", updated_at=WHEN, graph_data=json_ld)
    graph.validate()

    decoded = bson_round_trip(graph)
    assert set(decoded) == {"_id", "updated_at", "graph_data"}
    assert decoded["_id"] == "0"
    assert decoded["updated_at"] == WHEN
    assert decoded["graph_data"] == json_ld

    assert_reconstructed(
        model.Graph, decoded, {"_id": "0", "updated_at": WHEN, "graph_data": json_ld})

    rebuilt = semantic.get_graph_from_json(decoded["graph_data"])
    assert len(original) == len(rebuilt) == 6
    assert isomorphic(original, rebuilt)
    turtle = semantic.convert_graph_to_turtle(rebuilt)
    assert isomorphic(original, RdfGraph().parse(data=turtle, format="turtle"))


def test_rdf_isomorphism_control_detects_semantic_change(semantic):
    original = semantic.get_graph_from_ttl(TURTLE)
    changed = semantic.get_graph_from_ttl(TURTLE.replace("ex:count 3", "ex:count 999"))
    assert len(original) == len(changed)
    assert not isomorphic(original, changed)


def test_graph_clean_rejects_non_dict(model):
    with pytest.raises(model.ValidationError):
        model.Graph(_id="0", graph_data="not-a-dict").validate()


def test_log_insertion_deletion_round_trip_preserves_fields(model, semantic):
    original = semantic.get_graph_from_ttl(TURTLE)
    turtle_deleted = semantic.convert_graph_to_turtle(original)
    log_id, insertion_id, deletion_id, deletion_log_id = ObjectId(), ObjectId(), ObjectId(), ObjectId()

    log = model.Log(
        _id=log_id,
        uploaded_at=WHEN,
        origin_ip="192.0.2.10",
        action_type="insertion",
        action=insertion_id,
        user_details="synthetic-user",
    )
    log.validate()
    decoded = bson_round_trip(log)
    assert decoded == {
        "_id": log_id,
        "uploaded_at": WHEN,
        "origin_ip": "192.0.2.10",
        "action_type": "insertion",
        "action": insertion_id,
        "user_details": "synthetic-user",
    }
    restored = assert_reconstructed(model.Log, decoded, {
        "_id": log_id,
        "uploaded_at": WHEN,
        "origin_ip": "192.0.2.10",
        "action_type": "insertion",
        "action": insertion_id,
        "user_details": "synthetic-user",
    })
    assert model.serialize_log(restored) == model.serialize_log(log)

    insertion = model.Insertion(_id=insertion_id, log=log, ttl_content=TURTLE)
    insertion.validate()
    decoded = bson_round_trip(insertion)
    assert decoded == {"_id": insertion_id, "log": log_id, "ttl_content": TURTLE}
    assert_reconstructed(
        model.Insertion, decoded, {"_id": insertion_id, "log": log_id, "ttl_content": TURTLE})
    assert isomorphic(original, RdfGraph().parse(data=decoded["ttl_content"], format="turtle"))

    deletion_log = model.Log(
        _id=deletion_log_id,
        uploaded_at=WHEN,
        origin_ip="198.51.100.7",
        action_type="deletion",
        action=deletion_id,
    )
    deletion_log.validate()
    deletion = model.Deletion(_id=deletion_id, log=deletion_log, ttl_deleted_graph=turtle_deleted)
    deletion.validate()
    decoded = bson_round_trip(deletion)
    assert decoded == {"_id": deletion_id, "log": deletion_log_id, "ttl_deleted_graph": turtle_deleted}
    assert_reconstructed(model.Deletion, decoded, {
        "_id": deletion_id, "log": deletion_log_id, "ttl_deleted_graph": turtle_deleted})
    assert isomorphic(original, RdfGraph().parse(data=decoded["ttl_deleted_graph"], format="turtle"))


def test_reconstruction_check_detects_altered_or_missing_fields(model):
    insertion_id, log_id, deletion_id = ObjectId(), ObjectId(), ObjectId()
    expected_insertion = {"_id": insertion_id, "log": log_id, "ttl_content": TURTLE}
    expected_deletion = {"_id": deletion_id, "log": log_id, "ttl_deleted_graph": TURTLE}
    insertion = {"_id": insertion_id, "log": log_id, "ttl_content": TURTLE}
    deletion = {"_id": deletion_id, "log": log_id, "ttl_deleted_graph": TURTLE}
    # Controls: unmodified son passes.
    assert_reconstructed(model.Insertion, insertion, expected_insertion)
    assert_reconstructed(model.Deletion, deletion, expected_deletion)
    mutants = [
        (model.Insertion, dict(insertion, _id=ObjectId()), expected_insertion),
        (model.Insertion, {k: v for k, v in insertion.items() if k != "log"}, expected_insertion),
        (model.Insertion, dict(insertion, log=ObjectId()), expected_insertion),
        (model.Insertion, dict(insertion, ttl_content=""), expected_insertion),
        (model.Deletion, {k: v for k, v in deletion.items() if k != "log"}, expected_deletion),
        (model.Deletion, dict(deletion, log=ObjectId()), expected_deletion),
        (model.Deletion, dict(deletion, ttl_deleted_graph=""), expected_deletion),
    ]
    for cls, son, expected in mutants:
        with pytest.raises(AssertionError):
            assert_reconstructed(cls, son, expected)


def test_log_validation_rejects_bad_values(model):
    bad_ip = model.Log(_id=ObjectId(), origin_ip="not-an-ip", action_type="insertion", action=ObjectId())
    with pytest.raises(model.ValidationError):
        bad_ip.validate()
    bad_type = model.Log(_id=ObjectId(), origin_ip="192.0.2.10", action_type="other", action=ObjectId())
    with pytest.raises(model.ValidationError):
        bad_type.validate()
    missing = model.Deletion(_id=ObjectId(), log=model.Log(_id=ObjectId()))
    with pytest.raises(model.ValidationError):
        missing.validate()


# ---------------- idna CVE-2026-45409 / GHSA-65pc-fj4g-8rjx ---------------- #

OVERLONG = 300  # just above the 253/254 limits; correctness only, no timing

OVERLONG_INPUTS = {
    "arabic-digit": "٠" * OVERLONG,
    "katakana-middle-dot": "・" * OVERLONG + "漢",
}


@pytest.fixture
def contextual_calls(monkeypatch):
    calls = []
    for name in ("valid_contexto", "valid_contextj"):
        original = getattr(idna.core, name)

        def wrapper(*args, _original=original, _name=name, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(idna.core, name, wrapper)
    return calls


@pytest.mark.parametrize("label", sorted(OVERLONG_INPUTS))
@pytest.mark.parametrize(
    "func",
    [idna.encode, idna.core.check_label, idna.core.alabel, idna.core.ulabel],
    ids=lambda f: f.__name__,
)
def test_overlong_input_rejected_before_contextual_validation(func, label, contextual_calls):
    with pytest.raises(idna.IDNAError):
        func(OVERLONG_INPUTS[label])
    assert contextual_calls == []


def test_instrumentation_control_katakana_domain_runs_contextual_rules(contextual_calls):
    encoded = idna.encode("・漢.example")
    assert encoded.startswith(b"xn--") and encoded.endswith(b".example")
    assert "valid_contexto" in contextual_calls
    assert idna.decode(encoded) == "・漢.example"


def test_instrumentation_control_arabic_digit_domain_runs_contextual_rules(contextual_calls):
    # Leading ALEF satisfies the Bidi rule; Arabic-Indic digits are CONTEXTO.
    domain = "ا٠١.example"
    encoded = idna.encode(domain)
    assert encoded.startswith(b"xn--") and encoded.endswith(b".example")
    assert "valid_contexto" in contextual_calls
    assert idna.decode(encoded) == domain


# ---------------- python-dotenv CVE-2026-28684 / GHSA-mf9w-mj56-hr94 ---------------- #

class SymlinkOutcome:
    def __init__(self):
        self.result = None
        self.error = None
        self.forced_exdev_in_move = 0
        self.replace_to_link = 0
        self.target_text = None
        self.values = None


def run_symlink_scenario(tmp_path, monkeypatch, inject=None):
    """set_key through a synthetic symlink, forcing EXDEV only for that link.

    inject: optional exception raised by tempfile.NamedTemporaryFile.
    """
    import dotenv

    target = tmp_path / "target.env"
    target.write_text("KEEP=original\n")
    link = tmp_path / "link.env"
    link.symlink_to(target)
    link_str = str(link)
    outcome = SymlinkOutcome()
    state = {"in_move": False}

    real_rename, real_replace, real_move = os.rename, os.replace, shutil.move

    def rename(src, dst, *args, **kwargs):
        if state["in_move"] and os.fspath(dst) == link_str:
            outcome.forced_exdev_in_move += 1
            raise OSError(errno.EXDEV, "synthetic cross-device link")
        return real_rename(src, dst, *args, **kwargs)

    def replace(src, dst, *args, **kwargs):
        if os.fspath(dst) == link_str:
            outcome.replace_to_link += 1
        return real_replace(src, dst, *args, **kwargs)

    def move(src, dst, *args, **kwargs):
        state["in_move"] = True
        try:
            return real_move(src, dst, *args, **kwargs)
        finally:
            state["in_move"] = False

    monkeypatch.setattr(os, "rename", rename)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(shutil, "move", move)
    if inject is not None:
        def failing(*args, **kwargs):
            raise inject
        monkeypatch.setattr(tempfile, "NamedTemporaryFile", failing)

    try:
        outcome.result = dotenv.set_key(link_str, "ADDED", "value")
    except BaseException as err:  # recorded, never accepted as success
        outcome.error = err
    outcome.target_text = target.read_text()
    monkeypatch.undo()
    if outcome.error is None:
        outcome.values = dotenv.dotenv_values(link_str)
    return outcome


def assert_symlink_scenario_secure(outcome):
    assert outcome.error is None, "set_key failed: %r" % (outcome.error,)
    # The vulnerable branch (EXDEV inside shutil.move) or the replace path ran.
    assert outcome.forced_exdev_in_move or outcome.replace_to_link, "scenario not exercised"
    assert outcome.result == (True, "ADDED", "value")
    assert outcome.target_text == "KEEP=original\n"
    assert outcome.values == {"KEEP": "original", "ADDED": "value"}


def test_set_key_does_not_write_through_symlink_on_cross_device_fallback(tmp_path, monkeypatch):
    outcome = run_symlink_scenario(tmp_path, monkeypatch)
    assert_symlink_scenario_secure(outcome)


def test_symlink_scenario_rejects_injected_permission_error(tmp_path, monkeypatch):
    # An EACCES must never pass as a security success.
    outcome = run_symlink_scenario(tmp_path, monkeypatch, inject=PermissionError(errno.EACCES, "synthetic"))
    assert isinstance(outcome.error, PermissionError)
    assert outcome.forced_exdev_in_move == 0 and outcome.replace_to_link == 0
    with pytest.raises(AssertionError):
        assert_symlink_scenario_secure(outcome)


def test_symlink_scenario_rejects_write_through(tmp_path):
    # Control: a result where the target changed is not accepted.
    outcome = SymlinkOutcome()
    outcome.result = (True, "ADDED", "value")
    outcome.forced_exdev_in_move = 1
    outcome.target_text = "KEEP=original\nADDED='value'\n"
    outcome.values = {"KEEP": "original", "ADDED": "value"}
    with pytest.raises(AssertionError):
        assert_symlink_scenario_secure(outcome)


def test_set_key_regular_file_control(tmp_path):
    import dotenv

    path = tmp_path / "plain.env"
    path.write_text("KEEP=original\n")
    dotenv.set_key(str(path), "ADDED", "value")
    assert dotenv.dotenv_values(str(path)) == {"KEEP": "original", "ADDED": "value"}
