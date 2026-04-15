def comma_to_semicolon(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(",", ";")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def semicolon_to_comma(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(";", ",")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def normalisiere_spaltennamen(fieldnames):
    # Definiere erlaubte Zielnamen
    zielnamen = {
        "schueler_id": ["schueler_id", "schuelerid", "schueler id", "id", "sid", "id_schueler"],
        "vorname": ["vorname", "vor name", "vname", "first", "firstname"],
        "nachname": ["nachname", "nach name", "lname", "last", "lastname"],
        "klasse": ["klasse", "class", "klassenstufe"]
    }

    mapping = {}

    for original in fieldnames:
        clean = original.strip().lower().replace("_", " ")

        gefunden = False
        for ziel, varianten in zielnamen.items():
            if clean in varianten:
                mapping[original] = ziel
                gefunden = True
                break

        if not gefunden:
            # Falls unbekannt → Originalname behalten
            mapping[original] = original.strip()

    return mapping

