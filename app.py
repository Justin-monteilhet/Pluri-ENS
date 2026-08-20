from flask import Flask, jsonify, render_template, request
import sqlite3

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("./databases/cours_ens.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/courses")
def api_courses():
    query = request.args.get("q", "").strip()
    dept = request.args.get("dept", "").strip()
    periode = request.args.get("periode", "").strip()
    jour = request.args.get("jour", "").strip()
    conn = get_db()
    sql = """
        SELECT DISTINCT c.id, c.departement, c.titre, c.type, c.ects, c.volume_horaire,
               c.periode, c.code_ue, c.lien, c.notes,
               GROUP_CONCAT(DISTINCT p.nom) as professeurs,
               s.jour, s.heure_debut, s.heure_fin, s.lieu, s.horaire_brut
        FROM courses c
        LEFT JOIN course_professors cp ON c.id = cp.course_id
        LEFT JOIN professors p ON cp.professor_id = p.id
        LEFT JOIN schedules s ON c.id = s.course_id
        WHERE 1=1
    """
    params = []
    if query:
        sql += " AND (c.titre LIKE ? OR p.nom LIKE ? OR c.departement LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if dept:
        sql += " AND c.departement = ?"
        params.append(dept)
    if periode:
        sql += " AND c.periode LIKE ?"
        params.append(f"%{periode}%")
    if jour:
        sql += " AND s.jour = ?"
        params.append(jour)
    sql += " GROUP BY c.id ORDER BY c.departement, c.titre"
    rows = conn.execute(sql, params).fetchall()
    depts = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT departement FROM courses WHERE departement != '' ORDER BY departement"
        ).fetchall()
    ]
    conn.close()
    return jsonify(courses=[dict(r) for r in rows], departments=depts)


if __name__ == "__main__":
    app.run(debug=True, port=5000)