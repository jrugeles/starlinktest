# Publicar en GitHub

Nombre propuesto: **starlink-connectivity-lab**.

Descripción sugerida:

> Herramientas educativas en Python para pruebas de conectividad Starlink: telemetría gRPC, gráficas, CSV y mapas de obstrucciones. Wirid-LAB / UMNG.

## Desde el navegador

1. Inicia sesión en GitHub y abre https://github.com/new.
2. Selecciona la cuenta propietaria y escribe el nombre propuesto.
3. Elige la visibilidad que corresponda. Privado permite revisar antes de publicar; público permite acceso directo de los estudiantes.
4. Activa la creación de un README para inicializar el repositorio. No selecciones plantilla de `.gitignore` ni licencia en este paso.
5. Crea el repositorio, selecciona **Add file → Upload files** y sube el contenido de la carpeta extraída, no el ZIP. Reemplaza el README inicial con el preparado aquí.
6. Incluye `.gitignore`, `requirements.txt`, los tres `.py`, `THIRD_PARTY_NOTICES.md` y las carpetas `docs`, `licenses` y `tests`. Los archivos con punto inicial pueden estar ocultos en algunos sistemas.
7. Confirma la carga con un mensaje como `Añadir programas y guía de prácticas Starlink`.

Revisa que README.md aparezca en la raíz. No subas `.venv`, `__pycache__` ni `sesiones_starlink`.

## Con Git, después de crear un repositorio remoto vacío

Para esta alternativa, crea el remoto SIN inicializar README, licencia ni `.gitignore`. Dentro de la carpeta extraída:

```bash
git init -b main
git add .
git commit -m "Añadir programas y guía de prácticas Starlink"
git remote add origin https://github.com/jrugeles/starlink-connectivity-lab.git
git push -u origin main
```

Cambia propietario/nombre de la URL si elegiste otros. Usa la autenticación normal de GitHub para Git; nunca escribas tokens en archivos del proyecto. Si Git solicita identidad de autor, configura tu propio nombre y correo.

La URL anterior es el destino propuesto; no indica que el repositorio ya exista.
