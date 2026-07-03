# Copyright (c) Microsoft. All rights reserved.

"""Start the Microsoft Agents host with the LangChain agent."""

import sys

try:
    from agent import LangChainAgent
    from host_agent_server import create_and_run_host
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the correct directory")
    sys.exit(1)


def main():
    """Start the host with LangChainAgent."""
    try:
        print("Starting Microsoft Agents host with LangChainAgent...")
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
