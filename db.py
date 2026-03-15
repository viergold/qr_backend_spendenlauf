import sqlite3
import datetime

DB_PATH = "spielerdaten.db"


def get_conn():
    """Return a new sqlite3.Connection for the current thread/request."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def db_in():
    """Initialize database schema."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS spieler (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            runden INTEGER DEFAULT 0,
            klasse TEXT,
            zeitpunkt TEXT,
            beste_zeit REAL
        )
        """)
        conn.commit()


# Spieler hinzufügen (ID wird manuell gesetzt)
def spieler_hinzufuegen(id, name, klasse):
    with get_conn() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO spieler (id, name, klasse) VALUES (?, ?, ?)",
                (id, name, klasse)
            )
            conn.commit()
            print("Spieler hinzugefügt.")
        except sqlite3.IntegrityError:
            print("Fehler: Diese ID existiert bereits!")


def runde_hinzufuegen(id):
    with get_conn() as conn:
        cursor = conn.cursor()

        # Prüfen, ob Spieler existiert
        cursor.execute("SELECT runden, zeitpunkt, beste_zeit FROM spieler WHERE id = ?", (id,))
        result = cursor.fetchone()

        if result is None:
            print("Fehler: Diese ID existiert nicht.")
            return

        _, letzte_zeit, alte_beste_zeit = result

        jetzt = datetime.datetime.now()
        jetzt_str = jetzt.isoformat(timespec="seconds")

        # Laufzeit berechnen, falls es eine vorherige Zeit gibt
        if letzte_zeit is not None:
            letzte_dt = datetime.datetime.fromisoformat(letzte_zeit)
            laufzeit = (jetzt - letzte_dt).total_seconds()
        else:
            laufzeit = None

        # Runde + neue Zeit speichern
        cursor.execute("""
            UPDATE spieler
            SET runden = runden + 1,
                zeitpunkt = ?
            WHERE id = ?
        """, (jetzt_str, id))

        # Beste Zeit aktualisieren
        if laufzeit is not None:
            if alte_beste_zeit is None or laufzeit < alte_beste_zeit:
                cursor.execute("""
                    UPDATE spieler
                    SET beste_zeit = ?
                    WHERE id = ?
                """, (laufzeit, id))

        conn.commit()

        if laufzeit is None:
            print(f"Runde für ID {id} wurde erhöht. (Erste Runde, keine Laufzeit)")
        else:
            print(f"Runde für ID {id} wurde erhöht. Laufzeit: {laufzeit:.2f} Sekunden")


def get_name_klasse(id):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, klasse FROM spieler WHERE id = ?", (id,))
        result = cursor.fetchone()

    if result is None:
        return None, None

    name, klasse = result
    return name, klasse


def check_id(id):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM spieler WHERE id = ?", (id,))
        result = cursor.fetchone()
    return result is not None


def get_top_15(limit=15, klasse=None, min_runden=None):
    query = [
        "SELECT id, name, klasse, runden, zeitpunkt, beste_zeit",
        "FROM spieler"
    ]

    params = []
    where_clauses = []

    if klasse is not None:
        if isinstance(klasse, (list, tuple)) and klasse:
            placeholders = ",".join(["?"] * len(klasse))
            where_clauses.append(f"klasse IN ({placeholders})")
            params.extend(klasse)
        else:
            where_clauses.append("klasse = ?")
            params.append(klasse)

    if min_runden is not None:
        where_clauses.append("runden >= ?")
        params.append(min_runden)

    if where_clauses:
        query.append("WHERE " + " AND ".join(where_clauses))

    query.append("ORDER BY runden DESC")
    query.append("LIMIT ?")
    params.append(limit)

    sql = "\n".join(query)

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()


def get_best_15_classes(limit=15, min_avg_runden=None, klasse=None):
    query = [
        "SELECT klasse, AVG(runden) AS avg_runden",
        "FROM spieler",
        "WHERE klasse IS NOT NULL",
    ]

    params = []

    if klasse is not None:
        if isinstance(klasse, (list, tuple)) and klasse:
            placeholders = ",".join(["?"] * len(klasse))
            query.append(f"AND klasse IN ({placeholders})")
            params.extend(klasse)
        else:
            query.append("AND klasse = ?")
            params.append(klasse)

    query.extend([
        "GROUP BY klasse",
        "ORDER BY avg_runden DESC",
        "LIMIT ?",
    ])

    params.append(limit)

    if min_avg_runden is not None:
        group_index = query.index("GROUP BY klasse")
        query.insert(group_index + 1, "HAVING AVG(runden) >= ?")
        params.insert(-1, min_avg_runden)

    sql = "\n".join(query)

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()


def _build_klasse_where_clause(klasse):
    if klasse is None:
        return "", []

    if isinstance(klasse, (list, tuple)) and klasse:
        placeholders = ",".join(["?"] * len(klasse))
        return f" WHERE klasse IN ({placeholders})", list(klasse)

    return " WHERE klasse = ?", [klasse]


def get_total_kilometer(round_to_km, klasse=None):
    base = "SELECT SUM(runden) FROM spieler"
    klause, params = _build_klasse_where_clause(klasse)

    query = base + klause

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()

    if result is None or result[0] is None:
        return 0

    return result[0] * round_to_km


def get_total_runden(klasse=None):
    base = "SELECT SUM(runden) FROM spieler"
    klause, params = _build_klasse_where_clause(klasse)

    query = base + klause

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()

    if result is None or result[0] is None:
        return 0

    return result[0]


# Neue Funktion: schnellste Zeiten mit allen Filtern
def get_fastest(limit=15, klasse=None, min_runden=None, min_beste_zeit=None, max_beste_zeit=None):
    query = [
        "SELECT id, name, klasse, runden, beste_zeit",
        "FROM spieler"
    ]

    params = []
    where_clauses = ["beste_zeit IS NOT NULL"]

    if klasse is not None:
        if isinstance(klasse, (list, tuple)) and klasse:
            placeholders = ",".join(["?"] * len(klasse))
            where_clauses.append(f"klasse IN ({placeholders})")
            params.extend(klasse)
        else:
            where_clauses.append("klasse = ?")
            params.append(klasse)

    if min_runden is not None:
        where_clauses.append("runden >= ?")
        params.append(min_runden)

    if min_beste_zeit is not None:
        where_clauses.append("beste_zeit >= ?")
        params.append(min_beste_zeit)

    if max_beste_zeit is not None:
        where_clauses.append("beste_zeit <= ?")
        params.append(max_beste_zeit)

    if where_clauses:
        query.append("WHERE " + " AND ".join(where_clauses))

    query.append("ORDER BY beste_zeit ASC")
    query.append("LIMIT ?")
    params.append(limit)

    sql = "\n".join(query)

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()


def update_name_klasse(id, neuer_name=None, neue_klasse=None):
    if neuer_name is None and neue_klasse is None:
        print("Fehler: Es muss mindestens ein Wert (Name oder Klasse) angegeben werden.")
        return

    with get_conn() as conn:
        cursor = conn.cursor()

        # Prüfen, ob Spieler existiert
        cursor.execute("SELECT 1 FROM spieler WHERE id = ?", (id,))
        if cursor.fetchone() is None:
            print("Fehler: Diese ID existiert nicht.")
            return

        # Dynamisch UPDATE bauen
        updates = []
        params = []

        if neuer_name is not None:
            updates.append("name = ?")
            params.append(neuer_name)

        if neue_klasse is not None:
            updates.append("klasse = ?")
            params.append(neue_klasse)

        params.append(id)

        sql = f"UPDATE spieler SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        conn.commit()

        print(f"Spieler {id} erfolgreich aktualisiert.")

def get_kuerzeste_zeit_aller():
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, beste_zeit
            FROM spieler
            WHERE beste_zeit IS NOT NULL
            ORDER BY beste_zeit ASC
            LIMIT 1
        """)
        return cursor.fetchone()


def conn_close():
    pass


if __name__ == "__main__":
    db_in()
    with get_conn() as conn:
        for row in conn.execute("SELECT * FROM spieler"):
            print(row)