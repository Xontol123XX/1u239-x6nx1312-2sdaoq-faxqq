from waitress import serve
from serverScript import app  # pastikan nama file sesuai

serve(app, host='0.0.0.0', port=8000)
