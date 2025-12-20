from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class CraftEvent(BaseModel):
    Organization: str
    Event: str
    Date: str
    Time: str
    URL: HttpUrl
    organizer: str