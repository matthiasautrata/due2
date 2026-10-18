%# duty.lp: a duty's guards and witness conditions
%
% Splits the constraints of each duty, and the refinements of its action terms, into guards and
% witness conditions (due2-workflows.md §5.2). A guard decides whether the duty is owed; a
% witness condition decides whether a piece of evidence fulfils it. A leaf is a witness
% condition when its left operand reads the witness or `due2:actionTime`; every other leaf is a
% guard. A conjunction splits into its members, and every other node is one guard or one witness
% condition, or rejected with `MixedDutyConstraint` when it mixes the two. Variable letters:
% DESIGN.md § Vocabulary.
%
% - **Consumes:** `context_property/2` (lift.lp); `duty_node/1`, `duty_value/3` (structure.lp);
%   `top_constraint/2`, `top_refinement/2`, `conn/2`, `member/2`, `leaf/1`, `left/2`
%   (constraint.lp); `src/2`, `prop/2` (operand.lp).
% - **Provides:** `duty_root/2`, `duty_part/2`, `split_part/2`, `witness_leaf/1`,
%   `has_witness/1`, `has_guard/1`, `guard/2`, `witness_cond/2`; extends `reject/2`
%   (structure.lp).

%## The split

%*! duty_root(Duty, C)

`C` is a root of `Duty`'s conditions: one of its constraint roots, or a refinement root of one
of its action terms. A refinement of a root obligation's policy-level action is the
obligation's, like the action.
*%
duty_root(Duty, C) :- duty_node(Duty), top_constraint(Duty, C).
duty_root(Duty, C) :- duty_value(Duty, action, Term), top_refinement(Term, C).

%*! duty_part(Duty, C)

Node `C` is a conjunct of `Duty`'s conditions: a root, or a member of a conjunction that is
one.
*%
duty_part(Duty, C) :- duty_root(Duty, C).
duty_part(Duty, D) :- duty_part(Duty, C), conn(C, and), member(C, D).

%*! split_part(Duty, C)

Node `C` is one of the parts `Duty`'s conditions split into: a conjunct that is not itself a
conjunction. Each is a guard or a witness condition as a whole.
*%
split_part(Duty, C) :- duty_part(Duty, C), not conn(C, and).

%*! witness_leaf(C)

Leaf `C` reads the evidence: its left operand is bound to `due2:witnessSource`, or reads the
context property `due2:actionTime`. The second is the evidence's `occurred_at`, as
due2-workflows.md §5.2 says.
*%
witness_leaf(C) :- left(C, Op), src(Op, witness).
witness_leaf(C) :- left(C, Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, actionTime).

%*! has_witness(C)

The tree under node `C`, `C` included, has a witness leaf.
*%
has_witness(C) :- witness_leaf(C).
has_witness(C) :- member(C, D), has_witness(D).

%*! has_guard(C)

The tree under node `C`, `C` included, has a leaf that is not a witness leaf.
*%
has_guard(C) :- leaf(C), not witness_leaf(C).
has_guard(C) :- member(C, D), has_guard(D).

% A part that mixes the two cannot be split: a guard is read before the evidence and a witness
% condition per piece of it, so `or`, `xone`, or `not` over both has no single place to be read.
reject("MixedDutyConstraint", C) :- split_part(_, C), has_witness(C), has_guard(C).

%*! guard(Duty, C)

Node `C` is a guard of `Duty`: a split part with no witness leaf. Its world-`k` value is part
of whether the duty is owed.
*%
guard(Duty, C) :- split_part(Duty, C), not has_witness(C).

%*! witness_cond(Duty, C)

Node `C` is a witness condition of `Duty`: a split part whose leaves all read the evidence. It
is read against each piece of evidence in turn.
*%
witness_cond(Duty, C) :- split_part(Duty, C), has_witness(C), not has_guard(C).
