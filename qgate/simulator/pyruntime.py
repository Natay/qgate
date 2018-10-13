import numpy as np
import math


def _abs2(c) :
    return c.real ** 2 + c.imag ** 2

def _null(c) :
    return c
        
class Qubits :
    def __init__(self) :
        self.qubit_states = dict()

    def get_n_qubits(self) :
        n_qubits = 0
        for qstates in self.qubit_states.values() :
            n_qubits += len(qstates.qreglist)
        return n_qubits

    def __getitem__(self, key) :
        return self.qubit_states[key]
    
    def allocate_qubit_states(self, circ_idx, qreglist) :
        self.qubit_states[circ_idx] = QubitStates(qreglist)
        
    def prepare(self) :
        pass

    def get_states(self) :
        return self._get_values(func = _null, dtype = np.complex128)
    
    def get_probabilities(self) :
        return self._get_values(func = _abs2, dtype = np.float64)
        
    # private.
    def _get_values(self, func, dtype) :
        n_states = 2 ** self.get_n_qubits()
        values = np.empty([n_states], dtype)
        groups = self.qubit_states.values()
        for idx in range(n_states) :
            val = 1.
            for qstates in groups :
                state = qstates.get_state_by_global_idx(idx)
                val *= func(state)
            values[idx] = val
        return values
    
    
# representing a single qubit or entangled qubits.
class QubitStates :
    def __init__(self, qregset) :
        self.states = np.zeros([2 ** len(qregset)], np.complex128)
        self.states[0] = 1
        self.qreglist = list(qregset)

    def __getitem__(self, key) :
        return self.states[key]

    def __setitem__(self, key, value) :
        self.states[key] = value

    def get_n_lanes(self) :
        return len(self.qreglist)

    def get_lane(self, qreg) :
        return self.qreglist.index(qreg)

    def convert_to_local_lane_idx(self, idx) :
        local_idx = 0
        for bitpos, qreg in enumerate(self.qreglist) :
            if ((1 << qreg.id) & idx) != 0 :
                local_idx |= 1 << bitpos
        return local_idx
    
    def get_state_by_global_idx(self, idx) :
        local_idx = self.convert_to_local_lane_idx(idx)
        return self[local_idx]
    


def measure(rand_num, qstates, qreg) :

    lane = qstates.get_lane(qreg)

    bitmask_lane = 1 << lane
    bitmask_hi = ~((2 << lane) - 1)
    bitmask_lo = (1 << lane) - 1
    n_states = 2 ** (qstates.get_n_lanes() - 1)
    prob = 0.
    for idx in range(n_states) :
        idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
        qs = qstates[idx_lo]
        prob += (qs * qs.conj()).real

    if (rand_num < prob) :
        creg_value = 0
        norm = 1. / math.sqrt(prob)
        for idx in range(n_states) :
            idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
            idx_hi = idx_lo | bitmask_lane
            qstates[idx_lo] *= norm
            qstates[idx_hi] = 0.
    else :
        creg_value = 1
        norm = 1. / math.sqrt(1. - prob)
        for idx in range(n_states) :
            idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
            idx_hi = idx_lo | bitmask_lane
            qstates[idx_lo] = 0.
            qstates[idx_hi] *= norm

    return creg_value

def apply_reset(qstates, qreg) :

    lane = qstates.get_lane(qreg)
    bitmask_lane = 1 << lane
    bitmask_hi = ~((2 << lane) - 1)
    bitmask_lo = (1 << lane) - 1
    n_states = 2 ** (qstates.get_n_lanes() - 1)

    for idx in range(n_states) :
        idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
        idx_hi = idx_lo | bitmask_lane
        qstates[idx_lo] = qstates[idx_hi]
        qstates[idx_hi] = 0.


def apply_unary_gate(mat, qstates, qreg) :
    lane = qstates.get_lane(qreg)
    bitmask_lane = 1 << lane
    bitmask_hi = ~((2 << lane) - 1)
    bitmask_lo = (1 << lane) - 1
    n_states = 2 ** (qstates.get_n_lanes() - 1)
    for idx in range(n_states) :
        idx_lo = ((idx << 1) & bitmask_hi) | (idx & bitmask_lo)
        idx_hi = idx_lo | bitmask_lane
        qs0 = qstates[idx_lo]
        qs1 = qstates[idx_hi]
        qsout = np.matmul(mat, np.array([qs0, qs1], np.complex128).T)
        qstates[idx_lo] = qsout[0]
        qstates[idx_hi] = qsout[1]

        
def apply_control_gate(mat, qstates, control, target) :
    lane0 = qstates.get_lane(control)
    lane1 = qstates.get_lane(target)
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
        qsout = np.matmul(mat, np.array([qs0, qs1], np.complex128).T)
        qstates[idx_0] = qsout[0]
        qstates[idx_1] = qsout[1]
