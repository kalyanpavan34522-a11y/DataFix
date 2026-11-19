import os, zipfile, sys
src = r'C:\\Users\\pavan kalyan\\New folder (3)\\CareerAI'
# Destination inside artifact directory
artifact_dir = r'C:\\Users\\pavan kalyan\\.gemini\\antigravity\\brain\\cd6b5d22-0371-4310-9057-a0a5b5791567'
zip_path = os.path.join(artifact_dir, 'CareerAI_project.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(src):
        for f in files:
            fp = os.path.join(root, f)
            arcname = os.path.relpath(fp, src)
            zf.write(fp, arcname)
print('ZIP created at:', zip_path)
