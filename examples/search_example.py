import asyncio
from YouTubeMusic.Search import Search, Trending, Suggest


async def main():
    print("1. Search Song")
    print("2. Trending Songs (Music)")
    print("3. Suggest Songs")
    choice = input("\nChoose option (1/2/3): ").strip()

    # ---------------- SEARCH ----------------
    if choice == "1":
        query = input("Enter song name: ")

        results = await Search(query, limit=1)

        if not results or not results.get("main_results"):
            print("No results found.")
            return

        item = results["main_results"][0]

        print("\nSearch Result")
        print("Title     :", item.get("title"))
        print("Channel   :", item.get("channel"))
        print("Views     :", item.get("views"))
        print("Duration  :", item.get("duration"))
        print("Thumbnail :", item.get("thumbnail"))
        print("URL       :", item.get("url"))

    # ---------------- TRENDING ----------------
    elif choice == "2":
        results = await Trending(limit=10)

        if not results:
            print("No trending songs found.")
            return

        print("\nTrending Music Songs:\n")

        for i, item in enumerate(results, start=1):
            print(f"{i}. {item.get('title')}")
            print("   Channel  :", item.get("channel"))
            print("   Views    :", item.get("views"))
            print("   Duration :", item.get("duration"))
            print("   URL      : https://www.youtube.com/watch?v=" + item.get("video_id"))
            print()

    # ---------------- SUGGEST ----------------
    elif choice == "3":
        query = input("Enter song name for suggestions: ")

        results = await Suggest(query, limit=5)

        if not results:
            print("No suggestions found.")
            return

        print("\nSuggested Songs:\n")

        for i, item in enumerate(results, start=1):
            print(f"{i}. {item.get('title')}")
            print("   Channel  :", item.get("channel"))
            print("   Views    :", item.get("views"))
            print("   Duration :", item.get("duration"))
            print("   URL      : https://www.youtube.com/watch?v=" + item.get("video_id"))
            print()

    else:
        print("Invalid option.")


if __name__ == "__main__":
    asyncio.run(main())
