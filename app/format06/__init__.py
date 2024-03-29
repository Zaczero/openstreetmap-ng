from app.format06.changeset_mixin import Changeset06Mixin
from app.format06.diff_mixin import Diff06Mixin
from app.format06.element_mixin import Element06Mixin
from app.format06.note_mixin import Note06Mixin
from app.format06.note_rss_mixin import NoteRSS06Mixin
from app.format06.tag_mixin import Tag06Mixin
from app.format06.trace_mixin import Trace06Mixin
from app.format06.user_mixin import User06Mixin


class Format06(
    Changeset06Mixin,
    Element06Mixin,
    Note06Mixin,
    Diff06Mixin,
    Tag06Mixin,
    Trace06Mixin,
    User06Mixin,
):
    ...


class FormatRSS06(NoteRSS06Mixin):
    ...
