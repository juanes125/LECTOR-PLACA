# Lector de placas colombianas

Programa en Python que lee con la cámara placas colombianas de **carro** (`ABC123`) y de **moto** (`ABC12D`), en cualquier posición (inclinadas, de lado, al revés) y de cualquier color.

Proyecto de **Electiva Tecnológica 2** – Mecatrónica, Universidad de Caldas.
Equipo: **[Integrante 1]**, **[Integrante 2]**, **[Integrante 3]**.

## ¿Qué hace?
- El operador registra placas **autorizadas** y **vetadas** desde un menú en consola.
- La cámara detecta la placa, la endereza y la lee con OCR.
- Muestra un letrero: 🟩 `DATOS GUARDADOS - ENTRE` (autorizada), 🟥 `PLACA VETADA - NO PASE` (vetada), 🟧 `PLACA NO REGISTRADA`.
- Guarda la foto y anota cada lectura en `registro.csv`.
- **Reconocimiento facial por placa:** cada placa autorizada tiene asignadas las caras de las personas que pueden usar el vehículo (el dueño y quien él autorice). Al leer la placa, la cámara verifica el rostro del conductor: si es una de esas personas → `BIENVENIDO <nombre>`; si es otra persona → `ROSTRO NO AUTORIZADO - NO PASE`. Si la placa **no está registrada** → `ACERQUESE AL SUPERVISOR`. Si está vetada → `PLACA VETADA - NO PASE`.

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
Menú: `1` agregar placa autorizada · `2` agregar placa vetada · `3` eliminar placa · `4` ver listas · `5` asignar el rostro de una persona a una placa · `6` iniciar cámara · `7` ver personas registradas · `8` eliminar una persona (por cédula) · `9` salir.
En la ventana de video, la tecla `q` vuelve al menú.

**Registrar a alguien en un vehículo:** (1) agrega la placa con la opción `1` (el programa ofrece registrar el rostro enseguida), o usa la opción `5` con una placa ya autorizada; (2) la persona mira la cámara; (3) en el formulario de la ventana escribe el nombre (sin tildes), `Enter`, la cédula (6 a 10 números) y `Enter`. `Tab` cambia de campo y `Esc` cancela. Repite la opción `5` con la misma placa para agregar más personas autorizadas.

**Primera vez con la cámara:** se descargan solos 2 modelos faciales (~37 MB) en `Placas_Guardadas\modelos`; necesita internet.

## ¿Dónde se guarda todo?
`C:\Users\<usuario>\Placas_Guardadas\` → `autorizadas/`, `vetadas/`, `no_registradas/`, `placas.json`, `registro.csv`, `personas.json` (nombre, cédula y huella facial), `registro_personas.csv` (entradas por rostro) y `modelos/`.

> **Datos personales:** solo se guarda la *huella numérica* del rostro (128 números), no la foto. La cédula y la huella facial son datos personales protegidos por la Ley 1581 de 2012: registra solo personas que lo autoricen y borra a quien lo pida con la opción 7.

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
| No reconoce el rostro / no abre el formulario | Buena luz de frente, cara cerca y sin gorra; revisa que se descargaran los modelos en `modelos/`. |
| Error de descarga de modelos | Descarga los 2 archivos a mano (el programa imprime los enlaces) y guárdalos en `Placas_Guardadas\modelos`. |
