import os, shutil, zipfile

# Paths
temp_root = r'C:\Users\pavan kalyan\.gemini\antigravity\brain\cd6b5d22-0371-4310-9057-a0a5b5791567'
src = r'C:\Users\pavan kalyan\New folder (3)\CareerAI'
# Destination folder named DataFix inside artifact directory
dst = os.path.join(temp_root, 'DataFix')

# Remove existing DataFix folder if present
if os.path.isdir(dst):
    shutil.rmtree(dst)

# Copy the whole project
shutil.copytree(src, dst)

# Remove internal .claude directory (not needed for the user)
claude_dir = os.path.join(dst, '.claude')
if os.path.isdir(claude_dir):
    shutil.rmtree(claude_dir)

# Create zip of DataFix folder
zip_path = os.path.join(temp_root, 'DataFix.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(dst):
        for f in files:
            fp = os.path.join(root, f)
            # make archive name relative to the temp_root so zip contains "DataFix/..."
            arcname = os.path.relpath(fp, temp_root)
            zf.write(fp, arcname)

print('ZIP created at:', zip_path)
