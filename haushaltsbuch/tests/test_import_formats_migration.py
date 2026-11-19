from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS = Path(__file__).parents[1] / "migrations"


def _apply(conn: sqlite3.Connection, *names: str) -> None:
    for name in names:
        conn.executescript((MIGRATIONS / name).read_text())


def test_migration_extends_check_and_keeps_existing_rows_and_fks():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    _apply(conn, "001_household_core.sql", "002_bank_import.sql")

    conn.execute(
        "INSERT INTO module_haushaltsbuch_households"
        "(id,name,base_currency,timezone,owner_user_id) VALUES(1,'Test','EUR','UTC','u1')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_accounts"
        "(id,household_id,name,type,currency) VALUES(1,1,'Konto','checking','EUR')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(id,household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,1,1,'bestand.csv','csv',?,'u1')",
        ("0" * 64,),
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_rows"
        "(id,household_id,batch_id,source_line,fingerprint,fingerprint_strength) "
        "VALUES(1,1,1,1,?,'weak')",
        ("1" * 64,),
    )
    conn.commit()

    _apply(conn, "009_import_formats.sql")

    # Bestandsdaten bleiben erhalten (Batch UND referenzierende Zeile).
    batches = conn.execute(
        "SELECT id,source_format,display_filename FROM module_haushaltsbuch_import_batches"
    ).fetchall()
    assert batches == [(1, "csv", "bestand.csv")]
    rows = conn.execute(
        "SELECT id,batch_id FROM module_haushaltsbuch_import_rows"
    ).fetchall()
    assert rows == [(1, 1)], "Bestandszeile darf durch den Rebuild nicht verloren gehen"

    # Neue Werte sind jetzt erlaubt.
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,1,'auszug.pdf','pdf',?,'u1')",
        ("2" * 64,),
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,1,'paypal.csv','paypal',?,'u1')",
        ("3" * 64,),
    )

    # Unbekanntes bleibt abgelehnt - insbesondere 'crypto_trades' (Phase 3, nicht jetzt).
    for forbidden in ("crypto_trades", "unknown"):
        try:
            conn.execute(
                "INSERT INTO module_haushaltsbuch_import_batches"
                "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
                f"VALUES(1,1,'x.xyz',?,?,'u1')",
                (forbidden, "4" * 64),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError(f"source_format={forbidden!r} sollte vom CHECK abgelehnt werden")

    # Fremdschlüssel sind nach dem Rebuild weiter aktiv (Account muss existieren).
    try:
        conn.execute(
            "INSERT INTO module_haushaltsbuch_import_batches"
            "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
            "VALUES(1,999,'x.pdf','pdf',?,'u1')",
            ("5" * 64,),
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Fremdschlüssel auf accounts sollte nach dem Rebuild noch gelten")

    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migration_is_idempotent_and_keeps_rows_on_repeated_run():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    _apply(conn, "001_household_core.sql", "002_bank_import.sql")
    conn.execute(
        "INSERT INTO module_haushaltsbuch_households"
        "(id,name,base_currency,timezone,owner_user_id) VALUES(1,'Test','EUR','UTC','u1')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_accounts"
        "(id,household_id,name,type,currency) VALUES(1,1,'Konto','checking','EUR')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(id,household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,1,1,'bestand.csv','csv',?,'u1')",
        ("0" * 64,),
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_rows"
        "(id,household_id,batch_id,source_line,fingerprint,fingerprint_strength) "
        "VALUES(1,1,1,1,?,'weak')",
        ("1" * 64,),
    )
    conn.commit()

    _apply(conn, "009_import_formats.sql")
    _apply(conn, "009_import_formats.sql")

    assert conn.execute(
        "SELECT COUNT(*) FROM module_haushaltsbuch_import_batches"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT id,batch_id FROM module_haushaltsbuch_import_rows"
    ).fetchall() == [(1, 1)]
