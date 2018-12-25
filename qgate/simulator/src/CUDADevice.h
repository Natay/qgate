#pragma once

#include <cuda_runtime_api.h>
#include "DeviceTypes.h"

namespace qgate_cuda {

class CUDADevice {
public:
    enum { hTmpMemBufSize = 1 << 28 };
    enum { dTmpMemBufSize = 1 << 20 };

    CUDADevice() {
        h_buffer_ = NULL;
        d_buffer_ = NULL;
    }
    ~CUDADevice() {
        finalize();
    }

    void initialize(int devNo);
    
    void finalize();

    size_t getMemSize() const {
        return devProp_.totalGlobalMem;
    }
    
    void makeCurrent();

    void checkCurrentDevice();
    
    void allocate(void **pv, size_t size);

    void free(void *pv);
    
    template<class V>
    V *allocate(size_t size) {
        V *pv = NULL;
        allocate((void**)&pv, size * sizeof(V));
        return pv;
    }

    void hostAllocate(void **pv, size_t size);

    void hostFree(void *pv);
    
    template<class V>
    V *hostAllocate(size_t size) {
        V *pv = NULL;
        hostAllocate((void**)&pv, size * sizeof(V));
        return pv;
    }
    
    template<class V>
    V *getTmpHostMem(size_t size) {
        throwErrorIf(tmpHostMemSize<V>() < size, "Requested size too large.");
        return static_cast<V*>(h_buffer_);
    }

    template<class V>
    size_t tmpHostMemSize() const {
        return (size_t)hTmpMemBufSize / sizeof(V);
    }

    template<class V>
    V *getTmpDeviceMem(size_t size) {
        throwErrorIf(tmpDeviceMemSize<V>() < size, "Requested size too large.");
        return static_cast<V*>(d_buffer_);
    }

    template<class V>
    size_t tmpDeviceMemSize() const {
        return (size_t)dTmpMemBufSize / sizeof(V);
    }

private:
    void *h_buffer_;
    void *d_buffer_;
    int nMaxActiveBlocksInDevice_;
    cudaDeviceProp devProp_;
    
    int devNo_;
    static int currentDevNo_;
};


class CUDADevices {
public:
    CUDADevices();
    ~CUDADevices();

    CUDADevice &operator[](int idx) {
        return *devices_[idx];
    }

    void probe();

    void finalize();
    
    int size() const {
        return (int)devices_.size();
    }

    int maxNLanesInDevice() const;
    
    CUDADevice *defaultDevice();
    
private:
    typedef std::vector<CUDADevice*> Devices;
    Devices devices_;
};


}
