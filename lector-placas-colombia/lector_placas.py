# -*- coding: utf-8 -*-
"""
LECTOR DE PLACAS COLOMBIANAS  (carro: ABC123  |  moto: ABC12D)
  - El operador registra placas AUTORIZADAS y VETADAS desde un menu.
  - La camara lee la placa en tiempo real (OpenCV + EasyOCR), en cualquier
    posicion (inclinada, de lado, al reves) y de cualquier color.
  - Muestra un letrero (verde / rojo / naranja), guarda la foto en una carpeta
    y anota cada lectura en un registro CSV.
Instalacion:  pip install opencv-python easyocr numpy
"""

# ===== PARTE 1: LIBRERIAS =====
import os, re, csv, json, time, threading  # carpetas, regex, CSV, JSON, tiempos, hilo para el OCR
from datetime import datetime              # fecha y hora para los nombres de archivo
import cv2                                 # OpenCV: camara, imagenes y ventanas
import numpy as np                         # calculos con puntos (enderezar placas)
import easyocr                             # OCR: convierte la imagen de la placa en texto

# ===== PARTE 2: CONFIGURACION (puedes cambiar estos valores) =====
CARPETA_BASE = os.path.join(os.path.expanduser("~"), "Placas_Guardadas")  # fotos y registros (carpeta de tu usuario)
INDICE_CAMARA = 0                  # 0 = camara principal, 1 = externa
ANCHO_CAMARA, ALTO_CAMARA = 640, 480   # menos pixeles = mas rapido
OCR_CADA_N_FRAMES = 5              # se intenta leer una placa cada N cuadros
LECTURAS_PARA_CONFIRMAR = 2        # veces seguidas que debe leerse igual la placa
SEGUNDOS_ENTRE_LECTURAS = 10       # no guardar la misma placa otra vez antes de este tiempo
SEGUNDOS_LETRERO = 5               # tiempo que se ve el letrero
SEGUNDOS_ENTRE_PASADAS_COMPLETAS = 3   # leer la imagen completa (lo mas lento) solo cada N segundos
ANCHO_MAX_IMAGEN_COMPLETA = 640    # la imagen completa se reduce a este ancho
MAX_CANDIDATOS = 3                 # rectangulos que se prueban por cuadro
CONFIANZA_MINIMA = 0.30            # descarta lecturas dudosas del OCR
MAX_CORRECCIONES = 1               # caracteres que se pueden corregir por placa (0/O, 5/S...)
USAR_GPU = False                   # True solo con tarjeta NVIDIA y PyTorch con CUDA

PATRON_PLACA = re.compile(r"^[A-Z]{3}[0-9]{2}[A-Z0-9]$")   # carro LLLNNN o moto LLLNNL
CARACTERES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"        # lo unico que puede leer el OCR
NUM_A_LETRA = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}   # confusiones tipicas del OCR
LETRA_A_NUM = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "G": "6"}
BLANCO = (255, 255, 255)           # colores en BGR (azul, verde, rojo)
# resultado -> (texto del letrero, color, subcarpeta donde se guarda la foto)
ESTADOS = {
    "AUTORIZADA":    ("DATOS GUARDADOS - ENTRE", (0, 160, 0), "autorizadas"),
    "VETADA":        ("PLACA VETADA - NO PASE", (0, 0, 200), "vetadas"),
    "NO REGISTRADA": ("PLACA NO REGISTRADA", (0, 140, 255), "no_registradas"),
}


# ===== PARTE 3: CARPETAS Y LISTAS DE PLACAS =====
def ruta(*partes):
    """Ruta dentro de CARPETA_BASE, ej. ruta('placas.json')."""
    return os.path.join(CARPETA_BASE, *partes)


def crear_carpetas():
    """Crea las carpetas. Si no hay permiso para escribir, usa la carpeta del usuario."""
    global CARPETA_BASE
    try:
        for _, _, sub in ESTADOS.values():
            os.makedirs(ruta(sub), exist_ok=True)
        with open(ruta(".prueba"), "w") as f:      # comprueba que de verdad se puede escribir
            f.write("ok")
        os.remove(ruta(".prueba"))
    except OSError:
        print(f"  AVISO: sin permiso para escribir en {CARPETA_BASE}. Se usara la carpeta de tu usuario.")
        CARPETA_BASE = os.path.join(os.path.expanduser("~"), "Placas_Guardadas")
        for _, _, sub in ESTADOS.values():
            os.makedirs(ruta(sub), exist_ok=True)


def cargar_listas():
    """Lee placas.json; si no existe (o esta danado) empieza con listas vacias."""
    try:
        with open(ruta("placas.json"), encoding="utf-8") as f:
            datos = json.load(f)
        return {"autorizadas": datos.get("autorizadas", []), "vetadas": datos.get("vetadas", [])}
    except (OSError, ValueError):
        return {"autorizadas": [], "vetadas": []}


def guardar_listas(listas):
    """Guarda las listas para no perderlas al cerrar el programa."""
    with open(ruta("placas.json"), "w", encoding="utf-8") as f:
        json.dump(listas, f, indent=2, ensure_ascii=False)


# ===== PARTE 4: SISTEMA DEL OPERADOR (menu por consola) =====
def pedir_placa():
    """Pide una placa y valida el formato: carro (ABC123) o moto (ABC12D)."""
    while True:
        texto = input("Escribe la placa (carro: ABC123 / moto: ABC12D): ")
        texto = texto.strip().upper().replace(" ", "").replace("-", "")
        if PATRON_PLACA.match(texto):
            return texto
        print("  Formato invalido. Carro: 3 letras + 3 numeros. Moto: 3 letras + 2 numeros + 1 letra.")


def agregar_placa(listas, destino):
    """Agrega una placa a 'autorizadas' o 'vetadas' (y la saca de la otra lista)."""
    placa = pedir_placa()
    otra = "vetadas" if destino == "autorizadas" else "autorizadas"
    if placa in listas[otra]:                      # una placa no puede estar en las dos listas
        listas[otra].remove(placa)
        print(f"  (Se quito {placa} de la lista de {otra})")
    if placa not in listas[destino]:
        listas[destino].append(placa)
    guardar_listas(listas)
    print(f"  Placa {placa} guardada en {destino}.")


def eliminar_placa(listas):
    """Elimina una placa de cualquiera de las dos listas."""
    placa = pedir_placa()
    encontrada = False
    for lista in listas.values():
        if placa in lista:
            lista.remove(placa)
            encontrada = True
    guardar_listas(listas)
    print("  Placa eliminada." if encontrada else "  Esa placa no estaba registrada.")


# ===== PARTE 5: LECTURA DE PLACAS (deteccion + enderezado + OCR) =====
def ordenar_puntos(p):
    """Ordena 4 esquinas: arriba-izq, arriba-der, abajo-der, abajo-izq."""
    p = np.array(p, dtype="float32")
    suma, resta = p.sum(axis=1), np.diff(p, axis=1).ravel()      # x+y  y  y-x
    return np.array([p[suma.argmin()], p[resta.argmin()], p[suma.argmax()], p[resta.argmax()]], dtype="float32")


def buscar_candidatos(frame):
    """Busca rectangulos con forma de placa EN CUALQUIER ANGULO (proporcion 1.1:1 a 6:1)."""
    gris = cv2.bilateralFilter(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 11, 17, 17)  # gris y sin ruido: el color no importa
    bordes = cv2.dilate(cv2.Canny(gris, 30, 200), np.ones((3, 3), np.uint8))          # bordes sin huecos
    contornos, _ = cv2.findContours(bordes, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:25]             # los 25 mas grandes
    candidatos = []
    for c in contornos:
        area = cv2.contourArea(c)
        rect = cv2.minAreaRect(c)                  # rectangulo rotado minimo (cualquier angulo)
        (_, _), (w, h), _ = rect
        if area < 0.002 * frame.shape[0] * frame.shape[1] or min(w, h) < 20:
            continue                               # muy pequeno o muy delgado: ruido
        # proporcion largo/ancho de placa y que tan "llena" esta (rectangular)
        if 1.1 <= max(w, h) / min(w, h) <= 6.0 and area / (w * h) > 0.5:
            candidatos.append(cv2.boxPoints(rect))
    return candidatos


def enderezar(frame, caja):
    """Recorta el rectangulo y lo endereza (vista frontal) sin importar como estuviera girado."""
    tl, tr, br, bl = ordenar_puntos(caja)
    ancho = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    alto = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if ancho < 2 or alto < 2:
        return None
    destino = np.array([[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], dtype="float32")
    matriz = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype="float32"), destino)
    recorte = cv2.warpPerspective(frame, matriz, (ancho, alto))
    return cv2.rotate(recorte, cv2.ROTATE_90_CLOCKWISE) if alto > ancho else recorte   # que quede horizontal


def corregir_placa(texto):
    """
    Fuerza el texto del OCR al formato de carro (LLLNNN) o de moto (LLLNNL).
    Posiciones 1-3 = letras, 4-5 = numeros (se corrigen 0/O, 5/S...). La posicion 6 se
    respeta: numero = carro, letra = moto. Para no confundir palabras con placas se
    ignora COLOMBIA, se prefiere la lectura con menos correcciones y hay un maximo.
    """
    texto = re.sub(r"[^A-Z0-9]", "", texto.upper().replace("COLOMBIA", " "))
    mejor, mejor_n = None, MAX_CORRECCIONES + 1
    for i in range(len(texto) - 5):                # ventanas de 6 caracteres
        c = texto[i:i + 6]
        candidata = ("".join(NUM_A_LETRA.get(x, x) for x in c[:3])
                     + "".join(LETRA_A_NUM.get(x, x) for x in c[3:5]) + c[5])
        n = sum(a != b for a, b in zip(c, candidata))      # cuantos caracteres se corrigieron
        if n < mejor_n and PATRON_PLACA.match(candidata):
            mejor, mejor_n = candidata, n
            if n == 0:                             # lectura exacta: no se busca mas
                break
    return mejor


def leer_en_imagen(imagen, lector, rotaciones):
    """
    Lee el texto de una imagen y devuelve (placa, caja) o (None, None).
    Prueba 2 versiones (normal e invertida) para cubrir letras oscuras o claras, o sea
    placas de cualquier color. 'rotaciones' = giros extra de EasyOCR (180 = al reves).
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY) if imagen.ndim == 3 else imagen
    mejorada = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gris)        # mas contraste
    for version in (mejorada, cv2.bitwise_not(mejorada)):                              # normal e invertida
        textos = [r for r in lector.readtext(version, rotation_info=rotaciones, allowlist=CARACTERES)
                  if r[2] >= CONFIANZA_MINIMA]
        # la placa puede salir entera o en 2-3 pedazos (la moto tiene 2 renglones):
        # se prueban grupos de pedazos seguidos, asi un texto extra en medio no estorba
        for tam in (1, 2, 3):
            for ini in range(len(textos) - tam + 1):
                grupo = textos[ini:ini + tam]
                placa = corregir_placa("".join(r[1] for r in grupo))
                if placa:
                    puntos = np.concatenate([np.array(r[0], dtype="float32") for r in grupo])
                    return placa, cv2.boxPoints(cv2.minAreaRect(puntos))
    return None, None


def leer_placa(frame, lector, usar_imagen_completa=True):
    """
    Devuelve (placa, caja) o (None, None).
      Paso 1 (rapido): rectangulos candidatos, enderezados y leidos.
      Paso 2 (lento):  imagen completa probando 4 giros; solo si usar_imagen_completa.
    """
    for caja in buscar_candidatos(frame)[:MAX_CANDIDATOS]:
        recorte = enderezar(frame, caja)
        if recorte is None:
            continue
        recorte = cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)  # agrandar ayuda al OCR
        alto, ancho = recorte.shape[:2]
        casi_cuadrado = max(alto, ancho) / max(1, min(alto, ancho)) < 2.0    # placa de moto: orientacion dudosa
        placa, _ = leer_en_imagen(recorte, lector, [90, 180, 270] if casi_cuadrado else [180])
        if placa:
            return placa, caja
    if not usar_imagen_completa:
        return None, None
    escala = min(1.0, ANCHO_MAX_IMAGEN_COMPLETA / frame.shape[1])
    pequena = cv2.resize(frame, None, fx=escala, fy=escala) if escala < 1.0 else frame
    placa, caja = leer_en_imagen(pequena, lector, [90, 180, 270])
    return (placa, caja / escala) if placa else (None, None)    # caja / escala = coordenadas originales


# ===== PARTE 6: DECISION, GUARDADO DE IMAGEN Y REGISTRO =====
def anotar_registro(fila):
    """Agrega una fila a registro.csv. Si esta bloqueado (ej. abierto en Excel) usa un archivo de respaldo."""
    for nombre in ("registro.csv", "registro_respaldo.csv"):
        archivo = ruta(nombre)
        try:
            nuevo = not os.path.exists(archivo)
            with open(archivo, "a", newline="", encoding="utf-8") as f:
                escritor = csv.writer(f)
                if nuevo:
                    escritor.writerow(["fecha_hora", "placa", "estado", "imagen"])
                escritor.writerow(fila)
            return
        except OSError as e:
            print(f"  AVISO: no se pudo escribir en {archivo}: {e}")
    print("  AVISO: la lectura no quedo anotada. Cierra Excel si lo tienes abierto y revisa los permisos.")


def procesar_placa(placa, frame, listas):
    """Decide el estado de la placa, guarda la foto y el registro. Devuelve (letrero, color, ruta_foto)."""
    estado = ("VETADA" if placa in listas["vetadas"]            # vetada tiene prioridad
              else "AUTORIZADA" if placa in listas["autorizadas"] else "NO REGISTRADA")
    mensaje, color, subcarpeta = ESTADOS[estado]
    ahora = datetime.now()
    archivo = ruta(subcarpeta, f"{placa}_{ahora:%Y%m%d_%H%M%S}.jpg")      # PLACA_AAAAMMDD_HHMMSS.jpg
    try:
        ok, imagen = cv2.imencode(".jpg", frame)
        if not ok:
            raise OSError("no se pudo codificar la imagen")
        imagen.tofile(archivo)                                  # (a diferencia de imwrite, sirve con tildes)
    except OSError as e:
        print(f"  AVISO: no se pudo guardar la imagen ({e})")
        archivo = "ERROR: no se pudo guardar la imagen"
    anotar_registro([ahora.isoformat(sep=" ", timespec="seconds"), placa, estado, archivo])
    print(f"[{estado}] Placa {placa} -> imagen guardada en: {archivo}")
    return mensaje, color, archivo


# ===== PARTE 7: DIBUJO EN PANTALLA =====
def dibujar_letrero(frame, mensaje, color, placa, archivo):
    """Letrero grande arriba y, abajo, la ruta donde se guardo la imagen."""
    alto, ancho = frame.shape[:2]
    letra = cv2.FONT_HERSHEY_SIMPLEX
    cv2.rectangle(frame, (0, 0), (ancho, 90), color, -1)                     # banda de color
    cv2.putText(frame, mensaje, (15, 40), letra, 1.0, BLANCO, 3)
    cv2.putText(frame, f"Placa: {placa}", (15, 75), letra, 0.8, BLANCO, 2)
    cv2.rectangle(frame, (0, alto - 40), (ancho, alto), (40, 40, 40), -1)    # banda gris con la ruta
    cv2.putText(frame, "Guardado en: " + archivo[-70:], (10, alto - 14), letra, 0.5, BLANCO, 1)


def dibujar_caja(frame, caja, placa):
    """Contorno amarillo (puede estar girado) alrededor de la placa, con su texto."""
    puntos = np.array(caja, dtype=np.int32).reshape(-1, 1, 2)
    cv2.polylines(frame, [puntos], True, (0, 255, 255), 2)
    cv2.putText(frame, placa, (int(puntos[:, 0, 0].min()), max(int(puntos[:, 0, 1].min()) - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)


# ===== PARTE 8: CAMARA EN VIVO =====
class LectorEnSegundoPlano:
    """Lee placas en un hilo aparte: el video no se congela mientras el OCR trabaja."""

    def __init__(self, lector):
        self.lector = lector
        self.ocupado = False                # True mientras hay una lectura en curso
        self.resultado = None               # (placa, caja, imagen, fue_completa) o None
        self.ultima_completa = 0.0          # cuando se hizo la ultima lectura de imagen completa
        self.hilo = None
        self.candado = threading.Lock()     # evita que dos hilos toquen los datos a la vez

    def enviar(self, frame):
        """Manda un cuadro a leer, solo si no hay otra lectura en curso."""
        with self.candado:
            if self.ocupado:
                return
            self.ocupado = True
        self.hilo = threading.Thread(target=self._leer, args=(frame.copy(),), daemon=True)
        self.hilo.start()

    def _leer(self, imagen):
        """(Corre en el otro hilo) lee la placa y deja el resultado guardado."""
        completa = time.time() - self.ultima_completa >= SEGUNDOS_ENTRE_PASADAS_COMPLETAS
        try:
            placa, caja = leer_placa(imagen, self.lector, completa)
        except Exception as e:              # un fallo del OCR no debe cerrar el programa
            print("  Error en OCR:", e)
            placa, caja = None, None
        if completa:
            self.ultima_completa = time.time()
        with self.candado:
            self.resultado = (placa, caja, imagen, completa)
            self.ocupado = False

    def recoger(self):
        """Devuelve el ultimo resultado (y lo borra) o None si todavia no hay."""
        with self.candado:
            resultado, self.resultado = self.resultado, None
        return resultado

    def esperar(self):
        """Espera a que termine la lectura en curso (al cerrar la camara)."""
        if self.hilo is not None and self.hilo.is_alive():
            self.hilo.join(timeout=15)


def iniciar_camara(listas, lector):
    """Abre la camara y lee placas continuamente. Tecla 'q' para volver al menu."""
    # en Windows, CAP_DSHOW abre la camara mucho mas rapido
    cap = cv2.VideoCapture(INDICE_CAMARA, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(INDICE_CAMARA)
    if not cap.isOpened():
        print("  No se pudo abrir la camara. Revisa INDICE_CAMARA o los permisos.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO_CAMARA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO_CAMARA)
    print("  Camara iniciada. Presiona 'q' en la ventana para volver al menu.")

    hilo = LectorEnSegundoPlano(lector)
    cuadros = repeticiones = 0              # cuadros vistos / veces seguidas que se leyo la misma placa
    ultima = caja = letrero = None          # ultima placa leida, su contorno y el letrero activo
    momento_caja = 0.0                      # cuando se dibujo el contorno (se borra a los 2 s)
    guardadas = {}                          # placa -> cuando se guardo (anti-repeticion)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("  Error leyendo la camara.")
            break
        cuadros += 1

        # 1) recoger lo que ya leyo el hilo
        resultado = hilo.recoger()
        if resultado:
            placa, caja_nueva, imagen, fue_completa = resultado
            if placa:
                caja, momento_caja = caja_nueva, time.time()
                repeticiones = repeticiones + 1 if placa == ultima else 1
                ultima = placa
                # confirmar: misma placa varias veces seguidas y sin repetirla muy pronto
                if (repeticiones >= LECTURAS_PARA_CONFIRMAR
                        and time.time() - guardadas.get(placa, 0) > SEGUNDOS_ENTRE_LECTURAS):
                    guardadas[placa] = time.time()
                    mensaje, color, archivo = procesar_placa(placa, imagen, listas)   # foto del cuadro exacto
                    letrero = (mensaje, color, placa, archivo, time.time() + SEGUNDOS_LETRERO)
            elif fue_completa:              # ni la lectura de imagen completa la encontro: se olvida
                ultima, repeticiones, caja = None, 0, None

        # 2) mandar un cuadro nuevo a leer (el hilo lo ignora si sigue ocupado)
        if cuadros % OCR_CADA_N_FRAMES == 0:
            hilo.enviar(frame)

        # 3) dibujar y mostrar
        if ultima and caja is not None and time.time() - momento_caja < 2.0:
            dibujar_caja(frame, caja, ultima)
        if letrero and time.time() < letrero[4]:
            dibujar_letrero(frame, *letrero[:4])
        cv2.imshow("Lector de placas - presiona q para salir", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    hilo.esperar()
    cap.release()
    cv2.destroyAllWindows()


# ===== PARTE 9: PROGRAMA PRINCIPAL (menu) =====
MENU = """
========= CONTROL DE PLACAS =========
1. Agregar placa AUTORIZADA
2. Agregar placa VETADA
3. Eliminar una placa
4. Ver listas
5. Iniciar camara
6. Salir"""


def main():
    crear_carpetas()
    listas = cargar_listas()
    print("Cargando lector OCR (la primera vez descarga modelos, espera)...")
    lector = easyocr.Reader(["en"], gpu=USAR_GPU)      # 'en' lee letras y numeros de placas

    while True:
        print(MENU)
        opcion = input("Elige una opcion: ").strip()
        if opcion == "1":
            agregar_placa(listas, "autorizadas")
        elif opcion == "2":
            agregar_placa(listas, "vetadas")
        elif opcion == "3":
            eliminar_placa(listas)
        elif opcion == "4":
            print("\n  AUTORIZADAS:", ", ".join(listas["autorizadas"]) or "(vacia)")
            print("  VETADAS    :", ", ".join(listas["vetadas"]) or "(vacia)")
        elif opcion == "5":
            iniciar_camara(listas, lector)
        elif opcion == "6":
            print("Hasta luego.")
            break
        else:
            print("  Opcion no valida.")


if __name__ == "__main__":      # ejecuta main() solo si este archivo se corre directamente
    main()
