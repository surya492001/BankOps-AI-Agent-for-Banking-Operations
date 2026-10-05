from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "knowledge_base"


def parse_sop(text: str) -> tuple[dict, str]:
    """
    Split an SOP file into its metadata and its body.

    An SOP starts with a short header that says what it applies to:

        ---
        application: Card Management
        priority: P2
        ---
    """

    metadata = {}

    if not text.startswith("---"):
        return metadata, text

    header, separator, body = text[3:].partition("\n---")

    if not separator:
        return metadata, text

    for line in header.splitlines():
        key, found, value = line.partition(":")

        if found and value.strip():
            metadata[key.strip().lower()] = value.strip()

    return metadata, body.lstrip("\n")


def load_sops(knowledge_base_path: Path = KNOWLEDGE_BASE_PATH) -> list[dict]:
    """Read every SOP in the knowledge base."""

    sops = []

    for file_path in sorted(knowledge_base_path.glob("*.md")):

        metadata, body = parse_sop(
            file_path.read_text(encoding="utf-8")
        )

        sops.append(
            {
                "source": file_path.name,
                "application": metadata.get("application", ""),
                "priority": metadata.get("priority", ""),
                "content": body
            }
        )

    return sops
