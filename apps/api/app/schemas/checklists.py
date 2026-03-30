from pydantic import BaseModel, Field


class ChecklistItemResponse(BaseModel):
    id: str
    label: str
    description: str | None = None
    is_required: bool = True
    display_order: int


class ChecklistTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False
    items: list[ChecklistItemResponse] = []


class ChecklistTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    items: list[ChecklistItemResponse] | None = None


class ChecklistTemplateResponse(ChecklistTemplateCreate):
    id: str


class ChecklistRunItemResponse(BaseModel):
    label_snapshot: str
    completed: bool = False


class ChecklistRunCreate(BaseModel):
    template_id: str | None = None
    session_date: str
    symbol: str | None = None
    setup_tag: str | None = None
    reason_for_entry: str
    confidence_score: int | None = Field(default=None, ge=1, le=5)
    items: list[ChecklistRunItemResponse]


class ChecklistRunResponse(ChecklistRunCreate):
    id: str


class ChecklistRunUpdate(BaseModel):
    session_date: str | None = None
    symbol: str | None = None
    setup_tag: str | None = None
    reason_for_entry: str | None = None
    confidence_score: int | None = Field(default=None, ge=1, le=5)
    items: list[ChecklistRunItemResponse] | None = None
