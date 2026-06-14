from typing import Optional

from pydantic import BaseModel


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[str]
    exp: int
