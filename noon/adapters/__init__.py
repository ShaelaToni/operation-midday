"""Ingestion adapters: one per source. Each parses a platform's RAW export/response shape
into normalized ORM-row kwargs (the gotchas - micros, nested actions, 'spent', field-name
reads, status mapping - are handled HERE). Adapters are dict->dict (no DB I/O); the seeder
and import command do the actual ORM writes. This is the demo->prod seam: swap the fixture
reader for a live API client behind the same interface, zero downstream change.

Importing this package registers every adapter (side-effecting register() at module load).
Callers do `import noon.adapters` then get_adapter(source).
"""
from noon.adapters import google  # noqa: F401  (registers GoogleAdapter)
from noon.adapters import meta  # noqa: F401  (registers MetaAdapter)
from noon.adapters import taboola  # noqa: F401  (registers TaboolaAdapter)
