from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from utils import (
    handle_fintechnews,
    handle_glossy,
    handle_robbreport,
    handle_techcrunch,
    json_to_markdown,
    translate_text,
    upload_articles,
)

BACKEND_ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
    load_dotenv()
except ImportError:
    pass

DATA_DIR = BACKEND_ROOT / "data"
DEFAULT_SAMPLE_FILE = DATA_DIR / "techcrunch_startup_1.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_MAX_TOKENS = 400

app = FastAPI(title="AI Translation Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlatformType(str, Enum):
    TECHCRUNCH = "techcrunch"
    FINTECHNEWS = "fintechnews"
    GLOSSY = "glossy"
    ROBBREPORT = "robbreport"


PLATFORM_METADATA: Dict[PlatformType, Dict[str, Any]] = {
    PlatformType.TECHCRUNCH: {
        "label": "TechCrunch",
        "default_category": "Startup",
        "description": "Tin tức công nghệ và startup toàn cầu",
        "supported": True,
    },
    PlatformType.FINTECHNEWS: {
        "label": "Fintech News",
        "default_category": "Coin",
        "description": "Tin tức fintech và blockchain",
        "supported": True,
    },
    PlatformType.GLOSSY: {
        "label": "Glossy",
        "default_category": "Beauty",
        "description": "Tin tức beauty & lifestyle",
        "supported": True,
    },
    PlatformType.ROBBREPORT: {
        "label": "Robb Report",
        "default_category": "Lifestyle",
        "description": "Phong cách sống cao cấp",
        "supported": True,
    },
}


class CrawlRequest(BaseModel):
    platform: PlatformType = Field(..., description="Nguồn dữ liệu cần crawl.")
    links: List[str] = Field(..., min_items=1, description="Danh sách link bài viết.")
    output_path: Optional[str] = Field(
        None,
        description="Đường dẫn để lưu JSON; mặc định tự động tạo dưới thư mục data/.",
    )
    category: Optional[str] = Field(
        None,
        description="Category mong muốn; ghi đè category mặc định nếu cung cấp.",
    )
    convert_markdown: bool = Field(
        False, description="Nếu true, convert sang cấu trúc markdown sau khi crawl."
    )

    @validator("links", each_item=True)
    def validate_link(cls, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise ValueError("Link phải bắt đầu bằng http:// hoặc https://")
        return value


class CrawlResponse(BaseModel):
    platform: PlatformType
    output_path: str
    article_count: int
    category: Optional[str]
    articles: List[Dict[str, Any]]


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Nội dung tiếng Anh cần dịch.")
    max_chunk_tokens: Optional[int] = Field(
        None,
        ge=64,
        le=1024,
        description="Giới hạn token khi chia nhỏ (mặc định 400).",
    )


class TranslateResponse(BaseModel):
    translated_text: str


class MarkdownRequest(BaseModel):
    category: str = Field(..., min_length=1, description="Category dùng cho Markdown output.")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(
        ..., description="Dữ liệu JSON gốc."
    )
    output_path: Optional[str] = Field(
        None,
        description="Đường dẫn để lưu file Markdown JSON; mặc định tự động tạo.",
    )


class MarkdownResponse(BaseModel):
    output_path: str
    article_count: int
    articles: List[Dict[str, Any]]


class ArticleUpdateRequest(BaseModel):
    output_path: str = Field(..., description="Đường dẫn file JSON đã lưu.")
    index: int = Field(..., ge=0, description="Vị trí bài viết cần chỉnh sửa.")
    article: Dict[str, Any] = Field(..., description="Dữ liệu bài viết sau chỉnh sửa.")


class ArticleUpdateResponse(BaseModel):
    output_path: str
    article_index: int
    articles: List[Dict[str, Any]]


class UploadRequest(BaseModel):
    file_path: Optional[str] = Field(
        None, description="Đường dẫn file JSON cần đăng (mặc định là sample techcrunch)."
    )


class UploadResponse(BaseModel):
    output_path: str
    total: int
    success: int
    failed: int


Handler = Callable[[List[str], str], None]
HANDLERS: Dict[PlatformType, Optional[Handler]] = {
    PlatformType.TECHCRUNCH: handle_techcrunch,
    PlatformType.FINTECHNEWS: handle_fintechnews,
    PlatformType.GLOSSY: handle_glossy,
    PlatformType.ROBBREPORT: handle_robbreport,
}


def _resolve_output_path(
    path_str: Optional[str],
    platform: Optional[PlatformType] = None,
    prefix: str = "output",
) -> Path:
    if path_str:
        path = Path(path_str)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        slug = platform.value if platform else prefix
        filename = f"{slug}_{int(time.time())}.json"
        path = DATA_DIR / filename

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_existing_file(path_str: Optional[str]) -> Path:
    path = Path(path_str) if path_str else DEFAULT_SAMPLE_FILE
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


def _load_articles(path: Path) -> List[dict]:
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Không tìm thấy file output: {path}")
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Output không phải JSON hợp lệ.") from exc

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise HTTPException(status_code=500, detail="Định dạng JSON không được hỗ trợ.")


def _write_articles(path: Path, data: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)


def _get_default_category(platform: PlatformType) -> Optional[str]:
    meta = PLATFORM_METADATA.get(platform)
    return meta.get("default_category") if meta else None


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/platforms")
def list_platforms() -> List[Dict[str, Any]]:
    return [
        {
            "value": key.value,
            "label": meta["label"],
            "description": meta.get("description"),
            "default_category": meta.get("default_category"),
            "supported": meta.get("supported", False),
        }
        for key, meta in PLATFORM_METADATA.items()
    ]


@app.post("/crawl", response_model=CrawlResponse)
async def crawl_articles(payload: CrawlRequest) -> CrawlResponse:
    handler = HANDLERS.get(payload.platform)
    if handler is None:
        raise HTTPException(
            status_code=501,
            detail=f"Nguồn {payload.platform.value} chưa được hỗ trợ.",
        )

    output_path = _resolve_output_path(payload.output_path, payload.platform)
    await run_in_threadpool(handler, payload.links, str(output_path))

    articles = _load_articles(output_path)
    if payload.category:
        for article in articles:
            article["category"] = payload.category
        _write_articles(output_path, articles)

    final_category = payload.category or _get_default_category(payload.platform)
    if payload.convert_markdown:
        if not final_category:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp category để convert sang Markdown.",
            )
        await run_in_threadpool(json_to_markdown, final_category, articles, str(output_path))
        articles = _load_articles(output_path)

    return CrawlResponse(
        platform=payload.platform,
        output_path=str(output_path),
        article_count=len(articles),
        category=final_category,
        articles=articles,
    )


@app.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(payload: TranslateRequest) -> TranslateResponse:
    max_tokens = payload.max_chunk_tokens or DEFAULT_MAX_TOKENS
    translated = await run_in_threadpool(translate_text, payload.text, max_tokens)
    return TranslateResponse(translated_text=translated)


@app.post("/convert/markdown", response_model=MarkdownResponse)
async def convert_markdown(payload: MarkdownRequest) -> MarkdownResponse:
    output_path = _resolve_output_path(payload.output_path, prefix="markdown")
    await run_in_threadpool(json_to_markdown, payload.category, payload.data, str(output_path))
    articles = _load_articles(output_path)
    return MarkdownResponse(
        output_path=str(output_path),
        article_count=len(articles),
        articles=articles,
    )


@app.post("/articles/update", response_model=ArticleUpdateResponse)
async def update_article(payload: ArticleUpdateRequest) -> ArticleUpdateResponse:
    path = _resolve_existing_file(payload.output_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {path}")
    articles = _load_articles(path)
    if payload.index >= len(articles):
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết để cập nhật.")

    articles[payload.index] = payload.article
    _write_articles(path, articles)

    return ArticleUpdateResponse(
        output_path=str(path),
        article_index=payload.index,
        articles=articles,
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_endpoint(payload: UploadRequest) -> UploadResponse:
    path = _resolve_existing_file(payload.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {path}")

    stats = await run_in_threadpool(upload_articles, str(path))
    return UploadResponse(
        output_path=stats["file_path"],
        total=stats["total"],
        success=stats["success"],
        failed=stats["failed"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)
