import json
from sqlalchemy.orm import Session
from models_local.state import State


def get_state(key: str, db: Session):
    state = db.query(State).filter(State.key == key).first()
    if state:
        return json.loads(state.value)
    return None

def set_state(key: str, value, db: Session):
    from datetime import datetime, timezone
    serialized_value = json.dumps(value)
    state = db.query(State).filter(State.key == key).first()

    if state:
        state.value = serialized_value
        state.updated_at = datetime.now(timezone.utc)
    else:
        state = State(
            key=key,
            value=serialized_value
        )
        db.add(state)

    db.commit()
    return state