import os

file_path = 'app/routers/citas.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from app.models.usuario import Usuario', 'from app.models.usuario import Usuario, RolUsuario')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed missing import in citas.py")
