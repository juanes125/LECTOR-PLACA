# Evidencia de un cambio revisado

**Cambio:** commit `Acorta el codigo de 628 a 432 lineas sin cambiar el comportamiento`.

## Qué cambió
- Código de 628 a 432 líneas (−31 %).
- Se eliminó el modo "probar con una foto"; el menú pasó de 7 a 6 opciones (Salir = 6).
- Validación de placa unificada en un solo patrón (`PATRON_PLACA`) y letreros en un diccionario (`ESTADOS`).
- Lectura en segundo plano agrupada en la clase `LectorEnSegundoPlano`.

## Cómo se revisó
Se comparó la versión nueva contra la anterior con pruebas automáticas (cámara y OCR simulados):
- `corregir_placa`: 14 textos de prueba, mismos resultados en ambas versiones.
- Moto de dos renglones con la palabra COLOMBIA → `ABC12D`.
- Validación del operador: `AB12` se rechaza, `abc-12d` → `ABC12D`.
- CSV bloqueado → se usa `registro_respaldo.csv`.
- Ciclo de cámara simulado: ~29,6 cuadros/s y una sola foto guardada por placa.

## Pendiente (a cargo del revisor)
Probar con la cámara real y anotar el resultado: [ ] funciona  [ ] observaciones: ______
