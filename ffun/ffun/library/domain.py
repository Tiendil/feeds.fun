
import uuid
from typing import Iterable

from . import operations
from .entities import Entry

catalog_entries = operations.catalog_entries
get_entries_by_ids = operations.get_entries_by_ids
get_entries_by_filter = operations.get_entries_by_filter
get_new_entries = operations.get_new_entries
