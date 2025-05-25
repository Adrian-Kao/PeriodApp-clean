from flask import Flask, render_template
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

@app.route('/')
def map_view():
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    return render_template('map.html', GOOGLE_MAPS_API_KEY=api_key)

if __name__ == '__main__':
    app.run(debug=True)
