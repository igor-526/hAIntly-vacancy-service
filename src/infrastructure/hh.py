import asyncio
from typing import Any

import aiohttp
from pydantic import ValidationError

from infrastructure.hh_schemas import (
    Area,
    AreaList,
    Dictionaries,
    IndustryList,
    MetroCities,
    MetroCity,
    NamedList,
    ProfessionalRoles,
)


class HHError(RuntimeError):
    pass


class HHClient:
    ALLOWED = {
        "/dictionaries",
        "/areas",
        "/areas/countries",
        "/professional_roles",
        "/industries",
        "/metro",
        "/languages",
    }

    def __init__(
        self, *, base_url: str, user_agent: str, app_token: str, timeout: float, retries: int, backoff: float
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"HH-User-Agent": user_agent}
        self.app_token = app_token
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.retries = retries
        self.backoff = backoff

    async def get(self, path: str) -> Any:
        if path not in self.ALLOWED and not path.startswith(("/areas/", "/metro/")):
            raise ValueError("Неподдерживаемая HH-операция")
        for attempt in range(self.retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                    async with session.get(self.base_url + path) as response:
                        if response.status == 429 or response.status >= 500:
                            raise HHError(f"temporary status {response.status}")
                        if response.status != 200:
                            raise HHError(f"unexpected status {response.status}")
                        payload = await response.json()
                        if not isinstance(payload, (list, dict)) or not payload:
                            raise HHError("empty or structurally invalid payload")
                        return payload
            except (aiohttp.ClientError, TimeoutError, HHError) as exc:
                if attempt >= self.retries or (isinstance(exc, HHError) and "unexpected" in str(exc)):
                    raise HHError(type(exc).__name__) from exc
                await asyncio.sleep(self.backoff * (2**attempt))
        raise AssertionError

    async def _validated(self, path: str, schema):
        try:
            return schema.model_validate(await self.get(path)).model_dump()
        except ValidationError as exc:
            raise HHError("invalid payload") from exc

    async def dictionaries(self):
        return await self._validated("/dictionaries", Dictionaries)

    async def areas(self):
        return await self._validated("/areas", AreaList)

    async def area(self, area_id: str):
        return await self._validated(f"/areas/{area_id}", Area)

    async def countries(self):
        return await self._validated("/areas/countries", NamedList)

    async def professional_roles(self):
        return await self._validated("/professional_roles", ProfessionalRoles)

    async def industries(self):
        return await self._validated("/industries", IndustryList)

    async def metro(self):
        return await self._validated("/metro", MetroCities)

    async def metro_city(self, city_id: str):
        return await self._validated(f"/metro/{city_id}", MetroCity)

    async def languages(self):
        return await self._validated("/languages", NamedList)

    async def _get_authed(self, path: str, params: dict[str, Any] | None, access_token: str) -> Any:
        headers = {**self.headers, "Authorization": f"Bearer {access_token}"}
        for attempt in range(self.retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
                    async with session.get(self.base_url + path, params=params) as response:
                        if response.status == 429 or response.status >= 500:
                            raise HHError(f"temporary status {response.status}")
                        if response.status == 401:
                            raise HHError("authorization failed")
                        if response.status != 200:
                            raise HHError(f"unexpected status {response.status}")
                        return await response.json()
            except (aiohttp.ClientError, TimeoutError, HHError) as exc:
                if attempt >= self.retries or (isinstance(exc, HHError) and "unexpected" in str(exc)):
                    raise HHError(str(exc)) from exc
                await asyncio.sleep(self.backoff * (2**attempt))
        raise AssertionError

    async def search_vacancies(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get_authed("/vacancies", params, self.app_token)

    async def get_vacancy(self, vacancy_id: str) -> dict[str, Any]:
        return await self._get_authed(f"/vacancies/{vacancy_id}", None, self.app_token)
