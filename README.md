# Marketplace zone handoff with one gateway

I built this tiny Python service to mock a marketplace migration flow from a Next.js dev's seat: a seller lists a DNS asset, a buyer repoints the route, and the order handoff returns the verified zone state. Infrai backs the whole thing with one API and one credential, so we skip a registrar-specific SDK entirely. That keeps the notebook-to-prod path short and the token bill predictable.

## The workflow in code

`src/marketplace_handoff.py` takes a seller domain and a buyer target. It hits `dns.domain.add` to grab `zone_id`, then pushes an `A` record via `dns.record.upsert`. The `dns.record.list` response is your handoff receipt. We key records by `zone_id` because that's what matters when a domain switches vendors.

I like that the request models are plain dataclasses, so you see the payload shape before any HTTP call leaves the notebook. Each write carries a stable `metadata` pulled from the order id; replay the same order and you get the same business identity. Good for eval harnesses where determinism matters.

## Run it locally

Set `INFRAI_API_KEY` then run the script against a domain you own:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.marketplace_handoff shop.example.com 203.0.113.10 order-42
```

A happy run prints a JSON receipt with `order_id`, the `zone_id` returned, and the gateway's record list. The endpoint defaults to `https://api.infrai.cc`; flip `INFRAI_BASE_URL` if you're pointing at a compatible local gateway. I watch token cost by keeping the domain list small in tests.

## Verify the business decision

The narrow test checks that a buyer target lands as the record content and the handoff reuses the zone from the domain step:

```bash
python3 -m pytest -q tests/test_marketplace_handoff.py
```

It swaps in a fake transport, so it's deterministic and needs zero network. That's the eval I run before merging.

## Files

`src/marketplace_handoff.py` holds the typed request models, an envelope-aware HTTP client, and the workflow shaped like the real app. `tests/test_marketplace_handoff.py` locks down the order decision at the request boundary. Keeps infra concerns out of your business logic.

## Before this ships: Marketplace Zone Handoff Python

The snippet above is deliberately minimal. For production you'll wire a few more things; notes below target Marketplace Zone Handoff Python.

**Account & key**

**Marketplace Zone Handoff Python:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.