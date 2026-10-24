/*
 * The connectives are regular: making a leaf more definite never changes a definite node.
 *
 * A lemma for claim K of correctness-strategy.md §4.8. k_completion_key.als shows that a
 * completion gives every leaf either `U` or its real value. This model shows that the
 * connectives then give every node `U` or its real value. A finding is the Kleene conjunction of
 * its parts (due2-workflows.md §5.2), an `and` here. decisions/0016 relies on the same property:
 * an opaque leaf stays `U` in an authored tree, and the tree is decided only when every value of
 * the leaf decides it.
 *
 * The connectives are strong Kleene `and`, `or`, and `not` (due2-workflows.md §5.2), and `xone`
 * by counting, as clingo-i's compare.lp evaluates it: `T` when one member is `T` and none is
 * `U`, `F` when two are `T` or all are `F`, `U` otherwise.
 *
 * Run: formal/alloy/run.sh formal/alloy/kleene_regularity.als.
 * The scopes and times are in README.md.
 */
module kleene_regularity

abstract sig Bool3 {}
one sig T, F, U extends Bool3 {}

fun not3[b: Bool3]: Bool3 { b = T => F else (b = F => T else U) }

abstract sig ConnKind {}
one sig And, Or, Not, Xone extends ConnKind {}

abstract sig Node {}
sig Leaf extends Node {}

sig Conn extends Node {
  conn: one ConnKind,
  members: some Node
}

fact trees {
  no c: Conn | c in c.^members
  all c: Conn | c.conn = Not implies one c.members
}

// Lo knows less than Hi: each of its leaves is `U` or has Hi's value.
abstract sig World { v3: Node -> one Bool3 }
one sig Lo, Hi extends World {}

fact refinement {
  all l: Leaf | l.(Lo.v3) in U + l.(Hi.v3)
}

fact connectives {
  all w: World, c: Conn | let vs = c.members.(w.v3) {
    c.conn = And implies c.(w.v3) = (F in vs => F else (U in vs => U else T))
    c.conn = Or implies c.(w.v3) = (T in vs => T else (U in vs => U else F))
    c.conn = Not implies c.(w.v3) = not3[c.members.(w.v3)]
    c.conn = Xone implies {
      let ts = c.members & (w.v3).T, us = c.members & (w.v3).U |
        c.(w.v3) = ((one ts and no us) => T else ((not lone ts or (no ts and no us)) => F else U))
    }
  }
}

assert Regular {
  all n: Node | n.(Lo.v3) in U + n.(Hi.v3)
}

// Non-vacuity: an `xone` with a `U` member that is decided all the same, because two other
// members are `T`. Expected: an instance.
run XoneDecidedOverU {
  some c: Conn | c.conn = Xone and some c.members & (Lo.v3).U and c.(Lo.v3) != U
} for 4

check Regular for 7
