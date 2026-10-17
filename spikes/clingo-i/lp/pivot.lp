%# pivot.lp: the pivotal literals of an Indeterminate (solve 3 only)
%
% For an Indeterminate, finds the completion variables whose value alone changes the verdict, and
% the unknown atoms that read them (decisions/0011). Each answer set holds a completion `c`, one
% variable chosen as the pivot, and a second world `flip`: `c` with the pivot's value flipped.
% Only answer sets in which the two worlds' verdicts differ survive. interpret.py enumerates them
% bravely: the union of `unknown/1` over all of them is the reply's pivotal atoms. Variable
% letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `var/1`, `assigned/3`, `reads/2` (completion.lp); `verdict/2` (resolve.lp);
%   `holds/2` (applies.lp).
% - **Provides:** `pivot/1`, `unknown/1`; extends `world/1` and `assigned/3` (completion.lp).

world(flip).

%*! pivot(L)

`L` is the one variable this answer set flips.
*%
{ pivot(L) : var(L) } = 1.

% World flip: every variable keeps its value in c, except the pivot, which takes the other.
assigned(flip, L, V) :- assigned(c, L, V), not pivot(L).
assigned(flip, L, t) :- pivot(L), assigned(c, L, f).
assigned(flip, L, f) :- pivot(L), assigned(c, L, t).

% Only a flip that changes the verdict.
:- verdict(c, Verdict), verdict(flip, Verdict).

%*! unknown(X)

Atom `X` has finding `u` and reads the pivot in one of its `u` parts: one of the atoms that
make the verdict Indeterminate (decisions/0011).
*%
unknown(X) :- holds(applies(X), u), reads(X, L), pivot(L).

#show unknown/1.
