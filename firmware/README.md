# firmware

Firmware del **Arduino UNO** en `clasificador_uno/clasificador_uno.ino` (Fase 2).

- Bibliotecas: `Servo`, `LiquidCrystal_I2C`, `Keypad`, `EEPROM`.
- Protocolo serial 115 200 baudios, ASCII, fin de línea `\n` (especificación, sección 9).
- El Arduino **solo ejecuta comandos y reporta sensores/teclas**; la lógica de estados vive en Python.
- Prueba: Arduino IDE → Monitor Serial a 115 200, fin de línea "Nueva línea".
