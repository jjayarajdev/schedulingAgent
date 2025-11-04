# Quick Reference - New Folder Structure

**Last Updated:** October 26, 2025
**Status:** ✅ Cleaned and Organized

---

## 🗂️ Where to Find Things

| What You Need | Where It Is | Command |
|---------------|-------------|---------|
| **Main Documentation** | `README.md` | `cat README.md` |
| **Quick Start Guide** | `START_HERE.md` | `cat START_HERE.md` |
| **Backend (Flask)** | `backend/` | `cd backend` |
| **Frontend (React)** | `frontend/` | `cd frontend` |
| **Test UI** | `testing/ui/` | `cd testing/ui` |
| **Documentation** | `docs/` | `cd docs` |
| **Status Reports** | `docs/status-reports/` | `cd docs/status-reports` |
| **Summaries** | `docs/summaries/` | `cd docs/summaries` |
| **Unit Tests** | `tests/` | `cd tests` |
| **Infrastructure** | `infrastructure/` | `cd infrastructure` |
| **Lambda Functions** | `lambda/` | `cd lambda` |

---

## 🚀 Common Commands

### Start Backend
```bash
cd backend
python3 app.py
```
**URL:** http://localhost:5001

### Start Frontend
```bash
cd frontend
npm run dev
```
**URL:** http://localhost:5173

### Launch Test UI
```bash
cd testing/ui
./launch_test_ui.sh
```
**Opens:** Browser with test interface

### Run Tests
```bash
# Classification tests (v2.0)
cd tests/v2
python3 test_improved_classification.py

# Full regression
python3 test_results_table.py
```

---

## 📍 File Locations

### Configuration Files
- **Agent Config:** `backend/agent_config.json`
- **Package JSON (React):** `frontend/package.json`
- **Python Requirements:** `backend/requirements.txt`

### Important Documents
- **Cleanup Report:** `FOLDER_CLEANUP_SUMMARY.md` (root)
- **Executive Report:** `docs/status-reports/EXECUTIVE_STATUS_REPORT.md`
- **Action Items:** `docs/status-reports/NEXT_ACTION_ITEMS.md`
- **Routing Comparison:** `docs/ROUTING_COMPARISON.md`

### Test Files
- **Classification Tests:** `tests/v2/`
- **Test UI:** `testing/ui/test_ui.html`
- **Backend Tests:** `backend/test_*.py`

---

## 🔧 What Changed

### Backend
- **Before:** `frontend/backend/`
- **After:** `backend/`
- **Config:** `backend/agent_config.json`

### Frontend
- **Before:** `frontend/frontend/`
- **After:** `frontend/`
- **Cleaner!** ✅

### Test UI
- **Before:** `frontend/test_ui.html`
- **After:** `testing/ui/test_ui.html`
- **Launch:** `testing/ui/launch_test_ui.sh`

### Documentation
- **Before:** 12 MD files in root
- **After:** 2 in root, rest in `docs/`

---

## ✅ Everything Still Works

All file references have been updated:
- ✅ `backend/app.py` finds config correctly
- ✅ `testing/ui/launch_test_ui.sh` finds backend
- ✅ No broken imports
- ✅ No broken paths

---

## 📞 Need Help?

**For structure questions:**
```bash
cat FOLDER_CLEANUP_SUMMARY.md
```

**For quick start:**
```bash
cat START_HERE.md
```

**For project overview:**
```bash
cat README.md
```

---

**Created:** October 26, 2025
**Purpose:** Quick navigation reference for new folder structure
