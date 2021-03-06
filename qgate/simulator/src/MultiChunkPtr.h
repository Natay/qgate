#pragma once

#include "DeviceTypes.h"

namespace qgate_cuda {

template<class V>
struct MultiChunkPtr {

    MultiChunkPtr() {
        for (int idx = 0; idx < MAX_N_CHUNKS; ++idx)
            d_ptrs[idx] = NULL;
        nLanesInChunk = 0;
        mask = 0;
    }

    void setNLanesInChunk(int _nLanesInChunk) {
        nLanesInChunk = _nLanesInChunk;
        mask = (qgate::Qone << nLanesInChunk) - 1;
    }

    V *getPtr(qgate::QstateIdx idx) {
        int devIdx = int(idx >> nLanesInChunk);
        qgate::QstateIdx idxInDev = idx & mask;
        return &d_ptrs[devIdx][idxInDev];
    }

#ifdef __NVCC__
    __device__ __forceinline__
    V &operator[](qgate::QstateIdx idx) {
        int devIdx = int(idx >> nLanesInChunk);
        qgate::QstateIdx idxInDev = idx & mask;
        return d_ptrs[devIdx][idxInDev];
    }

    __device__ __forceinline__
    const V &operator[](qgate::QstateIdx idx) const {
        int devIdx = int(idx >> nLanesInChunk);
        qgate::QstateIdx idxInDev = idx & mask;
        return d_ptrs[devIdx][idxInDev];
    }
#endif
    
    V *d_ptrs[MAX_N_CHUNKS];
    int nLanesInChunk;
    qgate::QstateIdx mask;
};


}

