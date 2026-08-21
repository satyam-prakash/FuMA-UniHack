"""
Guards on the 252-column delivery contract.

Owned by Member 3. The exporters call these before writing a byte, so a
malformed row fails loudly here instead of shipping a wrong-width file to the
client.
"""

from typing import List, Mapping, Sequence, Tuple

from member3.delivery.columns import DELIVERY_COLUMN_COUNT, DELIVERY_COLUMNS

_EXPECTED = set(DELIVERY_COLUMNS)


class DeliveryValidationError(Exception):
    """Raised when headers or rows do not match the delivery contract."""


def _header_errors(headers: Sequence[str]) -> List[str]:
    headers = list(headers)
    if headers == DELIVERY_COLUMNS:
        return []

    errors: List[str] = []
    if len(headers) != DELIVERY_COLUMN_COUNT:
        errors.append(f"expected {DELIVERY_COLUMN_COUNT} columns, got {len(headers)}")
    missing = [column for column in DELIVERY_COLUMNS if column not in set(headers)]
    extra = [column for column in headers if column not in _EXPECTED]
    if missing:
        errors.append(f"missing columns: {missing[:5]}")
    if extra:
        errors.append(f"unexpected columns: {extra[:5]}")
    if not errors:  # same columns, wrong order
        index = next(
            i for i, (got, want) in enumerate(zip(headers, DELIVERY_COLUMNS)) if got != want
        )
        errors.append(
            f"column order differs at index {index}: "
            f"{headers[index]!r} should be {DELIVERY_COLUMNS[index]!r}"
        )
    return errors


def _row_errors(rows: Sequence[Mapping[str, str]]) -> List[str]:
    errors: List[str] = []
    for index, row in enumerate(rows):
        keys = set(row)
        missing = sorted(_EXPECTED - keys)
        extra = sorted(keys - _EXPECTED)
        if missing:
            errors.append(f"row {index}: missing columns: {missing[:5]}")
        if extra:
            errors.append(f"row {index}: unexpected columns: {extra[:5]}")
    return errors


def validate_delivery_headers(headers: Sequence[str]) -> None:
    """Raises DeliveryValidationError unless the headers are DELIVERY_COLUMNS, in order."""
    errors = _header_errors(headers)
    if errors:
        raise DeliveryValidationError("; ".join(errors))


def validate_delivery_rows(rows: Sequence[Mapping[str, str]]) -> None:
    """Raises DeliveryValidationError if any row's keys are not exactly DELIVERY_COLUMNS."""
    errors = _row_errors(rows)
    if errors:
        raise DeliveryValidationError("; ".join(errors))


def check_delivery(rows: Sequence[Mapping[str, str]]) -> Tuple[bool, List[str]]:
    """Non-raising form for the API, which reports problems instead of 500-ing."""
    errors = _row_errors(rows)
    return not errors, errors
