/*
 * Claim K of correctness-strategy.md §4.8: the completion key.
 *
 * due2-workflows.md §6.4 completes each `U` part to `T` or `F`. A part that reads an
 * `unresolved` state property is *completed*: it reads a variable, and two such parts read one
 * variable when they are the same expression, or, with opposite polarities, when one is the
 * other's complement (decisions/0012). Every other `U` part is *opaque*: a variable of its own
 * (decisions/0016). K is two claims:
 *
 *   KeySound   The key never merges parts whose truth values can differ under a value that
 *              fits both.
 *   OneSided   Under every real world, a completion reproduces every finding. So the parts the
 *              key leaves independent only add completions: they can widen a verdict to
 *              `Indeterminate`, never make it a wrong definite one.
 *
 * This model checks KeySound, and OneSided at the leaves. kleene_regularity.als checks the
 * connectives, which carry OneSided from the leaves to the findings; checked together, the two
 * do not finish in minutes even at scope 3.
 *
 * Each ordered kind is assumed totally ordered. XSD orders `dateTime` and `date` values only
 * partially, with and without a timezone, and due2-profiles.md §4 does not say what an order
 * operator gives on two values XSD leaves unordered. clingo-i declines such values.
 *
 * What the model leaves out, and why that does not weaken the checks:
 *
 * - Scope and unit, which are part of the key. Neither changes what an operator computes, so
 *   they only split key classes, and a key that is sound without them is sound with them.
 * - The source. Only a state property can be `unresolved` (due2-profiles.md §3), so every
 *   completed part reads one.
 * - Set-valued operands. `eq`, the order operators, and `isAnyOf` compare one left value
 *   (due2-profiles.md §4), and the spec gives them no reading over a set; clingo-i declines it.
 *   Every complement pair is among these operators.
 * - The other kinds of due2-profiles.md §3. A numeric kind stands for every totally ordered one,
 *   a string kind for every kind compared by identity, and the IRI kind for the rest.
 *
 * Run: formal/alloy/run.sh formal/alloy/k_completion_key.als.
 * The scopes and times are in README.md.
 */
module k_completion_key

// Kleene values

abstract sig Bool3 {}
one sig T, F, U extends Bool3 {}

fun not3[b: Bool3]: Bool3 { b = T => F else (b = F => T else U) }

// Values (due2-profiles.md §3 Kinds, §4)

abstract sig Kind {}
one sig Num, Str, Iri extends Kind {}

sig Value {
  kind: one Kind,
  // v.less: the values above v. A strict total order on the numeric values.
  less: set Value,
  // skos:broader edges between concepts (due2-profiles.md §4, Concept operands).
  broader: set Value
}

fact values {
  less in (kind.Num) -> (kind.Num)
  no iden & less
  less.less in less
  all disj v, w: kind.Num | w in v.less or v in w.less
  broader in (kind.Iri) -> (kind.Iri)
}

// A right operand as written: a lexical form with its datatype (due2-workflows.md §2 `Term`).
// Two terms may denote one value, as `5` and `5.0` do.
sig Term { denotes: one Value }

// Operands and their bindings (due2-profiles.md §3)

sig Property {}
sig Scheme { concepts: set Value }

// A left operand's binding as one policy sees it: the property it reads, its range's kind
// (none admits every kind), and its concept schemes, the union over that policy's layers
// (decisions/0015 #6).
sig Operand {
  prop: one Property,
  range: lone Kind,
  schemes: set Scheme
}

fact bindings {
  Scheme.concepts in kind.Iri
  // InvalidBinding: a concept scheme on a datatype range.
  all o: Operand | some o.schemes implies o.range in Iri
}

// Leaves (due2-profiles.md §4, §5). The connectives above them are in kleene_regularity.als.

abstract sig Op {}
one sig Eq, Neq, Lt, Lteq, Gt, Gteq, AnyOf, NoneOf extends Op {}

abstract sig Leaf {}

// A leaf on an `unresolved` state property.
sig Completed extends Leaf {
  operand: one Operand,
  op: one Op,
  right: some Term
}

// A leaf whose `U` is `missing`, `invalid`, `conflict`, or a misfit (decisions/0016 #2).
sig Opaque extends Leaf {}

fact normalisation {
  all l: Completed {
    // MalformedConstraint: one right value on an operator that is not set-based.
    l.op not in AnyOf + NoneOf implies one l.right
    // OperatorTypeMismatch: a right operand outside the range.
    some l.operand.range implies l.right.denotes.kind in l.operand.range
    // OperatorTypeMismatch on a concept operand: an operator other than these four, or an IRI
    // right operand in none of its schemes (decisions/0015 #8).
    some l.operand.schemes implies {
      l.op in Eq + Neq + AnyOf + NoneOf
      all t: l.right | t.denotes.kind = Iri implies t.denotes in l.operand.schemes.concepts
    }
  }
}

// Evaluation of a completed leaf on a value (due2-workflows.md §5.4, due2-profiles.md §4)

// A read value is `invalid` when it lies outside the range, or is an IRI in none of the
// operand's schemes (due2-profiles.md §3, decisions/0015 #4).
pred conforms[o: Operand, v: Value] {
  some o.range implies v.kind = o.range
  (some o.schemes and v.kind = Iri) implies v in o.schemes.concepts
}

// `eq` by value within a kind, and as `⊑` between concepts on an operand with a scheme. A value
// of another kind does not fit: `U`.
fun eqv[o: Operand, v, w: Value]: Bool3 {
  v.kind != w.kind => U
  else ((some o.schemes and v.kind = Iri) => (w in v.*broader => T else F)
  else (v = w => T else F))
}

// The order operators, within the ordered kind.
fun ord[x: Op, v, w: Value]: Bool3 {
  (v.kind != Num or w.kind != Num) => U
  else (x = Lt => (w in v.less => T else F)
  else (x = Lteq => (w in v.less + v => T else F)
  else (x = Gt => (v in w.less => T else F)
  else (v in w.less + w => T else F))))
}

// `isAnyOf`: the Kleene disjunction of the `eq`s against the right values.
fun anyEq[o: Operand, v: Value, ts: set Term]: Bool3 {
  (some t: ts | eqv[o, v, t.denotes] = T) => T
  else ((some t: ts | eqv[o, v, t.denotes] = U) => U else F)
}

fun val[l: Completed, v: Value]: Bool3 {
  not conforms[l.operand, v] => U
  else (l.op = Eq => eqv[l.operand, v, l.right.denotes]
  else (l.op = Neq => not3[eqv[l.operand, v, l.right.denotes]]
  else (l.op in Lt + Lteq + Gt + Gteq => ord[l.op, v, l.right.denotes]
  else (l.op = AnyOf => anyEq[l.operand, v, l.right]
  else not3[anyEq[l.operand, v, l.right]]))))
}

// A value fits a leaf when the leaf is `T` or `F` on it.
pred fits[l: Completed, v: Value] { val[l, v] != U }

// The key (due2-workflows.md §6.4, "Completions range over literals")

// The operator a leaf asserts, and whether it asserts it negatively: a complement asserts its
// base (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`).
fun base[x: Op]: Op {
  x = Neq => Eq else (x = Gteq => Lt else (x = Gt => Lteq else (x = NoneOf => AnyOf else x)))
}

pred negative[l: Completed] { l.op in Neq + Gteq + Gt + NoneOf }

// The key as due2-workflows.md §6.4 stated it before decisions/0023: the same operand binding
// (its property; the source is always the state), the same right operands as written terms, and
// equal or complementary operators.
pred sameVarBefore0023[a, b: Completed] {
  a.operand.prop = b.operand.prop
  a.right = b.right
  base[a.op] = base[b.op]
}

// The key as decisions/0023 states it: both operands have a concept scheme, or neither has. `eq`
// is `⊑` on the one and identity on the other (due2-profiles.md §4), so without this the key
// pairs `isNoneOf c` on the one with `isAnyOf c` on the other, and a concept below `c` makes
// both `F` (the run SchemeGap below).
pred sameVar[a, b: Completed] {
  sameVarBefore0023[a, b]
  some a.operand.schemes iff some b.operand.schemes
}

pred samePolarity[a, b: Completed] { negative[a] iff negative[b] }

// The key partitions the completed leaves, so each class is one variable.
assert KeyIsEquivalence {
  all a: Completed | sameVar[a, a]
  all a, b: Completed | sameVar[a, b] implies sameVar[b, a]
  all a, b, c: Completed | (sameVar[a, b] and sameVar[b, c]) implies sameVar[a, c]
}

// Claim K, soundness.
assert KeySound {
  all a, b: Completed, v: Value |
    (sameVar[a, b] and fits[a, v] and fits[b, v]) implies
      (samePolarity[a, b] => val[a, v] = val[b, v] else val[a, v] = not3[val[b, v]])
}

// Worlds (due2-workflows.md §6.4)

// The real world: each property has a value that fits every completed leaf reading it, and each
// opaque leaf is `T` or `F`, since a definite verdict must hold for both (decisions/0016). A
// value that turns out not to fit is outside the claim: it is the case L4 excludes.
one sig Real {
  pv: Property -> one Value,
  ov: Opaque -> one Bool3
}

fact real {
  Real.ov in Opaque -> (T + F)
  all l: Completed | fits[l, Real.pv[l.operand.prop]]
}

// One representative per key class.
one sig Key { rep: Completed -> one Completed }

fact key {
  all l: Completed | sameVar[l, Key.rep[l]]
  all a, b: Completed | sameVar[a, b] implies Key.rep[a] = Key.rep[b]
}

abstract sig World { v3: Leaf -> one Bool3 }

// RealW evaluates every leaf in the real world. CompW is the completion that gives each key
// class its representative's real value, and leaves every opaque leaf `U`.
one sig RealW, CompW extends World {}

fact leaves {
  all l: Completed | l.(RealW.v3) = val[l, Real.pv[l.operand.prop]]
  all l: Opaque | l.(RealW.v3) = Real.ov[l]
  all l: Completed | let r = Key.rep[l] |
    l.(CompW.v3) = (samePolarity[l, r] => r.(RealW.v3) else not3[r.(RealW.v3)])
  Opaque.(CompW.v3) in U
}

// Claim K, one-sidedness, at the leaves. CompW is a completion: it gives every key class one
// value, `T` or `F`. Every leaf there is `U` or has its real value. kleene_regularity.als checks
// that the connectives, `xone` and the conjunction of a finding included, then give every node
// `U` or its real value too. A finding that CompW leaves `U` is completed by its own variable,
// which takes its real value, so this completion reproduces every real finding. The verdict is
// a function of the findings, so the real verdict is among the completions' verdicts, and a
// definite verdict, the same under every completion, is the real one.
assert OneSidedAtLeaves {
  all l: Leaf | l.(CompW.v3) in U + l.(RealW.v3)
  all l: Completed | l.(CompW.v3) in T + F
}

// Gaps, as runs that find them. Each comment says whether an instance is expected.

// The key before decisions/0023 pairs two leaves with opposite polarity that are not opposite on a value
// fitting both. Expected: an instance, `isNoneOf c` with a scheme and `isAnyOf c` without one.
run SchemeGap {
  some a, b: Completed, v: Value {
    sameVarBefore0023[a, b]
    not samePolarity[a, b]
    fits[a, v] and fits[b, v]
    val[a, v] = val[b, v]
  }
} for 3

// #25: `x lteq 5` and `x gt 7` stay independent, so a completion may make both `T`, which no
// value of `x` gives. Expected: an instance.
run Issue25BothT {
  some a, b: Completed {
    a.operand.prop = b.operand.prop
    a.op = Lteq and b.op = Gt
    b.right.denotes in a.right.denotes.less
    not sameVar[a, b]
    some v: Value | fits[a, v] and fits[b, v]
    no v: Value | fits[a, v] and fits[b, v] and val[a, v] = T and val[b, v] = T
  }
} for 4

// due2-workflows.md §6.4 stated the gap as both `F` before v0.32, and decisions/0021 still
// does. A value above 5 and at most 7, such as 7, gives that. Expected: no instance.
run Issue25BothF {
  some a, b: Completed {
    a.operand.prop = b.operand.prop
    a.op = Lteq and b.op = Gt
    b.right.denotes in a.right.denotes.less
    no v: Value | fits[a, v] and fits[b, v] and val[a, v] = F and val[b, v] = F
  }
} for 4

// decisions/0016: pairing a misfit with its complement would be unsound. `x eq 5` and
// `x neq 5` are both `U` on a string. Expected: an instance.
run MisfitBreaksPairing {
  some a, b: Completed, v: Value {
    sameVar[a, b]
    not samePolarity[a, b]
    val[a, v] = U and val[b, v] = U
  }
} for 3

// Non-vacuity: a real world in which two distinct leaves form a complement pair, and a
// completed leaf is `F`. Expected: an instance.
run ComplementPair {
  some disj a, b: Completed | sameVar[a, b] and not samePolarity[a, b]
  F in Completed.(CompW.v3)
  some Opaque
} for 4

check KeyIsEquivalence for 6
check KeySound for 6
check OneSidedAtLeaves for 6
