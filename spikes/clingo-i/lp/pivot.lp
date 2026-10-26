%# pivot.lp: the pivotal literals of an Indeterminate (solve 3 only)
%
% For an Indeterminate, finds the completion variables whose value alone changes the verdict, and
% the unknown atoms that read them (decisions/0011). Each answer set holds a completion `c`, one
% variable chosen as the pivot, and a second world `flip`: `c` with the pivot's value flipped.
% Only answer sets in which the two worlds' verdicts differ survive. interpret.py enumerates them
% bravely: the union of `unknown/1` over all of them is the reply's pivotal atoms. Variable
% letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `var/1`, `assigned/3`, `reads/2`, `finding_atom/2` (completion.lp);
%   `verdict/2` (resolve.lp).
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

Atom or duty atom `X` has a `u` finding that reads the pivot in one of its `u` parts: one of
the atoms that make the verdict Indeterminate (decisions/0011). Only a `u` finding reads a
variable (completion.lp).
*%
unknown(X) :- reads(I, L), pivot(L), finding_atom(I, X).

#show unknown/1.

%## The range is exact

% Brave enumeration gives the union over the answer sets. The `unknown` atoms are those with a
% pivotal variable (decisions/0011 #1). The range is the least and the greatest `verdict(c,
% Verdict)` that occurs, in the chain `Deny < NotApplicable < Pending < Permit` (decisions/0011 #3).
%
% The flip constraint drops answer sets, so it is not obvious that every verdict some completion
% takes survives in some answer set. It does:
%
% 1. The completions are the corners of an `n`-dimensional cube, and two corners are neighbours when
%    they differ in one variable. The cube is connected: any corner reaches any other by flipping,
%    one at a time, the variables in which they differ.
% 2. An `Indeterminate` means at least two verdicts occur. Let corner `c₁` have verdict `V`, and
%    corner `c₂` some other verdict.
% 3. On the path from `c₁` to `c₂` the verdict starts at `V` and ends elsewhere, so some step goes
%    from a corner `c` with verdict `V` to a neighbour without it.
% 4. That step is an answer set of solve 3: completion `c`, pivot the flipped variable. So
%    `verdict(c, V)` is true in some answer set.
%
% Conversely, `c` in every answer set is a completion. So the brave `verdict(c, _)` atoms are
% exactly the verdicts the completions take, and the range is exact. In DESIGN.md § Worked example,
% `NotApplicable` occurs only at (`f`, `f`), and it survives through both of that corner's flips.
