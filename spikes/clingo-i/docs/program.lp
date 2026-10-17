%# The semantics program
%
% The files of `lp/`, in the order `clingo_i/interpret.py` loads them (`PROGRAM_FILES`).
% Solve 1 loads lift.lp to applies.lp, solve 2 every file but pivot.lp, and solve 3 all of them.
% This file is only the documentation's entry point: the interpreter loads the files directly,
% and `tests/test_docs.py` checks that the two lists agree.

#include "../lp/lift.lp".
#include "../lp/structure.lp".
#include "../lp/kleene.lp".
#include "../lp/constraint.lp".
#include "../lp/operand.lp".
#include "../lp/compare.lp".
#include "../lp/applies.lp".
#include "../lp/completion.lp".
#include "../lp/resolve.lp".
#include "../lp/integrity.lp".
#include "../lp/explain.lp".
#include "../lp/pivot.lp".
