#!/usr/bin/sudo python
"""
Usage:
- Run app: poetry run python run.py
"""
import uvicorn


def main():
    """
    Runs a local web app
    """
    host = "0.0.0.0"
    port = 8087
    print(f"gen3datalibrary.main:app running at {host}:{port}")
    uvicorn.run(
        "gen3datalibrary.main:app",
        host=host,
        port=port,
        reload=True,
        log_config=None,
    )


if __name__ == "__main__":
    main()
