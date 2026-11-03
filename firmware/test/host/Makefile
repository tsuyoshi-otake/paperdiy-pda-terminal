# Host tests for the firmware's terminal emulator (main/term/vt.cpp), built with the system C++ compiler
# against tiny FreeRTOS stubs. `make test` runs:
#   vt_unit       - scripted escape sequences (wrap, wide chars, DEC line drawing, scroll regions, alt screen,
#                   resize, DSR/DA replies) compared with vt_unit.expected.txt
#   compare_pyte  - real sessions of top, bash, tmux, vim, less and nano (fixtures/*.raw, recorded with
#                   capture.py) replayed through the emulator and through pyte
# Built with AddressSanitizer + UBSan so out-of-range cell access fails the test.
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O1 -g -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer
VT       := ../../main/term/vt.cpp
INC      := -Istubs -I../../main/term
PYTHON   ?= python3

all: test

snap: snap.cpp $(VT) ../../main/term/vt.h
	$(CXX) $(CXXFLAGS) $(INC) -o $@ snap.cpp $(VT)

vt_unit: vt_unit.cpp $(VT) ../../main/term/vt.h
	$(CXX) $(CXXFLAGS) $(INC) -o $@ vt_unit.cpp $(VT)

test: snap vt_unit
	./vt_unit > vt_unit.out
	diff -u vt_unit.expected.txt vt_unit.out
	@echo "vt_unit: OK"
	$(PYTHON) compare_pyte.py fixtures/*.raw

# re-record the fixtures (needs vim, less, top, nano, tmux in an UTF-8 locale); review the diff before committing
fixtures:
	cd fixtures && $(PYTHON) ../capture.py

clean:
	rm -f snap vt_unit vt_unit.out

.PHONY: all test fixtures clean
