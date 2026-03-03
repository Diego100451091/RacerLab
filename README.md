# RacerLab 🏁

Cronómetro de vueltas estilo racing para Logitech G29 (o cualquier volante / gamepad).

## Uso

1. **Doble clic en `launch.bat`** — instala dependencias automáticamente la primera vez.
2. Al abrir por primera vez: **pulsa L2** en el volante para que la app detecte el botón.
   - Si no tienes el volante conectado, pulsa **ESPACIO** para usar solo teclado.
3. ¡Listo! Cada vez que pulses **L2** (o **ESPACIO**), se registra el tiempo de esa vuelta.

## Controles

| Tecla / Botón | Acción |
|---|---|
| **L2** (volante) | Registrar vuelta |
| **ESPACIO** | Registrar vuelta (fallback teclado) |
| **R** | Reiniciar sesión |
| **ESC** | Salir |

## Colores

| Color | Significado |
|---|---|
| 🟣 Morado | Mejor vuelta (personal best) |
| 🟢 Verde | Más rápido que el mejor |
| 🟠 Naranja | Más lento pero dentro de 1 segundo |
| 🔴 Rojo | Más de 1 segundo por encima |

## Reconfigurar botón

Borra el fichero `config.json` y reinicia la app para volver a detectar el botón del volante.

## Requisitos

- Python 3.8+
- pygame 2.5+ (se instala automáticamente con `launch.bat`)
