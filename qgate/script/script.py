import qgate.model as model
import numbers

def _expand_args(args) :
    expanded = []
    if isinstance(args, (list, tuple, set)) :
        for child in args :
            expanded += _expand_args(child)
    else :
        expanded.append(args)
    return expanded

def _assert_is_number(obj) :
    if not isinstance(obj, numbers.Number) :
        raise RuntimeError('{} is not a number'.format(str(obj)))

def new_gatelist() :
    return model.GateList()

def new_qreg() :
    return model.Qreg()

def new_qregs(count) :
    return [model.Qreg() for _ in range(count)]

def release_qreg(qreg) :
    return model.ReleaseQreg(qreg)

def new_reference() :
    return model.Reference()

def new_references(count) :
    return [model.Reference() for _ in range(count)]

# functions to instantiate operators

def measure(outref, args) :
    if isinstance(args, model.Qreg):
        return model.Measure(outref, args)
    args = _expand_args(args)
    return model.PauliMeasure(outref, args)

def prob(outref, args) :
    if isinstance(args, model.Qreg):
        return model.Prob(outref, args)
    args = _expand_args(args)
    return model.PauliProb(outref, args)
    

def barrier(*qregs) :
    qregs = _expand_args(qregs)
    bar = model.Barrier(qregs)
    return bar

def reset(qreg) :
    return model.Reset(qreg)

def if_(refs, cond, clause) :
    refs = _expand_args(refs)
    gatelist = model.GateList()
    gatelist.set(clause)
    if_clause = model.IfClause(refs, cond, gatelist)
    return if_clause
#
# Gate
#
import qgate.model.gate_type as gtype

import sys
this = sys.modules[__name__]


# module level
#  gate type + gate parameters


class GateFactory :
    def __init__(self, gate_type) :
        self.gate = model.Gate(gate_type)

    @property
    def Adj(self) :
        self.gate.set_adjoint(True)
        return self

    def __call__(self, qreg) :
        self.gate.set_qreg(qreg)
        self.gate.check_constraints()
        return self.gate

class ConstGateFactory :
    def __init__(self, gate_type) :
        self.gate_type = gate_type
        
    @property
    def Adj(self) :
        factory = GateFactory(self.gate_type)
        return factory.Adj
        
    def __call__(self, qreg) :
        g = model.Gate(self.gate_type)
        g.set_qreg(qreg)
        g.check_constraints()
        return g


# // idle gate (identity)
# gate id a { U(0,0,0) a; }
this.I = ConstGateFactory(gtype.ID())

# // Clifford gate: Hadamard
# gate h a { u2(0,pi) a; }
this.H = ConstGateFactory(gtype.H())

# // Clifford gate: sqrt(Z) phase gate
# gate s a { u1(pi/2) a; }
this.S = ConstGateFactory(gtype.S())

# // C3 gate: sqrt(S) phase gate
# gate t a { u1(pi/4) a; }
this.T = ConstGateFactory(gtype.T())

# // Pauli gate: bit-flip
# gate x a { u3(pi,0,pi) a; }
this.X = ConstGateFactory(gtype.X())

# // Pauli gate: bit and phase flip
# gate y a { u3(pi,pi/2,pi/2) a; }
this.Y = ConstGateFactory(gtype.Y())

# // Pauli gate: phase flip
# gate z a { u1(pi) a; }
this.Z = ConstGateFactory(gtype.Z())

# // Rotation around X-axis
# gate rx(theta) a { u3(theta,-pi/2,pi/2) a; }
def Rx(theta) :
    _assert_is_number(theta)
    return GateFactory(gtype.RX(theta))

# // rotation around Y-axis
# gate ry(theta) a { u3(theta,0,0) a; }
def Ry(theta) :
    _assert_is_number(theta)
    return GateFactory(gtype.RY(theta))

# // rotation around Z axis
# gate rz(phi) a { u1(phi) a; }
def Rz(theta) :
    _assert_is_number(theta)
    return GateFactory(gtype.RZ(theta))

# 1 parameeter

# // 1-parameter 0-pulse single qubit gate
# gate u1(lambda) q { U(0,0,lambda) q; }
def U1(_lambda) :
    _assert_is_number(_lambda)
    return GateFactory(gtype.U1(_lambda))

# 2 parameeters

# // 2-parameter 1-pulse single qubit gate
# gate u2(phi,lambda) q { U(pi/2,phi,lambda) q; }
def U2(phi, _lambda) :
    _assert_is_number(_lambda)
    return GateFactory(gtype.U2(phi, _lambda))

# 3 parameeters

# // --- QE Hardware primitives ---
# // 3-parameter 2-pulse single qubit gate
# gate u3(theta,phi,lambda) q { U(theta,phi,lambda) q; }
def U3(theta, phi, _lambda) :
    _assert_is_number(theta)
    _assert_is_number(phi)
    _assert_is_number(_lambda)
    return GateFactory(gtype.U(theta, phi, _lambda))

# exp
def Expii(theta) :
    _assert_is_number(theta)
    return GateFactory(gtype.ExpiI(theta))

def Expiz(theta) :
    _assert_is_number(theta)
    return GateFactory(gtype.ExpiZ(theta))

# utility
this.SH = ConstGateFactory(gtype.SH())

class GatelistMacroFactory :
    def __init__(self, gate_type) :
        self.gate = model.GatelistMacro(gate_type)

    @property
    def Adj(self) :
        self.gate.set_adjoint(True)
        return self

    def __call__(self, *gatelist) :
        gatelist = _expand_args(gatelist)
        self.gate.set_gatelist(gatelist)
        self.gate.check_constraints()
        return self.gate


# multi qubit gate
def Expi(theta) :
    return GatelistMacroFactory(gtype.Expi(theta))


class ControlledGateFactory :

    def __init__(self, control) :
        self.control = _expand_args(control)
        if len(self.control) == 0 :
            raise RuntimeError('control qreg list must not be empty.')
        
    def create(self, gtype) :
        factory = GateFactory(gtype)
        factory.gate.set_ctrllist(self.control)
        return factory
        
    @property
    def I(self) :
        return self.create(gtype.ID())

    @property
    def H(self) :
        return self.create(gtype.H())
    
    @property
    def S(self) :
        return self.create(gtype.S())

    @property
    def T(self) :
        return self.create(gtype.T())

    @property
    def X(self) :
        return self.create(gtype.X())

    @property
    def Y(self) :
        return self.create(gtype.Y())

    @property
    def Z(self) :
        return self.create(gtype.Z())
    
    def Rx(self, theta) :
        _assert_is_number(theta)
        return self.create(gtype.RX(theta))

    def Ry(self, theta) :
        _assert_is_number(theta)
        return self.create(gtype.RY(theta))

    def Rz(self, theta) :
        _assert_is_number(theta)
        return self.create(gtype.RZ(theta))
    
    def U1(self, _lambda) :
        _assert_is_number(_lambda)
        return self.create(gtype.U1(_lambda))

    def U2(self, phi, _lambda) :
        _assert_is_number(phi)
        _assert_is_number(_lambda)
        return self.create(gtype.U2(phi, _lambda))

    def U3(self, theta, phi, _lambda) :
        _assert_is_number(theta)
        _assert_is_number(phi)
        _assert_is_number(_lambda)
        return self.create(gtype.U(theta, phi, _lambda))

    # multi qubit gate
    def create_gatelistmacro(self, gtype) :
        factory = GatelistMacroFactory(gtype)
        factory.gate.set_ctrllist(self.control)
        return factory
    
    def Expii(self, theta) :
        return self.create(gtype.ExpiI(theta))
    
    def Expiz(self, theta) :
        return self.create(gtype.ExpiZ(theta))

    # utility
    @property
    def SH(self) :
        return self.create(gtype.SH())
    
    def Expi(self, theta) :
        return self.create_gatelistmacro(gtype.Expi(theta))

    
def controlled(*control) :
    return ControlledGateFactory(control);

this.ctrl = controlled

# swap
def Swap(qreg0, qreg1) :
    g = model.MultiQubitGate(gtype.SWAP())
    g.set_qreglist([qreg0, qreg1])
    return g
