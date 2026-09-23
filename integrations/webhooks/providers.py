"""HTTP client for a provider's REST API: OAuth token refresh, retries with backoff, Retry-After.

Used by the reconciliation job to fetch the provider's view of orders.
"""

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger("webhooks")

RETRYABLE = {429, 500, 502, 503, 504}


class ProviderError(Exception):
    pass


@dataclass
class ProviderOrder:
    order_id: str
    payment_status: str
    amount_paise: int


class ProviderClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str, *, transport: httpx.BaseTransport | None = None,
                 max_retries: int = 4, backoff_s: float = 0.5, sleep=time.sleep):
        self.http = httpx.Client(base_url=base_url, transport=transport, timeout=15)
        self.client_id, self.client_secret = client_id, client_secret
        self.max_retries, self.backoff_s, self.sleep = max_retries, backoff_s, sleep
        self._token: str | None = None

    def _refresh_token(self) -> None:
        r = self.http.post("/oauth/token", data={"grant_type": "client_credentials",
                                                 "client_id": self.client_id, "client_secret": self.client_secret})
        if r.status_code != 200:
            raise ProviderError(f"Token refresh failed: HTTP {r.status_code}")
        self._token = r.json()["access_token"]

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._token is None:
            self._refresh_token()
        refreshed = False
        for attempt in range(self.max_retries + 1):
            try:
                r = self.http.request(method, url, headers={"Authorization": f"Bearer {self._token}"}, **kwargs)
            except httpx.TransportError as e:  # timeouts, connection resets
                if attempt == self.max_retries:
                    raise ProviderError(f"Network error after {attempt + 1} attempts: {e}") from e
                self.sleep(self.backoff_s * 2 ** attempt)
                continue
            if r.status_code == 401 and not refreshed:  # expired token: refresh once, then retry
                log.info("Provider token expired; refreshing")
                self._refresh_token()
                refreshed = True
                continue
            if r.status_code in RETRYABLE and attempt < self.max_retries:
                wait = float(r.headers.get("Retry-After", self.backoff_s * 2 ** attempt))
                log.warning("Provider returned %s; retrying in %.1fs", r.status_code, wait)
                self.sleep(wait)
                continue
            if r.status_code >= 400:
                raise ProviderError(f"{method} {url} failed: HTTP {r.status_code}")
            return r
        raise ProviderError(f"{method} {url} failed after {self.max_retries + 1} attempts")

    def list_orders(self, since: str) -> list[ProviderOrder]:
        orders, page = [], 1
        while True:
            data = self.request("GET", "/v1/orders", params={"updated_since": since, "page": page}).json()
            orders += [ProviderOrder(o["order_id"], o["payment_status"], int(o["amount_paise"])) for o in data["items"]]
            if not data.get("has_more"):
                return orders
            page += 1
