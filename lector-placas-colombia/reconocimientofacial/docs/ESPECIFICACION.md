# Especificación del proyecto

## Problema
Controlar de forma manual quién entra a un parqueadero o instalación es lento y propenso a errores; no queda registro de las placas que pasan.

## Usuario
Operador / portero que maneja el sistema en un computador con cámara.

## Objetivo general
Leer automáticamente placas colombianas con una cámara, decidir si el vehículo está autorizado, vetado o no registrado, y dejar evidencia (foto y registro).

## Alcance
**Incluye:** placas de carro (LLLNNN) y moto (LLLNNL), cualquier orientación y color, listas de autorizadas/vetadas, letrero en pantalla, foto y registro CSV, y reconocimiento facial: cada placa tiene asignadas las caras de las personas autorizadas a usar el vehículo; solo ellas entran.
**No incluye:** apertura de barreras, base de datos en red, placas de otros países, lectura de video grabado.

## Entradas y salidas
| Entradas | Salidas |
|---|---|
| Video de la cámara | Letrero en pantalla (verde/rojo/naranja) |
| Placas escritas por el operador | Foto `PLACA_AAAAMMDD_HHMMSS.jpg` en su carpeta |
| Nombre y cédula de personas nuevas | `registro.csv`, `placas.json`, `personas.json` y `registro_personas.csv` |

## Procesamiento
1. Capturar cuadro → 2. Buscar rectángulos con forma de placa (cualquier ángulo) → 3. Enderezar → 4. OCR (imagen normal e invertida) → 5. Corregir al formato de placa → 6. Confirmar 2 lecturas seguidas → 7. Decidir estado, mostrar letrero, guardar foto y registro. 8. Si la placa es autorizada: detectar el rostro y compararlo solo con las personas asignadas a esa placa; si coincide, entra; si no, se niega. Placa no registrada: «Acérquese al supervisor».

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
| Normal | Operador asigna el rostro del dueño a su placa | Queda guardado (nombre, cédula, huella) |
| Normal | Dueño o persona asignada con su placa | «Bienvenido», entra |
| Inválido | Otra persona con una placa ajena | «Rostro no autorizado - no pase» |
| Inválido | Placa no registrada | «Acérquese al supervisor» |
| Frontera | Cédula de 4 dígitos | Rechaza y avisa |
| Extremo | Nadie frente a la cámara 30 s | Cancela la etapa del rostro |
| Extremo | Placa vetada | «No pase»; no se pide el rostro |

## Uso previsto de IA
Claude se usó como apoyo para generar, depurar y reducir el código. Cada cambio fue revisado y probado por el equipo (ver commits).
