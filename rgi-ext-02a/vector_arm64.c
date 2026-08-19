#include <arm_neon.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

static uint64_t ns(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW,&t); return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec; }

int main(void){
#if !defined(__aarch64__)
  fprintf(stderr,"not aarch64\n"); return 3;
#else
  const size_t n = 1u<<22;
  const int reps = 32;
  float *a = aligned_alloc(64,n*sizeof(float));
  float *b = aligned_alloc(64,n*sizeof(float));
  float *c = aligned_alloc(64,n*sizeof(float));
  if(!a||!b||!c) return 5;
  for(size_t i=0;i<n;i++){a[i]=(float)(i%251)*0.001f;b[i]=(float)(i%127)*0.002f;}
  const float32x4_t half=vdupq_n_f32(0.5f);
  uint64_t t0=ns();
  for(int r=0;r<reps;r++){
    for(size_t i=0;i<n;i+=4){
      float32x4_t x=vld1q_f32(a+i), y=vld1q_f32(b+i);
      vst1q_f32(c+i,vfmaq_f32(half,x,y));
    }
  }
  uint64_t t1=ns();
  double checksum=0.0; for(size_t i=0;i<n;i+=4096) checksum += c[i];
  double sec=(double)(t1-t0)/1e9;
  double bytes=(double)n*sizeof(float)*3.0*(double)reps;
  printf("{\"architecture\":\"aarch64\",\"kernel\":\"NEON_FMA\",\"neon_asimd\":true,\"elements\":%zu,\"repetitions\":%d,\"elapsed_ns\":%llu,\"effective_bytes_per_second\":%.3f,\"checksum\":%.9f}\n",n,reps,(unsigned long long)(t1-t0),bytes/sec,checksum);
  free(a);free(b);free(c);return 0;
#endif
}
