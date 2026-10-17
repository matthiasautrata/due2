%# kleene.lp: truth values
%
% The three truth values and their order (due2-workflows.md §5.1). The integrity constraints
% over them are in integrity.lp. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** nothing.
% - **Provides:** `rank/2`, `two_valued/1`.

%*! rank(V, N)

Truth value `V` has rank `N` in the order `f` < `u` < `t`. Kleene conjunction is the value of
the least rank (`#min`, applies.lp, completion.lp, and compare.lp), disjunction the
greatest (`#max`), and negation maps rank `N` to `2 - N`.
*%
rank(f, 0).
rank(u, 1).
rank(t, 2).

%*! two_valued(V)

`V` is `f` or `t`: a value a completed item can take.
*%
two_valued(f; t).
