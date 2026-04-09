from flask import Flask, render_template, request, jsonify
from db import (
    db_in,
    get_all_klassen,
    get_students_by_class,
    get_money,
    update_total_money,
)

app = Flask(__name__)





# Startseite: Klassenübersicht
@app.route("/")
def index():
    klassen = get_all_klassen()
    return render_template("index.html", klassen=klassen)


# Klassenseite: Spenden für die Klasse eintragen
@app.route("/klasse/<klasse>")
def klasse_page(klasse):
    students = get_students_by_class(klasse)
    return render_template("klasse.html", klasse=klasse, students=students)


@app.route("/klasse/<klasse>/spenden", methods=["POST"])
def klasse_spenden(klasse):
    data = request.form

    total = 0
    for key, value in data.items():
        value = value.strip()
        if value:
            try:
                total += int(value)
            except ValueError:
                pass

    update_total_money(klasse, total)

    return jsonify({
        "status": "ok",
        "klasse": klasse,
        "total_spenden": total
    })


# Klassenseite: erlaufene Geldbeträge pro Schüler anzeigen
@app.route("/klasse/<klasse>/erlaufenes_geld")
def klasse_erlaufenes_geld(klasse):
    students = get_students_by_class(klasse)

    geld_liste = []
    for sid, name in students:
        geld = get_money(sid)
        geld_liste.append((sid, name, geld))

    return render_template(
        "klasse_erlaufenes_geld.html",
        klasse=klasse,
        geld_liste=geld_liste
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6500)