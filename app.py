import os
import glob
import pandas as pd
from flask import Flask, send_from_directory, jsonify
from main_scanner import run_scanner

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'GuruEdge_index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    try:
        # We will run the scan. This could take a few minutes!
        print("Starting scan from web UI...")
        results = run_scanner(
            use_fundamentals=True,
            use_llm=True,
            save_csv=True,
            max_per_sector=3
        )
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        print(f"Error running scan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/latest-scan', methods=['GET'])
def get_latest_scan():
    try:
        # Find all CSV files that start with scan_
        list_of_files = glob.glob('scan_*.csv')
        if not list_of_files:
            return jsonify({"status": "error", "message": "No scan results found."}), 404

        # Find the latest created CSV file
        latest_file = max(list_of_files, key=os.path.getmtime)
        print(f"Loading latest scan file: {latest_file}")
        
        # Read the CSV
        df = pd.read_csv(latest_file)
        
        # Convert any NaN to None (null in JSON)
        df = df.where(pd.notnull(df), None)
        
        # Rename columns to match what JS expects if needed, 
        # or just let frontend handle the matching column names
        data = df.to_dict(orient='records')
        
        return jsonify({
            "status": "success", 
            "data": data, 
            "filename": latest_file,
            "timestamp": os.path.getmtime(latest_file)
        })
    except Exception as e:
        print(f"Error reading latest scan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Run the server
    print("========================================")
    print("  GURU EDGE SERVER STARTED")
    print("  Go to: http://localhost:5000")
    print("========================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
