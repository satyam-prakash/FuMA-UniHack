"""
CSV writer for the 252-column delivery format.

Owned by Member 3. Encodes UTF-8 **with BOM** because the client opens the file
in Excel, which otherwise mangles ``®`` and ``™`` in brand names.
"""

import csv
import io
from typing import Mapping, Sequence

from member3.delivery.columns import DELIVERY_COLUMNS
from member3.delivery.validators import validate_delivery_rows


def rows_to_csv_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    """Serialises delivery rows to CSV bytes: BOM + header + CRLF line endings."""
    validate_delivery_rows(rows)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=DELIVERY_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
