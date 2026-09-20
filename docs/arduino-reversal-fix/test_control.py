"""Compile actual motor control functions with fake pins and encoder counters."""
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('main.cpp').read_text()
constants = source[source.index('const float wheelRadiusM'):source.index('WheelProtocol wheelProtocol;')]
functions = source[source.index('void stopMotors() {'):]
harness = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <algorithm>
#define PI 3.14159265358979323846
#define HIGH 1
#define LOW 0
const int PWMA=5, PWMB=6, AIN1=7, AIN2=8, BIN1=9, BIN2=10;
int pins[20]={};
void analogWrite(int pin, int value) { pins[pin]=value; }
void digitalWrite(int, int) {}
void noInterrupts() {}
void interrupts() {}
int constrain(int x,int lo,int hi) { return std::max(lo,std::min(x,hi)); }
'''+constants+r'''
WheelControlState wheelAState, wheelBState;
float targetSpeedA=0, targetSpeedB=0, measuredSpeedA=0, measuredSpeedB=0;
long encoder1Count=0, encoder2Count=0, lastE1=0, lastE2=0;
int encoderLeftSign=1, encoderRightSign=1;
unsigned long lastControlTime=0;
bool motorFault=false;
'''+functions+r'''
void reset(int a, int b) {
  wheelAState=WheelControlState(); wheelBState=WheelControlState();
  wheelAState.direction=a; wheelBState.direction=b;
  encoder1Count=encoder2Count=lastE1=lastE2=0;
  lastControlTime=0; stopMotors();
}
void checkTransition(int a,int b,float ta,float tb) {
  reset(a,b); targetSpeedA=ta; targetSpeedB=tb;
  for(unsigned long t=20;t<=220;t+=20) {
    runWheelControl(t);
    assert(pins[PWMA]==0 && pins[PWMB]==0);
  }
  runWheelControl(240);
  assert(pins[PWMA]>0 && pins[PWMB]>0);
  assert(wheelAState.direction==(ta>0?1:-1));
  assert(wheelBState.direction==(tb>0?1:-1));
}
int main() {
  // Both ways from a spin to forward; forward to spin and to reverse.
  checkTransition(-1,1,0.08f,0.08f);
  checkTransition(1,-1,0.08f,0.08f);
  checkTransition(1,1,-0.03f,0.03f);
  checkTransition(1,1,-0.08f,-0.08f);
  reset(1,1); targetSpeedA=targetSpeedB=0.08f;
  runWheelControl(20);
  assert(pins[PWMA]>0 && pins[PWMB]>0); // no gratuitous coast
  stopMotors();
  assert(pins[PWMA]==0 && pins[PWMB]==0);
  reset(-1,1); targetSpeedA=targetSpeedB=0.08f;
  // A still moving: timeout alone must not allow reversal.
  for(unsigned long t=20;t<=400;t+=20) {
    encoder1Count+=10; runWheelControl(t);
    assert(pins[PWMA]==0 && pins[PWMB]==0);
  }
  runWheelControl(420); runWheelControl(440);
  assert(pins[PWMA]==0 && pins[PWMB]==0);
  runWheelControl(460);
  assert(pins[PWMA]>0 && pins[PWMB]>0);
  // Immediate cancellation while waiting.
  reset(-1,1); targetSpeedA=targetSpeedB=0.08f;
  runWheelControl(20); stopMotors(); runWheelControl(40);
  assert(pins[PWMA]==0 && pins[PWMB]==0);
  // Invalid control interval retains the existing stop behavior.
  targetSpeedA=targetSpeedB=0.08f; runWheelControl(1000);
  assert(pins[PWMA]==0 && pins[PWMB]==0);
}
'''
with tempfile.TemporaryDirectory(prefix='kasif-control-') as tmp:
    cpp=Path(tmp)/'test.cpp'; binary=Path(tmp)/'test'
    cpp.write_text(harness)
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
print('Motor control regression tests passed.')
