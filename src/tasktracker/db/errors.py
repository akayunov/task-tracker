from sqlalchemy.exc import IntegrityError


def constraint_name(exc: IntegrityError) -> str | None:
    name = getattr(exc.orig, 'constraint_name', None)
    if isinstance(name, str):
        return name
    return None
