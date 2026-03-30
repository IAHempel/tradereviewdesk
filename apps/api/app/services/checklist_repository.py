from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser
from app.core.persistence import use_file_persistence
from app.db.session import SessionLocal
from app.models.checklists import ChecklistRun, ChecklistRunItem, ChecklistTemplate, ChecklistTemplateItem
from app.schemas.checklists import (
    ChecklistItemResponse,
    ChecklistRunCreate,
    ChecklistRunItemResponse,
    ChecklistRunResponse,
    ChecklistRunUpdate,
    ChecklistTemplateCreate,
    ChecklistTemplateResponse,
    ChecklistTemplateUpdate,
)
from app.services import state_store
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _template_to_response(template: ChecklistTemplate) -> ChecklistTemplateResponse:
    items = sorted(template.items, key=lambda item: item.display_order)
    return ChecklistTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        is_default=template.is_default,
        items=[
            ChecklistItemResponse(
                id=item.id,
                label=item.label,
                description=item.description,
                is_required=item.is_required,
                display_order=item.display_order,
            )
            for item in items
        ],
    )


def _run_to_response(run: ChecklistRun) -> ChecklistRunResponse:
    items = sorted(run.items, key=lambda item: item.id)
    return ChecklistRunResponse(
        id=run.id,
        template_id=run.template_id,
        session_date=str(run.session_date),
        symbol=run.symbol,
        setup_tag=run.setup_tag,
        reason_for_entry=run.reason_for_entry,
        confidence_score=run.confidence_score,
        items=[ChecklistRunItemResponse(label_snapshot=item.label_snapshot, completed=item.completed) for item in items],
    )


def _seed_templates(session, user_id: str, current_user: CurrentUser) -> None:
    for template in state_store.list_checklist_templates(current_user):
        db_template = ChecklistTemplate(
            user_id=user_id,
            name=template.name,
            description=template.description,
            is_default=template.is_default,
        )
        session.add(db_template)
        session.flush()
        for item in template.items:
            session.add(
                ChecklistTemplateItem(
                    template_id=db_template.id,
                    label=item.label,
                    description=item.description,
                    is_required=item.is_required,
                    display_order=item.display_order,
                )
            )


def _seed_runs(session, user_id: str, current_user: CurrentUser) -> None:
    for run in state_store.list_checklist_runs(current_user):
        db_run = ChecklistRun(
            user_id=user_id,
            template_id=None,
            session_date=run.session_date,
            symbol=run.symbol,
            setup_tag=run.setup_tag,
            reason_for_entry=run.reason_for_entry,
            confidence_score=run.confidence_score,
        )
        session.add(db_run)
        session.flush()
        for item in run.items:
            session.add(
                ChecklistRunItem(
                    checklist_run_id=db_run.id,
                    template_item_id=None,
                    label_snapshot=item.label_snapshot,
                    completed=item.completed,
                )
            )


def list_templates(current_user: CurrentUser) -> list[ChecklistTemplateResponse] | None:
    def action() -> list[ChecklistTemplateResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            templates = list(
                session.scalars(
                    select(ChecklistTemplate)
                    .options(selectinload(ChecklistTemplate.items))
                    .where(ChecklistTemplate.user_id == user.id)
                    .order_by(ChecklistTemplate.created_at.asc())
                )
            )
            if not templates and use_file_persistence():
                _seed_templates(session, user.id, current_user)
                session.commit()
                templates = list(
                    session.scalars(
                        select(ChecklistTemplate)
                        .options(selectinload(ChecklistTemplate.items))
                        .where(ChecklistTemplate.user_id == user.id)
                        .order_by(ChecklistTemplate.created_at.asc())
                    )
                )
            return [_template_to_response(template) for template in templates]

    return with_db_fallback(action)


def create_template(payload: ChecklistTemplateCreate, current_user: CurrentUser) -> ChecklistTemplateResponse | None:
    def action() -> ChecklistTemplateResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            template = ChecklistTemplate(
                user_id=user.id,
                name=payload.name,
                description=payload.description,
                is_default=payload.is_default,
            )
            session.add(template)
            session.flush()
            for item in payload.items:
                session.add(
                    ChecklistTemplateItem(
                        template_id=template.id,
                        label=item.label,
                        description=item.description,
                        is_required=item.is_required,
                        display_order=item.display_order,
                    )
                )
            session.commit()
            refreshed = session.scalar(
                select(ChecklistTemplate)
                .options(selectinload(ChecklistTemplate.items))
                .where(ChecklistTemplate.id == template.id, ChecklistTemplate.user_id == user.id)
            )
            return _template_to_response(refreshed)

    return with_db_fallback(action)


def update_template(
    template_id: str,
    payload: ChecklistTemplateUpdate,
    current_user: CurrentUser,
) -> ChecklistTemplateResponse | None:
    def action() -> ChecklistTemplateResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            template = session.scalar(
                select(ChecklistTemplate)
                .options(selectinload(ChecklistTemplate.items))
                .where(ChecklistTemplate.id == template_id, ChecklistTemplate.user_id == user.id)
            )
            if template is None:
                return None

            if payload.name is not None:
                template.name = payload.name
            if payload.description is not None:
                template.description = payload.description
            if payload.is_default is not None:
                template.is_default = payload.is_default
            if payload.items is not None:
                template.items.clear()
                session.flush()
                for item in payload.items:
                    session.add(
                        ChecklistTemplateItem(
                            template_id=template.id,
                            label=item.label,
                            description=item.description,
                            is_required=item.is_required,
                            display_order=item.display_order,
                        )
                    )

            session.add(template)
            session.commit()
            refreshed = session.scalar(
                select(ChecklistTemplate)
                .options(selectinload(ChecklistTemplate.items))
                .where(ChecklistTemplate.id == template.id, ChecklistTemplate.user_id == user.id)
            )
            return _template_to_response(refreshed) if refreshed is not None else None

    return with_db_fallback(action)


def list_runs(current_user: CurrentUser) -> list[ChecklistRunResponse] | None:
    def action() -> list[ChecklistRunResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            runs = list(
                session.scalars(
                    select(ChecklistRun)
                    .options(selectinload(ChecklistRun.items))
                    .where(ChecklistRun.user_id == user.id)
                    .order_by(ChecklistRun.session_date.desc(), ChecklistRun.created_at.desc())
                )
            )
            if not runs and use_file_persistence():
                _seed_runs(session, user.id, current_user)
                session.commit()
                runs = list(
                    session.scalars(
                        select(ChecklistRun)
                        .options(selectinload(ChecklistRun.items))
                        .where(ChecklistRun.user_id == user.id)
                        .order_by(ChecklistRun.session_date.desc(), ChecklistRun.created_at.desc())
                    )
                )
            return [_run_to_response(run) for run in runs]

    return with_db_fallback(action)


def create_run(payload: ChecklistRunCreate, current_user: CurrentUser) -> ChecklistRunResponse | None:
    def action() -> ChecklistRunResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = ChecklistRun(
                user_id=user.id,
                template_id=payload.template_id,
                session_date=payload.session_date,
                symbol=payload.symbol,
                setup_tag=payload.setup_tag,
                reason_for_entry=payload.reason_for_entry,
                confidence_score=payload.confidence_score,
            )
            session.add(run)
            session.flush()
            for item in payload.items:
                session.add(
                    ChecklistRunItem(
                        checklist_run_id=run.id,
                        template_item_id=None,
                        label_snapshot=item.label_snapshot,
                        completed=item.completed,
                    )
                )
            session.commit()
            refreshed = session.scalar(
                select(ChecklistRun)
                .options(selectinload(ChecklistRun.items))
                .where(ChecklistRun.id == run.id, ChecklistRun.user_id == user.id)
            )
            return _run_to_response(refreshed)

    return with_db_fallback(action)


def get_run(run_id: str, current_user: CurrentUser) -> ChecklistRunResponse | None:
    def action() -> ChecklistRunResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = session.scalar(
                select(ChecklistRun)
                .options(selectinload(ChecklistRun.items))
                .where(ChecklistRun.id == run_id, ChecklistRun.user_id == user.id)
            )
            if run is None:
                return None
            return _run_to_response(run)

    return with_db_fallback(action)


def update_run(
    run_id: str,
    payload: ChecklistRunUpdate,
    current_user: CurrentUser,
) -> ChecklistRunResponse | None:
    def action() -> ChecklistRunResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = session.scalar(
                select(ChecklistRun)
                .options(selectinload(ChecklistRun.items))
                .where(ChecklistRun.id == run_id, ChecklistRun.user_id == user.id)
            )
            if run is None:
                return None

            if payload.session_date is not None:
                run.session_date = payload.session_date
            if payload.symbol is not None:
                run.symbol = payload.symbol
            if payload.setup_tag is not None:
                run.setup_tag = payload.setup_tag
            if payload.reason_for_entry is not None:
                run.reason_for_entry = payload.reason_for_entry
            if payload.confidence_score is not None:
                run.confidence_score = payload.confidence_score
            if payload.items is not None:
                run.items.clear()
                session.flush()
                for item in payload.items:
                    session.add(
                        ChecklistRunItem(
                            checklist_run_id=run.id,
                            template_item_id=None,
                            label_snapshot=item.label_snapshot,
                            completed=item.completed,
                        )
                    )

            session.add(run)
            session.commit()
            refreshed = session.scalar(
                select(ChecklistRun)
                .options(selectinload(ChecklistRun.items))
                .where(ChecklistRun.id == run.id, ChecklistRun.user_id == user.id)
            )
            return _run_to_response(refreshed) if refreshed is not None else None

    return with_db_fallback(action)


def delete_template(template_id: str, current_user: CurrentUser) -> bool | None:
    def action() -> bool:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            template = session.scalar(
                select(ChecklistTemplate).where(ChecklistTemplate.id == template_id, ChecklistTemplate.user_id == user.id)
            )
            if template is None:
                return False
            session.delete(template)
            session.commit()
            return True

    return with_db_fallback(action)


def delete_run(run_id: str, current_user: CurrentUser) -> bool | None:
    def action() -> bool:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            run = session.scalar(select(ChecklistRun).where(ChecklistRun.id == run_id, ChecklistRun.user_id == user.id))
            if run is None:
                return False
            session.delete(run)
            session.commit()
            return True

    return with_db_fallback(action)
