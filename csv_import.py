import csv
from db import db_in, spieler_hinzufuegen, conn_close
import helper

def importiere_csv(dateipfad):
    db_in()

    with open(dateipfad, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        # Header bereinigen (Leerzeichen entfernen)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        for row in reader:
            # Auch Werte bereinigen
            row = {k.strip(): v.strip() for k, v in row.items()}

            try:
                schueler_id = int(row["schueler_id"])
            except ValueError:
                print(f"Ungültige ID in Zeile: {row}")
                continue

            name = f"{row['vorname']} {row['nachname']}"
            klasse = row["klasse"]

            spieler_hinzufuegen(schueler_id, name, klasse)

    print("CSV‑Import abgeschlossen.")
    conn_close()


if __name__ == "__main__":

    helper.comma_to_semicolon("schueler.csv", "schueler.csv")
    helper.semicolon_to_comma("schueler.csv", "schueler.csv")
    helper.normalisiere_spaltennamen("schueler.csv")
    importiere_csv("schueler.csv")
