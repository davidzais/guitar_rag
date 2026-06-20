from pydantic import BaseModel, Field
from enum import Enum



class Category(Enum):
    INSTRUCTION = "INSTRUCTION"
    SONG_TUTORIAL = "SONG_TUTORIAL"
    PERFORMANCE = "PERFORMANCE"
    PRODUCT_DEMO = "PRODUCT_DEMO"
    OTHER = "OTHER"


class Classification(BaseModel):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


