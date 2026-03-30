from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.checklists import ChecklistTemplateCreate, ChecklistTemplateResponse, ChecklistTemplateUpdate
from app.services import billing_service, checklist_repository, state_store

router = APIRouter()


@router.get("", response_model=list[ChecklistTemplateResponse])
def list_templates(current_user: CurrentUser = Depends(require_current_user)) -> list[ChecklistTemplateResponse]:
    if use_file_persistence():
        return state_store.list_checklist_templates(current_user)

    return require_database_result(checklist_repository.list_templates(current_user), "Checklist templates")


@router.post("", response_model=ChecklistTemplateResponse)
def create_template(
    payload: ChecklistTemplateCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> ChecklistTemplateResponse:
    billing_service.require_feature_access(current_user, "checklists")

    if use_file_persistence():
        templates = state_store.list_checklist_templates(current_user)
        item = ChecklistTemplateResponse(id=f"template-{len(templates) + 1}", **payload.model_dump())
        templates.append(item)
        state_store.save_checklist_templates(templates, current_user)
        return item

    return require_database_result(checklist_repository.create_template(payload, current_user), "Checklist template")


@router.put("/{template_id}", response_model=ChecklistTemplateResponse)
def update_template(
    template_id: str,
    payload: ChecklistTemplateUpdate,
    current_user: CurrentUser = Depends(require_current_user),
) -> ChecklistTemplateResponse:
    if use_file_persistence():
        templates = state_store.list_checklist_templates(current_user)
        for idx, template in enumerate(templates):
            if template.id == template_id:
                updated = template.model_copy(update=payload.model_dump(exclude_unset=True))
                templates[idx] = updated
                state_store.save_checklist_templates(templates, current_user)
                return updated
        raise HTTPException(status_code=404, detail="Checklist template not found")

    updated = checklist_repository.update_template(template_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Checklist template not found")
    return updated


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, str]:
    if use_file_persistence():
        templates = state_store.list_checklist_templates(current_user)
        filtered = [template for template in templates if template.id != template_id]
        if len(filtered) == len(templates):
            raise HTTPException(status_code=404, detail="Checklist template not found")
        state_store.save_checklist_templates(filtered, current_user)
        return {"deleted": template_id}

    deleted = checklist_repository.delete_template(template_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Checklist template not found")
    return {"deleted": template_id}
