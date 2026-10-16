# Lector de placas colombianas

Programa en Python que lee con la cámara placas colombianas de **carro** (`ABC123`) y de **moto** (`ABC12D`), en cualquier posición (inclinadas, de lado, al revés) y de cualquier color.

Proyecto de **Electiva Tecnológica 2** – Mecatrónica, Universidad de Caldas.
Equipo: **[Integrante 1]**, **[Integrante 2]**, **[Integrante 3]**.

## ¿Qué hace?
- El operador registra placas **autorizadas** y **vetadas** desde un menú en consola.
- La cámara detecta la placa, la endereza y la lee con OCR.
- Muestra un letrero: 🟩 `DATOS GUARDADOS - ENTRE` (autorizada), 🟥 `PLACA VETADA - NO PASE` (vetada), 🟧 `PLACA NO REGISTRADA`.
- Guarda la foto y anota cada lectura en `registro.csv`.

## Instalación (VS Code)
1. Instalar **Python 3.12** (marcar *Add python.exe to PATH*) y **Visual Studio Code**.
2. En VS Code instalar las extensiones **Python** y **Pylance** (Microsoft).
3. Instalar las librerías en la terminal de VS Code:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Ejecutar
```bash
python lector_placas.py
```
La primera vez necesita internet: EasyOCR descarga sus modelos (~100 MB).

## Uso
Menú: `1` agregar autorizada · `2` agregar vetada · `3` eliminar · `4` ver listas · `5` iniciar cámara · `6` salir.
En la ventana de video, la tecla `q` vuelve al menú.

## ¿Dónde se guarda todo?
`C:\Users\<usuario>\Placas_Guardadas\` → `autorizadas/`, `vetadas/`, `no_registradas/`, `placas.json`, `registro.csv`.

## Documentación
- [Especificación del proyecto](docs/ESPECIFICACION.md)
- [Acuerdo de colaboración del equipo](docs/ACUERDO_COLABORACION.md)
- [Evidencia de un cambio revisado](docs/EVIDENCIA_CAMBIO.md)

## Problemas frecuentes
| Problema | Solución |
|---|---|
| `No module named cv2` | Falta instalar las librerías en ese PC (paso 3). |
| No abre la cámara | Cerrar Zoom/Teams o cambiar `INDICE_CAMARA` a `1`. |
| Va lento | Subir `OCR_CADA_N_FRAMES` (ej. 8). |
| No lee la placa | Más luz, sin reflejos, bien enfocada. |
