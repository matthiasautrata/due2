%# The semantics program
%
% The files of `lp/`, in the order `clingo_i/interpret.py` loads them (`PROGRAM_FILES`).
% Solve 1 and solve 2 load every file but pivot.lp; solve 3 loads all of them. This file is only
% the documentation's entry point: the interpreter loads the files directly, and
% `tests/test_docs.py` checks that the two lists agree.

#include "../lp/lift.lp".
#include "../lp/structure.lp".
#include "../lp/kleene.lp".
#include "../lp/applies.lp".
#include "../lp/completion.lp".
#include "../lp/resolve.lp".
#include "../lp/explain.lp".
#include "../lp/pivot.lp".
