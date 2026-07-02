#!/usr/bin/env python3
import os
import sys
import json
import csv
import re
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Config
PORT = 8088
RESULTS_DIR = os.path.expanduser("~/job_scout_results")
CSV_FILENAME = "job_scout_tracker.csv"

# Global state for run logs
run_logs = []
run_status = {"running": False}
lock = threading.Lock()

def get_safe_folder_name(company, title):
    safe_company = re.sub(r'[^\w\s-]', '', company).strip().replace(' ', '_')
    safe_title   = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    return f"{safe_company}_{safe_title}"[:50]

def run_job_scout():
    global run_logs, run_status
    with lock:
        if run_status["running"]:
            return
        run_status["running"] = True
        run_logs.clear()
        run_logs.append("=== Starting Job Scout Pipeline ===\n")
    
    try:
        # Run python job_scout_v3.py in a subprocess
        # We run it in the same directory as this server
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "job_scout_v3.py")
        
        # Specify environment to run python unbuffered so we get real-time stdout
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=script_dir,
            text=True,
            env=env
        )
        
        for line in process.stdout:
            with lock:
                run_logs.append(line)
        
        process.wait()
        with lock:
            run_logs.append(f"\n=== Process finished with exit code {process.returncode} ===\n")
    except Exception as e:
        with lock:
            run_logs.append(f"\n[Error] Failed to run Job Scout: {e}\n")
    finally:
        with lock:
            run_status["running"] = False

class DashboardHandler(BaseHTTPRequestHandler):
        
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/" or path == "/index.html":
            self.serve_static("index.html", "text/html")
        elif path == "/api/jobs":
            self.handle_get_jobs()
        elif path == "/api/logs":
            self.handle_get_logs()
        else:
            self.send_error(404, "File Not Found")
            
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/run":
            self.handle_run_scout()
        elif path == "/api/update-status":
            self.handle_update_status()
        elif path == "/api/open-folder":
            self.handle_open_folder()
        else:
            self.send_error(404, "API Endpoint Not Found")

    def serve_static(self, filename, content_type):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, filename)
        
        if not os.path.exists(file_path):
            self.send_error(404, f"File {filename} not found")
            return
            
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())
            
    def handle_get_jobs(self):
        csv_path = os.path.join(RESULTS_DIR, CSV_FILENAME)
        if not os.path.exists(csv_path):
            self.send_json({"jobs": [], "message": "Tracker file does not exist yet. Run Job Scout first."})
            return
            
        jobs = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Calculate safe folder name
                    row["Folder"] = get_safe_folder_name(row["Company"], row["Job Title"])
                    jobs.append(row)
            # Sort jobs: higher score first
            jobs.sort(key=lambda x: float(x.get("Score", 0)), reverse=True)
            self.send_json({"jobs": jobs})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_get_logs(self):
        with lock:
            response_data = {
                "running": run_status["running"],
                "logs": "".join(run_logs)
            }
        self.send_json(response_data)

    def handle_run_scout(self):
        global run_status
        with lock:
            already_running = run_status["running"]
            
        if already_running:
            self.send_json({"status": "already_running", "message": "Job Scout is already executing."})
            return
            
        # Spawn thread to run the process
        t = threading.Thread(target=run_job_scout)
        t.daemon = True
        t.start()
        self.send_json({"status": "started", "message": "Job Scout execution started."})

    def handle_update_status(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json({"error": "Missing payload"}, status=400)
            return
            
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
            company = data.get("company")
            title = data.get("title")
            new_status = data.get("status")
            
            if not company or not title or not new_status:
                self.send_json({"error": "Missing fields"}, status=400)
                return
                
            csv_path = os.path.join(RESULTS_DIR, CSV_FILENAME)
            if not os.path.exists(csv_path):
                self.send_json({"error": "Tracker file does not exist"}, status=404)
                return
                
            rows = []
            updated = False
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['Company'] == company and row['Job Title'] == title:
                        row['Status'] = new_status
                        updated = True
                    rows.append(row)
                    
            if updated:
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                self.send_json({"success": True, "message": "Job status updated."})
            else:
                self.send_json({"error": "Job not found in tracker"}, status=404)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_open_folder(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_json({"error": "Missing payload"}, status=400)
            return
            
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
            date_found = data.get("date")
            folder_name = data.get("folder")
            
            if not date_found or not folder_name:
                self.send_json({"error": "Missing parameters"}, status=400)
                return
                
            # Basic validation to prevent directory traversal
            if ".." in folder_name or "/" in folder_name or "\\" in folder_name:
                self.send_json({"error": "Invalid folder name"}, status=400)
                return
                
            folder_path = os.path.join(RESULTS_DIR, date_found, folder_name)
            if os.path.exists(folder_path):
                # On Windows, os.startfile opens Explorer. On macOS/Linux, we use open/xdg-open
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder_path])
                else:
                    subprocess.Popen(["xdg-open", folder_path])
                self.send_json({"success": True, "message": f"Opened folder: {folder_name}"})
            else:
                self.send_json({"error": f"Folder {folder_name} not found locally at path: {folder_path}"}, status=404)
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def main():
    # Make sure results directory exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Try importing ThreadingHTTPServer if available (Python 3.7+)
    try:
        from http.server import ThreadingHTTPServer
        server_class = ThreadingHTTPServer
    except ImportError:
        server_class = HTTPServer
        
    server = server_class(("", PORT), DashboardHandler)
    print("=" * 60)
    print(f"Job Scout Dashboard running at: http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        server.server_close()

if __name__ == "__main__":
    main()
