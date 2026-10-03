from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class Opportunity:
    id: str
    type: str
    title: str
    authority: str
    geography: list[str]
    status: str
    status_label: str
    deadline: str | None
    deadline_at: str | None
    deadline_precision: str
    description: str
    beneficiaries: list[str]
    requirements: list[str]
    tags: list[str]
    source_id: str
    source_name: str
    official_url: str | None
    last_verified: str
    external_id: str | None = None
    # Fail closed: a connector must explicitly prove that official_url is
    # a user-facing, record-specific source page rather than a portal home.
    specific_link: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
