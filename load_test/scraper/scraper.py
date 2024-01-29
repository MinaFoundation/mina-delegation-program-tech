from flask import Flask, request, jsonify
import json
import datetime
import os

app = Flask(__name__)


@app.route("/")
def start_page():
    message = """
    <h1>Scrapper</h1>
    <p>Scrapper is a service that receives data from the load test and saves it to a file.</p>
    <p>It is a simple Flask app that runs on port 8080.</p>
    <p>It has two endpoints:</p>
    <ul>
        <li>GET <a href="/">/</a></li>
        <li>POST <a href="/v1/submit">/v1/submit</a></li>
    </ul>
    <p>GET / returns this message.</p>
    <p>POST /v1/submit receives a JSON payload and saves it to a file.</p>
    <p>It returns a JSON response with a message and the path to the file.</p>
    """
    return message


@app.route("/v1/submit", methods=["POST"])
def submit():
    data = request.json
    now = datetime.datetime.now()
    filename = now.strftime("payload-%Y-%m-%d-%H:%M:%S,%f") + ".json"
    directory = "requests"

    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename)
    with open(filepath, "w") as f:
        json.dump(data, f)

    return jsonify({"message": "Data received and saved", "file": filepath}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
