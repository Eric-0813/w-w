#!/usr/bin/env python3
"""Value a supplied long-only portfolio CSV; never fetch data or submit orders.

Amounts are JSON decimal strings. Values are calculated without rounding, with
up to 50 significant digits; percentages are rounded to eight decimal places.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException, Inexact, ROUND_HALF_EVEN, localcontext
from pathlib import Path


FIELDS = {"symbol", "quantity", "price", "currency", "price_as_of", "fx_to_base"}
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def decimal_text(value: Decimal) -> str:
    if not value:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def number(value: str, field: str, *, positive: bool = False) -> Decimal:
    # Bound exponent/length so malformed inputs cannot produce enormous output.
    if len(value) > 256 or not NUMBER.fullmatch(value):
        raise ValueError(f"{field} must be a finite decimal number")
    parsed = Decimal(value)
    if not parsed.is_finite() or (parsed and abs(parsed.adjusted()) > 100):
        raise ValueError(f"{field} must be finite with a scientific-notation exponent between -100 and 100")
    if parsed < 0 or (positive and parsed == 0):
        raise ValueError(f"{field} must be {'positive' if positive else 'nonnegative'}")
    return parsed if parsed else Decimal(0)


def currency_code(value: str) -> str:
    # Case can encode units: GBp denotes pence, while GBP denotes pounds.
    # Never uppercase an input currency and silently change its units.
    value = value.strip()
    if not re.fullmatch(r"[A-Z]{3}", value):
        raise ValueError("currency must be an uppercase three-letter major-unit code, such as USD")
    if value in {"GBX", "ZAC", "ILA"}:
        raise ValueError("minor-unit currency codes are unsupported; convert prices to major units and provide matching FX rates")
    return value


def timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO 8601 timestamp with a timezone offset") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} requires a timezone offset")
    return parsed.astimezone(timezone.utc)


def percentage(value: Decimal, total: Decimal) -> str | None:
    if not total:
        return None
    with localcontext() as context:
        context.prec = 50
        context.traps[Inexact] = False
        return decimal_text((value / total * 100).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN))


def build_snapshot(
    path: str | Path,
    base_currency: str,
    as_of: str | None = None,
    max_age_days: int = 3,
) -> dict:
    """Read the complete CSV, then return a validated valuation snapshot."""
    base = currency_code(base_currency)
    now = timestamp(as_of, "as_of") if as_of is not None else datetime.now(timezone.utc)
    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError("max_age_days must be a nonnegative integer")
    try:
        max_age = timedelta(days=max_age_days)
    except OverflowError as exc:
        raise ValueError("max_age_days is too large") from exc

    positions = []
    warnings = []
    seen = set()
    quote_times = set()
    exposure = {}
    fx_rates = {}
    total = Decimal(0)

    with Path(path).open(encoding="utf-8-sig", newline="") as handle, localcontext() as context:
        context.prec = 50
        context.traps[Inexact] = True
        reader = csv.DictReader(handle, strict=True)
        if not reader.fieldnames:
            raise ValueError("CSV is empty or missing its header")
        headers = [name.strip() for name in reader.fieldnames]
        if len(headers) != len(set(headers)):
            raise ValueError("CSV contains duplicate column names")
        if set(headers) != FIELDS:
            missing = ", ".join(sorted(FIELDS - set(headers))) or "none"
            extra = ", ".join(sorted(set(headers) - FIELDS)) or "none"
            raise ValueError(f"CSV columns do not match schema (missing: {missing}; unexpected: {extra})")
        reader.fieldnames = headers

        for row in reader:
            line = reader.line_num
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("row has an incorrect number of columns")
                row = {key: value.strip() for key, value in row.items()}
                symbol = row["symbol"].upper()
                if not symbol or len(symbol) > 128 or any(ord(char) < 32 for char in symbol):
                    raise ValueError("symbol must be a nonempty instrument identifier (maximum 128 characters)")
                currency = currency_code(row["currency"])
                identity = (symbol, currency)
                if identity in seen:
                    raise ValueError("duplicate symbol/currency; consolidate lots before analysis")
                seen.add(identity)
                quantity = number(row["quantity"], "quantity")
                price = number(row["price"], "price")
                quote_time = timestamp(row["price_as_of"], "price_as_of")
                if quote_time > now:
                    raise ValueError("price_as_of is later than the snapshot as_of")
                quote_times.add(quote_time)
                fx_text = row["fx_to_base"]
                fx = number(fx_text or ("1" if currency == base else ""), "fx_to_base", positive=True)
                if currency == base and fx != 1:
                    raise ValueError("fx_to_base must be 1 or blank for the base currency")
                fx_rates.setdefault(currency, set()).add(fx)
                value = quantity * price * fx
                total += value
                exposure[currency] = exposure.get(currency, Decimal(0)) + value
                positions.append({
                    "symbol": symbol,
                    "quantity": decimal_text(quantity),
                    "price": decimal_text(price),
                    "currency": currency,
                    "price_as_of": quote_time.isoformat(),
                    "fx_to_base": decimal_text(fx),
                    "value_base": decimal_text(value),
                })
                if now - quote_time > max_age:
                    warnings.append({"code": "stale_price", "symbol": symbol, "currency": currency,
                                     "message": "Price age exceeds max_age_days (calendar days)."})
                if quantity > 0 and price == 0:
                    warnings.append({"code": "zero_price", "symbol": symbol, "currency": currency,
                                     "message": "A positive holding has a zero price; check the supplied valuation."})
            except (ValueError, DecimalException) as exc:
                detail = str(exc) if isinstance(exc, ValueError) else "numeric calculation exceeds supported precision"
                raise ValueError(f"CSV line {line}: {detail}") from exc

    if not positions:
        raise ValueError("CSV contains no positions")
    if len(quote_times) > 1:
        warnings.append({"code": "mixed_price_times", "message": "Prices have different timestamps; this is not a synchronized market snapshot."})
    if any(currency != base for currency in exposure):
        warnings.append({"code": "fx_time_unverified", "message": "FX timestamps are not provided by this schema; rate freshness is unverified."})
    if any(len(rates) > 1 for rates in fx_rates.values()):
        warnings.append({"code": "mixed_fx_rates", "message": "The same quote currency has different supplied FX rates; check valuation consistency."})
    if not total:
        warnings.append({"code": "zero_total", "message": "Total value is zero; portfolio weights are undefined."})
    for position in positions:
        position["weight_pct"] = percentage(Decimal(position["value_base"]), total)

    return {
        "base_currency": base,
        "as_of": now.isoformat(),
        "max_age_days": max_age_days,
        "total_value_base": decimal_text(total),
        "positions": positions,
        "quote_currency_exposure": [
            {"currency": currency, "value_base": decimal_text(value), "weight_pct": percentage(value, total)}
            for currency, value in sorted(exposure.items())
        ],
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--base-currency", required=True, help="Uppercase major-unit reporting currency (e.g. USD); FX rates come from the CSV.")
    parser.add_argument("--as-of", help="Timezone-aware snapshot timestamp; defaults to current UTC time.")
    parser.add_argument("--max-age-days", type=int, default=3, help="Warn when prices are older than this many calendar days (default: 3).")
    args = parser.parse_args(argv)
    try:
        result = build_snapshot(args.input_csv, args.base_currency, args.as_of, args.max_age_days)
    except (OSError, UnicodeError, csv.Error, ValueError, DecimalException, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
