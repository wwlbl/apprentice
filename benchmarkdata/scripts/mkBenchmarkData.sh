#!/bin/bash

for i in {7..8}; do python mkBenchmarkData.py -c -o ../f${i}.txt                        -n 1000   -r 0   -f ${i};done
# for i in {1..6}; do python mkBenchmarkData.py -c -o ../f${i}_noise_0.1.txt              -n 1000   -r 0.1 -f ${i};done
# for i in {1..6}; do python mkBenchmarkData.py -c -o ../f${i}_noise_0.5.txt              -n 1000   -r 0.5 -f ${i};done
# for i in {1..6}; do python mkBenchmarkData.py -c -o ../f${i}_test.txt           -s 9999 -n 100000 -r 0   -f ${i};done
# for i in {1..6}; do python mkBenchmarkData.py -c -o ../f${i}_noise_0.1_test.txt -s 9999 -n 100000 -r 0.1 -f ${i};done
# for i in {1..6}; do python mkBenchmarkData.py -c -o ../f${i}_noise_0.5_test.txt -s 9999 -n 100000 -r 0.5 -f ${i};done
