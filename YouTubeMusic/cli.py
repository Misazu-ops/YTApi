import asyncio
import argparse
import os

from YouTubeMusic import (
    Search,
    get_stream,
    __version__,
    __author__,
)
from YouTubeMusic.Update import check_for_update


async def run_search(query: str, fetch_stream: bool = False, cookies: str | None = None):
    update_info = await check_for_update()

    if update_info and update_info.get("update_available"):
        print(f"Update available: {update_info['latest_version']}")
        print(f"Current version: {update_info['current_version']}")
        print("Run: pip install --upgrade YouTubeMusic\n")

    results = await Search(query, limit=1)

    if not results or not results.get("main_results"):
        print("No results found.")
        return

    item = results["main_results"][0]

    print("\nResult")
    print("Title     :", item.get("title"))
    print("Channel   :", item.get("channel"))
    print("Views     :", item.get("views"))
    print("Duration  :", item.get("duration"))
    print("Thumbnail :", item.get("thumbnail"))
    print("URL       :", item.get("url"))

    if fetch_stream:
        if not cookies:
            print("\nCookies path not provided.")
            print("Provide --cookies <path> to extract stream URL.")
            return

        if not os.path.exists(cookies):
            print("\nCookies path not found.")
            print("Provide valid --cookies <path> to extract stream URL.")
            return

        print("\nExtracting audio stream...")
        stream_url = await get_stream(item.get("url"), cookies)

        if stream_url:
            print("Stream URL :", stream_url)
        else:
            print("Failed to extract stream URL.")


def cli():
    parser = argparse.ArgumentParser(prog="YouTubeMusic")

    parser.add_argument(
        "query",
        nargs="*",
        help="Search query or YouTube URL",
    )

    parser.add_argument(
        "--stream",
        action="store_true",
        help="Extract direct audio stream URL (requires cookies)",
    )

    parser.add_argument(
        "--cookies",
        type=str,
        help="Path to cookies.txt file",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"YouTubeMusic {__version__}",
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Show package information",
    )

    args = parser.parse_args()

    if args.info:
        print("Package  : YouTubeMusic")
        print("Version  :", __version__)
        print("Author   :", __author__)
        return

    if not args.query:
        print("Please provide a search query.")
        return

    query = " ".join(args.query)

    asyncio.run(
        run_search(
            query=query,
            fetch_stream=args.stream,
            cookies=args.cookies,
        )
    )


if __name__ == "__main__":
    cli()
