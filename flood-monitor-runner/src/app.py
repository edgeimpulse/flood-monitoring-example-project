from flask import Flask, send_file

import io, os
import threading
import time
from datetime import datetime
import matplotlib
matplotlib.use('Agg')

import flood_monitor
app = Flask(__name__, template_folder='../views', static_folder='../views/public')

def generate_plot():
    while True:
        # Run flood-monitor.py here:
        flood_monitor.main()    

        # Sleep for 15 minutes
        time.sleep(900)

# Start the background thread
thread = threading.Thread(target=generate_plot)
thread.daemon = True
thread.start()

@app.route('/plot')
def plot():
    if not os.path.exists('static/plot.png'):
        return 'Plot not ready yet, please try again in a few minutes'
    return send_file('../static/plot.png', mimetype='image/png')
@app.route('/plot_all')
def plot_all():
    if not os.path.exists('static/plot_all.png'):
        return 'Plot not ready yet, please try again in a few minutes'
    return send_file('../static/plot_all.png', mimetype='image/png')
@app.route('/output.csv')
def download_csv():
    if not os.path.exists('static/output.csv'):
        return 'CSV file not ready yet, please try again in a few minutes'
    return send_file('../static/output.csv', mimetype='text/csv', as_attachment=True)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)