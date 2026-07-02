import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.config import settings
from app.errors import AppError, BadSelection, NotFound, NotReady
from app.http_client import close_http_client, init_http_client
from app.jobs import create_job, get_job, resolve_total, run_job
from app.languages import DEFAULT_LANGUAGE, LANGUAGES, normalize
from app.media.packager import make_zip_filename, resolve_single_talk, stream_zip
from app.models import CatalogResponse, ConferenceDetail, DownloadRequest, LanguagesResponse
from app.source import catalog, cache as src_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_CATALOG_REFRESH_INTERVAL = 6 * 3600  # 6 hours — catches new conferences within half a day


async def _catalog_refresh_loop() -> None:
    """FR-8: background task that periodically re-warms the English catalog cache.

    Clearing the cache every 6 hours ensures a brand-new conference (published
    on the first weekend of April or October) appears within 6 hours without
    any manual intervention or redeploy.
    """
    while True:
        await asyncio.sleep(_CATALOG_REFRESH_INTERVAL)
        try:
            await src_cache.clear()
            logger.info("Catalog cache cleared for scheduled refresh (FR-8).")
            # Pre-warm English so the first user after the clear doesn't wait.
            await catalog.list_conferences(DEFAULT_LANGUAGE)
            logger.info("Catalog cache re-warmed (English).")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Catalog refresh failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_http_client(settings)
    refresh_task = asyncio.create_task(_catalog_refresh_loop())
    yield
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
    await close_http_client()


app = FastAPI(title="GC Downloader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/languages", response_model=LanguagesResponse)
async def get_languages() -> LanguagesResponse:
    return LanguagesResponse(languages=LANGUAGES, default=DEFAULT_LANGUAGE)


@app.get("/api/catalog", response_model=CatalogResponse)
async def get_catalog(lang: str = Query(default=DEFAULT_LANGUAGE)) -> CatalogResponse:
    conferences = await catalog.list_conferences(normalize(lang))
    return CatalogResponse(conferences=conferences)


@app.get("/api/conferences/{conference_id}", response_model=ConferenceDetail)
async def get_conference(
    conference_id: str, lang: str = Query(default=DEFAULT_LANGUAGE)
) -> ConferenceDetail:
    return await catalog.get_conference(conference_id, normalize(lang))


@app.post("/api/jobs", status_code=202)
async def create_download_job(
    request: DownloadRequest, background_tasks: BackgroundTasks
) -> dict:
    has_sel = any((s.session_ids or s.talk_ids) for s in request.selection)
    if not has_sel:
        raise BadSelection("No talks selected.")
    total = await resolve_total(request)
    if total == 0:
        raise BadSelection("No talks resolved from selection.")
    job = create_job(request, total)
    background_tasks.add_task(run_job, job.job_id)
    return {"job_id": job.job_id, "total": total}


@app.get("/api/jobs/{job_id}")
async def get_download_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise NotFound(f"Job {job_id} not found or expired.")
    return {
        "job_id": job.job_id,
        "state": job.state,
        "total": job.total,
        "completed": job.completed,
        "skipped": job.skipped,
        "download_ready": job.download_ready,
        "error_msg": job.error_msg,
    }


@app.get("/api/jobs/{job_id}/download")
async def download_job_result(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise NotFound(f"Job {job_id} not found or expired.")
    if not job.download_ready or not job.temp_path or not os.path.exists(job.temp_path):
        raise NotReady("Job is not ready for download yet.")
    return FileResponse(
        path=job.temp_path,
        media_type=job.content_type,
        filename=job.filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.post("/api/download")
async def download(request: DownloadRequest) -> StreamingResponse:
    has_sessions = any(s.session_ids for s in request.selection)
    total_talk_ids = sum(len(s.talk_ids or []) for s in request.selection)
    if not request.selection or (not has_sessions and total_talk_ids == 0):
        raise BadSelection("No talks selected.")

    # Single talk_id and no session selections → stream bare MP3
    if not has_sessions and total_talk_ids == 1:
        mp3_bytes, filename = await resolve_single_talk(request)
        return StreamingResponse(
            iter([mp3_bytes]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(mp3_bytes)),
                "X-Content-Type-Options": "nosniff",
            },
        )

    # Multiple talks → stream a ZIP
    filename = make_zip_filename(request)
    return StreamingResponse(
        stream_zip(request),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
