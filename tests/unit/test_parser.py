from holdings_monitor.sources.parsing import extract_record_from_cells, records_to_dataframe


def test_extract_record_from_cells_combined_code_and_name() -> None:
    row = ["2330 台積電", "4,873,000", "10.50%"]
    record = extract_record_from_cells(row)
    assert record is not None
    assert record["symbol"] == "2330"
    assert record["name"] == "台積電"
    assert record["weight_pct"] == "10.50%"


def test_records_to_dataframe_deduplicates_and_normalizes() -> None:
    frame = records_to_dataframe(
        [
            {
                "symbol": "2330",
                "name": "台積電",
                "holding_value": "4,873,000",
                "weight_pct": "10.50%",
            },
            {
                "symbol": "2330",
                "name": "台積電",
                "holding_value": "4,000,000",
                "weight_pct": "9.50%",
            },
            {
                "symbol": "2454",
                "name": "聯發科",
                "holding_value": "3,100,000",
                "weight_pct": "8.50%",
            },
            {
                "symbol": "2308",
                "name": "台達電",
                "holding_value": "2,100,000",
                "weight_pct": "5.50%",
            },
            {
                "symbol": "3711",
                "name": "日月光投控",
                "holding_value": "1,100,000",
                "weight_pct": "4.50%",
            },
            {"symbol": "2382", "name": "廣達", "holding_value": "1,000,000", "weight_pct": "3.50%"},
        ]
    )
    assert list(frame["symbol"]) == ["2330", "2454", "2308", "3711", "2382"]
    assert float(frame.iloc[0]["weight_pct"]) == 10.5
