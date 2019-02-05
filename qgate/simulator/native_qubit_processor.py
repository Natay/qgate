import numpy as np
from . import qubits
from . import glue

class NativeQubitProcessor :

    def __init__(self, dtype, ptr) :
        self.dtype = dtype
        self.ptr = ptr

    def clear(self) :
        glue.qubit_processor_clear(self.ptr)

    def prepare(self) :
        glue.qubit_processor_prepare(self.ptr)
        
    def initialize_qubit_states(self, qstates, n_lanes, n_lanes_per_chunk, device_ids) :
        glue.qubit_processor_initialize_qubit_states(self.ptr, qstates.ptr, n_lanes, n_lanes_per_chunk, device_ids)

    def reset_qubit_states(self, qstates) :
        glue.qubit_processor_reset_qubit_states(self.ptr, qstates.ptr)
        
    def calc_probability(self, qstates, local_lane) :
        return glue.qubit_processor_calc_probability(self.ptr, qstates.ptr, local_lane)
        
    def measure(self, rand_num, qstates, local_lane) :
        return glue.qubit_processor_measure(self.ptr, rand_num, qstates.ptr, local_lane)
    
    def apply_reset(self, qstates, local_lane) :
        glue.qubit_processor_apply_reset(self.ptr, qstates.ptr, local_lane)

    def apply_unary_gate(self, gate_type, qstates, local_lane) :
        mat = gate_type.pymat()
        
        mat = np.asarray(mat, dtype=np.complex128, order='C')
        glue.qubit_processor_apply_unary_gate(self.ptr, mat, qstates.ptr, local_lane)

    def apply_control_gate(self, gate_type, qstates, local_control_lane, local_target_lane) :
        mat = gate_type.pymat()
        
        mat = np.asarray(mat, dtype=np.complex128, order='C')
        glue.qubit_processor_apply_control_gate(self.ptr, mat, qstates.ptr,
                                                local_control_lane, local_target_lane)

    def get_states(self, values, offset, mathop,
                   lanes, qstates_list, n_states, start, step) :
        if mathop == qubits.null :
            mathop = 0
        elif mathop == qubits.abs2 :
            mathop = 1
        else :
            raise RuntimeError('unknown math operation, {}'.format(str(mathop)))

        lane_transform_list = []
        for qstates in qstates_list :
            lanes_in_qstates = [lane for lane in lanes if lane.qstates == qstates]
            # lane_transform[local_lane] -> external_lane
            lane_transform = [None] * len(lanes_in_qstates)
            for lane in lanes_in_qstates :
                lane_transform[lane.local] = lane.external
            lane_transform_list.append(lane_transform)
        
        qstates_ptrs = [qstates.ptr for qstates in qstates_list]
        glue.qubit_processor_get_states(self.ptr,
                                        values, offset,
                                        mathop,
                                        lane_transform_list, qstates_ptrs, len(lanes),
                                        n_states, start, step)
