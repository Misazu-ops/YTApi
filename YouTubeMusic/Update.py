import importlib.metadata
import httpx


PYPI_URL = "https://pypi.org/pypi/{}/json"


async def check_for_update(package_name: str = "YouTubeMusic"):
    try:
        current_version = importlib.metadata.version(package_name)

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(PYPI_URL.format(package_name))
            resp.raise_for_status()
            latest_version = resp.json().get("info", {}).get("version")

        if not latest_version:
            return None

        return {
            "package": package_name,
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": current_version != latest_version,
        }

    except Exception:
        return None
