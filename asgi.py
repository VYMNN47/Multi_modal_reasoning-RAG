import logging
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders, UploadFile
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import app as application
import model


MAX_REQUEST_BYTES = application.MAX_UPLOAD_BYTES + 64 * 1024
logger = logging.getLogger(__name__)


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
                headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, secure_send)


async def homepage(request: Request):
    return FileResponse(application.ROOT / "assets/index.html")


async def health(request: Request):
    return JSONResponse({"status": "ok"})


async def examples(request: Request):
    return JSONResponse({"examples": application.example_catalog(), "max_upload_bytes": application.MAX_UPLOAD_BYTES})


async def example_image(request: Request):
    path = application.EXAMPLE_FILES.get(request.path_params["filename"])
    if path is None:
        raise HTTPException(404, "Image not found.")
    return FileResponse(path)


async def analyze(request: Request):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, "Submit assessments from this website.")
    try:
        async with request.form(max_files=2, max_fields=4, max_part_size=32 * 1024) as form:
            names = ("question", "context", "language", "case")
            if any(key not in (*names, "images") for key in form):
                raise ValueError("The assessment contains an unsupported field.")
            values = {name: form.get(name, "English" if name == "language" else "upload" if name == "case" else "") for name in names}
            if any(len(form.getlist(name)) > 1 or not isinstance(value, str) for name, value in values.items()):
                raise ValueError("Assessment text fields must contain one text value each.")
            files = form.getlist("images")
            if any(not isinstance(file, UploadFile) for file in files):
                raise ValueError("Choose complete PNG/JPEG image files.")
            uploads = [await file.read(application.MAX_UPLOAD_BYTES + 1) for file in files]
            result = await run_in_threadpool(application.assess, uploads=uploads, **values)
        return JSONResponse(result)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, 422)
    except model.GeminiError as exc:
        return JSONResponse({"error": str(exc)}, 503)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected assessment failure")
        return JSONResponse({"error": "The assessment could not be completed. Try again later."}, 500)


async def http_error(request: Request, exc: HTTPException):
    return JSONResponse({"error": str(exc.detail)}, exc.status_code)


app = Starlette(routes=[
    Route("/", homepage),
    Route("/api/health", health),
    Route("/api/examples", examples),
    Route("/api/example-images/{filename}", example_image),
    Route("/api/analyze", analyze, methods=["POST"]),
    Mount("/assets", app=StaticFiles(directory=application.ROOT / "assets")),
], exception_handlers={HTTPException: http_error}, max_body_size=MAX_REQUEST_BYTES)
app = SecurityHeaders(app)
