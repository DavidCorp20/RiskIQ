from app.data.persistence import PortfolioPersistenceService


class FakeRepository:
    def __init__(self):
        self.rows = []

    def insert(self, row):
        self.rows.append(row)
        return str(len(self.rows))


def test_save_batch_uses_named_collection():
    service = PortfolioPersistenceService.__new__(PortfolioPersistenceService)
    service.loans = FakeRepository()
    count = service.save_batch("loans", [{"loan_id": "L1"}, {"loan_id": "L2"}])
    assert count == 2
    assert len(service.loans.rows) == 2


def test_save_batch_rejects_unknown_collection():
    service = PortfolioPersistenceService.__new__(PortfolioPersistenceService)
    try:
        service.save_batch("unknown", [{"x": 1}])
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
