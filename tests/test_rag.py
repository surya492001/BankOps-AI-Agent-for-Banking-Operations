import pytest

from app.rag.ingest import ingest
from app.rag.retriever import NO_APPLICABLE_SOP, search_sop, vectorstore
from app.rag.sop import load_sops, parse_sop


@pytest.mark.parametrize(
    "query, expected_source",
    [
        (
            "P1 payment processing incident SLA breached escalation",
            "P1_payment_incident_SOP.md",
        ),
        (
            "P2 card management latency incident",
            "P2_card_management_SOP.md",
        ),
        (
            "P2 internet banking login issue resolved SLA breached",
            "P2_internet_banking_SOP.md",
        ),
    ],
)
def test_sop_found_for_matching_incident(query, expected_source):
    result = search_sop.invoke({"query": query})

    assert result.startswith("SOP_FOUND")

    # The closest match comes first and must be the right SOP.
    first_source = result.split("Source: ")[1].splitlines()[0]

    assert first_source == expected_source


def test_p1_payment_sop_names_the_escalation_team():
    result = search_sop.invoke(
        {"query": "P1 payment processing incident SLA breached escalation"}
    )

    assert "Payments L2" in result


@pytest.mark.parametrize(
    "query",
    [
        "What is the SOP for a failed NEFT batch?",
        "P3 ATM switch cash withdrawal failures",
        "Is the payments gateway healthy right now?",
        "mobile banking app crash",
        "weather in Mumbai",
    ],
)
def test_no_sop_returned_when_nothing_is_relevant(query):
    assert search_sop.invoke({"query": query}) == NO_APPLICABLE_SOP


def test_ingest_is_repeatable():
    before = vectorstore._collection.count()

    assert before > 0

    chunks = ingest()

    assert chunks == before

    # The retriever must keep working after the index is rebuilt.
    result = search_sop.invoke(
        {"query": "P1 payment processing incident SLA breached escalation"}
    )

    assert result.startswith("SOP_FOUND")


def test_matching_sop_is_returned_in_full():
    result = search_sop.invoke({"query": "P2 card management latency incident"})

    # Sections from the start and the end of the SOP are both present.
    assert "## Initial Investigation" in result
    assert "## SLA Breach" in result
    assert "## Evidence and Traceability" in result

    # Each SOP appears once, even when several of its chunks matched.
    assert result.count("Source: P2_card_management_SOP.md") == 1


# These are the queries a weaker model writes: short, and too generic for
# the distance threshold alone. The application filter makes them reliable.
@pytest.mark.parametrize(
    "query, application, expected_source",
    [
        ("Internet banking login issue", "Internet Banking", "P2_internet_banking_SOP.md"),
        ("Some users are unable to log in", "Internet Banking", "P2_internet_banking_SOP.md"),
        ("slow response times", "Card Management", "P2_card_management_SOP.md"),
        ("UPI payment failures timeout", "Payment Processing", "P1_payment_incident_SOP.md"),
        ("incident", "payment processing", "P1_payment_incident_SOP.md"),
        ("login issue", "Internet Banking (APP-IB-001)", "P2_internet_banking_SOP.md"),
        # Weaker models pass the code or the ID instead of the name.
        ("payment delays", "APP-PAY-001", "P1_payment_incident_SOP.md"),
        ("payment delays", "1", "P1_payment_incident_SOP.md"),
        ("card latency", "app-card-001", "P2_card_management_SOP.md"),
    ],
)
def test_sop_found_by_application(query, application, expected_source):
    result = search_sop.invoke({"query": query, "application": application})

    assert result.startswith("SOP_FOUND")
    assert result.count("Source: ") == 1
    assert f"Source: {expected_source}" in result


@pytest.mark.parametrize(
    "query, application",
    [
        ("ATM cash withdrawal failures", "ATM Switch"),
        # Generic wording that scores close to every SOP must still not
        # pull in an SOP written for a different application.
        ("P3 incident SOP escalation procedure SLA breach", "ATM Switch"),
        ("P1 payment processing incident SLA breached escalation", "ATM Switch"),
        ("ATM cash withdrawal failures", "APP-ATM-001"),
        ("ATM cash withdrawal failures", "4"),
    ],
)
def test_no_sop_for_application_without_one(query, application):
    result = search_sop.invoke({"query": query, "application": application})

    assert result == NO_APPLICABLE_SOP


def test_sop_result_states_what_it_applies_to():
    result = search_sop.invoke(
        {"query": "card latency", "application": "Card Management"}
    )

    assert "Applies to application: Card Management" in result
    assert "Applies to priority: P2" in result

    # The metadata header is not part of the guidance shown to the agent.
    assert "---\napplication:" not in result


def test_every_sop_declares_application_and_priority():
    sops = load_sops()

    assert len(sops) == 3

    for sop in sops:
        assert sop["application"], sop["source"]
        assert sop["priority"] in {"P1", "P2", "P3"}, sop["source"]
        assert sop["content"].startswith("# ")


def test_parse_sop_without_header():
    assert parse_sop("# Title\n\nBody") == ({}, "# Title\n\nBody")


def test_unrecognised_application_falls_back_to_relevance_search():
    # Text that names no known application must not hide a relevant SOP...
    found = search_sop.invoke(
        {
            "query": "P1 payment processing incident SLA breached escalation",
            "application": "the payments platform",
        }
    )

    assert "Source: P1_payment_incident_SOP.md" in found

    # ...and must not invent one either.
    missing = search_sop.invoke(
        {"query": "mobile app crash", "application": "Mobile Banking"}
    )

    assert missing == NO_APPLICABLE_SOP
