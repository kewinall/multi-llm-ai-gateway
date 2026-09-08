import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import GatewayError
from app.models import ChatCompletionRequest
from app.router import ModelRouter
from app.security import require_api_key

settings = get_settings()
router = ModelRouter(settings)

app = FastAPI(
    title="Multi-LLM AI Gateway",
    version="0.1.0",
    description="OpenAI-compatible multi-provider LLM gateway.",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(GatewayError)
async def gateway_error_handler(_request: Request, exc: GatewayError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/v1/providers", dependencies=[Depends(require_api_key)])
async def providers() -> dict[str, object]:
    return {"providers": router.provider_status()}


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported in v0.1")

    try:
        result, route_metadata = await router.route(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["gateway"] = route_metadata
    return result
