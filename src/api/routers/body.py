"""Body composition endpoints."""

from fastapi import APIRouter, Depends
from ..auth import get_api_key
from ..dependencies import get_db, get_user_id, date_range, pagination
from ..schemas import BodyComposition, make_page

router = APIRouter(
    prefix="/api/v1/body", tags=["body"], dependencies=[Depends(get_api_key)]
)


@router.get("/composition")
async def body_composition(
    db=Depends(get_db),
    user_id: int = Depends(get_user_id),
    dates=Depends(date_range),
    pages=Depends(pagination),
):
    """Return paginated body composition measurements."""
    rows, total = await db.query_body_composition(
        user_id, dates[0], dates[1], pages[0], pages[1]
    )
    return make_page(rows, total, pages[0], pages[1], BodyComposition)
