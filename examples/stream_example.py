import asyncio
import os
from YouTubeMusic.Stream import get_stream, get_video_stream


async def main():
    url = input("Enter YouTube video URL: ").strip()

    if not url:
        print("URL is required.")
        return

    stream_type = input("Choose type (audio/video): ").strip().lower()

    if stream_type not in ("audio", "video"):
        print("Invalid type. Choose 'audio' or 'video'.")
        return

    use_cookies = input("Use cookies? (y/n): ").strip().lower() == "y"

    cookies_path = None
    if use_cookies:
        cookies_path = input("Enter cookies.txt path: ").strip()

        if not cookies_path or not os.path.exists(cookies_path):
            print("Invalid cookies path.")
            return

    print("\nExtracting stream...")

    if stream_type == "audio":
        stream_url = await get_stream(url, cookies_path)
    else:
        stream_url = await get_video_stream(url, cookies_path)

    if stream_url:
        print("\nStream URL:")
        print(stream_url)
    else:
        print("Failed to extract stream URL.")


if __name__ == "__main__":
    asyncio.run(main())
