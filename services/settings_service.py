import json
from sqlalchemy.orm import Session
from models_local.settings import Settings

def get_setting(key: str, db: Session):
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        return json.loads(setting.value).strip('"')
    return None

def set_setting(key: str, value, db: Session):
    from datetime import datetime, timezone
    serialized_value = json.dumps(value)
    setting = db.query(Settings).filter(Settings.key == key).first()

    if setting:
        setting.value = serialized_value
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = Settings(
            key=key,
            value=serialized_value
        )
        db.add(setting)

    db.commit()
    return setting