import sqlite3
import unicodedata
import os
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "databases", "cours_ens.db")

def strip_accents(s):
    if not s: return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("STRIP_ACCENTS", 1, strip_accents)
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/schedule")
def schedule():
    return render_template("schedule.html")

@app.route("/api/courses")
def api_courses():
    query = request.args.get("q", "").strip()
    dept = request.args.get("dept", "").strip()
    type_cours = request.args.get("type", "").strip()
    periode = request.args.get("periode", "").strip()
    jour = request.args.get("jour", "").strip()

    sql = """
        SELECT DISTINCT c.id, c.departement, c.titre, c.type, c.ects, c.volume_horaire,
               c.periode, c.code_ue, c.lien, c.notes,
               GROUP_CONCAT(DISTINCT p.nom) as professeurs,
               GROUP_CONCAT(DISTINCT s.jour) as jour,
               GROUP_CONCAT(DISTINCT s.horaire_brut) as horaire_brut,
               GROUP_CONCAT(DISTINCT s.lieu) as lieu,
               GROUP_CONCAT(DISTINCT 
                   COALESCE(
                       CASE WHEN s.jour IS NOT NULL AND s.heure_debut IS NOT NULL 
                       THEN s.jour || ' (' || s.heure_debut || '-' || s.heure_fin || ')' END,
                       s.horaire_brut, 
                       s.jour
                   )
               ) as horaire_affichage
        FROM courses c
        LEFT JOIN course_professors cp ON c.id = cp.course_id
        LEFT JOIN professors p ON cp.professor_id = p.id
        LEFT JOIN schedules s ON c.id = s.course_id
        WHERE 1=1
    """
    params = []

    if query:
        sql += " AND (STRIP_ACCENTS(c.titre) LIKE ? OR STRIP_ACCENTS(p.nom) LIKE ? OR STRIP_ACCENTS(c.departement) LIKE ?)"
        q_norm = f"%{strip_accents(query)}%"
        params.extend([q_norm, q_norm, q_norm])
    if dept:
        sql += " AND c.departement = ?"
        params.append(dept)
    if type_cours:
        sql += " AND STRIP_ACCENTS(c.type) LIKE ?"
        params.append(f"%{strip_accents(type_cours)}%")
    if periode:
        sql += " AND STRIP_ACCENTS(c.periode) LIKE ?"
        params.append(f"%{strip_accents(periode)}%")
    if jour:
        sql += " AND STRIP_ACCENTS(s.jour) = ?"
        params.append(strip_accents(jour))

    sql += " GROUP BY c.id ORDER BY c.departement, c.titre"

    # Context manager pour auto-close la DB
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        depts = [r[0] for r in conn.execute("SELECT DISTINCT departement FROM courses WHERE departement != '' AND departement IS NOT NULL ORDER BY departement").fetchall()]
        types = [r[0] for r in conn.execute("SELECT DISTINCT type FROM courses WHERE type != '' AND type IS NOT NULL AND type != '-' ORDER BY type").fetchall()]

    return jsonify(courses=[dict(r) for r in rows], departments=depts, types=types)

@app.route("/api/plannable_courses", methods=["GET"])
def get_plannable_courses():
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT 
            c.id AS course_id, c.departement, c.titre, c.type, c.ects,
            c.volume_horaire, c.periode, c.code_ue, c.lien, c.notes,
            s.id AS schedule_id, s.jour, s.heure_debut, s.heure_fin, s.lieu, s.horaire_brut
        FROM courses c
        JOIN schedules s ON c.id = s.course_id
        WHERE s.jour IS NOT NULL AND s.jour != ''
          AND s.heure_debut IS NOT NULL AND s.heure_debut != ''
          AND s.heure_fin IS NOT NULL AND s.heure_fin != ''
        ORDER BY c.id, s.id
    """
    rows = cur.execute(query).fetchall()
    conn.close()

    courses = {}
    for row in rows:
        cid = row["course_id"]
        if cid not in courses:
            courses[cid] = {
                "id": cid,
                "departement": row["departement"],
                "titre": row["titre"],
                "type": row["type"],
                "ects": row["ects"],
                "volume_horaire": row["volume_horaire"],
                "periode": row["periode"],
                "code_ue": row["code_ue"],
                "lien": row["lien"],
                "notes": row["notes"],
                "schedules": []
            }
        courses[cid]["schedules"].append({
            "id": row["schedule_id"],
            "jour": row["jour"],
            "heure_debut": row["heure_debut"],
            "heure_fin": row["heure_fin"],
            "lieu": row["lieu"],
            "horaire_brut": row["horaire_brut"]
        })

    return jsonify(list(courses.values()))

if __name__ == "__main__":
    app.run(debug=True, port=5000)