# 🚨 STREAMLIT CLOUD FIX - Do This Now

Your app is failing because packages aren't installing. Follow these exact steps:

## Step 1: Update Your Repository

Replace your current `app.py` with the new `app_fixed.py` file I created:

```bash
# If using git:
cp app_fixed.py app.py
git add app.py requirements.txt packages.txt
git commit -m "Fix package installation"
git push
```

## Step 2: Verify These Files Exist in ROOT

Your GitHub repo must have these files **in the root directory**:

```
your-repo/
├── app.py                 ← Use the new app_fixed.py
├── requirements.txt       ← Updated with >= versions
├── packages.txt           ← System dependencies
├── database_setup.sql
└── .streamlit/
    └── (don't commit secrets.toml)
```

## Step 3: Fix requirements.txt

Your `requirements.txt` should be:

```txt
streamlit>=1.31.0
supabase>=2.3.0
langchain>=0.1.0
langchain-anthropic>=0.1.0
langchain-community>=0.0.20
sentence-transformers>=2.2.0
anthropic>=0.18.0
python-dotenv>=1.0.0
```

Notice: Using `>=` instead of `==` for better compatibility.

## Step 4: Create packages.txt

Create a file called `packages.txt` in root with:

```txt
build-essential
python3-dev
```

## Step 5: Streamlit Cloud Settings

1. Go to https://share.streamlit.io
2. Find your app
3. Click "⋮" menu → "Settings"
4. Verify:
   - **Main file path**: `app.py`
   - **Python version**: 3.10 or 3.11

5. Add secrets (Settings → Secrets):
```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Step 6: Reboot

1. Click "Manage app" (bottom right of your app)
2. Click "Reboot app"
3. **Wait 3-5 minutes** for packages to install
4. Watch the logs for errors

## Step 7: Check Status

The new `app_fixed.py` will show you:
- ✅ Which packages installed successfully
- ❌ Which packages failed (with error details)
- Step-by-step what to fix next

## If It STILL Doesn't Work

### Option A: Use Simpler Requirements

Replace `requirements.txt` with minimal versions:

```txt
streamlit
supabase
anthropic
sentence-transformers
python-dotenv
```

This lets pip figure out compatible versions automatically.

### Option B: Deploy to Hugging Face Instead

Streamlit Cloud sometimes has package installation issues. Try Hugging Face Spaces:

1. Go to https://huggingface.co/spaces
2. Create new Space
3. Choose "Streamlit" as SDK
4. Upload your files
5. Add secrets in Settings

### Option C: Local Development Only

For now, just run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

This always works. Once stable, try deploying again.

## Common Streamlit Cloud Issues

### Issue: "Failed to build sentence-transformers"
**Fix**: Add to packages.txt:
```
build-essential
python3-dev
rust
```

### Issue: "Version conflict"
**Fix**: Use `>=` in requirements.txt instead of `==`

### Issue: "App keeps restarting"
**Fix**: Check app logs for memory issues. Sentence-transformers needs ~1GB RAM.

### Issue: "Secrets not found"
**Fix**: 
1. Go to Settings → Secrets in Streamlit Cloud
2. Use TOML format (not JSON)
3. No quotes around keys
4. Reboot app after saving

## Test Locally First

Before deploying, verify everything works locally:

```bash
# Create fresh environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Test imports
python -c "from supabase import create_client; print('✅ Works!')"

# Run app
streamlit run app.py
```

If local works but Streamlit Cloud fails, it's a deployment configuration issue.

## Quick Debug Commands

```bash
# Check if files are in root
ls -la
# Should show: app.py, requirements.txt, packages.txt

# Verify requirements.txt format
cat requirements.txt
# Should have package names, one per line

# Test Python version
python --version
# Should be 3.9, 3.10, or 3.11
```

## The New app_fixed.py Does This:

1. **Shows package status** - You'll see exactly what's installed
2. **Graceful errors** - Clear messages about what's wrong
3. **Step-by-step fixes** - Tells you what to do next
4. **Validates everything** - Checks packages, credentials, database

Use this to diagnose the exact issue!

## Contact Support

If nothing works:
1. Screenshot the package status from app_fixed.py
2. Copy the full error from Streamlit Cloud logs
3. Share your requirements.txt content
4. Open GitHub issue or contact me

---

**TL;DR:**
1. Use `app_fixed.py` as your `app.py`
2. Update `requirements.txt` with `>=` versions
3. Add `packages.txt`
4. Reboot app in Streamlit Cloud
5. Wait 5 minutes
6. Check the status display in the app
