from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.local_session import get_db
from schemas.setting import SettingIn, SettingOut
from services.settings_service import get_setting, set_setting

router = APIRouter()

@router.get("/{key}", response_model=SettingOut)
def read_setting(key: str, db: Session = Depends(get_db)):
    value = get_setting(key, db)
    return {"key": key, "value": value}

@router.post("/", response_model=SettingOut)
def write_setting(setting: SettingIn, db: Session = Depends(get_db)):
    setting_obj = set_setting(setting.key, setting.value, db)
    return {"key": setting_obj.key, "value": setting.value}