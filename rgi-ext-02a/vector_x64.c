#define _GNU_SOURCE
#include <immintrin.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>

static uint64_t ns(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW,&t); return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec; }

int main(void){
#if !defined(__x86_64__)
  fprintf(stderr,"not x86_64\n"); return 3;
#else
  __builtin_cpu_init();
  int avx512 = __builtin_cpu_supports("avx512f") != 0;
  int avx2 = __builtin_cpu_supports("avx2") != 0;
  if(!avx512){ fprintf(stderr,"AVX512F unavailable\n"); return 4; }
  const size_t n = 1u<<22;
  const int reps = 32;
  float *a = aligned_alloc(64,n*sizeof(float));
  float *b = aligned_alloc(64,n*sizeof(float));
  float *c = aligned_alloc(64,n*sizeof(float));
  if(!a||!b||!c) return 5;
  for(size_t i=0;i<n;i++){a[i]=(float)(i%251)*0.001f;b[i]=(float)(i%127)*0.002f;}
  uint64_t t0=ns();
  for(int r=0;r<reps;r++){
    for(size_t i=0;i<n;i+=16){
      __m512 x=_mm512_load_ps(a+i), y=_mm512_load_ps(b+i);
      _mm512_store_ps(c+i,_mm512_fmadd_ps(x,y,_mm512_set1_ps(0.5f)));
    }
  }
  uint64_t t1=ns();
  double checksum=0.0; for(size_t i=0;i<n;i+=4096) checksum += c[i];
  double sec=(double)(t1-t0)/1e9;
  double bytes=(double)n*sizeof(float)*3.0*(double)reps;
  printf("{\"architecture\":\"x86_64\",\"kernel\":\"AVX512_FMA\",\"avx512f\":%s,\"avx2\":%s,\"elements\":%zu,\"repetitions\":%d,\"elapsed_ns\":%llu,\"effective_bytes_per_second\":%.3f,\"checksum\":%.9f}\n",avx512?"true":"false",avx2?"true":"false",n,reps,(unsigned long long)(t1-t0),bytes/sec,checksum);
  free(a);free(b);free(c);return 0;
#endif
}
