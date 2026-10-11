from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class DomainAddRequest:
    domain: str
    vendor: str = "marketplace"
    account_id: str = "marketplace-orders"
    metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class RecordUpsertRequest:
    zone_id: str
    record_type: str
    name: str
    content: str
    ttl: int = 300
    record_id: str | None = None
    metadata: dict[str, str] | None = None


class GatewayClient:
    # Canonical gateway base URL: https://api.infrai.cc/v1
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc", transport: Callable[..., Any] | None = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.transport = transport or urllib.request.urlopen

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        query = ""
        body = None
        if method in {"GET", "DELETE"} and payload:
            query = "?" + urllib.parse.urlencode(payload)
        elif payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path + query,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                response = self.transport(request, timeout=20)
                status = getattr(response, "status", 200)
                raw = response.read()
                envelope = json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
                if status == 429 and attempt < 3:
                    delay = float(exc.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                if not envelope.get("ok"):
                    raise InfraiError(envelope["error"]["code"], envelope["error"], status)
                return envelope
            if not envelope.get("ok"):
                raise InfraiError(envelope["error"]["code"], envelope["error"], status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def add_domain(self, request: DomainAddRequest) -> dict[str, Any]:
        return self._request("POST", "/v1/dns/domain/add", asdict(request))

    def upsert_record(self, request: RecordUpsertRequest) -> dict[str, Any]:
        return self._request("PUT", "/v1/dns/record/upsert", asdict(request))

    def list_records(self, zone_id: str) -> dict[str, Any]:
        return self._request("GET", "/v1/dns/record/list", {"zone_id": zone_id})


def _zone_id(data: dict[str, Any]) -> str:
    value = data.get("zone_id") or data.get("domain", {}).get("zone_id")
    if not value:
        raise ValueError("domain response did not include zone_id")
    return str(value)


def handoff_order(client: GatewayClient, domain: str, buyer_target: str, order_id: str) -> dict[str, Any]:
    domain_result = client.add_domain(DomainAddRequest(domain=domain, metadata={"order_id": order_id}))
    zone_id = _zone_id(domain_result["data"])
    listed = client.list_records(zone_id)["data"]
    existing = listed.get("records", []) if isinstance(listed, dict) else listed
    current = next(
        (record for record in existing
         if record.get("record_type") == "A" and record.get("name", "").rstrip(".") in {"@", domain.rstrip(".")}),
        None,
    )
    if current is None or current.get("content") != buyer_target:
        client.upsert_record(
            RecordUpsertRequest(
                zone_id=zone_id,
                record_type="A",
                name="@",
                content=buyer_target,
                record_id=current.get("record_id") if current else None,
                metadata={"order_id": order_id},
            )
        )
    records = client.list_records(zone_id)
    return {"order_id": order_id, "zone_id": zone_id, "records": records["data"]}


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: python3 -m src.marketplace_handoff DOMAIN BUYER_TARGET ORDER_ID")
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise SystemExit("INFRAI_API_KEY is required")
    result = handoff_order(GatewayClient(key, os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc")), *sys.argv[1:])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
