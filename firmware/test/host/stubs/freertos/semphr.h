#pragma once
#include <mutex>
inline SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(){ return new std::recursive_mutex(); }
inline int xSemaphoreTakeRecursive(SemaphoreHandle_t m, unsigned){ ((std::recursive_mutex*)m)->lock(); return 1; }
inline int xSemaphoreGiveRecursive(SemaphoreHandle_t m){ ((std::recursive_mutex*)m)->unlock(); return 1; }
inline void vSemaphoreDelete(SemaphoreHandle_t m){ delete (std::recursive_mutex*)m; }
