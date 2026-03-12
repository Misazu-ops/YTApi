import asyncio
from YouTubeMusic.Playlist import get_playlist_songs


async def main():
    playlist_url = input("Enter playlist URL or ID: ")

    songs = await get_playlist_songs(playlist_url)

    if not songs:
        print("No songs found.")
        return

    print(f"\nFound {len(songs)} songs.\n")

    for i, song in enumerate(songs[:5], start=1):
        print(f"{i}. {song.get('title')}")
        print("   Channel :", song.get("channel"))
        print("   Duration:", song.get("duration"))
        print("   URL     :", song.get("url"))
        print()


if __name__ == "__main__":
    asyncio.run(main())
