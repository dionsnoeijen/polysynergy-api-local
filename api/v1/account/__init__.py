from fastapi import APIRouter
from . import account, my_chat_windows

router = APIRouter()

router.include_router(account.router, prefix="/accounts", tags=["Accounts"])
router.include_router(my_chat_windows.router, tags=["My Chat Windows"])
