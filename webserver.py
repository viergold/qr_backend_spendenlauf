from flask import Flask, render_template, request, jsonify, Response
from flask import redirect, url_for
from db import (
    get_klassen_money,
    get_money_per,
    get_all_klassen,
    get_students_by_class,
    get_money,
    update_total_money,
)

# Export-Funktionen
from export import (
    export_csv_class,
    export_csv_top_runden,
    export_csv_fastest,
    export_pdf_class,
    export_html_autoprint_class_table,
    export_csv_top15_class,
    export_csv_fastest_class,
    export_csv_class_ranking,
    export_csv_all_students,
    export_csv_min_runden,
    export_csv_time_filter,
    export_html_autoprint_all_classes,
    export_pdf_all_classes
)

app = Flask(__name__)

# ---------------------------------------------------------
# STARTSEITE MIT DROPDOWN + EXPORT-BUTTONS
# ---------------------------------------------------------
@app.route("/")
def index():
    klassen = get_all_klassen()
    return render_template("index_klassen.html", klassen=klassen)


# ---------------------------------------------------------
# KLASSENSEITEN
# ---------------------------------------------------------
@app.route("/klasse/<klasse>")
def klasse_page(klasse):
    students = get_students_by_class(klasse)
    spenden = {sid: get_money_per(sid) for sid, name in students}
    return render_template("klasse.html", klasse=klasse, students=students, spenden=spenden)


@app.route("/klasse/<klasse>/spenden", methods=["POST"])
def klasse_spenden(klasse):
    data = request.form
    total = 0

    for key, value in data.items():
        value = value.strip()
        if value:
            try:
                total += float(value)
            except ValueError:
                pass

    update_total_money(klasse, total)
    return redirect(url_for("success_page"))


@app.route("/success")
def success_page():
    return render_template("success.html")


@app.route("/klasse/<klasse>/erlaufenes_geld")
def klasse_erlaufenes_geld(klasse):
    students = get_students_by_class(klasse)
    geld_liste = []

    for sid, name in students:
        geld = get_money(sid)
        geld_liste.append((sid, name, geld))

    total_geld = get_klassen_money(klasse)

    return render_template(
        "klasse_erlaufenes_geld.html",
        klasse=klasse,
        geld_liste=geld_liste,
        total_geld=total_geld
    )


# ---------------------------------------------------------
# EXPORT ROUTEN – CSV
# ---------------------------------------------------------
@app.route("/export/csv/class/<klasse>")
def route_csv_class(klasse):
    return Response(
        export_csv_class(klasse),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=klasse_{klasse}.csv"}
    )


@app.route("/export/csv/top/runden")
def route_csv_top_runden():
    return Response(
        export_csv_top_runden(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=top_runden.csv"}
    )


@app.route("/export/csv/top/fastest")
def route_csv_fastest():
    return Response(
        export_csv_fastest(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=top_fastest.csv"}
    )


@app.route("/export/csv/top15/<klasse>")
def route_csv_top15_class(klasse):
    return Response(
        export_csv_top15_class(klasse),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=top15_{klasse}.csv"}
    )


@app.route("/export/csv/fastest/<klasse>")
def route_csv_fastest_class(klasse):
    return Response(
        export_csv_fastest_class(klasse),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fastest_{klasse}.csv"}
    )


@app.route("/export/csv/class_ranking")
def route_csv_class_ranking():
    return Response(
        export_csv_class_ranking(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=klassen_ranking.csv"}
    )


@app.route("/export/csv/all_students")
def route_csv_all_students():
    return Response(
        export_csv_all_students(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=alle_schueler.csv"}
    )


@app.route("/export/csv/min_runden/<int:min_runden>")
def route_csv_min_runden(min_runden):
    return Response(
        export_csv_min_runden(min_runden),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=min_runden_{min_runden}.csv"}
    )


@app.route("/export/csv/time_filter/<float:max_time>")
def route_csv_time_filter(max_time):
    return Response(
        export_csv_time_filter(max_time),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=time_filter_{max_time}.csv"}
    )


# ---------------------------------------------------------
# EXPORT ROUTEN – PDF
# ---------------------------------------------------------
@app.route("/export/pdf/class/<klasse>")
def route_pdf_class(klasse):
    return Response(
        export_pdf_class(klasse),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=klasse_{klasse}.pdf"}
    )


@app.route("/export/pdf/all_classes")
def route_pdf_all_classes():
    pdfs = export_pdf_all_classes()
    # Hinweis: ZIP kann ich dir bauen, wenn du willst
    return jsonify({"status": "PDFs erzeugt", "klassen": list(pdfs.keys())})


# ---------------------------------------------------------
# EXPORT ROUTEN – HTML DRUCK
# ---------------------------------------------------------
@app.route("/druck/<klasse>")
def route_druck_class(klasse):
    return Response(
        export_html_autoprint_class_table(klasse),
        mimetype="text/html"
    )


@app.route("/druck/alle")
def route_druck_all_classes():
    html_pages = export_html_autoprint_all_classes()
    return Response(
        "<hr>".join(html_pages.values()),
        mimetype="text/html"
    )


# ---------------------------------------------------------
# SERVER STARTEN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6500)