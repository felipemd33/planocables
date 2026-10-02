"""Prototipo P6: lista de corte de ductos y rieles desde el topografico. http://127.0.0.1:8770"""
import os, tempfile, traceback
from flask import Flask, request, jsonify, send_file
import leer

app = Flask(__name__)
AQUI = os.path.dirname(os.path.abspath(__file__))


@app.get('/')
def index():
    return send_file(os.path.join(AQUI, 'index.html'))


@app.post('/leer')
def leer_pdf():
    f = request.files.get('pdf')
    if not f:
        return jsonify(error='Cargá un PDF'), 400
    fd, p = tempfile.mkstemp(suffix='.pdf'); os.close(fd)
    try:
        f.save(p)
        d = leer.leer(p); d['archivo'] = f.filename
        return jsonify(d)
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500
    finally:
        os.remove(p)


if __name__ == '__main__':
    app.run('127.0.0.1', int(os.environ.get('P6_PORT', 8770)))
