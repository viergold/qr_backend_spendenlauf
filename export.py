import csv
import io
from fpdf import FPDF
from db import (
    get_students_by_class,
    get_top_15,
    get_fastest,
    get_all_klassen,
    get_conn
)

# ---------------------------------------------------------
# Hilfsfunktion: Nachnamen extrahieren
# ---------------------------------------------------------
def extract_lastname(fullname):
    return fullname.strip().split(" ")[-1].lower()


# ---------------------------------------------------------
# CSV EXPORT – Klasse
# ---------------------------------------------------------
def export_csv_class(klasse):
    students = get_students_by_class(klasse)
    students_sorted = sorted(students, key=lambda x: extract_lastname(x[1]))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Header
    writer.writerow(["ID", "Name", "Klasse", "Runden"])

    # Jede Zeile korrekt schreiben
    for sid, name in students_sorted:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
            runden = cur.fetchone()[0]

        writer.writerow([sid, name, klasse, runden])

    # UTF‑8 BOM für Excel
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# CSV EXPORT – Top Runden
# ---------------------------------------------------------
def export_csv_top_runden(limit=10):
    top = get_top_15(limit=limit)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Name", "Klasse", "Runden"])

    for row in top:
        writer.writerow([row[0], row[1], row[2], row[3]])

    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# CSV EXPORT – Schnellste Zeiten
# ---------------------------------------------------------
def export_csv_fastest(limit=10):
    fastest = get_fastest(limit=limit)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Name", "Klasse", "Runden", "Beste Zeit"])

    for row in fastest:
        writer.writerow([row[0], row[1], row[2], row[3], row[4]])

    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# PDF EXPORT – Klasse (schwarz-weiß, hoher Kontrast)
# ---------------------------------------------------------
def export_pdf_class(klasse):
    students = get_students_by_class(klasse)
    students_sorted = sorted(students, key=lambda x: extract_lastname(x[1]))

    pdf = FPDF(format="A4")
    pdf.add_page()

    # Titel
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, f"Klasse {klasse}", ln=True, align="C")
    pdf.ln(5)

    # Tabellenkopf
    pdf.set_font("Arial", "B", 12)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.6)

    pdf.cell(100, 10, "Name", border=1)
    pdf.cell(40, 10, "ID", border=1)
    pdf.cell(40, 10, "Runden", border=1)
    pdf.ln()

    # Tabelleninhalt
    pdf.set_font("Arial", "", 11)
    pdf.set_line_width(0.4)

    for sid, name in students_sorted:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
            runden = cur.fetchone()[0]

        pdf.cell(100, 8, name, border=1)
        pdf.cell(40, 8, str(sid), border=1)
        pdf.cell(40, 8, str(runden), border=1)
        pdf.ln()

    return bytes(pdf.output(dest="S"))


# ---------------------------------------------------------
# HTML DRUCK – Klasse (A4, schwarz-weiß, hoher Kontrast)
# ---------------------------------------------------------
def export_html_autoprint_class_table(klasse):
    students = get_students_by_class(klasse)
    students_sorted = sorted(students, key=lambda x: extract_lastname(x[1]))

    rows = ""
    for sid, name in students_sorted:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
            runden = cur.fetchone()[0]

        rows += f"""
            <tr>
                <td>{name}</td>
                <td>{sid}</td>
                <td>{runden}</td>
            </tr>
        """

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Druck – Spendenlauf</title>

        <style>
            @page {{
                size: A4;
                margin: 18mm;
            }}

            body {{
                font-family: Arial, sans-serif;
                color: #000;
            }}

            h2 {{
                text-align: center;
                margin-bottom: 10px;
                font-size: 22px;
                font-weight: bold;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }}

            th, td {{
                border: 2px solid #000;
                padding: 6px 8px;
            }}

            th {{
                font-weight: bold;
                background: #fff;
                border-bottom: 3px solid #000;
            }}

            tr:nth-child(even) td {{
                background: #f5f5f5;
            }}

            .page {{
                page-break-after: always;
            }}
        </style>

        <script>
            window.onload = function() {{
                window.print();
                setTimeout(() => window.history.back(), 500);
            }};
        </script>
    </head>

    <body>
        <div class="page">
            <h2>Klasse {klasse}</h2>
            <table>
                <tr>
                    <th>Name</th>
                    <th>ID</th>
                    <th>Runden</th>
                </tr>
                {rows}
            </table>
        </div>
    </body>
    </html>
    """

    return html


# ---------------------------------------------------------
# TOP 15 PRO KLASSE
# ---------------------------------------------------------
def export_csv_top15_class(klasse):
    students = get_students_by_class(klasse)

    enriched = []
    for sid, name in students:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
            runden = cur.fetchone()[0]
        enriched.append((sid, name, runden))

    students_sorted = sorted(enriched, key=lambda x: x[2], reverse=True)[:15]

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Name", "ID", "Runden"])

    for sid, name, runden in students_sorted:
        writer.writerow([name, sid, runden])

    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# SCHNELLSTE ZEITEN PRO KLASSE
# ---------------------------------------------------------
def export_csv_fastest_class(klasse):
    students = get_students_by_class(klasse)

    enriched = []
    for sid, name in students:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT beste_zeit FROM spieler WHERE id = ?", (sid,))
            beste = cur.fetchone()[0]
        enriched.append((sid, name, beste))

    students_sorted = sorted(enriched, key=lambda x: x[2] if x[2] else 999999)[:15]

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Name", "ID", "Beste Zeit"])

    for sid, name, beste in students_sorted:
        writer.writerow([name, sid, beste])

    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# KLASSEN-RANKING
# ---------------------------------------------------------
def export_csv_class_ranking():
    klassen = get_all_klassen()
    rows = [["Klasse", "Durchschnittsrunden"]]

    for k in klassen:
        students = get_students_by_class(k)

        runden_liste = []
        for sid, name in students:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
                runden = cur.fetchone()[0]
            runden_liste.append(runden)

        avg = sum(runden_liste) / len(runden_liste) if runden_liste else 0
        rows.append([k, round(avg, 2)])

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerows(rows)
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# GESAMTLISTE ALLER SCHÜLER
# ---------------------------------------------------------
def export_csv_all_students():
    klassen = get_all_klassen()
    rows = [["Klasse", "Name", "ID", "Runden", "Beste Zeit"]]

    for k in klassen:
        students = get_students_by_class(k)

        for sid, name in students:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT runden, beste_zeit FROM spieler WHERE id = ?", (sid,))
                runden, beste = cur.fetchone()

            rows.append([k, name, sid, runden, beste])

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerows(rows)
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# MINDEST-RUNDEN-FILTER
# ---------------------------------------------------------
def export_csv_min_runden(min_runden):
    rows = [["Name", "ID", "Klasse", "Runden"]]

    klassen = get_all_klassen()
    for k in klassen:
        students = get_students_by_class(k)

        for sid, name in students:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT runden FROM spieler WHERE id = ?", (sid,))
                runden = cur.fetchone()[0]

            if runden >= min_runden:
                rows.append([name, sid, k, runden])

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerows(rows)
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# ZEIT-FILTER
# ---------------------------------------------------------
def export_csv_time_filter(max_time):
    max_time = float(max_time)

    rows = [["Name", "ID", "Klasse", "Beste Zeit"]]

    klassen = get_all_klassen()
    for k in klassen:
        students = get_students_by_class(k)

        for sid, name in students:
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT beste_zeit FROM spieler WHERE id = ?", (sid,))
                beste = cur.fetchone()[0]

            if beste and beste <= max_time:
                rows.append([name, sid, k, beste])

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerows(rows)
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------
# ALLE KLASSEN – PDF
# ---------------------------------------------------------
def export_pdf_all_classes():
    klassen = get_all_klassen()
    pdfs = {}

    for k in klassen:
        pdfs[k] = export_pdf_class(k)

    return pdfs


# ---------------------------------------------------------
# ALLE KLASSEN – HTML DRUCK
# ---------------------------------------------------------
def export_html_autoprint_all_classes():
    klassen = get_all_klassen()
    html_pages = {}

    for k in klassen:
        html_pages[k] = export_html_autoprint_class_table(k)

    return html_pages