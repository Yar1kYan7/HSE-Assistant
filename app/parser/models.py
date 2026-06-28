from dataclasses import dataclass
from datetime import date


@dataclass
class Homework:
    subject: str
    date: date
    subgroup: str
    content: str
    link: str | None = None

    def __hash__(self):
        return hash((self.subject, self.date, self.subgroup, self.content, self.link))

    def __eq__(self, other):
        if not isinstance(other, Homework):
            return False
        return (
            self.subject == other.subject
            and self.date == other.date
            and self.subgroup == other.subgroup
            and self.content == other.content
            and self.link == other.link
        )
