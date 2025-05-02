from flask import Flask, render_template_string
import threading

app = Flask(__name__)

# Сюда будет передана ссылка на clients из server.py
shared_state = {
    "clients": {}
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cluster Monitor</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        table { border-collapse: collapse; width: 50%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .free { color: green; }
        .busy { color: orange; }
    </style>
</head>
<body>
    <h1>Clients Status</h1>
    <table>
        <tr>
            <th>Client ID</th>
            <th>Status</th>
        </tr>
        {% for client, status in clients.items() %}
        <tr>
            <td>{{ client }}</td>
            <td class="{{ status }}">{{ status }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, clients=shared_state["clients"])

def run_flask_app(shared_clients):
    shared_state["clients"] = shared_clients
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
