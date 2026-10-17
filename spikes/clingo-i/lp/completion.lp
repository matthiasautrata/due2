%# completion.lp: the completion variables, and one completion of them
%
% Each `u` part reads a completion literal, and each literal names a variable. One answer set
% gives every variable `t` or `f`, so solve 2's answer sets are exactly the completions, `2^n` of
% them for `n` variables (due2-workflows.md §6.4, decisions/0012). Every completed value is
% indexed by a world, so that pivot.lp can hold a second completion beside the first.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_target/2`, `atom_party/3` (structure.lp); `holds/2`,
%   `part_of/2` (applies.lp); `rank/2` (kleene.lp).
% - **Provides:** `lit_of/2`, `var/1`, `world/1`, `assigned/3`, `completed/3`.

%*! lit_of(I, L)

The `u` part `I` reads the completion literal `L`: `target(T)` for a target part, the atom's
target, and `party(F, Party)` for a party part, its function and party. Parts with the same
literal are one variable: the same request field tested against the same value
(decisions/0012 #1). Different values of one field, `target(a)` and `target(b)`, are different
variables (decisions/0012 #3). Every part reads its literal positively; complementary
polarities come only from constraints, which are declined (#47).
*%
lit_of(part(X, target), target(T)) :- atom_target(X, T), holds(part(X, target), u).
lit_of(part(X, party(F)), party(F, Party)) :- atom_party(X, F, Party), holds(part(X, party(F)), u).

%*! var(L)

`L` is a completion variable. interpret.py counts `var/1` atoms after grounding and declines the
vector above the variable cap (correctness-strategy.md §3).
*%
var(L) :- lit_of(_, L).

%*! world(W)

`W` is a world: an index for one completion held in the answer set. World `c` (for
"completion") is the completion the answer set chose; pivot.lp adds `flip`.
*%
world(c).

%*! assigned(W, L, V)

In world `W`, variable `L` has value `V`, `t` or `f`.
*%
% The choice: exactly one value for each variable in world c.
{ assigned(c, L, t); assigned(c, L, f) } = 1 :- var(L).

%*! completed(W, I, V)

In world `W`, item `I` has value `V`, `t` or `f`. A `u` part takes its literal's value, every
other part keeps its finding, and `applies(X)` is the Kleene conjunction of the completed parts.
*%
completed(W, I, V) :- world(W), lit_of(I, L), assigned(W, L, V).
completed(W, I, V) :- world(W), part_of(_, I), holds(I, V), V != u.
% The #min-as-function idiom of applies.lp, over the completed parts.
completed(W, applies(X), V) :- world(W), atom(X), rank(V, Min),
    Min = #min { N : part_of(X, I), completed(W, I, Vp), rank(Vp, N) }.
