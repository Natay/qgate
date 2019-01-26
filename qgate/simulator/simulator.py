import qgate.model as model
import qgate.model.gate as gate
from .qubits import Qubits, qproc, Lane
from .creg_values import CregValues
import numpy as np
import math
import random

def _op_key(op_tuple) :
    return op_tuple[0].idx


class Simulator :
    def __init__(self, defpkg, dtype) :
        self.defpkg = defpkg
        self.processor = defpkg.create_qubit_processor(dtype)
        self._qubits = Qubits(dtype)

    def set_circuits(self, circuits) :
        if len(circuits) == 0 :
            raise RuntimeError('empty circuits')
        self.circuits = circuits
        
    def qubits(self) :
        return self._qubits
    
    def creg_values(self) :
        return self._creg_values

    def prepare(self, n_lanes_per_chunk = None, device_ids = []) :
        self.processor.clear()

        # merge all gates, and sort them.
        ops = []
        for circuit_idx, circuit in enumerate(self.circuits) :
            ops += [(op, circuit_idx) for op in circuit.ops]
        # FIXME: refine operator ordering
        ops = sorted(ops, key = _op_key)
        self.ops = ops

        # create lane map and define external_lane.
        lanes = {}
        for external_lane, qreg in enumerate(self.circuits.qregset) :
            lane = Lane(external_lane)
            lanes[qreg.id] = lane
        
        # initialize qubit states
        for circuit in self.circuits :
            assert len(circuit.qregset) != 0, "empty qreg set."
            
            qstates = self.defpkg.create_qubit_states(self._qubits.dtype)
            n_lanes = len(circuit.qregset)
            
            # multi chunk
            if n_lanes_per_chunk is None :
                n_lanes_per_chunk = n_lanes
            else :
                n_lanes_per_chunk = min(n_lanes, n_lanes_per_chunk)
                
            qproc(qstates).initialize_qubit_states(qstates, n_lanes, n_lanes_per_chunk, device_ids);
            self._qubits.add_qubit_states(qstates)

            for local_lane, qreg in enumerate(circuit.qregset) :
                lane = lanes[qreg.id]
                lane.set_qstates_layout(qstates, local_lane)                

        self._qubits.set_lanes(lanes)

        self.processor.prepare()
        self._qubits.prepare()

        for qstates in self._qubits.get_qubit_states() :
            qproc(qstates).reset_qubit_states(qstates);
        
        self._creg_values = CregValues()
        self._creg_values.add(self.circuits.cregset)

        # storage for previously measured value (used on reset)
        # FIXME: move to qubits
        self.bit_values = dict()
        for qreg in self.circuits.qregset :
            self.bit_values[qreg.id] = -1
        
        self.step_iter = iter(self.ops)

    def run_step(self) :
        try :
            op_circ = next(self.step_iter)
            op = op_circ[0]
            qstates = self._qubits[op_circ[1]]
            self._apply_op(op, qstates)
            return True
        except StopIteration :
            return False

    def run(self) :
        while self.run_step() :
            pass

    def terminate(self) :
        # release resources.
        self.circuits = None
        self._creg_values = None
        self.ops = None
        self._qubits = None
        
    def _apply_op(self, op, qstates) :
        if isinstance(op, model.Clause) :
            self._apply_clause(op, qstates)
        elif isinstance(op, model.IfClause) :
            self._apply_if_clause(op, qstates)
        elif isinstance(op, model.Measure) :
            self._measure(op, qstates)
        elif isinstance(op, gate.ID) : # nop
            pass
        elif isinstance(op, gate.UnaryGate) :
            self._apply_unary_gate(op, qstates)
        elif isinstance(op, gate.ControlGate) :
            self._apply_control_gate(op, qstates)
        elif isinstance(op, model.Barrier) :
            pass  # Since this simulator runs step-wise, able to ignore barrier.
        elif isinstance(op, model.Reset) :
            self._apply_reset(op, qstates)
        else :
            assert False, "Unknown operator."

    def _apply_if_clause(self, op, qstates) :
        if self._creg_values.get_packed_value(op.creg_array) == op.val :
            self._apply_op(op.clause, qstates)            

    def _apply_clause(self, op, qstates) :
        for clause_op in op.ops :
            self._apply_op(clause_op, qstates)
    
    def _measure(self, op, qstates) :
        for in0, creg in zip(op.in0, op.cregs) :
            rand_num = random.random()
            lane = self._qubits.get_lane(in0)
            creg_value = qproc(qstates).measure(rand_num, qstates, lane.local)
            self._creg_values.set(creg, creg_value)
            self.bit_values[in0.id] = creg_value

    def _apply_reset(self, op, qstates) :
        for qreg in op.qregset :
            bitval = self.bit_values[qreg.id]
            if bitval == -1 :
                raise RuntimeError('Qubit is not measured.')
            if bitval == 1 :
                lane = self._qubits.get_lane(qreg)
                qproc(qstates).apply_reset(qstates, lane.local)

            self.bit_values[qreg.id] = -1
                    
    def _apply_unary_gate(self, op, qstates) :
        for in0 in op.in0 :
            lane = self._qubits.get_lane(in0)
            qproc(qstates).apply_unary_gate(op.get_matrix(), qstates, lane.local)

    def _apply_control_gate(self, op, qstates) :
        for in0, in1 in zip(op.in0, op.in1) :
            lane0 = self._qubits.get_lane(in0)
            lane1 = self._qubits.get_lane(in1)
            qproc(qstates).apply_control_gate(op.get_matrix(),
                                              qstates, lane0.local, lane1.local)
