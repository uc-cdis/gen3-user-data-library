#!/usr/bin/sudo python
"""
This is a single Python entry-point for a simple run, intended to be used
for debugging.

In general, you should prefer the `run.sh` and `test.sh` scripts in this
directory for running the service and testing. But if you need to debug
the running service (from PyCharm, for example), this is a good
script to use (if you properly setup everything else external to this).

Specifically, this assumes you have properly migrated the database and have the needed
environment variables for prometheus (and another other setup done by the
bash scripts in this same directory).
"""
import uvicorn


def main():
    """
    Runs a local web app
    """
    host = "0.0.0.0"
    port = 8000
    print(f"gen3userdatalibrary.main:app_instance running at {host}:{port}")
    uvicorn.run("gen3userdatalibrary.main:app_instance", host=host, port=port, reload=True, log_config=None, )


if __name__ == "__main__":
    main()
