"""FastAPI wrapper around the demo service, plus the static page."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from t2lgepa.webapp.service import DemoService

STATIC = Path(__file__).resolve().parent / "static"


class CompareRequest(BaseModel):
    task: str
    question: str = ""
    options: list[str] = Field(default_factory=list)
    passage: str | None = None
    example_id: str | None = None


def create_app(service: DemoService, results_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Mistral adaptation demo")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/meta")
    def meta() -> dict:
        return service.meta()

    @app.get("/api/sample")
    def sample(task: str) -> dict:
        try:
            return service.sample(task)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/compare")
    def compare(request: CompareRequest) -> dict:
        try:
            return service.compare(
                request.task, request.question, request.options,
                request.passage, request.example_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/results")
    def results() -> dict:
        from t2lgepa.analysis import accuracy_table, cost_table
        from t2lgepa.tables import collect

        directory = Path(results_dir) if results_dir is not None else service.results_dir
        accuracy, cost = collect(directory)
        return {
            "accuracy_md": accuracy_table(accuracy) if accuracy else "",
            "cost_md": cost_table(cost) if cost else "",
        }

    return app


def build(cfg_path: str, results_dir: str, base_url: str) -> FastAPI:
    from t2lgepa.client import VLLMClient
    from t2lgepa.config import load_config
    from t2lgepa.t2l import lora_module_name

    cfg = load_config(cfg_path)
    client = VLLMClient(base_url, cfg.model_id,
                        adapters=[lora_module_name(t) for t in cfg.tasks])
    return create_app(DemoService(cfg, results_dir, client), results_dir)


def main(argv: list[str] | None = None) -> int:
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/mistral.yaml")
    parser.add_argument("--results", default="/data/quan.lt/temp/t2l-mistral/results")
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args(argv)

    uvicorn.run(build(args.config, args.results, args.base_url),
                host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
