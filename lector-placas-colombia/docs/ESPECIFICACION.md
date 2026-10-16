# Especificación del proyecto

## Problema
Controlar de forma manual quién entra a un parqueadero o instalación es lento y propenso a errores; no queda registro de las placas que pasan.

## Usuario
Operador / portero que maneja el sistema en un computador con cámara.

## Objetivo general
Leer automáticamente placas colombianas con una cámara, decidir si el vehículo está autorizado, vetado o no registrado, y dejar evidencia (foto y registro).

## Alcance
**Incluye:** placas de carro (LLLNNN) y moto (LLLNNL), cualquier orientación y color, listas de autorizadas/vetadas, letrero en pantalla, foto y registro CSV.
**No incluye:** apertura de barreras, base de datos en red, placas de otros países, lectura de video grabado.

## Entradas y salidas
| Entradas | Salidas |
|---|---|
| Video de la cámara | Letrero en pantalla (verde/rojo/naranja) |
| Placas escritas por el operador | Foto `PLACA_AAAAMMDD_HHMMSS.jpg` en su carpeta |
| Configuración (constantes del código) | `registro.csv` y `placas.json` |

## Procesamiento
1. Capturar cuadro → 2. Buscar rectángulos con forma de placa (cualquier ángulo) → 3. Enderezar → 4. OCR (imagen normal e invertida) → 5. Corregir al formato de placa → 6. Confirmar 2 lecturas seguidas → 7. Decidir estado, mostrar letrero, guardar foto y registro.

## Criterios de éxito
- Lee la placa correctamente con buena luz a 30–60 cm.
- El video se mantiene fluido (~30 fps) mientras lee.
- No repite la misma placa antes de 10 s.
- No se cae si la carpeta no tiene permisos o el CSV está abierto.

## Casos de prueba
| Tipo | Ejemplo | Resultado esperado |
|---|---|---|
| Normal | `ABC123` autorizada | Letrero verde, foto y registro |
| Normal | Moto `ABC12D` | Se lee y clasifica |
| Frontera | Placa girada / al revés | Se detecta y se lee |
| Frontera | Letra confundida (`A8C123`) | Se corrige a `ABC123` |
| Inválido | Operador escribe `AB12` | Rechaza el formato |
| Inválido | Palabra `COLOMBIA` | No se toma como placa |
| Extremo | CSV abierto en Excel | Usa `registro_respaldo.csv` |
| Extremo | Sin placa / mala luz | No guarda nada |

## Uso previsto de IA
Claude se usó como apoyo para generar, depurar y reducir el código. Cada cambio fue revisado y probado por el equipo (ver commits).
