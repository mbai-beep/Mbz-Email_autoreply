import subprocess
import time
import sys

#If it crashes → restarts automatically
RESTART_DELAY = 5  # seconds


def run():
    while True:
        try:
            print("🚀 Starting Email Bot...")

            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=open("bot.log", "a"),
                stderr=open("error.log", "a")
            )

            process.wait()

            print("❌ Bot crashed! Restarting in 5 seconds...")

        except Exception as e:
            print(f"Wrapper error: {e}")

        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    run()