from __future__ import annotations

from app.database import db_session
from app.models import User


def main():
    with db_session() as db:
        user = db.query(User).filter(User.whatsapp_user_id == "demo-waid").first()
        if not user:
            user = User(whatsapp_user_id="demo-waid", phone_number="whatsapp:+10000000000", timezone="UTC")
            db.add(user)


if __name__ == "__main__":
    main() 