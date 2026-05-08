from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def render_home(request: Request):
    return templates.TemplateResponse(
        request=request, name="home.html", context={"request": request}
    )


@router.get("/email")
async def render_email(request: Request):
    return templates.TemplateResponse(
        request=request, name="email.html", context={"request": request}
    )


@router.get("/crafter")
async def render_crafter(request: Request):
    return templates.TemplateResponse(
        request=request, name="crafter.html", context={"request": request}
    )


@router.get("/orders")
async def render_orders(request: Request):
    return templates.TemplateResponse(
        request=request, name="orders.html", context={"request": request}
    )


@router.get("/settings")
async def render_settings(request: Request):
    return templates.TemplateResponse(
        request=request, name="settings.html", context={"request": request}
    )


@router.get("/dev")
async def render_dev(request: Request):
    return templates.TemplateResponse(
        request=request, name="dev.html", context={"request": request}
    )
