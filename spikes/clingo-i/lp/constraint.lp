%# constraint.lp: the authored constraint trees, and their static checks
%
% Reads the constraints of each rule and duty, and each action term's refinements, as the tree
% the policy authored: a leaf compares a left operand with right operand values, and a connective
% node combines its members (due2-profiles.md §4, §5). The tree is not rewritten to DNF:
% compare.lp gives every node its Kleene value directly (DESIGN.md § `compare.lp`). A tree that is
% not admissible gets a `reject`; one whose reading the spike does not trust is declined. Variable
% letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `triple/3`, `voc/2`, `operator/2`, `set_based/1`, `connective/1`,
%   `is_list/1`, `list_item/2`, `unplaceable/2`, `stated/3` (lift.lp); `rule/1`, `duty_node/1`,
%   `action_term/1` (structure.lp).
% - **Provides:** `top_value/3`, `top_constraint/2`, `top_refinement/2`, `cnode/1`, `conn/2`,
%   `member/2`, `reach_c/2`, `scope/2`, `node_tree/2`, `leaf/1`, `left/2`, `c_operator/2`, `op/2`,
%   `right_value/2`, `right/2`, `unit/2`; extends `reject/2` (structure.lp) and
%   `unsupported/1` (lift.lp).

%## The roots

%*! top_value(Kind, Owner, C)

`Owner` has the root `C`: `Kind` is `constraint` for the `odrl:constraint` of a rule or a duty,
and `refinement` for an action term's `odrl:refinement`. A list value gives each of its items.
*%
top_value(constraint, R, C) :- rule(R), triple(R, Pred, C), voc(constraint, Pred).
top_value(constraint, Duty, C) :- duty_node(Duty), triple(Duty, Pred, C), voc(constraint, Pred).
top_value(refinement, Term, C) :- action_term(Term), triple(Term, Pred, C), voc(refinement, Pred).

%*! top_constraint(Owner, C)

The rule or duty `Owner` has the constraint root `C`. Each root of a rule is one conjunct of the
rule's atoms (applies.lp); duty.lp splits a duty's roots into guards and witness conditions.
*%
top_constraint(Owner, C) :- top_value(constraint, Owner, C), not is_list(C).
top_constraint(Owner, C) :- top_value(constraint, Owner, List), is_list(List), list_item(List, C).

%*! top_refinement(Term, C)

Action term `Term` has the refinement root `C`, one conjunct of every atom with that action
term.
*%
top_refinement(Term, C) :- top_value(refinement, Term, C), not is_list(C).
top_refinement(Term, C) :- top_value(refinement, Term, List), is_list(List), list_item(List, C).

%## The nodes

%*! cnode(C)

`C` is a node of some constraint tree: a root, or a member of a node.
*%
cnode(C) :- top_constraint(_, C).
cnode(C) :- top_refinement(_, C).
cnode(D) :- member(_, D).

%*! conn(C, K)

Node `C` is a connective of kind `K`: `and`, `or`, `xone`, `negation`
(`dprod:not`), or `andSequence`.
*%
conn(C, K) :- cnode(C), triple(C, Pred, _), voc(K, Pred), connective(K).

%*! member(C, D)

`D` is a member of the connective `C`. Like a set right operand, the members may be one list
or repeated values (due2-profiles.md §4).
*%
member(C, D) :- conn(C, K), triple(C, Pred, D), voc(K, Pred), not is_list(D).
member(C, D) :- conn(C, K), triple(C, Pred, List), voc(K, Pred), is_list(List), list_item(List, D).

%*! reach_c(C, D)

`D` is below `C` in a tree: the transitive closure of `member/2`.
*%
reach_c(C, D) :- member(C, D).
reach_c(C, D2) :- reach_c(C, D), member(D, D2).

%*! scope(C, Scope)

Node `C` refines what `Scope` names: `rule` under a rule's constraint root, `action` under an
action term's refinement root. It is `constraint.scope` of due2-workflows.md §3.1, and part of
the completion key (completion.lp).
*%
scope(C, rule) :- top_constraint(_, C).
scope(C, action) :- top_refinement(_, C).
scope(D, Scope) :- scope(C, Scope), member(C, D).

%*! node_tree(Node, C)

`C` lies in a constraint tree of the structure node `Node`: under one of its constraint roots,
or under a refinement root of an action term it states. A tree shared by two nodes is in both.
*%
node_tree(Node, C) :- top_constraint(Node, C).
node_tree(Node, C) :- stated(Node, action, Term), top_refinement(Term, C).
node_tree(Node, D) :- node_tree(Node, C), member(C, D).

%*! leaf(C)

Node `C` compares a left operand: it has an `odrl:leftOperand`.
*%
leaf(C) :- cnode(C), triple(C, Pred, _), voc(leftOperand, Pred).

%*! left(C, Op)

Leaf `C` has left operand `Op`.
*%
left(C, Op) :- leaf(C), triple(C, Pred, Op), voc(leftOperand, Pred).

%*! c_operator(C, Iri)

Leaf `C` states the operator `Iri`.
*%
c_operator(C, Iri) :- leaf(C), triple(C, Pred, Iri), voc(operator, Pred).

%*! op(C, O)

Leaf `C` has the core operator `O`, such as `eq` or `isPartOf`.
*%
op(C, O) :- c_operator(C, Iri), operator(Iri, O).

%*! right_value(C, Term)

Leaf `C` states `Term` as an `odrl:rightOperand` value, a list or not.
*%
right_value(C, Term) :- leaf(C), triple(C, Pred, Term), voc(rightOperand, Pred).

%*! right(C, Term)

`Term` is a right operand value of leaf `C`: a value that is not a list, or an item of a list.
Repeated values and one list are the same set (decisions/0013).
*%
right(C, Term) :- right_value(C, Term), not is_list(Term).
right(C, Term) :- right_value(C, List), is_list(List), list_item(List, Term).

%*! unit(C, Iri)

Leaf `C` labels its right operand with the unit `Iri` (`odrl:unit`). It converts nothing
(compare.lp), and it is part of the completion key (completion.lp).
*%
unit(C, Iri) :- leaf(C), triple(C, Pred, Iri), voc(unit, Pred).

%## Rejections

% A node that is neither a leaf nor a connective; a leaf without one left operand, one
% operator, and a right operand; several values on a scalar operator; a list with other values,
% or two lists; the empty list on a set-based operator, which ODRL gives no meaning and which
% would make the leaf's value independent of the request (due2-diagnostics.md,
% MalformedConstraint; decisions/0013, amendment); a connective over the empty list, for the
% same reasons (decisions/0017).
reject("MalformedConstraint", C) :- cnode(C), not leaf(C), not conn(C, _).
reject("MalformedConstraint", C) :- leaf(C), #count { Op : left(C, Op) } != 1.
reject("MalformedConstraint", C) :- leaf(C), #count { Iri : c_operator(C, Iri) } != 1.
reject("MalformedConstraint", C) :- leaf(C), not right_value(C, _).
reject("MalformedConstraint", C) :- op(C, O), not set_based(O),
    #count { Term : right_value(C, Term) } > 1.
reject("MalformedConstraint", C) :- right_value(C, List), is_list(List), right_value(C, Term),
    Term != List.
reject("MalformedConstraint", C) :- op(C, O), set_based(O), right_value(C, List), voc(nil, List).
% Without this rule, the connective rules of compare.lp and completion.lp would give such a node
% the identities they start from: `and ()` would be `t`, and `or ()` and `xone ()` would be `f`.
reject("MalformedConstraint", C) :- conn(C, K), triple(C, Pred, List), voc(K, Pred), voc(nil, List).
reject("UnsupportedOperator", C) :- c_operator(C, Iri), not operator(Iri, _).
reject("UnsupportedConnective", C) :- conn(C, andSequence).
reject("FloatingPointOperand", C) :- right(C, Term), unplaceable(Term, "value: xsd:double").
reject("FloatingPointOperand", C) :- right(C, Term), unplaceable(Term, "value: xsd:float").
reject("MixedDuration", C) :- right(C, Term), unplaceable(Term, "value: mixed xsd:duration").

%## Declines

% A node with readings the spec does not settle, or none at all.
unsupported("constraint: leaf with a connective") :- leaf(C), conn(C, _).
unsupported("constraint: two connectives") :- conn(C, K), conn(C, K2), K != K2.
% With no member, `dprod:not` is over the empty list, which the rejections cover.
unsupported("constraint: dprod:not with several members") :- conn(C, negation),
    #count { D : member(C, D) } > 1.
unsupported("constraint: cycle") :- reach_c(C, C).
% A node shared by a rule's constraint and an action's refinement would need two completion
% variables, one per scope, for one value (completion.lp).
unsupported("constraint: node in two scopes") :- scope(C, rule), scope(C, action).
% A list on a scalar operator, the empty list included: one value that is a list, which no
% scalar comparison reads.
unsupported("constraint: list on a scalar operator") :- op(C, O), not set_based(O),
    right_value(C, List), is_list(List).
