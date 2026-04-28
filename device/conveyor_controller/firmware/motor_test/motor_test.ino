/*
 * Motor Hardware Diagnostic
 * Tests each pin individually to find wiring issue
 */

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(25, OUTPUT);  // ENA
  pinMode(26, OUTPUT);  // IN1
  pinMode(27, OUTPUT);  // IN2

  Serial.println("\n=== MOTOR PIN DIAGNOSTIC ===\n");

  // Test 1: IN1=HIGH, IN2=LOW, ENA=HIGH (no PWM, full power)
  Serial.println("[Test 1] GPIO26=HIGH, GPIO27=LOW, GPIO25=HIGH (digital, full power)");
  Serial.println("  -> Motor should spin FORWARD");
  digitalWrite(26, HIGH);
  digitalWrite(27, LOW);
  digitalWrite(25, HIGH);
  delay(3000);
  digitalWrite(25, LOW);
  digitalWrite(26, LOW);
  Serial.println("  -> Stopped\n");
  delay(1000);

  // Test 2: IN1=LOW, IN2=HIGH, ENA=HIGH
  Serial.println("[Test 2] GPIO26=LOW, GPIO27=HIGH, GPIO25=HIGH (digital, full power)");
  Serial.println("  -> Motor should spin REVERSE");
  digitalWrite(26, LOW);
  digitalWrite(27, HIGH);
  digitalWrite(25, HIGH);
  delay(3000);
  digitalWrite(25, LOW);
  digitalWrite(27, LOW);
  Serial.println("  -> Stopped\n");
  delay(1000);

  // Test 3: PWM on ENA
  Serial.println("[Test 3] PWM on GPIO25, speed=255 (max)");
  ledcAttach(25, 1000, 8);
  digitalWrite(26, HIGH);
  digitalWrite(27, LOW);
  ledcWrite(25, 255);
  delay(3000);
  ledcWrite(25, 0);
  digitalWrite(26, LOW);
  Serial.println("  -> Stopped\n");
  delay(1000);

  // Test 4: Individual pin toggle (for multimeter check)
  Serial.println("[Test 4] Pin voltage check (use multimeter if available)");

  Serial.println("  GPIO25 = HIGH (3.3V expected)");
  ledcDetach(25);
  pinMode(25, OUTPUT);
  digitalWrite(25, HIGH);
  delay(2000);
  Serial.printf("  GPIO25 read: %d\n", digitalRead(25));
  digitalWrite(25, LOW);

  Serial.println("  GPIO26 = HIGH (3.3V expected)");
  digitalWrite(26, HIGH);
  delay(2000);
  Serial.printf("  GPIO26 read: %d\n", digitalRead(26));
  digitalWrite(26, LOW);

  Serial.println("  GPIO27 = HIGH (3.3V expected)");
  digitalWrite(27, HIGH);
  delay(2000);
  Serial.printf("  GPIO27 read: %d\n", digitalRead(27));
  digitalWrite(27, LOW);

  Serial.println("\n=== DIAGNOSTIC COMPLETE ===");
  Serial.println("If motor did NOT spin in any test:");
  Serial.println("  1. Is 12V power supply connected to L298N?");
  Serial.println("  2. Is L298N ENA jumper REMOVED?");
  Serial.println("  3. Are wires: GPIO25->ENA, GPIO26->IN1, GPIO27->IN2?");
  Serial.println("  4. Are motor wires connected to L298N OUT1/OUT2?");
  Serial.println("  5. Try connecting motor directly to 12V to verify motor works");
}

void loop() {
  delay(1000);
}
