import aiohttp


class ProfileServiceError(RuntimeError):
    pass


class ProfileServiceClient:
    def __init__(self, *, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def get_hh_token(self, account_id: str, user_id: str, refresh: bool = True) -> str:
        params = {"refresh": "true" if refresh else "false"}
        url = f"{self.base_url}/internal/hh/hh-token/{account_id}"
        headers = {"X-User-Id": user_id}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 401:
                        raise ProfileServiceError("hh_token_refresh_failed")
                    if response.status == 404:
                        raise ProfileServiceError("account_not_found")
                    if response.status != 200:
                        raise ProfileServiceError(f"unexpected status {response.status}")
                    payload = await response.json()
                    return payload["access_token"]
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ProfileServiceError(f"connection error: {type(exc).__name__}") from exc
