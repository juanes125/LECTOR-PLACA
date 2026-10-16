# -*- coding: utf-8 -*-
"""
RECONOCIMIENTO FACIAL: cada placa tiene asignadas las caras de las personas autorizadas
a usar ese vehiculo (el dueño y quien el quiera).

Registro (lo hace el operador, opcion 5 del menu):
  se escribe la placa, la camara ve la cara y aparece un formulario para NOMBRE y CEDULA.
  Se puede repetir para agregar mas personas a la misma placa.
Entrada (cuando la camara lee una placa autorizada):
  - la cara es de una persona asignada a esa placa -> "BIENVENIDO <nombre>"
  - la cara es de otra persona (o desconocida)      -> "ROSTRO NO AUTORIZADO - NO PASE"
Solo se guarda la "huella" numerica del rostro (128 numeros), NO la foto.

Modelos (OpenCV, se descargan solos la primera vez, ~37 MB):
  YuNet = encuentra rostros  |  SFace = convierte el rostro en 128 numeros
Requiere  opencv-python 4.8 o mayor.
"""
import os, json, time, urllib.request
from datetime import datetime
import cv2
import numpy as np

# ===== CONFIGURACION =====
MODELOS = {   # archivo -> de donde se descarga
    "yunet.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
UMBRAL_COINCIDENCIA = 0.363     # parecido minimo (coseno) para decir "es la misma persona"
CONFIRMACIONES = 3              # lecturas seguidas iguales para dar por reconocida a la persona
RECONOCER_CADA_N_FRAMES = 3     # se analiza un cuadro de cada N (mas rapido)
LECTURAS_PARA_DENEGAR = 8       # lecturas seguidas "no es de esta placa" antes de negar la entrada
CUADROS_PARA_REGISTRO = 6       # lecturas del rostro antes de abrir el formulario de registro
SEGUNDOS_MAX_ROSTRO = 30        # entrada: si no aparece un rostro en este tiempo, se cancela
SEGUNDOS_MAX_REGISTRO = 60      # registro: tiempo maximo para que la persona mire a la camara
SEGUNDOS_AVISO = 4              # tiempo que se ve el mensaje final
MAX_HUELLAS_POR_PERSONA = 5     # huellas guardadas por persona (mejora el reconocimiento)
VERDE, ROJO, NARANJA, BLANCO, AMARILLO = (0, 160, 0), (0, 0, 200), (0, 140, 255), (255, 255, 255), (0, 255, 255)
LETRA = cv2.FONT_HERSHEY_SIMPLEX


def texto(frame, t, pos, escala=0.6, color=BLANCO, grosor=1, ancho_max=None):
    """Atajo para escribir texto en la imagen (si se da ancho_max, se achica para que quepa)."""
    while ancho_max and escala > 0.4 and cv2.getTextSize(t, LETRA, escala, grosor)[0][0] > ancho_max:
        escala -= 0.05
    cv2.putText(frame, t, pos, LETRA, escala, color, grosor, cv2.LINE_AA)


class Rostros:
    def __init__(self, carpeta):
        self.carpeta = carpeta                        # donde se guarda personas.json y los modelos
        self.archivo = os.path.join(carpeta, "personas.json")
        self.detector = self.reconocedor = None       # se cargan en preparar()
        self.personas = self._cargar()                # {cedula: {nombre, huellas, placas, registrado}}
        self.fase = None                              # None | "buscando" | "formulario"
        self.aviso = None                             # (linea1, linea2, color, hasta_cuando)

    # ---------- personas guardadas ----------
    def _cargar(self):
        try:
            with open(self.archivo, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _guardar(self):
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(self.personas, f, ensure_ascii=False)

    def listar(self):
        """Lineas de texto con las personas registradas (para el menu)."""
        return [f"  C.C. {c}  -  {p['nombre']}  (placas: {', '.join(p['placas']) or '-'})"
                for c, p in self.personas.items()]

    def tiene_rostros(self, placa):
        """True si hay al menos una persona con huella asignada a esta placa."""
        return any(placa in p["placas"] and p["huellas"] for p in self.personas.values())

    def quitar_placa(self, placa):
        """Quita la placa de todas las personas; las que se quedan sin placas se borran (con su huella)."""
        for cedula in list(self.personas):
            if placa in self.personas[cedula]["placas"]:
                self.personas[cedula]["placas"].remove(placa)
                if not self.personas[cedula]["placas"]:
                    del self.personas[cedula]
        self._guardar()

    def eliminar(self, cedula):
        """Borra una persona y su huella facial. Devuelve True si existia."""
        existia = self.personas.pop(cedula, None) is not None
        self._guardar()
        return existia

    # ---------- modelos ----------
    def preparar(self):
        """Descarga (si faltan) y carga los modelos. Devuelve False si no se pudo."""
        try:
            carpeta = os.path.join(self.carpeta, "modelos")
            os.makedirs(carpeta, exist_ok=True)
            for nombre, url in MODELOS.items():
                ruta = os.path.join(carpeta, nombre)
                if not (os.path.exists(ruta) and os.path.getsize(ruta) > 100_000):
                    print(f"  Descargando modelo facial {nombre} (solo la primera vez)...")
                    urllib.request.urlretrieve(url, ruta)
                    if os.path.getsize(ruta) < 100_000:      # descarga incompleta o pagina de error
                        os.remove(ruta)
                        raise OSError("descarga incompleta")
            self.detector = cv2.FaceDetectorYN.create(os.path.join(carpeta, "yunet.onnx"), "", (320, 320), 0.8, 0.3, 5000)
            self.reconocedor = cv2.FaceRecognizerSF.create(os.path.join(carpeta, "sface.onnx"), "")
            return True
        except Exception as e:
            print(f"  AVISO: no se pudo preparar el reconocimiento facial ({e}).")
            print(f"  Descarga a mano estos archivos y guardalos en {carpeta} con estos nombres:")
            for nombre, url in MODELOS.items():
                print(f"    {nombre}  <-  {url}")
            print("  Mientras tanto el programa funciona solo con placas.")
            return False

    def _detectar(self, frame):
        """Devuelve las caras encontradas (una fila por cara) o lista vacia."""
        self.detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, caras = self.detector.detect(frame)
        return [] if caras is None else list(caras)

    def _huella(self, frame, cara):
        """Convierte un rostro en 128 numeros (normalizados) que lo identifican."""
        h = self.reconocedor.feature(self.reconocedor.alignCrop(frame, cara)).flatten().astype("float32")
        return h / (np.linalg.norm(h) + 1e-9)

    def _buscar(self, huella, placa):
        """Compara SOLO con las personas asignadas a esta placa. Devuelve (cedula, parecido) o (None, maximo)."""
        mejor, mejor_c = -1.0, None
        for cedula, p in self.personas.items():
            if placa not in p["placas"]:
                continue
            for h in p["huellas"]:
                parecido = float(np.dot(huella, np.array(h, dtype="float32")))   # coseno (ya normalizadas)
                if parecido > mejor:
                    mejor, mejor_c = parecido, cedula
        return (mejor_c, mejor) if mejor >= UMBRAL_COINCIDENCIA else (None, mejor)

    # ---------- flujo ----------
    @property
    def activo(self):
        return self.fase is not None

    @property
    def en_formulario(self):
        return self.fase == "formulario"

    def iniciar(self, placa, modo="entrada"):
        """Empieza a buscar un rostro. modo 'entrada' = verificar al conductor de esta placa;
        modo 'registro' = guardar a una persona nueva para esta placa."""
        self.fase, self.placa, self.modo, self.t0 = "buscando", placa, modo, time.time()
        self.cuadros = self.vistos = self.desconocidos = 0
        self.candidato, self.huellas_nuevas = None, []

    def cancelar(self):
        """Cancela la etapa actual (tecla q fuera del formulario)."""
        return self._terminar("CANCELADO", "REGISTRO CANCELADO", "", NARANJA)

    def _terminar(self, estado, linea1, linea2, color, cedula="", nombre=""):
        self.fase = None
        self.aviso = (linea1, linea2, color, time.time() + SEGUNDOS_AVISO)
        return {"estado": estado, "placa": self.placa, "cedula": cedula, "nombre": nombre}

    def paso(self, frame):
        """Se llama en cada cuadro de video mientras esta activo. Dibuja y devuelve None, o un
        resultado {estado, placa, cedula, nombre} cuando termina."""
        if self.fase == "formulario":
            self._dibujar_formulario(frame)
            return None
        registro = self.modo == "registro"
        limite = SEGUNDOS_MAX_REGISTRO if registro else SEGUNDOS_MAX_ROSTRO
        if time.time() - self.t0 > limite:
            return self._terminar("SIN ROSTRO", "NO SE DETECTO ROSTRO", "Intente de nuevo", NARANJA)
        self.cuadros += 1
        restante = int(limite - (time.time() - self.t0))
        alto = frame.shape[0]
        cv2.rectangle(frame, (0, alto - 80), (frame.shape[1], alto - 45), (40, 40, 40), -1)
        accion = "REGISTRO" if registro else "ROSTRO"
        texto(frame, f"{accion} ({self.placa}): mire a la camara - {restante}s", (10, alto - 55), 0.6)
        if self.cuadros % RECONOCER_CADA_N_FRAMES:      # solo se analiza 1 de cada N cuadros
            return None
        caras = self._detectar(frame)
        if not caras:
            self.vistos = self.desconocidos = 0
            return None
        cara = max(caras, key=lambda c: c[2] * c[3])    # la cara mas grande (la mas cercana)
        x, y, w, h = [int(v) for v in cara[:4]]
        cv2.rectangle(frame, (x, y), (x + w, y + h), AMARILLO, 2)
        huella = self._huella(frame, cara)
        if registro:                                     # guardar varias huellas y abrir el formulario
            self.vistos += 1
            self.huellas_nuevas = (self.huellas_nuevas + [huella])[-MAX_HUELLAS_POR_PERSONA:]
            if self.vistos >= CUADROS_PARA_REGISTRO:
                self.fase, self.campos, self.foco, self.error = "formulario", ["", ""], 0, ""
            return None
        cedula, _ = self._buscar(huella, self.placa)     # entrada: es alguien asignado a esta placa?
        if cedula:
            self.desconocidos = 0
            self.vistos = self.vistos + 1 if cedula == self.candidato else 1
            self.candidato = cedula
            texto(frame, self.personas[cedula]["nombre"], (x, max(y - 8, 15)), 0.6, AMARILLO, 2)
            if self.vistos >= CONFIRMACIONES:
                p = self.personas[cedula]
                return self._terminar("RECONOCIDO", "BIENVENIDO " + p["nombre"], f"C.C. {cedula}  -  ENTRE",
                                      VERDE, cedula, p["nombre"])
        else:
            self.vistos, self.candidato = 0, None
            self.desconocidos += 1
            texto(frame, "Verificando...", (x, max(y - 8, 15)), 0.6, AMARILLO, 2)
            if self.desconocidos >= LECTURAS_PARA_DENEGAR:       # otra persona: no entra
                return self._terminar("DENEGADO", "ROSTRO NO AUTORIZADO - NO PASE",
                                      "Esta persona no esta asignada a esta placa", ROJO)
        return None

    # ---------- formulario (nombre y cedula) ----------
    def tecla(self, k):
        """Recibe una tecla mientras esta el formulario. Devuelve el resultado al terminar, o None."""
        if k == 27:                                      # Esc = cancelar
            return self._terminar("CANCELADO", "REGISTRO CANCELADO", "", NARANJA)
        if k == 9:                                       # Tab = cambiar de campo
            self.foco = 1 - self.foco
        elif k == 8:                                     # Retroceso = borrar
            self.campos[self.foco] = self.campos[self.foco][:-1]
        elif k == 13:                                    # Enter = siguiente campo / guardar
            nombre, cedula = self.campos[0].strip(), self.campos[1]
            if self.foco == 0 and len(nombre) >= 3:
                self.foco = 1
            elif len(nombre) < 3:
                self.error, self.foco = "Escribe el nombre (minimo 3 letras)", 0
            elif not (cedula.isdigit() and 6 <= len(cedula) <= 10):
                self.error, self.foco = "La cedula debe tener de 6 a 10 numeros", 1
            else:
                return self._registrar(nombre, cedula)
        elif 32 <= k < 127:                              # letra, numero o espacio
            c = chr(k)
            if self.foco == 0 and (c.isalpha() or c == " ") and len(self.campos[0]) < 40:
                self.campos[0] += c.upper()
            elif self.foco == 1 and c.isdigit() and len(self.campos[1]) < 10:
                self.campos[1] += c
        return None

    def _registrar(self, nombre, cedula):
        """Guarda la persona (nombre, cedula, huella facial y placa)."""
        huellas = [h.tolist() for h in self.huellas_nuevas[-3:]]
        p = self.personas.setdefault(cedula, {"nombre": nombre, "huellas": [], "placas": [],
                                              "registrado": datetime.now().isoformat(timespec="seconds")})
        p["huellas"] = (p["huellas"] + huellas)[-MAX_HUELLAS_POR_PERSONA:]   # si ya existia, suma huellas
        if self.placa not in p["placas"]:
            p["placas"].append(self.placa)
        self._guardar()
        return self._terminar("REGISTRADO", "PERSONA REGISTRADA - ENTRE", f"{p['nombre']}  C.C. {cedula}",
                              VERDE, cedula, p["nombre"])

    def _dibujar_formulario(self, frame):
        """Cuadro en pantalla con los campos Nombre y Cedula."""
        alto, ancho = frame.shape[:2]
        x0, y0, x1, y1 = int(ancho * 0.06), int(alto * 0.15), int(ancho * 0.94), int(alto * 0.85)
        capa = frame.copy()
        cv2.rectangle(capa, (x0, y0), (x1, y1), (30, 30, 30), -1)
        cv2.addWeighted(capa, 0.85, frame, 0.15, 0, frame)          # fondo oscuro semitransparente
        texto(frame, f"PERSONA AUTORIZADA - placa {self.placa}", (x0 + 15, y0 + 32), 0.7, AMARILLO, 2)
        for i, (etiqueta, valor) in enumerate(zip(("Nombre:", "Cedula:"), self.campos)):
            y = y0 + 80 + i * 70
            texto(frame, etiqueta, (x0 + 15, y - 8), 0.55)
            cv2.rectangle(frame, (x0 + 15, y), (x1 - 15, y + 34), AMARILLO if self.foco == i else (120, 120, 120), 2)
            cursor = "_" if self.foco == i and int(time.time() * 2) % 2 == 0 else ""   # cursor parpadeante
            texto(frame, valor + cursor, (x0 + 25, y + 25), 0.7, BLANCO, 2)
        if self.error:
            texto(frame, self.error, (x0 + 15, y0 + 215), 0.55, (80, 80, 255), 2)
        texto(frame, "Tab: cambiar campo | Enter: guardar | Esc: cancelar", (x0 + 15, y1 - 38), 0.5)
        texto(frame, "Al guardar, la persona autoriza guardar su huella facial (Ley 1581)", (x0 + 15, y1 - 14), 0.45, (200, 200, 200))

    def dibujar_aviso(self, frame):
        """Mensaje final (bienvenida, registro...) durante unos segundos."""
        if self.aviso and time.time() < self.aviso[3]:
            l1, l2, color, _ = self.aviso
            ancho = frame.shape[1]
            cv2.rectangle(frame, (0, 95), (ancho, 175), color, -1)
            texto(frame, l1, (15, 130), 0.9, BLANCO, 2, ancho - 30)
            texto(frame, l2, (15, 162), 0.7, BLANCO, 2, ancho - 30)
