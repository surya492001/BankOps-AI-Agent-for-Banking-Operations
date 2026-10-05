import os
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

from app.database.database import SessionLocal
from app.models.application import Application
from app.rag.sop import BASE_DIR, load_sops


CHROMA_PATH = Path(os.getenv("CHROMA_PATH", BASE_DIR / "chroma_db"))

# Chroma distance: lower = more similar.
MAX_DISTANCE = 0.75

NO_APPLICABLE_SOP = "NO_APPLICABLE_SOP"


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vectorstore = Chroma(
    persist_directory=str(CHROMA_PATH),
    embedding_function=embeddings
)


def resolve_application(application: str) -> str | None:
    """
    Return the name of the known application that the given text refers to.

    The agent may pass the name ("Internet Banking"), the code
    ("APP-IB-001"), both together or the numeric ID. Returns None when
    the text does not identify a known application.
    """

    wanted = str(application).strip().lower()

    if not wanted:
        return None

    db = SessionLocal()

    try:
        applications = db.query(Application).all()

        for known in applications:
            name = (known.application_name or "").lower()
            code = (known.application_code or "").lower()

            if (
                (name and (name in wanted or wanted in name))
                or (code and code in wanted)
                or wanted == str(known.application_id)
            ):
                return known.application_name

        return None

    finally:
        db.close()


def find_relevant_sop(
    query: str,
    application: str | None = None
) -> list[tuple]:
    """
    Return (source, distance) for each SOP that applies, closest first.

    Vector similarity is good at ranking SOPs but a distance on its own
    cannot tell whether an SOP really applies: generic incident wording
    scores close to every SOP. So when the incident's application is
    known, only SOPs written for that application are considered. The
    distance threshold is used when no application is given, or when
    the text given does not identify a known application.
    """

    known_application = (
        resolve_application(application)
        if application
        else None
    )

    if known_application:
        has_sop = any(
            sop["application"].lower() == known_application.lower()
            for sop in load_sops()
        )

        if not has_sop:
            return []

        results = vectorstore.similarity_search_with_score(
            query,
            k=3,
            filter={"application": known_application}
        )

    else:
        results = [
            (document, score)
            for document, score in vectorstore.similarity_search_with_score(
                query,
                k=3
            )
            if score <= MAX_DISTANCE
        ]

    # Results arrive closest first, so the first hit per SOP is its best.
    best = {}

    for document, score in results:
        source = document.metadata.get("source")

        if source and source not in best:
            best[source] = score

    return list(best.items())


@tool
def search_sop(query: str, application: str | None = None) -> str:
    """
    Search the banking SOP knowledge base.

    When investigating an incident, pass the incident's application name
    or application code (from get_application) as `application`. Only
    SOPs written for that application are returned, and
    NO_APPLICABLE_SOP is returned when the application has none.

    Leave `application` empty for general questions; an SOP is then
    returned only when it is sufficiently relevant to the query.

    A matching SOP is returned in full, with the application and
    priority it applies to.
    """

    relevant_results = find_relevant_sop(query, application)

    if not relevant_results:
        return NO_APPLICABLE_SOP

    sops = {
        sop["source"]: sop
        for sop in load_sops()
    }

    output = ["SOP_FOUND"]

    for source, score in relevant_results:

        sop = sops.get(source)

        if not sop:
            continue

        output.append(
            f"""
Source: {source}
Applies to application: {sop["application"] or "not specified"}
Applies to priority: {sop["priority"] or "not specified"}
Similarity distance: {score:.4f}

SOP Content:
{sop["content"]}
"""
        )

    if len(output) == 1:
        return NO_APPLICABLE_SOP

    return "\n\n---\n\n".join(output)
