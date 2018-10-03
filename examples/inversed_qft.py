# OPENQASM 2.0;
# include "qelib1.inc";
# qreg q[4];
# creg c[4];
# h q;
# barrier q;
# h q[0];
# measure q[0] -> c[0];
# if(c==1) u1(pi/2) q[1];
# h q[1];
# measure q[1] -> c[1];
# if(c==1) u1(pi/4) q[2];
# if(c==2) u1(pi/2) q[2];
# if(c==3) u1(pi/2+pi/4) q[2];
# h q[2];
# measure q[2] -> c[2];
# if(c==1) u1(pi/8) q[3];
# if(c==2) u1(pi/4) q[3];
# if(c==3) u1(pi/4+pi/8) q[3];
# if(c==4) u1(pi/2) q[3];
# if(c==5) u1(pi/2+pi/8) q[3];
# if(c==6) u1(pi/2+pi/4) q[3];
# if(c==7) u1(pi/2+pi/4+pi/8) q[3];
# h q[3];
# measure q[3] -> c[3];


from qasm.script import *

# include "qelib1.inc";
from qasm.qelib1 import *

from qasm.processor import *
import simulator.simulator

new_program()


q = allocate_qreg(4) # qreg q[4];
c = allocate_creg(4) # creg c[4];
op (
    h(q),                                               # h q;
    barrier(q),                                         # barrier q;
    h(q[0]),                                            # h q[0];
    measure(q[0], c[0]),                                # measure q[0] -> c[0];
    if_c(c, 1, u1(math.pi / 2., q[1])),                 # if(c==1) u1(pi/2) q[1];
    h(q[1]),                                            # h q[1];
    measure(q[1], c[1]),                                # measure q[1] -> c[1];
    if_c(c, 1, u1(math.pi / 4., q[2])),                 # if(c==1) u1(pi/4) q[2];
    if_c(c, 2, u1(math.pi / 2., q[2])),                 # if(c==2) u1(pi/2) q[2];
    if_c(c, 3, u1(math.pi / 2. + math.pi / 4., q[2])),  # if(c==3) u1(pi/2+pi/4) q[2];
    h(q[2]),                                            # h q[2];
    measure(q[2], c[2]),                                # measure q[2] -> c[2];
    if_c(c, 1, u1(math.pi / 8., q[3])),                 # if(c==1) u1(pi/8) q[3];
    if_c(c, 2, u1(math.pi / 4., q[3])),                 # if(c==2) u1(pi/4) q[3];
    if_c(c, 3, u1(math.pi / 4. + math.pi / 8., q[3])),  # if(c==3) u1(pi/4+pi/8) q[3];
    if_c(c, 4, u1(math.pi / 2., q[3])),                 # if(c==4) u1(pi/2) q[3];
    if_c(c, 5, u1(math.pi / 2. + math.pi / 8., q[3])),  # if(c==5) u1(pi/2+pi/8) q[3];
    if_c(c, 6, u1(math.pi / 2. + math.pi / 4., q[3])),  # if(c==6) u1(pi/2+pi/4) q[3];
    if_c(c, 7, u1(math.pi / 2. + math.pi / 4. + math.pi / 8., q[3])),
                                                        # if(c==7) u1(pi/2+pi/4+pi/8) q[3];
    h(q[3]),                                            # h q[3];
    measure(q[3], c[3])                                 # measure q[3] -> c[3];
)

program = current_program()
program = process(program, isolate_circuits=True)
sim = simulator.py(program)
sim.prepare()
while sim.run_step() :
    pass
sim.terminate()