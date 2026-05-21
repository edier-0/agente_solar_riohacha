from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply small, targeted schema fixes for older databases.

    The project currently uses ``create_all`` for fresh setups, but that does
    not evolve existing tables. This helper patches known schema drift without
    requiring users to drop their database volume.
    """
    inspector = inspect(engine)

    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}

        role_column = next(
            (column for column in inspector.get_columns("users") if column["name"] == "role"),
            None,
        )
        role_values = list(getattr(role_column["type"], "enums", []) if role_column else [])
        if role_values != ["admin", "empresa", "analista"]:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE users "
                        "MODIFY COLUMN role ENUM('admin', 'empresa', 'analista') "
                        "NOT NULL DEFAULT 'empresa'"
                    )
                )

        if "vista_preferida" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN vista_preferida ENUM('simple', 'detallado', 'operacional') "
                        "NOT NULL DEFAULT 'simple' AFTER `role`"
                    )
                )

    if inspector.has_table("radiacion_solar"):
        radiacion_columns = {column["name"] for column in inspector.get_columns("radiacion_solar")}
        missing_radiacion_columns = []

        if "temperatura_max" not in radiacion_columns:
            missing_radiacion_columns.append("ADD COLUMN temperatura_max FLOAT NULL")
        if "temperatura_min" not in radiacion_columns:
            missing_radiacion_columns.append("ADD COLUMN temperatura_min FLOAT NULL")
        if "precipitacion_mm" not in radiacion_columns:
            missing_radiacion_columns.append("ADD COLUMN precipitacion_mm FLOAT NULL")
        if "viento_kmh_max" not in radiacion_columns:
            missing_radiacion_columns.append("ADD COLUMN viento_kmh_max FLOAT NULL")

        if missing_radiacion_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE radiacion_solar "
                        + ", ".join(missing_radiacion_columns)
                    )
                )
