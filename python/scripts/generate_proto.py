"""Generate Python protobuf stubs from .proto definition."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from grpc_tools import protoc


def generate() -> None:
    python_root = Path(__file__).resolve().parent.parent
    project_root = python_root.parent
    proto_path = project_root / "proto"
    output_path = python_root / "agent" / "grpc_generated"

    # Ensure output dir exists and is importable
    output_path.mkdir(parents=True, exist_ok=True)
    init_file = output_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    cmd = [
        "grpc_tools.protoc",
        f"--proto_path={proto_path}",
        f"--python_out={output_path}",
        f"--grpc_python_out={output_path}",
        str(proto_path / "agent.proto"),
    ]
    ret = protoc.main(cmd)
    if ret != 0:
        print(f"[ERROR] protoc failed with return code {ret}")
        sys.exit(1)
    grpc_stub = output_path / "agent_pb2_grpc.py"
    grpc_stub.write_text(
        grpc_stub.read_text(encoding="utf-8").replace(
            "import agent_pb2 as agent__pb2",
            "from . import agent_pb2 as agent__pb2",
        ),
        encoding="utf-8",
    )
    print(f"[OK] Generated *_pb2.py and *_pb2_grpc.py in {output_path}")


if __name__ == "__main__":
    generate()
