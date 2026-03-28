from __future__ import annotations

import hashlib
import io
import os
import re
from datetime import datetime
from typing import Any

import pandas as pd

from holdings_monitor.domain.models import HoldingRecord
from holdings_monitor.exceptions import ParseError
from holdings_monitor.time_utils import now_in_timezone

PARSER_VERSION = "2026.03.29"

IGNORE_NAME_KEYWORDS = {
    "持股權重",
    "股票代號",
    "證券代號",
    "股票名稱",
    "證券名稱",
    "名稱",
    "簡稱",
    "基金資產",
    "淨資產",
    "流通在外單位數",
    "每單位淨值",
    "查詢",
    "上傳時間",
    "申購買回清單",
    "說明",
    "友善列印",
    "匯出xlsx檔",
    "無資料",
    "項目",
    "金額",
    "權重",
    "比例",
    "比重",
    "股數",
    "數量",
}


def normalize_space(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_text(text: Any) -> str:
    return re.sub(r"\s+", "", str(text)).strip().lower()


def now_taipei() -> datetime:
    timezone_name = os.getenv("HOLDINGS_MONITOR_TIMEZONE", "Asia/Taipei")
    return now_in_timezone(timezone_name)


def parse_number(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None

    text = text.replace("NTD", "").replace("ntd", "")
    text = text.replace(",", "").replace("%", "").strip()
    text = re.sub(r"[^0-9\.\-]", "", text)

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def parse_possible_date(text: str) -> str | None:
    text = text.strip().replace(".", "/")
    sep = "-" if "-" in text else "/"
    parts = text.split(sep)
    if len(parts) != 3:
        return None
    try:
        year, month, day = map(int, parts)
    except ValueError:
        return None
    if year < 1911:
        year += 1911
    try:
        dt = datetime(year, month, day)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def extract_date_candidates_from_text(text: str) -> list[str]:
    matches = re.findall(r"\b(?:20\d{2}|1\d{2})[/-]\d{1,2}[/-]\d{1,2}\b", text)
    parsed = []
    for item in matches:
        candidate = parse_possible_date(item)
        if candidate:
            parsed.append(candidate)
    return parsed


def extract_snapshot_date_from_text(text: str) -> str:
    label_patterns = [
        r"(?:資料日期|淨值日期|上傳時間|更新日期)\s*[:：]\s*((?:20\d{2}|1\d{2})[/-]\d{1,2}[/-]\d{1,2})",
    ]
    for pattern in label_patterns:
        match = re.search(pattern, text)
        if match:
            candidate = parse_possible_date(match.group(1))
            if candidate:
                return candidate
    dates = extract_date_candidates_from_text(text)
    if dates:
        return max(dates)
    return now_taipei().strftime("%Y-%m-%d")


def is_code_text(text: str) -> bool:
    return bool(re.fullmatch(r"\d{4,6}", text.strip()))


def normalize_code(text: str) -> str | None:
    match = re.search(r"(\d{4,6})", str(text))
    return match.group(1) if match else None


def is_weight_text(text: str) -> bool:
    s = normalize_space(text)
    match = re.fullmatch(r"(\d{1,2}(?:\.\d+)?)\s*%", s)
    if not match:
        return False
    try:
        value = float(match.group(1))
    except ValueError:
        return False
    return 0 < value <= 100


def is_numeric_amount_text(text: str) -> bool:
    s = normalize_space(text)
    if "%" in s or "/" in s or "-" in s:
        return False
    value = parse_number(s)
    if value is None:
        return False
    return value > 0


def clean_name(text: str) -> str:
    return normalize_space(text).strip("|,;:：")


def is_name_text(text: str) -> bool:
    s = clean_name(text)
    if not s:
        return False
    if s in IGNORE_NAME_KEYWORDS:
        return False
    if "%" in s:
        return False
    if is_code_text(s):
        return False
    if not re.search(r"[A-Za-z一-鿿]", s):
        return False
    if len(s) > 40:
        return False
    return True


def split_code_name_from_text(text: str) -> tuple[str | None, str | None]:
    s = normalize_space(text)
    match = re.search(
        r"(\d{4,6})\s*[- ]\s*([A-Za-z一-鿿][A-Za-z0-9一-鿿\-\+\.\(\) /]{0,40})$",
        s,
    )
    if match:
        return match.group(1).strip(), clean_name(match.group(2))
    return None, None


def extract_record_from_cells(cells: list[str]) -> dict[str, Any] | None:
    cleaned = [
        normalize_space(cell)
        for cell in cells
        if normalize_space(cell) and normalize_text(cell) not in {"nan", "none"}
    ]
    if not cleaned:
        return None

    symbol = None
    name = None
    symbol_idx = None
    name_idx = None
    weight_text = None
    holding_value_text = None

    for idx, cell in enumerate(cleaned):
        code, maybe_name = split_code_name_from_text(cell)
        if code and maybe_name:
            symbol = code
            name = maybe_name
            symbol_idx = idx
            name_idx = idx
            break

    if symbol is None:
        for idx, cell in enumerate(cleaned):
            if is_code_text(cell):
                maybe_symbol = normalize_code(cell)
                maybe_name = None
                if idx + 1 < len(cleaned) and is_name_text(cleaned[idx + 1]):
                    maybe_name = clean_name(cleaned[idx + 1])
                if maybe_symbol and maybe_name:
                    symbol = maybe_symbol
                    name = maybe_name
                    symbol_idx = idx
                    name_idx = idx + 1
                    break

    if symbol is None:
        for idx, cell in enumerate(cleaned):
            if is_code_text(cell):
                symbol = normalize_code(cell)
                symbol_idx = idx
                break

    if symbol and not name:
        for idx, cell in enumerate(cleaned):
            if idx == symbol_idx:
                continue
            if is_name_text(cell):
                name = clean_name(cell)
                name_idx = idx
                break

    if not (symbol and name):
        return None

    excluded = {index for index in (symbol_idx, name_idx) if index is not None}
    remainder = [(idx, cleaned[idx]) for idx in range(len(cleaned)) if idx not in excluded]

    for _, cell in remainder:
        if weight_text is None and is_weight_text(cell):
            weight_text = cell

    amount_candidates: list[tuple[float, str]] = []
    for _, cell in remainder:
        if cell == weight_text:
            continue
        if is_numeric_amount_text(cell):
            value = parse_number(cell)
            if value is not None:
                amount_candidates.append((value, cell))

    if amount_candidates:
        amount_candidates.sort(reverse=True, key=lambda item: item[0])
        holding_value_text = amount_candidates[0][1]

    if not weight_text:
        return None

    return {
        "symbol": symbol,
        "name": name,
        "holding_value": holding_value_text,
        "weight_pct": weight_text,
    }


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        raise ParseError("no holdings extracted")

    frame = pd.DataFrame(records).copy()
    if "holding_value" not in frame.columns:
        frame["holding_value"] = None

    frame["symbol"] = frame["symbol"].astype(str).str.extract(r"(\d{4,6})", expand=False)
    frame["name"] = frame["name"].astype(str).map(clean_name)
    frame["holding_value"] = frame["holding_value"].apply(parse_number)
    frame["weight_pct"] = frame["weight_pct"].apply(parse_number)

    frame = frame[frame["symbol"].notna()]
    frame = frame[frame["name"].notna() & (frame["name"] != "")]
    frame = frame[
        ~frame["name"].str.contains("合計|總計|小計|基金資產|淨資產|每單位淨值", na=False)
    ]
    frame = frame[frame["weight_pct"].notna()]
    frame = frame[(frame["weight_pct"] > 0) & (frame["weight_pct"] <= 100)]
    frame = frame.sort_values(["symbol", "weight_pct"], ascending=[True, False])
    frame = frame.drop_duplicates(subset=["symbol"], keep="first")
    frame = frame.sort_values("weight_pct", ascending=False).reset_index(drop=True)

    if len(frame) < 5:
        raise ParseError(f"too few holdings extracted: {len(frame)}")

    return frame[["symbol", "name", "holding_value", "weight_pct"]].copy()


def extract_holdings_from_raw_dataframe(raw_df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in raw_df.iterrows():
        cells = []
        for value in row.tolist():
            string = normalize_space(value)
            if string and normalize_text(string) not in {"nan", "none"}:
                cells.append(string)
        if not cells:
            continue
        record = extract_record_from_cells(cells)
        if record:
            records.append(record)
            continue
        joined = " | ".join(cells)
        parts = [part.strip() for part in re.split(r"[|｜]", joined) if part.strip()]
        record = extract_record_from_cells(parts)
        if record:
            records.append(record)
    return records


def parse_holdings_excel(
    raw_bytes: bytes, currency: str = "TWD"
) -> tuple[str, list[HoldingRecord]]:
    excel_bytes = io.BytesIO(raw_bytes)
    try:
        sheets = pd.read_excel(
            excel_bytes,
            sheet_name=None,
            engine="openpyxl",
            header=None,
            dtype=str,
        )
    except Exception as exc:  # pragma: no cover - dependent on external file corruption
        raise ParseError(f"failed to load workbook: {exc}") from exc

    if not sheets:
        raise ParseError("workbook has no sheets")

    workbook_texts = []
    best_records: list[dict[str, Any]] = []
    for sheet_name, frame in sheets.items():
        workbook_texts.append(sheet_name)
        workbook_texts.append(frame.head(30).astype(str).to_string())
        records = extract_holdings_from_raw_dataframe(frame)
        if len(records) > len(best_records):
            best_records = records

    snapshot_date = extract_snapshot_date_from_text("\n".join(workbook_texts))
    frame = records_to_dataframe(best_records)

    holdings = [
        HoldingRecord(
            symbol=str(row.symbol),
            name=str(row.name),
            weight_pct=float(row.weight_pct),
            holding_value=None if pd.isna(row.holding_value) else float(row.holding_value),
            shares=None,
            currency=currency,
        )
        for row in frame.itertuples(index=False)
    ]
    return snapshot_date, holdings


def holdings_hash(holdings: list[HoldingRecord]) -> str:
    payload = (
        pd.DataFrame([item.to_dict() for item in holdings])
        .sort_values("symbol")
        .to_csv(index=False)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
