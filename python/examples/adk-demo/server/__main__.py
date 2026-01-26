# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
from pathlib import Path

import click
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette

# Local imports
from server.agents.routes import create_agent_routes

# Load .env file from project root (go up from server/ directory)
project_root = Path(__file__).parent.parent
dotenv_path = project_root / ".env"
print(f"DEBUG: Loading .env from: {dotenv_path}")
print(f"DEBUG: .env file exists: {dotenv_path.exists()}")
if dotenv_path.exists():
    with open(dotenv_path, 'r') as f:
        content = f.read()
        print(f"DEBUG: .env file content ({len(content)} bytes):")
        # Print each line to see what's in there
        for i, line in enumerate(content.split('\n'), 1):
            if 'OPENAI_API_KEY' in line:
                print(f"DEBUG: Line {i}: {line[:30]}... (length: {len(line)})")
load_dotenv(dotenv_path=dotenv_path)
print(f"DEBUG: After load_dotenv, OPENAI_API_KEY in os.environ: {'OPENAI_API_KEY' in os.environ}")
print(f"DEBUG: OPENAI_API_KEY value length: {len(os.getenv('OPENAI_API_KEY', ''))}")

logging.basicConfig(level=logging.INFO)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=10000)
def main(host: str, port: int):
    base_url = f"http://{host}:{port}"
    base_path = "/agents"
    routes = create_agent_routes(base_url=base_url, base_path=base_path)

    app = Starlette(routes=routes)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
