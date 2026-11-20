CC=cc
CFLAGS=-std=c11 -Wall -Wextra -O2
all: osh
osh: src/osh.c
	$(CC) $(CFLAGS) -o $@ $<
test: osh
	python3 tests/run_all.py
clean:
	rm -f osh
.PHONY: all test clean
