"""HTTP dependency security regressions. No Docker, MongoDB, network or test.env."""

import h11
import pytest


REQUEST_HEAD = b"POST /log HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n"


def parse(raw_body):
    """Feed a chunked request body to a server-side h11 connection; return its events."""
    connection = h11.Connection(h11.SERVER)
    connection.receive_data(REQUEST_HEAD + raw_body)
    events = []
    while True:
        event = connection.next_event()
        if event in (h11.NEED_DATA, h11.PAUSED):
            return events
        events.append(event)
        if isinstance(event, h11.EndOfMessage):
            return events


def body_of(events):
    return b"".join(bytes(e.data) for e in events if isinstance(e, h11.Data))


def test_well_formed_chunked_body_is_accepted():
    # Compatibility control: must pass on both vulnerable and patched h11.
    events = parse(b"5\r\nhello\r\n0\r\n\r\n")

    assert body_of(events) == b"hello"
    assert isinstance(events[-1], h11.EndOfMessage)


@pytest.mark.parametrize("terminator", [b"XX", b"\n\n", b"\r "], ids=["letters", "bare-lf", "cr-space"])
def test_malformed_chunk_terminator_is_rejected(terminator):
    # Chunk data must be followed by CRLF. Verified only against h11 0.14.0 (accepts the
    # bad bytes) and 0.16.0 (rejects them); 0.16.0 is the fixed version set by the audit
    # for GHSA-vqfr-h8mv-ghfj / CVE-2025-43859 (audit record PYSEC-2026-348, lenient
    # line terminators in chunked bodies). Other releases were not exercised.
    with pytest.raises(h11.RemoteProtocolError):
        parse(b"5\r\nhello" + terminator + b"0\r\n\r\n")
