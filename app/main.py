"""
FastAPI Application Entry Point
"""
import io
import logging
import os
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from app.routers import dashboard
from .authz import AuthzEngine
from .core.storage import GCSStorage, LocalStorage, StorageBackend
from .middleware import AuditMiddleware
from .routers import (
    admin_router,
    audit_router,
    auth_router,
    examples_router,
    health_router,
    items_router,
)
from .security import get_current_user, verify_access
from app.routers.workbench import router as workbench_router, webhooks_router




# 📡 IMPORT NEW LIVE CHANNELS AND SYSTEMS OF RECORD (Using safe relative paths)
from .routers.policies import router as policies_router
from .routers.insights import router as insights_router
from .routers.chat import router as chat_router
from .routers.data_manager import router as data_manager_router


# 🟢 RESTORE WORKBENCH ROUTER HERE!
from .routers.workbench import router as workbench_router

# 📡 IMPORT THE NEW WEBHOOKS ROUTER
from .routers.webhooks import router as webhooks_router

from fastapi import FastAPI
app = FastAPI()




log = logging.getLogger(__name__)

BASE_PATH = os.getenv("BASE_PATH", "")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"
if BASE_PATH == "/":
    BASE_PATH = ""
log.info(f"API Base Path: '{BASE_PATH}' (empty means root)")

# =============================================================================
# APPLICATION SETUP
# =============================================================================
app = FastAPI(
    title="AutoPilot API",
    description="AI Command Center — Full-stack template with FastAPI, Next.js, and PostgreSQL",
    version="2.0.0",
    docs_url=f"{BASE_PATH}/api/docs",
    redoc_url=f"{BASE_PATH}/api/redoc",
    openapi_url=f"{BASE_PATH}/api/openapi.json",
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3001")
cors_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

# =============================================================================
# API ROUTER WITH AUTHORIZATION
# =============================================================================
api_router = APIRouter(
    prefix=f"{BASE_PATH}/api",
    dependencies=[Depends(verify_access)],
)

def get_storage_dependency() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "gcs":
        bucket = os.getenv("GCS_BUCKET")
        prefix = os.getenv("GCS_PREFIX", "")
        if not bucket:
            raise ValueError("GCS_BUCKET environment variable is required")
        return GCSStorage(bucket, prefix)
    else:
        path = os.getenv("LOCAL_STORAGE_PATH", "./document_storage")
        return LocalStorage(path)

# =============================================================================
# INCLUDE ROUTERS
# =============================================================================
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(audit_router)
api_router.include_router(items_router)
api_router.include_router(examples_router)

app.include_router(dashboard.router, prefix="/api")
api_router.include_router(workbench_router, prefix="/workbench", tags=["Workbench"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

# =============================================================================
# FILE STORAGE ENDPOINTS
# =============================================================================
@api_router.get("/files/", tags=["Files"])
async def list_files(
    prefix: str = "",
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    files = await storage.list_files(prefix)
    return {"files": files, "count": len(files)}

@api_router.post("/files/{file_path:path}", tags=["Files"])
async def upload_file(
    file_path: str,
    file: UploadFile = File(...),
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    content = await file.read()
    url = await storage.save(file_path, content, file.content_type)
    return {
        "path": file_path,
        "url": url,
        "content_type": file.content_type,
        "size": len(content),
    }

@api_router.get("/files/{file_path:path}", tags=["Files"])
async def download_file(
    file_path: str,
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    try:
        content, content_type = await storage.load(file_path)
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file_path}"'},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

@api_router.delete("/files/{file_path:path}", tags=["Files"])
async def delete_file(
    file_path: str,
    storage: StorageBackend = Depends(get_storage_dependency),
    user: dict = Depends(get_current_user),
):
    await storage.delete(file_path)
    return {"status": "deleted", "path": file_path}

# Mount template routers to app
app.include_router(api_router)

# =============================================================================
# MOUNT DYNAMIC ROUND 2 ROUTERS (Safely mounted to the fully defined app!)
# =============================================================================
app.include_router(policies_router)
app.include_router(insights_router)
app.include_router(chat_router)
app.include_router(data_manager_router)

# 🟢 RESTORE AND MOUNT WORKBENCH ROUTER!
app.include_router(workbench_router)

app.include_router(policies_router, prefix="/api/policies")
app.include_router(policies_router, prefix="/api/ai/policies")
app.include_router(workbench_router)
app.include_router(webhooks_router)  


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================
@app.get("/")
@app.get("/api")
@app.get("/api/")
async def api_base_handshake():
    print("📡 [SUPERVITY] Base handshake ping received on /api!")
    return {
        "status": "ok",
        "message": "AutoPilot Command Center API is live and healthy!"
    }



async def root():
    return {
        "name": "AutoPilot API",
        "version": "2.0.0",
        "docs": f"{BASE_PATH}/api/docs",
        "health": f"{BASE_PATH}/api/health",
        "base_path": BASE_PATH or "/",
    }

if BASE_PATH:
    @app.get(BASE_PATH)
    async def base_path_root():
        return {
            "name": "AutoPilot API",
            "version": "2.0.0",
            "docs": f"{BASE_PATH}/api/docs",
            "health": f"{BASE_PATH}/api/health",
            "base_path": BASE_PATH,
        }
