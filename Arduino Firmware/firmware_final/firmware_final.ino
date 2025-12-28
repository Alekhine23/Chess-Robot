#include <AccelStepper.h>
#include <MultiStepper.h>

#include <VarSpeedServo.h>

const int signal_servo = 12;
const int stepPinRight = 5;
const int dirPinRight = 6;
const int stepPinLeft = 3;
const int dirPinLeft = 4;
const int stepPinBase = 7;
const int dirPinBase = 8;
const int MS1 = 9;
const int MS2 = 10;
const int MS3 = 11;

int command = 0;
int angle;
int speed;
int expectedBytes;

const float degPerStep = 0.9;
int gearRatio = 5;

AccelStepper stepperRight(AccelStepper::DRIVER, stepPinRight, dirPinRight);
AccelStepper stepperLeft(AccelStepper::DRIVER, stepPinLeft, dirPinLeft);
AccelStepper stepperBase(AccelStepper::DRIVER, stepPinBase, dirPinBase);

VarSpeedServo myServo;

void setup() {
  pinMode(stepPinRight, OUTPUT);
  pinMode(dirPinRight, OUTPUT);
  pinMode(stepPinLeft, OUTPUT);
  pinMode(dirPinLeft, OUTPUT);
  pinMode(stepPinBase, OUTPUT);
  pinMode(dirPinBase, OUTPUT);

  pinMode(MS1, OUTPUT);
  pinMode(MS2, OUTPUT);
  pinMode(MS3, OUTPUT);
  digitalWrite(MS1, HIGH);
  digitalWrite(MS2, LOW);
  digitalWrite(MS3, LOW);

  Serial.begin(9600);
  myServo.attach(signal_servo);
  myServo.slowmove(95, 10);
  delay(1000);

  stepperRight.setMaxSpeed(100);
  stepperRight.setAcceleration(100);

  stepperLeft.setMaxSpeed(100);
  stepperLeft.setAcceleration(100);

  stepperBase.setMaxSpeed(100);
  stepperBase.setAcceleration(100);
}

void loop() {
   
  if (Serial.available() > 0) {
    command = Serial.read();

    switch (command) {
      case (1):
        expectedBytes = 2;
        break;
      case (2):
        expectedBytes = 6;
        break;
    }

    unsigned long startTime = millis();
    while (Serial.available() < expectedBytes) {
      if (millis() - startTime > 1000) {
        return;
      }
    }

    switch (command) {
      case (1):
        angle = Serial.read();
        speed = Serial.read();
        myServo.slowmove(angle, speed);

        while(myServo.isMoving()) {
        delay(10);
        }
        delay(100);
        break;

      case (2):
        int angleRight = Serial.read();
        int dirRight = Serial.read();
        int angleLeft = Serial.read();
        int dirLeft = Serial.read();
        int angleBase = Serial.read();
        int dirBase = Serial.read();

        stepperRight.setPinsInverted(dirRight == 0, false, false);
        stepperLeft.setPinsInverted(dirLeft == 0, false, false);
        stepperBase.setPinsInverted(dirBase == 0, false, false);

        int stepsRight = round((angleRight * gearRatio)/degPerStep);
        int stepsLeft = round((angleLeft * gearRatio)/degPerStep);
        int stepsBase = round((angleBase * gearRatio)/degPerStep);

        stepperRight.move(stepsRight);
        stepperLeft.move(stepsLeft);
        stepperBase.move(stepsBase);

        while (stepperRight.distanceToGo() != 0 || stepperLeft.distanceToGo() != 0 || stepperBase.distanceToGo() != 0) {
          stepperRight.run();
          stepperLeft.run();
          stepperBase.run();
          }
        break;
      
      default:
        break;
    }
  }
}
