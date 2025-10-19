# How to View Swagger UI Documentation

**Problem:** Opening `BULK_OPS_API_DOCS.html` directly shows "Failed to fetch ./BULK_OPS_API_SWAGGER.yaml" error

**Reason:** Browsers block loading local files due to CORS (Cross-Origin Resource Sharing) security policy

---

## ✅ Solution 1: Use the Provided Script (Easiest)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs

# Run the documentation server
./serve-docs.sh
```

**What it does:**
- Starts a local HTTP server on port 8080
- Automatically opens the Swagger UI in your browser
- Press Ctrl+C to stop the server

**URL:** http://localhost:8080/BULK_OPS_API_DOCS.html

---

## ✅ Solution 2: Manual HTTP Server

If `serve-docs.sh` doesn't work, use Python's built-in HTTP server:

### Using Python 3 (Recommended)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs

# Start HTTP server
python3 -m http.server 8080

# Open browser manually
open http://localhost:8080/BULK_OPS_API_DOCS.html
```

### Using Python 2 (Fallback)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs

# Start HTTP server
python -m SimpleHTTPServer 8080

# Open browser manually
open http://localhost:8080/BULK_OPS_API_DOCS.html
```

### Using Node.js http-server

```bash
# Install http-server globally
npm install -g http-server

# Start server
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs
http-server -p 8080

# Open browser
open http://localhost:8080/BULK_OPS_API_DOCS.html
```

---

## ✅ Solution 3: View the YAML Directly

If you just need to read the API specification without the interactive UI:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/docs

# View in terminal
less BULK_OPS_API_SWAGGER.yaml

# Or open in text editor
open -a "Visual Studio Code" BULK_OPS_API_SWAGGER.yaml
```

---

## ✅ Solution 4: Import into Swagger Editor Online

1. Go to: https://editor.swagger.io/
2. Click **File → Import file**
3. Select `BULK_OPS_API_SWAGGER.yaml`
4. View and edit the spec interactively online

**Pros:**
- No local server needed
- Full Swagger UI features
- Can edit and validate the spec

**Cons:**
- Requires internet connection
- Uploading spec to external site (no sensitive data in this spec)

---

## ✅ Solution 5: Import into Postman

The Postman collection is already provided and doesn't have CORS issues:

```bash
# Open Postman
open -a Postman

# Import the collection
# File → Import → Select BULK_OPS_POSTMAN_COLLECTION.json
```

**Collection includes:**
- 11 pre-configured API requests
- Example payloads
- Expected responses
- AWS Signature v4 authentication template

---

## 🔍 Troubleshooting

### Error: "Port 8080 already in use"

```bash
# Find process using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use a different port
python3 -m http.server 8081
open http://localhost:8081/BULK_OPS_API_DOCS.html
```

### Error: "python3: command not found"

```bash
# Check if Python is installed
python --version

# If installed, use python instead
python -m SimpleHTTPServer 8080
```

### Error: "serve-docs.sh: Permission denied"

```bash
# Make script executable
chmod +x serve-docs.sh

# Then run it
./serve-docs.sh
```

---

## 📝 Why CORS Blocks Local Files

When you open an HTML file directly (`file:///path/to/file.html`), browsers apply strict security policies:

- ❌ Cannot load other local files via fetch/XMLHttpRequest
- ❌ Cannot load files from different origins
- ✅ Can load files from the same HTTP server

**Solution:** Serve files via HTTP server (any of the methods above)

---

## 🎯 Recommended Method

**For quick viewing:**
```bash
./serve-docs.sh
```

**For development/testing:**
```bash
python3 -m http.server 8080 &
# Runs in background
```

**For sharing:**
- Import into Swagger Editor online
- Or use Postman collection

---

## 📚 Alternative Documentation Formats

If Swagger UI doesn't work, you have these alternatives:

| Format | File | Use Case |
|--------|------|----------|
| **Interactive Swagger UI** | `BULK_OPS_API_DOCS.html` | Full featured API explorer |
| **OpenAPI YAML** | `BULK_OPS_API_SWAGGER.yaml` | Machine-readable spec |
| **Postman Collection** | `BULK_OPS_POSTMAN_COLLECTION.json` | API testing |
| **Markdown Docs** | `API_DOCUMENTATION_README.md` | Complete documentation |
| **Quick Reference** | `API_QUICK_REFERENCE.md` | One-page cheat sheet |

---

**Quick Link:** After starting the server, visit:
http://localhost:8080/BULK_OPS_API_DOCS.html

**Documentation:** See `API_DOCUMENTATION_INDEX.md` for all available docs
