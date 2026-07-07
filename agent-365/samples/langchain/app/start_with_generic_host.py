"""Starts the generic host with the LangChain agent implementation."""

import sys

try:
    from agent import LangChainAgent
    from host_agent_server import create_and_run_host
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the correct directory")
    sys.exit(1)


def main():
    """Start the generic host and return the process exit code."""
    try:
        print("Starting Generic Agent Host with LangChainAgent...")
        print()

        create_and_run_host(LangChainAgent)

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
