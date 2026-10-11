from src.marketplace_handoff import handoff_order


class FakeClient:
    def __init__(self):
        self.zone_id = None
        self.record = None

    def add_domain(self, request):
        assert request.domain == "shop.example.com"
        return {"ok": True, "data": {"zone_id": "zone-7"}}

    def upsert_record(self, request):
        self.zone_id = request.zone_id
        self.record = request
        return {"ok": True, "data": {"record_id": "record-1"}}

    def list_records(self, zone_id):
        assert zone_id == "zone-7"
        if self.record is None:
            return {"ok": True, "data": {"records": []}}
        return {"ok": True, "data": [{"name": "@", "content": self.record.content}]}


def test_order_handoff_writes_buyer_target_to_returned_zone():
    client = FakeClient()
    receipt = handoff_order(client, "shop.example.com", "203.0.113.10", "order-42")
    assert receipt == {
        "order_id": "order-42",
        "zone_id": "zone-7",
        "records": [{"name": "@", "content": "203.0.113.10"}],
    }
    assert client.record.metadata == {"order_id": "order-42"}


def test_order_handoff_reuses_existing_apex_a_record():
    class ExistingClient(FakeClient):
        def list_records(self, zone_id):
            if self.record is None:
                return {"data": {"records": [{"record_id": "record-1", "record_type": "A", "name": "shop.example.com", "content": "203.0.113.10"}]}}
            return super().list_records(zone_id)

    client = ExistingClient()
    handoff_order(client, "shop.example.com", "203.0.113.10", "order-42")
    assert client.record is None
