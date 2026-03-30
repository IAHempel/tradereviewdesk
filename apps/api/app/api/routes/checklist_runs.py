from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.checklists import ChecklistRunCreate, ChecklistRunResponse, ChecklistRunUpdate
from app.services import billing_service, checklist_repository, state_store

router = APIRouter()


@router.get("", response_model=list[ChecklistRunResponse])
def list_runs(current_user: CurrentUser = Depends(require_current_user)) -> list[ChecklistRunResponse]:
    if use_file_persistence():
        return state_store.list_checklist_runs(current_user)

    return require_database_result(checklist_repository.list_runs(current_user), "Checklist runs")


@router.post("", response_model=ChecklistRunResponse)
def create_run(
    payload: ChecklistRunCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> ChecklistRunResponse:
    billing_service.require_feature_access(current_user, "checklists")

    if use_file_persistence():
        runs = state_store.list_checklist_runs(current_user)
        item = ChecklistRunResponse(id=f"run-{len(runs) + 1}", **payload.model_dump())
        runs.append(item)
        state_store.save_checklist_runs(runs, current_user)
        return item

    return require_database_result(checklist_repository.create_run(payload, current_user), "Checklist run")


@router.get("/{run_id}", response_model=ChecklistRunResponse)
def get_run(run_id: str, current_user: CurrentUser = Depends(require_current_user)) -> ChecklistRunResponse:
    if use_file_persistence():
        runs = state_store.list_checklist_runs(current_user)
        for item in runs:
            if item.id == run_id:
                return item
        if not runs:
            raise HTTPException(status_code=404, detail="Checklist run not found")
        return runs[0]

    run = checklist_repository.get_run(run_id, current_user)
    if run is None:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return run


@router.put("/{run_id}", response_model=ChecklistRunResponse)
def update_run(
    run_id: str,
    payload: ChecklistRunUpdate,
    current_user: CurrentUser = Depends(require_current_user),
) -> ChecklistRunResponse:
    billing_service.require_feature_access(current_user, "checklists")

    if use_file_persistence():
        runs = state_store.list_checklist_runs(current_user)
        for idx, run in enumerate(runs):
            if run.id == run_id:
                updated = run.model_copy(update=payload.model_dump(exclude_unset=True))
                runs[idx] = updated
                state_store.save_checklist_runs(runs, current_user)
                return updated
        raise HTTPException(status_code=404, detail="Checklist run not found")

    updated = checklist_repository.update_run(run_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return updated


@router.delete("/{run_id}")
def delete_run(run_id: str, current_user: CurrentUser = Depends(require_current_user)) -> dict[str, str]:
    if use_file_persistence():
        runs = state_store.list_checklist_runs(current_user)
        filtered = [run for run in runs if run.id != run_id]
        if len(filtered) == len(runs):
            raise HTTPException(status_code=404, detail="Checklist run not found")
        state_store.save_checklist_runs(filtered, current_user)
        return {"deleted": run_id}

    deleted = checklist_repository.delete_run(run_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Checklist run not found")
    return {"deleted": run_id}
