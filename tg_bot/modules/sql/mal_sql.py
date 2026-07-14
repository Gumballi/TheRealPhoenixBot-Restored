from sqlalchemy import Column, String, Integer
from tg_bot.modules.sql import BASE, SESSION


class MALTokens(BASE):
    __tablename__ = "mal_tokens"
    id = Column(Integer, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)

    def __init__(self, access_token, refresh_token):
        self.id = 1
        self.access_token = access_token
        self.refresh_token = refresh_token


MALTokens.__table__.create(checkfirst=True)


def get_tokens():
    try:
        return SESSION.query(MALTokens).get(1)
    finally:
        SESSION.close()


def update_tokens(access_token, refresh_token):
    curr = SESSION.query(MALTokens).get(1)
    if not curr:
        curr = MALTokens(access_token, refresh_token)
        SESSION.add(curr)
    else:
        curr.access_token = access_token
        curr.refresh_token = refresh_token
    SESSION.commit()
