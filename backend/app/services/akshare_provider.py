from __future__ import annotations

import socket
from datetime import datetime
from typing import Any

import pandas as pd

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS


class ProviderError(RuntimeError):
    pass


class AkshareProvider:
    name = "akshare"

    def __init__(self, timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def _ak(self) -> Any:
        try:
            import akshare as ak
        except ImportError as exc:
            raise ProviderError("AKShare is not installed") from exc
        return ak

    def get_spot_table(self) -> pd.DataFrame:
        ak = self._ak()
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            return ak.stock_zh_a_spot_em()
        except Exception as exc:
            raise ProviderError(f"AKShare spot query failed: {exc}") from exc

    def get_stock_summary(self, code: str) -> dict[str, Any]:
        spot_df = self.get_spot_table()
        code_column = _first_existing_column(spot_df, ["代码", "证券代码", "code"])
        if code_column is None:
            raise ProviderError("AKShare spot table missing code column")

        match = spot_df.loc[spot_df[code_column].astype(str) == code]
        if match.empty:
            raise ProviderError(f"Stock code {code} not found in spot table")

        row = match.iloc[0].to_dict()
        return {
            "code": code,
            "name": _value_any(row, ["名称", "股票名称", "证券简称", "name"]),
            "latest_price": _number_any(row, ["最新价", "最新价格", "收盘", "price"]),
            "change_pct": _number_any(row, ["涨跌幅", "涨跌幅(%)", "change_pct"]),
            "pe_ttm": _number_any(row, ["市盈率-动态", "动态市盈率", "市盈率", "PE(TTM)", "pe_ttm"]),
            "pb": _number_any(row, ["市净率", "PB", "pb"]),
            "market_cap": _number_any(row, ["总市值", "market_cap"]),
            "float_market_cap": _number_any(row, ["流通市值", "float_market_cap"]),
            "data_time": datetime.now().astimezone().isoformat(),
            "source": self.name,
            "raw_fields": {str(key): _jsonable(value) for key, value in row.items()},
        }

    def get_kline(
        self,
        code: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        ak = self._ak()
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            df = ak.stock_zh_a_hist(
                symbol=code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception as exc:
            raise ProviderError(f"AKShare kline query failed: {exc}") from exc

        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            rows.append(
                {
                    "date": _value_any(raw, ["日期", "date"]),
                    "open": _number_any(raw, ["开盘", "open"]),
                    "close": _number_any(raw, ["收盘", "close"]),
                    "high": _number_any(raw, ["最高", "high"]),
                    "low": _number_any(raw, ["最低", "low"]),
                    "volume": _number_any(raw, ["成交量", "volume"]),
                    "amount": _number_any(raw, ["成交额", "amount"]),
                    "change_pct": _number_any(raw, ["涨跌幅", "涨跌幅(%)", "change_pct"]),
                }
            )
        return [row for row in rows if row["date"]]

    def get_financial_indicators(self, code: str) -> list[dict[str, Any]]:
        ak = self._ak()
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            df = ak.stock_financial_analysis_indicator(symbol=code)
        except Exception as exc:
            raise ProviderError(f"AKShare financial indicator query failed: {exc}") from exc

        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            rows.append(
                {
                    "report_date": _value_any(raw, ["日期", "报告期", "报表日期", "公告日期", "date"]),
                    "revenue": _number_any(raw, ["营业收入", "营业总收入", "主营业务收入", "revenue"]),
                    "net_profit": _number_any(raw, ["净利润", "归属于母公司所有者的净利润", "归母净利润", "扣非净利润", "net_profit"]),
                    "roe": _number_any(raw, ["净资产收益率(%)", "加权净资产收益率(%)", "净资产收益率", "ROE", "roe"]),
                    "gross_margin": _number_any(raw, ["销售毛利率(%)", "毛利率", "销售毛利率", "gross_margin"]),
                    "debt_ratio": _number_any(raw, ["资产负债率(%)", "资产负债率", "debt_ratio"]),
                    "raw_fields": {str(key): _jsonable(value) for key, value in raw.items()},
                }
            )
        return [row for row in rows if row["report_date"]]

    def get_concept_boards(self) -> pd.DataFrame:
        ak = self._ak()
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            return ak.stock_board_concept_name_em()
        except Exception as exc:
            raise ProviderError(f"AKShare concept board query failed: {exc}") from exc

    def get_concept_constituents(self, board_name: str) -> pd.DataFrame:
        ak = self._ak()
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            return ak.stock_board_concept_cons_em(symbol=board_name)
        except Exception as exc:
            raise ProviderError(f"AKShare concept constituent query failed: {exc}") from exc

    def find_concept_boards(self, keywords: list[str], limit: int = 3) -> list[str]:
        boards = self.get_concept_boards()
        name_column = _first_existing_column(boards, ["板块名称", "名称", "概念名称"])
        if name_column is None:
            raise ProviderError("AKShare concept board table missing name column")

        scored: list[tuple[int, str]] = []
        for _, row in boards.iterrows():
            board_name = _value(row.to_dict(), name_column)
            if not board_name:
                continue
            score = _keyword_score(board_name, keywords)
            if score > 0:
                scored.append((score, board_name))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in scored[:limit]]

    def get_ranked_concept_candidates(
        self,
        keywords: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        board_names = self.find_concept_boards(keywords, limit=3)
        if not board_names:
            return []

        by_code: dict[str, dict[str, Any]] = {}
        for board_name in board_names:
            constituents = self.get_concept_constituents(board_name)
            for _, row in constituents.iterrows():
                raw = row.to_dict()
                code = _value_any(raw, ["代码", "证券代码", "code"])
                name = _value_any(raw, ["名称", "股票名称", "证券简称", "name"])
                if not code or not name:
                    continue
                score = _number_any(raw, ["总市值", "流通市值", "market_cap", "float_market_cap"]) or 0
                existing = by_code.get(code)
                if existing is None or score > existing["rank_value"]:
                    by_code[code] = {
                        "code": code,
                        "name": name,
                        "board_name": board_name,
                        "market_cap": _number_any(raw, ["总市值", "market_cap"]),
                        "float_market_cap": _number_any(raw, ["流通市值", "float_market_cap"]),
                        "pe_ttm": _number_any(raw, ["市盈率-动态", "动态市盈率", "市盈率", "PE(TTM)", "pe_ttm"]),
                        "change_pct": _number_any(raw, ["涨跌幅", "涨跌幅(%)", "change_pct"]),
                        "rank_value": score,
                    }

        ranked = sorted(
            by_code.values(),
            key=lambda item: (item["rank_value"] is None, -(item["rank_value"] or 0), item["code"]),
        )
        return ranked[:limit]


def _value(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None or pd.isna(value) or value == "-":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _value_any(row: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = _value(row, key)
        if value is not None:
            return value
    return None


def _number_any(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _number(row, key)
        if value is not None:
            return value
    return None


def _jsonable(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _keyword_score(text: str, keywords: list[str]) -> int:
    normalized_text = text.lower()
    score = 0
    for index, keyword in enumerate(keywords):
        normalized_keyword = str(keyword).strip().lower()
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_text or normalized_text in normalized_keyword:
            score += 100 - index
            continue
        for token in _keyword_tokens(normalized_keyword):
            if token and token in normalized_text:
                score += 10
    return score


def _keyword_tokens(keyword: str) -> list[str]:
    separators = [" ", "/", "、", ",", "，", "-", "_"]
    tokens = [keyword]
    for separator in separators:
        next_tokens: list[str] = []
        for token in tokens:
            next_tokens.extend(token.split(separator))
        tokens = next_tokens
    return [token.strip() for token in tokens if len(token.strip()) >= 2]
