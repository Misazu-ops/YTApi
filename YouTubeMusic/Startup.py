import httpx
from YouTubeMusic import __version__, __author__


PYPI_URL = "https://pypi.org/pypi/{}/json"


async def check_latest_version(pkg_name: str = "YouTubeMusic"):
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(PYPI_URL.format(pkg_name))
            if r.status_code == 200:
                return r.json().get("info", {}).get("version")
    except Exception:
        return None

    return None


async def get_startup_info():
    latest = await check_latest_version("YouTubeMusic")

    return {
        "current_version": __version__,
        "latest_version": latest,
        "author": __author__,
        "update_available": bool(latest and latest != __version__),
    }
