#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend and proxy API calls to the backend.
Run this to view the UI locally.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import urllib.parse
import json
import os

FRONTEND_DIR = "frontend"
BACKEND_URL = "http://localhost:5001"
PORT = 8000

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle API proxy
        if self.path.startswith("/api/"):
            self.proxy_request()
            return
        
        # Serve frontend files
        self.serve_static()
    
    def do_POST(self):
        # Handle API proxy
        if self.path.startswith("/api/"):
            self.proxy_request()
            return
        
        # For non-API POST, serve static
        self.serve_static()
    
    def proxy_request(self):
        """Proxy API requests to the backend"""
        try:
            url = f"{BACKEND_URL}{self.path}"
            
            # Read request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = None
            if content_length > 0:
                body = self.rfile.read(content_length)
            
            # Create request
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', self.headers.get('Content-Type', 'application/json'))
            req.add_header('Content-Length', str(content_length) if body else '0')
            
            # Make request to backend with timeout
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    self.send_response(response.status)
                    for header, value in response.headers.items():
                        if header.lower() not in ['connection', 'transfer-encoding', 'content-encoding']:
                            self.send_header(header, value)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(response.read())
            except urllib.error.HTTPError as e:
                # Handle HTTP errors properly
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_body = e.read() if e.fp else b'{"error":"HTTP Error"}'
                self.wfile.write(error_body)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_json = json.dumps({"error": f"Proxy error: {str(e)}"})
            self.wfile.write(error_json.encode('utf-8'))
    
    def serve_static(self):
        """Serve static frontend files"""
        path = self.path
        if path == "/":
            path = "/index.html"
        
        # Remove query string
        path = path.split('?')[0]
        
        file_path = os.path.join(FRONTEND_DIR, path.lstrip("/"))
        
        # Security: prevent directory traversal
        abs_frontend = os.path.abspath(FRONTEND_DIR)
        abs_file = os.path.abspath(file_path)
        if not abs_file.startswith(abs_frontend):
            self.send_error(403, "Forbidden")
            return
        
        if os.path.isfile(file_path):
            self.send_response(200)
            
            # Set content type
            if file_path.endswith('.html'):
                self.send_header('Content-Type', 'text/html; charset=utf-8')
            elif file_path.endswith('.js'):
                self.send_header('Content-Type', 'application/javascript')
            elif file_path.endswith('.css'):
                self.send_header('Content-Type', 'text/css')
            elif file_path.endswith('.json'):
                self.send_header('Content-Type', 'application/json')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            # Try index.html for SPA routing
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.isfile(index_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    if not os.path.exists(FRONTEND_DIR):
        print(f"Error: Frontend directory '{FRONTEND_DIR}' not found!")
        exit(1)
    
    server = HTTPServer(("", PORT), ProxyHandler)
    print(f"🚀 Frontend server running at http://localhost:{PORT}")
    print(f"📡 Proxying API calls to {BACKEND_URL}")
    print(f"📂 Serving files from {FRONTEND_DIR}/")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        server.server_close()

