#!/usr/bin/env python3
"""
Environment Setup Script for Metabolic Health Data Analysis App

This script helps you set up the necessary environment variables for the application
and stores them in a .env file.
"""

import os
import sys
import subprocess
from pathlib import Path
import re


def print_header():
    """Print header text"""
    print("\n" + "=" * 70)
    print("  METABOLIC HEALTH DATA ANALYSIS - ENVIRONMENT SETUP")
    print("=" * 70 + "\n")


def setup_openai_key():
    """Set up the OpenAI API key environment variable and store in .env file"""
    print("Setting up OpenAI API key for the AI Assistant\n")

    # Check if environment variable is already set
    current_key = os.environ.get("OPENAI_API_KEY")

    # Check if .env file exists and contains API key
    env_file = Path(".env")
    env_key = None

    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()
            match = re.search(r'OPENAI_API_KEY="?([^"\n]+)"?', content)
            if match:
                env_key = match.group(1)
                if (
                    not current_key
                ):  # Set env var if only in file but not in environment
                    os.environ["OPENAI_API_KEY"] = env_key
                    current_key = env_key
                print(f"Found API key in .env file (ending with ...{env_key[-4:]})")

    if current_key:
        print(f"OpenAI API key is currently set (ending with ...{current_key[-4:]})")
        change = input("Would you like to change it? (y/n): ").lower()
        if change != "y":
            return

    # Get API key from user
    api_key = input("\nEnter your OpenAI API key: ").strip()

    if not api_key:
        print("\nNo API key provided. Skipping setup.")
        return

    # Set for current session
    os.environ["OPENAI_API_KEY"] = api_key

    # Save to .env file
    try:
        # Check if .env exists and read its content
        env_content = ""
        if env_file.exists():
            with open(env_file, "r") as f:
                env_content = f.read()

        # Update or add OPENAI_API_KEY
        if "OPENAI_API_KEY" in env_content:
            env_content = re.sub(
                r'OPENAI_API_KEY="?[^"\n]+"?',
                f'OPENAI_API_KEY="{api_key}"',
                env_content,
            )
        else:
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f'OPENAI_API_KEY="{api_key}"\n'

        # Write back to .env file
        with open(env_file, "w") as f:
            f.write(env_content)

        print("\nAPI key has been saved to .env file and set for the current session.")

        # Create .gitignore if it doesn't exist or update it
        gitignore_file = Path(".gitignore")
        if not gitignore_file.exists():
            with open(gitignore_file, "w") as f:
                f.write(".env\n")
            print("Created .gitignore file to protect your API key.")
        else:
            with open(gitignore_file, "r") as f:
                gitignore_content = f.read()

            if ".env" not in gitignore_content:
                with open(gitignore_file, "a") as f:
                    if not gitignore_content.endswith("\n"):
                        f.write("\n")
                    f.write(".env\n")
                print("Updated .gitignore file to protect your API key.")
            else:
                print(".gitignore already contains .env entry.")

    except Exception as e:
        print(f"\nError saving API key to .env file: {e}")
        print("Your API key is set for the current session only.")


def run_application():
    """Ask if user wants to run the application"""
    run_app = input("\nWould you like to run the application now? (y/n): ").lower()
    if run_app == "y":
        print("\nStarting the application...\n")
        try:
            subprocess.run([sys.executable, "run.py"])
        except Exception as e:
            print(f"Error running application: {e}")
    else:
        print("\nYou can run the application later using: python run.py")


def main():
    """Main function"""
    print_header()
    setup_openai_key()
    run_application()
    print("\nSetup complete!\n")


if __name__ == "__main__":
    main()
