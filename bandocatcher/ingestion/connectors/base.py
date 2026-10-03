from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Opportunity:
    id: str
    external_id: Optional[str]
    type: str
    title: str
    authority: str
    geography: list
    status: str
    status_label: str
    deadline: Optional[str]
    deadline_at: Optional[str]
    deadline_precision: str
    description: str
    beneficiaries: list
    requirements: list
    tags: list
    source_id: str
    source_name: str
    official_url: str
    last_verified: str
    specific_link: bool = True

    def to_dict(self):
        return asdict(self)
