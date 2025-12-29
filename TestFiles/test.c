// C Program to Check Even or Odd Using Modulo Operator
#include <stdio.h>


int main() {
    int c[8] = {1,2,3,4,5,6,7,8};

    int i = 0;
    int a[3] = {2,1,1};
    int asdf = c[a[0]*a[1]+a[1]];

    return 0;
}
//clang -S -emit-llvm foo.c