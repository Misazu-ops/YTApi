import multiprocessing
import time
import sys
from bot import run_bot
from api import run_api

def main():
    bot_process = multiprocessing.Process(target=run_bot)
    api_process = multiprocessing.Process(target=run_api)
    bot_process.start()
    api_process.start()
    print("Bot and API started in parallel.")
    try:
        while True:
            time.sleep(1)
            if not bot_process.is_alive():
                print("Bot process stopped.")
                break
            if not api_process.is_alive():
                print("API process stopped.")
                break
    except KeyboardInterrupt:
        print("Shutting down...")
        bot_process.terminate()
        api_process.terminate()
        bot_process.join()
        api_process.join()
        sys.exit(0)

if __name__ == "__main__":
    main()
