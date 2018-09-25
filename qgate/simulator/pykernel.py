import numpy as np
import math
import qasm.model as qasm
import random



class PyKernelStateAccessor :
    def __init__(self, all_qregs, qubit_groups, creg_dict) :
        self.qregs = all_qregs
        self.qubit_groups = qubit_groups
        self.creg_dict = creg_dict

    def get_probability_list(self) :
        n_states = 2 ** len(self.qregs)
        prob_list = np.empty([n_states], np.float64)
        groups = self.qubit_groups.values()
        for idx in range(n_states) :
            prob = 1.
            for qstates in groups :
                val = qstates.get_state_by_global_idx(idx)
                prob *= (val * val.conj()).real
            prob_list[idx] = prob
        return prob_list

    def get_creg_dict(self) :
        return self.creg_dict
    
    def get_creg_array_values(self, creg_array) :
        return self.creg_dict.get_values(creg_array)

    def get_creg_array_values_as_bits(self, creg_array) :
        return self.creg_dict.get_as_bits()
    
    def get_creg_value(self, creg) :
        return self.creg_dict.get(creg)


# representing a single qubit or entangled qubits.
# All methods are accessed only from PyKernels/PyKernelStateAccessor
# Must not be used from other modules.
class QubitStates :
    def __init__(self, qregset) :
        self.states = np.zeros([2 ** len(qregset)], np.complex128)
        self.states[0] = 1
        self.qregset = qregset
        self.qreglist = list(qregset)

    def __getitem__(self, key) :
        return self.states[key]

    def __setitem__(self, key, value) :
        self.states[key] = value

    def get_n_lanes(self) :
        return len(self.qregset)

    def get_lane(self, qreg) :
        return self.qreglist.index(qreg)

    def convert_to_local_lane_idx(self, idx) :
        local_idx = 0
        for bitpos, qreg in enumerate(self.qregset) :
            if ((1 << qreg.id) & idx) != 0 :
                local_idx |= 1 << bitpos
        return local_idx
    
    def get_state_by_global_idx(self, idx) :
        local_idx = self.convert_to_local_lane_idx(idx)
        return self[local_idx]

    
# creg arrays and their values.
# All methods are accessed only from PyKernels/PyKernelStateAccessor
# Must not be used from other modules.
class CregDict :
    def __init__(self, creg_arrays) :
        self.creg_dict = dict()
        for creg_array in creg_arrays :
            values = np.zeros([creg_array.length()])
            self.creg_dict[creg_array] = values

    def __getitem__(self, key) :
        return self.creg_dict[key]

    def get_creg_arrays(self) :
        return self.creg_dict.keys()
    
    def set(self, creg, value) :
        values = self.creg_dict[creg.creg_array]
        values[creg.idx] = value
        
    def get(self, creg) :
        values = self.creg_dict[creg.creg_array]
        return values[creg.idx]

    def get_values(self, creg_array) :
        return self.creg_dict[creg_array]

    def get_as_bits(self, creg_array) :
        values = self.creg_dict[creg_array]
        bits = 0
        for idx in range(len(values)) :
            if values[idx] == 1 :
                bits |= 1 << idx
        return bits



class PyKernel :
    def __init__(self, all_qregset) :
        self.all_qregset = all_qregset
        self.qubit_groups = {}

    # public methods
    
    def set_qregset(self, circuit_idx, qregset) :
        self.qubit_groups[circuit_idx] = QubitStates(qregset)

    def set_creg_arrays(self, creg_arrays) :
        self.creg_dict = CregDict(creg_arrays)

    def apply_op(self, op, circ_idx) :
        if isinstance(op, qasm.Measure) :
            self._measure(op, circ_idx)
        elif isinstance(op, qasm.UnaryGate) :
            self._apply_unary_gate(op, circ_idx)
        elif isinstance(op, qasm.ControlGate) :
            self._apply_control_gate(op, circ_idx)
        elif isinstance(op, qasm.Barrier) :
            pass  # Since this simulator runs step-wise, able to ignore barrier.
        elif isinstance(op, qasm.Reset) :
            self._apply_reset(op, circ_idx)
        else :
            assert False, "Unknown operator."

    def get_state_accessor(self) :
        return PyKernelStateAccessor(self.all_qregset, self.qubit_groups, self.creg_dict)            
    def get_creg_array_as_bits(self, creg_array) :
        return self.creg_dict.get_as_bits(creg_array)

    # private methods
    
    def _measure(self, op, circ_idx) :
        qstates = self.qubit_groups[circ_idx]

        for in0, creg in zip(op.in0, op.cregs) :
            lane = qstates.get_lane(in0)
            
            bitmask_lane = 1 << lane
            bitmask_hi = ~((2 << lane) - 1)
            bitmask_lo = (1 << lane) - 1
            n_states = 2 ** (qstates.get_n_lanes() - 1)
            prob = 0.
            for idx in range(n_states) :
                idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                qs = qstates[idx_lo]
                prob += (qs * qs.conj()).real

            if (random.random() < prob) :
                self.creg_dict.set(creg, 0)
                norm = 1. / math.sqrt(prob)
                for idx in range(n_states) :
                    idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                    idx_hi = idx_lo | bitmask_lane
                    qstates[idx_lo] *= norm
                    qstates[idx_hi] = 0.
            else :
                self.creg_dict.set(creg, 1)
                norm = 1. / math.sqrt(1. - prob)
                for idx in range(n_states) :
                    idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                    idx_hi = idx_lo | bitmask_lane
                    qstates[idx_lo] = 0.
                    qstates[idx_hi] *= norm

    def _apply_reset(self, op, circ_idx) :
        qstates = self.qubit_groups[circ_idx]

        for qreg in op.qregset :
            lane = qstates.get_lane(qreg)
            bitmask_lane = 1 << lane
            bitmask_hi = ~((2 << lane) - 1)
            bitmask_lo = (1 << lane) - 1
            n_states = 2 ** (qstates.get_n_lanes() - 1)

            prob = 0.
            for idx in range(n_states) :
                idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                qs_lo = qstates[idx_lo]
                prob += (qs_lo * qs_lo.conj()).real

            # Assuming reset is able to be applyed after measurement.
            # Ref: https://quantumcomputing.stackexchange.com/questions/3908/possibility-of-a-reset-quantum-gate
            # FIXME: add a mark to qubit that tells if it entangles or not.
            if prob == 0. :
                # prob == 0 means previous measurement gave creg = 1.
                # negating this qubit
                idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                idx_hi = idx_lo | bitmask_lane
                qstates[idx_lo] = qstates[idx_hi]
                qstates[idx_hi] = 0.
            else :
                assert False, "Is traceout suitable?"
                norm = math.sqrt(1. / prob)
                for idx in range(n_states) :
                    idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                    idx_hi = idx_lo | bitmask_lane
                    qstates[idx_lo] *= norm
                    qstates[idx_hi] = 0.
                    
    def _apply_unary_gate(self, op, circ_idx) :
        qstates = self.qubit_groups[circ_idx]

        for in0 in op.in0 :
            lane = qstates.get_lane(in0)
            bitmask_lane = 1 << lane
            bitmask_hi = ~((2 << lane) - 1)
            bitmask_lo = (1 << lane) - 1
            n_states = 2 ** (qstates.get_n_lanes() - 1)
            for idx in range(n_states) :
                idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
                idx_hi = idx_lo | bitmask_lane
                qs0 = qstates[idx_lo]
                qs1 = qstates[idx_hi]
                qsout = np.matmul(op.get_matrix(), np.matrix([qs0, qs1], np.complex128).T)
                qstates[idx_lo] = qsout[0]
                qstates[idx_hi] = qsout[1]

    def _apply_control_gate(self, op, circ_idx) :
        qstates = self.qubit_groups[circ_idx]

        for in0, in1 in zip(op.in0, op.in1) :
            lane0 = qstates.get_lane(in0)
            lane1 = qstates.get_lane(in1)
            bitmask_control = 1 << lane0
            bitmask_target = 1 << lane1

            bitmask_lane_max = max(bitmask_control, bitmask_target)
            bitmask_lane_min = min(bitmask_control, bitmask_target)
        
            bitmask_hi = ~(bitmask_lane_max * 2 - 1)
            bitmask_mid = (bitmask_lane_max - 1) & ~((bitmask_lane_min << 1) - 1)
            bitmask_lo = bitmask_lane_min - 1
        
            n_states = 1 << (qstates.get_n_lanes() - 2)
            for idx in range(n_states) :
                idx_0 = ((idx << 2) & bitmask_hi) | ((idx << 1) & bitmask_mid) | (idx & bitmask_lo) | bitmask_control
                idx_1 = idx_0 | bitmask_target
            
                qs0 = qstates[idx_0]
                qs1 = qstates[idx_1]
            
                qsout = np.matmul(op.get_matrix(), np.matrix([qs0, qs1], np.complex128).T)
                qstates[idx_0] = qsout[0]
                qstates[idx_1] = qsout[1]
