from app.data.discovery import DataDiscoveryService


def test_discovery_maps_common_credit_columns():
    rows = [
        {"Cliente": "C001", "Credito": "L001", "Saldo": 1000, "Dias_Mora": 12, "Segmento": "A"},
        {"Cliente": "C002", "Credito": "L002", "Saldo": 500, "Dias_Mora": 0, "Segmento": "B"},
    ]

    result = DataDiscoveryService().discover(rows)
    mappings = {item["source"]: item["target"] for item in result["mapping_suggestions"]}

    assert result["row_count"] == 2
    assert mappings["Cliente"] == "customer_id"
    assert mappings["Credito"] == "loan_id"
    assert mappings["Saldo"] == "outstanding_principal"
    assert mappings["Dias_Mora"] == "dpd"
    assert result["coverage_score"] > 0


def test_discovery_warns_when_required_fields_are_missing():
    result = DataDiscoveryService().discover([{"Saldo": 1000, "Estado": "active"}])

    assert "customer_id" in result["warnings"][0]
    assert "loan_id" in result["warnings"][0]
