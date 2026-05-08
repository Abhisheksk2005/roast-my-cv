from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ScrapeRequest(BaseModel):
    linkedin_url: str


class ScrapeResponse(BaseModel):
    success: bool
    name: str = ""
    degree: str = ""
    university: str = ""
    graduation_year: int = 0
    current_job: str = ""
    current_company: str = ""
    error: str = ""


@router.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_profile(req: ScrapeRequest):
    _ = req
    return ScrapeResponse(
        success=False,
        error="linkedin_scraping_disabled",
    )
