/*
 * escaner_i2c.ino — Encuentra la dirección I2C de la LCD 20×4.
 *
 * Uso: cargarlo en el UNO con la LCD conectada (SDA = A4, SCL = A5, VCC = 5 V, GND).
 * Abrir el Monitor Serial a 115 200. La dirección típica es 0x27 o 0x3F.
 * Copiar la dirección encontrada en LCD_DIRECCION de clasificador_uno.ino.
 * Generado con Claude Code (Anthropic); basado en el escáner I2C clásico de Arduino Playground.
 */
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setWireTimeout(25000, true);  // no colgarse si el bus está mal conectado
  Serial.println(F("Escaner I2C: buscando dispositivos..."));
}

void loop() {
  uint8_t encontrados = 0;
  for (uint8_t direccion = 1; direccion < 127; direccion++) {
    Wire.beginTransmission(direccion);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Serial.print(F("Dispositivo en 0x"));
      if (direccion < 16) Serial.print('0');
      Serial.println(direccion, HEX);
      encontrados++;
    } else if (error == 5) {
      Serial.println(F("Tiempo agotado en el bus I2C: revisar SDA/SCL y GND"));
      break;
    }
  }
  if (encontrados == 0) Serial.println(F("Ningun dispositivo. Revisar cables, 5 V y GND."));
  Serial.println(F("--- nueva busqueda en 5 s ---"));
  delay(5000);
}
