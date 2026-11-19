/*
 * ============================================================================
 *  clasificador_uno.ino — Firmware del Arduino UNO
 *  Cyber Insanos · HACKATHÓN TESCo 2026 · Reto 1 (clasificador de residuos)
 * ============================================================================
 *
 *  QUÉ HACE: ejecuta comandos que llegan por el puerto serial y reporta sensores
 *  y teclas. NO decide nada: la máquina de estados vive en Python
 *  (backend/app/orchestrator.py).
 *
 *  PROTOCOLO: especificación, sección 9 + docs/api_contrato.md, sección 5.
 *  115 200 baudios, ASCII, una orden por línea terminada en '\n' ('\r' se ignora).
 *
 *  REGLAS DE DISEÑO
 *   - No bloqueante: todo con millis(). delay() solo en setup().
 *   - Nunca se mueven los dos servos a la vez (si llega una orden de movimiento
 *     mientras un servo trabaja → ERR:OCUPADO).
 *   - Siempre se responde (OK, *_OK o ERR:<código>).
 *   - Watchdog lógico: 15 s sin comandos → trampilla cerrada, disco a HOME y WATCHDOG.
 *
 *  SECCIONES DEL ARCHIVO
 *   1. Pines              6. LCD 20×4
 *   2. Configuración      7. LEDs e iluminación
 *   3. Calibración EEPROM 8. Teclado 4×4
 *   4. Servos             9. Parser de comandos
 *   5. Sensores IR       10. Watchdog
 *                        11. setup() y loop()
 *
 *  Bibliotecas: Servo, EEPROM y Wire (incluidas en el IDE),
 *  LiquidCrystal I2C (Frank de Brabander) y Keypad (Mark Stanley, Alexander Brevig).
 *  Generado con Claude Code (Anthropic) y revisado por el equipo; ver docs/recursos_externos.md.
 */

#include <Wire.h>
#include <Servo.h>
#include <EEPROM.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>

// ============================================================================
//  1. PINES (especificación, sección 8.1). No quedan pines libres en el UNO.
// ============================================================================
const uint8_t PIN_IR_BANDEJA      = 2;   // FC-51 #1: presencia en la bandeja (activo en BAJO)
const uint8_t PIN_IR_CAIDA        = 3;   // FC-51 #2: confirmación de caída (activo en BAJO, INT1)
const uint8_t PIN_SERVO_DISCO     = 9;   // Servo del carrusel (MG996R)
const uint8_t PIN_SERVO_TRAMPILLA = 10;  // Servo de la trampilla (SG90)
const uint8_t PIN_LED_VERDE       = A0;  // LED de estado verde   (resistencia 220–330 Ω)
const uint8_t PIN_LED_AMARILLO    = A1;  // LED de estado amarillo
const uint8_t PIN_LED_ROJO        = A2;  // LED de estado rojo
const uint8_t PIN_LUZ             = A3;  // Iluminación blanca a través del TIP120
// A4 (SDA) y A5 (SCL): LCD I2C. D0 y D1: USB serial.

// Teclado 4×4: filas D4–D7, columnas D8, D11, D12, D13.
// Nota: D13 también tiene el LED "L" de la placa; parpadea un poco al leer el teclado. Es normal.
byte PINES_FILAS[4]    = {4, 5, 6, 7};
byte PINES_COLUMNAS[4] = {8, 11, 12, 13};

// ============================================================================
//  2. CONFIGURACIÓN (todos los valores ajustables están aquí)
// ============================================================================
const long     VELOCIDAD_SERIAL       = 115200;
const uint8_t  LARGO_MAX_LINEA        = 80;     // caracteres por línea (contrato 5)

// --- LCD ---
const uint8_t  LCD_DIRECCION          = 0x27;   // [COMPLETAR] verificar con firmware/escaner_i2c (0x27 o 0x3F)
const uint8_t  LCD_COLUMNAS           = 20;
const uint8_t  LCD_FILAS              = 4;
const uint8_t  LCD_CARACTERES_POR_CICLO = 2;    // caracteres que se escriben por vuelta de loop() (no bloquear)
const unsigned long SCROLL_MS         = 350;    // velocidad del texto desplazándose (línea 4)
const uint8_t  SCROLL_SEPARACION      = 3;      // espacios entre el final y el inicio del texto

// --- Servo del disco ---
const unsigned long PASO_DISCO_MS     = 20;     // rampa: 1° cada 20 ms (más grande = más suave y lento)
const uint8_t  SOBREPASO_JUEGO        = 5;      // grados de más al bajar, para llegar siempre "desde abajo"
const uint8_t  ANG_DEFECTO[3]         = {170, 90, 10}; // Orgánica, Inorgánica, Peligroso (solo si la EEPROM está vacía)
const uint8_t  ANG_HOME_DEFECTO       = 90;

// --- Servo de la trampilla ---
const uint8_t  ANG_TRAMPILLA_CERRADA  = 0;      // [COMPLETAR] medir con el mecanismo armado
const uint8_t  ANG_TRAMPILLA_ABIERTA  = 90;     // [COMPLETAR] medir con el mecanismo armado
const unsigned long TRAMPILLA_ABIERTA_MS = 600; // tiempo que la trampilla queda abierta
const unsigned long TRAMPILLA_CIERRE_MS  = 300; // tiempo para que la trampilla termine de cerrar

// --- Sensores y tiempos ---
const unsigned long ANTIRREBOTE_IR_MS = 300;    // objeto estable ≥ 300 ms → OBJ / vacío ≥ 300 ms → LIBRE
const unsigned long DROP_TIMEOUT_MS   = 2000;   // sin caída en 2 s desde que se abre → DROP_TIMEOUT
const unsigned long WATCHDOG_MS       = 15000;  // sin comandos en 15 s → falla segura
const unsigned long PARPADEO_MS       = 300;    // medio periodo del parpadeo de los LEDs

// --- EEPROM ---
const int      EEPROM_DIRECCION       = 0;
const uint16_t EEPROM_MARCA           = 0xC1A5; // "EEPROM válida": si no está, se cargan los valores por defecto

// --- Tipos (van aquí arriba, antes de cualquier función, porque el IDE de Arduino
//     genera los prototipos de las funciones justo antes de la primera de ellas) ---

// Qué está haciendo la parte mecánica. Solo puede haber UNA cosa a la vez.
enum EstadoMov : uint8_t {
  MOV_REPOSO,          // nada se mueve: se aceptan órdenes de movimiento
  MOV_DISCO,           // el disco está en su rampa
  MOV_DROP_ABIERTA,    // trampilla abierta, esperando TRAMPILLA_ABIERTA_MS
  MOV_DROP_CERRANDO,   // trampilla cerrándose
  MOV_DROP_ESPERA,     // trampilla cerrada, esperando la confirmación de caída hasta 2 s
  MOV_WD_CERRANDO      // watchdog: cerrando la trampilla antes de llevar el disco a HOME
};

// Qué respuesta mandar cuando el disco termine su rampa.
enum Respuesta : uint8_t { RESP_NINGUNA, RESP_POS, RESP_ANG, RESP_HOME };

// ============================================================================
//  3. CALIBRACIÓN EN EEPROM
// ============================================================================
struct Calibracion {
  uint16_t marca;       // EEPROM_MARCA si los datos son válidos
  uint8_t  angulo[3];   // ángulo del servo para cada bote (0, 1, 2)
  uint8_t  home;        // ángulo de reposo del disco
};
Calibracion cal;

// Lee la calibración. Solo si la EEPROM está vacía o dañada usa (y guarda) los valores por defecto.
void cargarCalibracion() {
  EEPROM.get(EEPROM_DIRECCION, cal);
  bool valida = (cal.marca == EEPROM_MARCA) && (cal.home <= 180);
  for (uint8_t i = 0; i < 3; i++) {
    if (cal.angulo[i] > 180) valida = false;
  }
  if (!valida) {
    cal.marca = EEPROM_MARCA;
    for (uint8_t i = 0; i < 3; i++) cal.angulo[i] = ANG_DEFECTO[i];
    cal.home = ANG_HOME_DEFECTO;
    EEPROM.put(EEPROM_DIRECCION, cal);
  }
}

void guardarCalibracion() {
  EEPROM.put(EEPROM_DIRECCION, cal);  // put solo reescribe los bytes que cambiaron
}

// ============================================================================
//  4. SERVOS (disco con rampa no bloqueante; trampilla con tiempos)
// ============================================================================
Servo servoDisco;
Servo servoTrampilla;

EstadoMov estadoMov = MOV_REPOSO;
Respuesta respuestaPendiente = RESP_NINGUNA;
uint8_t   idPendiente = 0;

int angDisco = ANG_HOME_DEFECTO;   // ángulo que se le ha mandado al servo del disco
int angDestinoFinal = ANG_HOME_DEFECTO;
int angDestinoTramo = ANG_HOME_DEFECTO;  // destino intermedio (sobrepaso) o final
unsigned long ultimoPasoDisco = 0;

bool trampillaAbierta = false;
unsigned long inicioDrop = 0;      // cuándo se abrió la trampilla
unsigned long inicioFase = 0;      // inicio de la fase actual (cierre)

// Bandera de la interrupción del FC-51 #2 (volatile: la cambia la interrupción).
volatile bool caidaArmada = false;
volatile bool caidaDetectada = false;

bool ocupado() {
  return estadoMov != MOV_REPOSO;
}

void cerrarTrampilla() {
  servoTrampilla.write(ANG_TRAMPILLA_CERRADA);
  trampillaAbierta = false;
}

// Empieza a mover el disco hacia "destino" con rampa.
// Para eliminar el juego mecánico, siempre llega desde un ángulo MENOR:
// si el destino es menor que el ángulo actual, primero baja SOBREPASO_JUEGO grados de más.
void iniciarMovimientoDisco(int destino, Respuesta resp, uint8_t id) {
  angDestinoFinal = destino;
  respuestaPendiente = resp;
  idPendiente = id;
  if (destino < angDisco) {
    angDestinoTramo = max(0, destino - (int)SOBREPASO_JUEGO);
  } else {
    angDestinoTramo = destino;
  }
  ultimoPasoDisco = millis();
  estadoMov = MOV_DISCO;
}

void enviarRespuestaDisco() {
  switch (respuestaPendiente) {
    case RESP_POS:  Serial.print(F("POS_OK:")); Serial.println(idPendiente); break;
    case RESP_ANG:  Serial.print(F("ANG_OK:")); Serial.println(angDisco);    break;
    case RESP_HOME: Serial.println(F("HOME_OK"));                            break;
    default: break;  // movimiento interno (watchdog): no se responde
  }
  respuestaPendiente = RESP_NINGUNA;
}

// Un paso de la rampa cada PASO_DISCO_MS.
void actualizarDisco() {
  if (estadoMov != MOV_DISCO) return;
  if (millis() - ultimoPasoDisco < PASO_DISCO_MS) return;
  ultimoPasoDisco = millis();

  if (angDisco < angDestinoTramo)      angDisco++;
  else if (angDisco > angDestinoTramo) angDisco--;
  servoDisco.write(angDisco);

  if (angDisco == angDestinoTramo) {
    if (angDestinoTramo != angDestinoFinal) {
      angDestinoTramo = angDestinoFinal;  // terminó el sobrepaso: ahora sube al destino
    } else {
      estadoMov = MOV_REPOSO;
      enviarRespuestaDisco();
    }
  }
}

// Interrupción del FC-51 #2: un objeto que cae puede pasar en pocos milisegundos,
// por eso no se lee en loop() sino con interrupción (flanco de bajada).
void isrCaida() {
  if (caidaArmada) caidaDetectada = true;
}

bool leerCaida() {
  noInterrupts();
  bool hubo = caidaDetectada;
  interrupts();
  return hubo;
}

void iniciarDrop() {
  noInterrupts();
  caidaDetectada = false;
  caidaArmada = true;
  interrupts();
  servoTrampilla.write(ANG_TRAMPILLA_ABIERTA);
  trampillaAbierta = true;
  inicioDrop = millis();
  estadoMov = MOV_DROP_ABIERTA;
}

void terminarDrop(bool confirmado) {
  noInterrupts();
  caidaArmada = false;
  interrupts();
  estadoMov = MOV_REPOSO;
  Serial.println(confirmado ? F("DROP_OK") : F("DROP_TIMEOUT"));
}

// Secuencia de DROP: abrir → esperar → cerrar → responder.
// DROP_OK se manda cuando la trampilla YA está cerrada, para que el backend pueda
// mandar HOME en cuanto lo reciba (sin ERR:OCUPADO).
void actualizarTrampilla() {
  unsigned long ahora = millis();
  switch (estadoMov) {
    case MOV_DROP_ABIERTA:
      if (ahora - inicioDrop >= TRAMPILLA_ABIERTA_MS) {
        cerrarTrampilla();
        inicioFase = ahora;
        estadoMov = MOV_DROP_CERRANDO;
      }
      break;
    case MOV_DROP_CERRANDO:
      if (ahora - inicioFase >= TRAMPILLA_CIERRE_MS) estadoMov = MOV_DROP_ESPERA;
      break;
    case MOV_DROP_ESPERA:
      if (leerCaida())                              terminarDrop(true);
      else if (ahora - inicioDrop >= DROP_TIMEOUT_MS) terminarDrop(false);
      break;
    case MOV_WD_CERRANDO:
      if (ahora - inicioFase >= TRAMPILLA_CIERRE_MS) {
        iniciarMovimientoDisco(cal.home, RESP_NINGUNA, 0);
      }
      break;
    default:
      break;
  }
}

// ============================================================================
//  5. SENSOR IR DE LA BANDEJA (FC-51 #1) con antirrebote
// ============================================================================
bool irLecturaAnterior = false;    // última lectura cruda (true = hay objeto)
unsigned long irCambioMs = 0;      // cuándo cambió la lectura cruda
bool objetoEstable = false;        // estado confirmado (lo que ya se reportó)

// Manda OBJ o LIBRE una sola vez por flanco, cuando la lectura lleva ≥ 300 ms sin cambiar.
void revisarBandeja() {
  bool hayObjeto = (digitalRead(PIN_IR_BANDEJA) == LOW);  // FC-51: BAJO = detecta
  unsigned long ahora = millis();
  if (hayObjeto != irLecturaAnterior) {
    irLecturaAnterior = hayObjeto;
    irCambioMs = ahora;
    return;
  }
  if (hayObjeto != objetoEstable && ahora - irCambioMs >= ANTIRREBOTE_IR_MS) {
    objetoEstable = hayObjeto;
    Serial.println(hayObjeto ? F("OBJ") : F("LIBRE"));
  }
}

// ============================================================================
//  6. LCD 20×4 I2C (escritura NO bloqueante)
// ============================================================================
// El texto se guarda en "lcdDeseado" y loop() lo copia a la pantalla de 2 en 2 caracteres,
// solo los que cambiaron. Así una orden LCD no detiene la rampa del disco ni el serial.
LiquidCrystal_I2C lcd(LCD_DIRECCION, LCD_COLUMNAS, LCD_FILAS);

char lcdDeseado[LCD_FILAS][LCD_COLUMNAS + 1];
char lcdMostrado[LCD_FILAS][LCD_COLUMNAS + 1];
uint8_t cursorFila = 255, cursorCol = 255;   // 255 = posición desconocida

char textoScroll[LARGO_MAX_LINEA + 1];
uint8_t largoScroll = 0;
uint8_t posScroll = 0;
bool scrollActivo = false;
unsigned long ultimoScroll = 0;

// La LCD (HD44780) solo muestra ASCII imprimible: cualquier otro byte se cambia por '?'.
char caracterSeguro(char c) {
  return (c >= 32 && c <= 126) ? c : '?';
}

// Escribe "largo" caracteres de "texto" en una fila; recorta a 20 y rellena con espacios.
void lcdPonerLinea(uint8_t fila, const char* texto, uint8_t largo) {
  if (fila >= LCD_FILAS) return;
  for (uint8_t i = 0; i < LCD_COLUMNAS; i++) {
    lcdDeseado[fila][i] = (i < largo) ? caracterSeguro(texto[i]) : ' ';
  }
}

void lcdPonerLinea(uint8_t fila, const char* texto) {
  lcdPonerLinea(fila, texto, strlen(texto));
}

void dibujarScroll() {
  uint8_t total = largoScroll + SCROLL_SEPARACION;
  for (uint8_t i = 0; i < LCD_COLUMNAS; i++) {
    uint8_t idx = (posScroll + i) % total;
    lcdDeseado[3][i] = (idx < largoScroll) ? textoScroll[idx] : ' ';
  }
}

void iniciarScroll(const char* texto) {
  largoScroll = 0;
  while (texto[largoScroll] != '\0' && largoScroll < LARGO_MAX_LINEA) {
    textoScroll[largoScroll] = caracterSeguro(texto[largoScroll]);
    largoScroll++;
  }
  textoScroll[largoScroll] = '\0';
  if (largoScroll <= LCD_COLUMNAS) {     // cabe: se muestra fijo
    scrollActivo = false;
    lcdPonerLinea(3, textoScroll, largoScroll);
  } else {
    scrollActivo = true;
    posScroll = 0;
    ultimoScroll = millis();
    dibujarScroll();
  }
}

void actualizarScroll() {
  if (!scrollActivo) return;
  if (millis() - ultimoScroll < SCROLL_MS) return;
  ultimoScroll = millis();
  posScroll = (posScroll + 1) % (largoScroll + SCROLL_SEPARACION);
  dibujarScroll();
}

// Copia a la pantalla hasta LCD_CARACTERES_POR_CICLO caracteres que hayan cambiado.
void actualizarLcd() {
  uint8_t escritos = 0;
  for (uint8_t f = 0; f < LCD_FILAS; f++) {
    for (uint8_t c = 0; c < LCD_COLUMNAS; c++) {
      if (lcdDeseado[f][c] == lcdMostrado[f][c]) continue;
      if (escritos >= LCD_CARACTERES_POR_CICLO) return;
      if (cursorFila != f || cursorCol != c) lcd.setCursor(c, f);
      lcd.write(lcdDeseado[f][c]);
      lcdMostrado[f][c] = lcdDeseado[f][c];
      cursorFila = f;
      cursorCol = (c + 1 < LCD_COLUMNAS) ? c + 1 : 255;  // al final de la fila el cursor salta raro
      escritos++;
    }
  }
}

// Orden LCD:<l1>|<l2>|<l3>|<l4>. Las líneas que falten quedan en blanco; las de más se ignoran.
void ordenLcd(const char* args) {
  scrollActivo = false;
  uint8_t fila = 0;
  const char* inicio = args;
  while (fila < LCD_FILAS) {
    const char* fin = strchr(inicio, '|');
    uint8_t largo = fin ? (uint8_t)(fin - inicio) : strlen(inicio);
    lcdPonerLinea(fila, inicio, largo);
    fila++;
    if (!fin) break;
    inicio = fin + 1;
  }
  while (fila < LCD_FILAS) {   // líneas que no llegaron → en blanco
    lcdPonerLinea(fila, "", 0);
    fila++;
  }
}

// ============================================================================
//  7. LEDs DE ESTADO E ILUMINACIÓN
// ============================================================================
const uint8_t SIN_LED = 255;
uint8_t ledActivo = SIN_LED;
bool ledParpadeo = false;
bool ledEncendido = false;
unsigned long ultimoParpadeo = 0;

// Enciende un solo LED (o ninguno), fijo o parpadeando.
void ponerLed(uint8_t pin, bool parpadeo) {
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_AMARILLO, LOW);
  digitalWrite(PIN_LED_ROJO, LOW);
  ledActivo = pin;
  ledParpadeo = parpadeo;
  ledEncendido = (pin != SIN_LED);
  ultimoParpadeo = millis();
  if (pin != SIN_LED) digitalWrite(pin, HIGH);
}

void actualizarLed() {
  if (ledActivo == SIN_LED || !ledParpadeo) return;
  if (millis() - ultimoParpadeo < PARPADEO_MS) return;
  ultimoParpadeo = millis();
  ledEncendido = !ledEncendido;
  digitalWrite(ledActivo, ledEncendido ? HIGH : LOW);
}

// ============================================================================
//  8. TECLADO 4×4 (solo reporta KEY:<tecla>; los menús viven en Python)
// ============================================================================
char TECLAS[4][4] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
Keypad teclado = Keypad(makeKeymap(TECLAS), PINES_FILAS, PINES_COLUMNAS, 4, 4);

void revisarTeclado() {
  char tecla = teclado.getKey();   // no bloquea; ya trae antirrebote
  if (tecla) {
    Serial.print(F("KEY:"));
    Serial.println(tecla);
  }
}

// ============================================================================
//  9. PARSER DE COMANDOS
// ============================================================================
char bufferLinea[LARGO_MAX_LINEA + 1];
uint8_t largoLinea = 0;
bool lineaDesbordada = false;
unsigned long ultimoComandoMs = 0;
bool watchdogDisparado = false;

void aMayusculas(char* s) {
  for (; *s; s++) *s = toupper(*s);
}

// Lee un ángulo 0–180. Devuelve 0 = correcto, 1 = no es número (ERR:ARG), 2 = fuera de rango.
uint8_t leerAngulo(const char* s, int& valor) {
  uint8_t n = strlen(s);
  if (n == 0 || n > 3) return (n > 3 && strspn(s, "0123456789") == n) ? 2 : 1;
  for (uint8_t i = 0; i < n; i++) {
    if (!isdigit(s[i])) return 1;
  }
  valor = atoi(s);
  return (valor <= 180) ? 0 : 2;
}

// Lee un id de bote (0, 1 o 2). Devuelve -1 si no es válido.
int leerIdBote(const char* s) {
  if (strlen(s) == 1 && s[0] >= '0' && s[0] <= '2') return s[0] - '0';
  return -1;
}

void errorArg()      { Serial.println(F("ERR:ARG")); }
void errorOcupado()  { Serial.println(F("ERR:OCUPADO")); }
void responderOk()   { Serial.println(F("OK")); }

void responderErrorAngulo(uint8_t codigo) {
  if (codigo == 2) Serial.println(F("ERR:ANG_RANGO"));
  else             errorArg();
}

// Interpreta una línea completa (sin '\n') y responde SIEMPRE.
void procesarLinea(char* linea) {
  // Separa "COMANDO" de "argumentos" en el primer ':'
  char* args = strchr(linea, ':');
  if (args) { *args = '\0'; args++; }
  aMayusculas(linea);
  bool hayArgs = (args != NULL);

  // --- Sin argumentos ---
  if (strcmp(linea, "PING") == 0) {
    if (hayArgs) { errorArg(); return; }
    Serial.println(F("PONG"));
    return;
  }
  if (strcmp(linea, "STATUS") == 0) {
    if (hayArgs) { errorArg(); return; }
    Serial.print(F("STATUS:ang="));  Serial.print(angDisco);
    Serial.print(F(",tramp="));      Serial.print(trampillaAbierta ? F("ABIERTA") : F("CERRADA"));
    Serial.print(F(",obj="));        Serial.print(objetoEstable ? 1 : 0);
    Serial.print(F(",cal="));        Serial.print(cal.angulo[0]);
    Serial.print('/');               Serial.print(cal.angulo[1]);
    Serial.print('/');               Serial.println(cal.angulo[2]);
    return;
  }
  if (strcmp(linea, "HOME") == 0) {
    if (hayArgs) { errorArg(); return; }
    if (ocupado()) { errorOcupado(); return; }
    iniciarMovimientoDisco(cal.home, RESP_HOME, 0);
    return;
  }
  if (strcmp(linea, "DROP") == 0) {
    if (hayArgs) { errorArg(); return; }
    if (ocupado()) { errorOcupado(); return; }
    iniciarDrop();
    return;
  }

  // --- Textos para la LCD (se respetan mayúsculas y minúsculas del texto) ---
  if (strcmp(linea, "LCD") == 0) {
    if (!hayArgs) { errorArg(); return; }
    ordenLcd(args);
    responderOk();
    return;
  }
  if (strcmp(linea, "LCD_SCROLL") == 0) {
    if (!hayArgs) { errorArg(); return; }
    iniciarScroll(args);
    responderOk();
    return;
  }

  // --- Con argumentos ---
  if (!hayArgs) {
    if (strcmp(linea, "POS") == 0 || strcmp(linea, "ANG") == 0 || strcmp(linea, "LIGHT") == 0 ||
        strcmp(linea, "LED") == 0 || strcmp(linea, "CAL") == 0) {
      errorArg();
    } else {
      Serial.println(F("ERR:CMD_DESCONOCIDO"));
    }
    return;
  }
  aMayusculas(args);

  if (strcmp(linea, "POS") == 0) {
    int id = leerIdBote(args);
    if (id < 0) { errorArg(); return; }
    if (ocupado()) { errorOcupado(); return; }
    iniciarMovimientoDisco(cal.angulo[id], RESP_POS, id);
    return;
  }
  if (strcmp(linea, "ANG") == 0) {
    int grados;
    uint8_t codigo = leerAngulo(args, grados);
    if (codigo != 0) { responderErrorAngulo(codigo); return; }
    if (ocupado()) { errorOcupado(); return; }
    iniciarMovimientoDisco(grados, RESP_ANG, 0);
    return;
  }
  if (strcmp(linea, "LIGHT") == 0) {
    if (strcmp(args, "ON") == 0)       digitalWrite(PIN_LUZ, HIGH);
    else if (strcmp(args, "OFF") == 0) digitalWrite(PIN_LUZ, LOW);
    else { errorArg(); return; }
    responderOk();
    return;
  }
  if (strcmp(linea, "LED") == 0) {
    // LED:<COLOR> o LED:<COLOR>:PARPADEO
    bool parpadeo = false;
    char* modo = strchr(args, ':');
    if (modo) {
      *modo = '\0';
      modo++;
      if (strcmp(modo, "PARPADEO") != 0) { errorArg(); return; }
      parpadeo = true;
    }
    uint8_t pin;
    if (strcmp(args, "VERDE") == 0)         pin = PIN_LED_VERDE;
    else if (strcmp(args, "AMARILLO") == 0) pin = PIN_LED_AMARILLO;
    else if (strcmp(args, "ROJO") == 0)     pin = PIN_LED_ROJO;
    else if (strcmp(args, "OFF") == 0 && !parpadeo) pin = SIN_LED;
    else { errorArg(); return; }
    ponerLed(pin, parpadeo);
    responderOk();
    return;
  }
  if (strcmp(linea, "CAL") == 0) {
    // CAL:<id>:<ángulo> → guarda en EEPROM (no mueve el disco)
    char* textoAngulo = strchr(args, ':');
    if (!textoAngulo) { errorArg(); return; }
    *textoAngulo = '\0';
    textoAngulo++;
    int id = leerIdBote(args);
    if (id < 0) { errorArg(); return; }
    int grados;
    uint8_t codigo = leerAngulo(textoAngulo, grados);
    if (codigo != 0) { responderErrorAngulo(codigo); return; }
    cal.angulo[id] = grados;
    guardarCalibracion();
    Serial.print(F("CAL_OK:")); Serial.print(id);
    Serial.print(':');          Serial.println(grados);
    return;
  }

  Serial.println(F("ERR:CMD_DESCONOCIDO"));
}

// Junta los caracteres del serial en líneas. Ignora '\r'.
void leerSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (lineaDesbordada) {
        Serial.println(F("ERR:LINEA_LARGA"));
        ultimoComandoMs = millis();
        watchdogDisparado = false;
      } else if (largoLinea > 0) {
        bufferLinea[largoLinea] = '\0';
        ultimoComandoMs = millis();      // cualquier línea recibida reinicia el watchdog
        watchdogDisparado = false;
        procesarLinea(bufferLinea);
      }
      largoLinea = 0;
      lineaDesbordada = false;
      continue;
    }
    if (lineaDesbordada) continue;       // descarta el resto de una línea demasiado larga
    if (largoLinea >= LARGO_MAX_LINEA) { lineaDesbordada = true; continue; }
    bufferLinea[largoLinea++] = c;
  }
}

// ============================================================================
//  10. WATCHDOG LÓGICO (falla segura si la PC deja de mandar comandos)
// ============================================================================
// El backend manda PING cada 3 s. Si en 15 s no llega nada: se cierra la trampilla,
// después (nunca a la vez) el disco vuelve a HOME, y se avisa con WATCHDOG.
void revisarWatchdog() {
  if (watchdogDisparado) return;
  if (millis() - ultimoComandoMs < WATCHDOG_MS) return;
  watchdogDisparado = true;

  noInterrupts();
  caidaArmada = false;
  interrupts();

  bool trampillaEnUso = trampillaAbierta || estadoMov == MOV_DROP_ABIERTA ||
                        estadoMov == MOV_DROP_CERRANDO || estadoMov == MOV_DROP_ESPERA;
  cerrarTrampilla();
  if (trampillaEnUso) {
    inicioFase = millis();
    respuestaPendiente = RESP_NINGUNA;
    estadoMov = MOV_WD_CERRANDO;            // primero termina de cerrar, luego HOME
  } else {
    iniciarMovimientoDisco(cal.home, RESP_NINGUNA, 0);  // también corta un movimiento a medias
  }

  scrollActivo = false;
  lcdPonerLinea(0, "SIN ENLACE CON PC");
  lcdPonerLinea(1, "Trampilla cerrada");
  lcdPonerLinea(2, "Disco en reposo");
  lcdPonerLinea(3, "Revise el USB");
  Serial.println(F("WATCHDOG"));
}

// ============================================================================
//  11. setup() y loop()
// ============================================================================
void setup() {
  Serial.begin(VELOCIDAD_SERIAL);

  pinMode(PIN_IR_BANDEJA, INPUT_PULLUP);
  pinMode(PIN_IR_CAIDA, INPUT_PULLUP);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_AMARILLO, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  pinMode(PIN_LUZ, OUTPUT);
  digitalWrite(PIN_LUZ, LOW);
  ponerLed(SIN_LED, false);

  cargarCalibracion();

  // Falla segura al arrancar: primero la trampilla cerrada, luego el disco a HOME.
  // write() antes de attach() hace que el primer pulso ya sea el ángulo correcto.
  // (Aquí sí se permite delay(): solo ocurre una vez al encender.)
  servoTrampilla.write(ANG_TRAMPILLA_CERRADA);
  servoTrampilla.attach(PIN_SERVO_TRAMPILLA);
  trampillaAbierta = false;
  delay(500);
  angDisco = angDestinoFinal = angDestinoTramo = cal.home;
  servoDisco.write(angDisco);
  servoDisco.attach(PIN_SERVO_DISCO);
  delay(800);

  // LCD
  lcd.init();
  Wire.setWireTimeout(25000, true);   // si el bus I2C falla, no se cuelga el programa
  lcd.backlight();
  lcd.clear();
  memset(lcdMostrado, ' ', sizeof(lcdMostrado));  // después de clear() la pantalla está en blanco
  lcdPonerLinea(0, "== CLASIFICADOR ==");
  lcdPonerLinea(1, "Cyber Insanos");
  lcdPonerLinea(2, "Esperando PC...");
  lcdPonerLinea(3, "");

  // FC-51 #2 por interrupción (D3 = INT1)
  attachInterrupt(digitalPinToInterrupt(PIN_IR_CAIDA), isrCaida, FALLING);

  // Bandeja: si al arrancar ya hay objeto, se reportará OBJ tras 300 ms.
  irLecturaAnterior = (digitalRead(PIN_IR_BANDEJA) == LOW);
  irCambioMs = millis();
  objetoEstable = false;

  ultimoComandoMs = millis();
  Serial.println(F("READY"));
}

void loop() {
  leerSerial();          // órdenes de la PC
  actualizarDisco();     // rampa del disco
  actualizarTrampilla(); // secuencia de DROP y del watchdog
  revisarBandeja();      // OBJ / LIBRE
  revisarTeclado();      // KEY:<tecla>
  actualizarLed();       // parpadeo
  actualizarScroll();    // texto de la línea 4
  actualizarLcd();       // escribe en la LCD poco a poco
  revisarWatchdog();     // falla segura
}
