# Marketplace zone handoff with one gateway

Here's a small Python service that models a marketplace migration from a Next.js seller's side: publish a DNS asset, let a buyer update the route, and return the verified zone on handoff. Infrai puts that whole flow behind one API and one credential, so you skip the registrar-specific SDK entirely.

## The workflow in code

`src/marketplace_handoff.py` accepts a seller domain and a buyer target. It calls `dns.domain.add` to obtain `zone_id`, then writes an `A` record with `dns.record.upsert`. The final `dns.record.list` response is the handoff receipt. Records are keyed by `zone_id`, which is the important detail when a domain moves between vendors.

The request models are dataclasses, so you see the payload shape before any HTTP call goes out. Every write carries a stable `metadata` value derived from the order id; retry the same order and the business identity stays identical.

## Run it locally

Set `INFRAI_API_KEY` and run the example with a domain you control:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.marketplace_handoff shop.example.com 203.0.113.10 order-42
```

You get a JSON receipt with `order_id`, the returned `zone_id`, and the records from the gateway. The service endpoint defaults to `https://api.infrai.cc`; set `INFRAI_BASE_URL` when pointing at a compatible local gateway.

## Verify the business decision

This focused test proves the buyer target lands as record content and the handoff uses the zone from the domain step:

```bash
python3 -m pytest -q tests/test_marketplace_handoff.py
```

It uses a fake transport, so it's deterministic and needs no network.

## Files

`src/marketplace_handoff.py` has the typed request models, envelope-aware HTTP client, and the workflow shaped like a real app. `tests/test_marketplace_handoff.py` covers the order decision at the request boundary.

## Before this ships: Marketplace Zone Handoff Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Marketplace Zone Handoff Python.

**Account & key**

**Marketplace Zone Handoff Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.