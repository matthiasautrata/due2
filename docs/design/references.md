# due2 — Annotated references

**Status:** living list, started 2026-10-17.

Every source that informed a decision, a spec section, or a review goes here, with what was looked at, why, and what we took from it. The list is the seed of a future paper's bibliography and related-work section. It is also the knowledge base: a newcomer can see from it which established notions due2 builds on, and where.

**Entry format.** Citation and link · **Read:** when, for which issue, and how much (abstract, sections, code at a commit) · **Learned:** what we took or rejected, in one to three sentences · **Used in:** the sections that cite it. Add an entry when research informs work, and update **Used in** when a citation moves. Tooling and benchmark sources for the host question stay in `implementation-alternatives-ii.md` § References. Unfinished citations are marked *(complete for the .bib)*.

## 1. ODRL: standards, semantics, evaluators

- **W3C, *ODRL Information Model 2.2* and *ODRL Vocabulary & Expression 2.2*** (2018). <https://www.w3.org/TR/odrl-model/>, <https://www.w3.org/TR/odrl-vocab/>.
  **Read:** throughout. **Learned:** the normative base: rule structure, conflict strategies, the set-based operators (Vocab §3.16.7–3.16.12) and their list right operands. A set right operand may also be written as repeated values: IM §2.5.1 asks for a "list" without naming `rdf:List`, Vocab §5.1 says only that `rdf:List` SHOULD be used, the vocabulary file (`ODRL22.ttl`) gives `odrl:rightOperand` no functional restriction and notes that "a list of values may be used", and the normative JSON-LD context (<http://www.w3.org/ns/odrl.jsonld>) maps `rightOperand` without `@container: @list`, so a JSON array in ODRL's own serialisation becomes repeated triples. **Used in:** `odrl22-shape.ttl`, `odrl22-conformance.md`, normalisation spec, `decisions/0005`, `decisions/0013`.
- **Steyskal and Polleres, *Towards Formal Semantics for ODRL Policies*,** RuleML 2015. <https://aic.ai.wu.ac.at/~polleres/publications/stey-poll-2015RuleML.pdf>.
  **Read:** for normalisation stage 1. **Learned:** the first formal reading of ODRL's compound forms. **Used in:** normalisation spec § References.
- **De Vos, Kirrane, Padget, and Satoh, *ODRL Policy Modelling and Compliance Checking*,** RuleML+RR 2019. <https://doi.org/10.1007/978-3-030-31095-0_3>.
  **Read:** for normalisation stage 1. **Learned:** compliance checking of ODRL in answer set programming, a precedent for `decisions/0009`. **Used in:** normalisation spec § References.
- **Salas, Pareti, Yumuşak, Gheisari, Ibáñez, and Konstantinidis, *Evaluation and Comparison Semantics for ODRL*,** 2025. arXiv:2509.05139.
  **Read:** 2026-10-09 and again 2026-10-17 (#55). **Learned:** monitoring as the modality; null is false (SPARQL filter semantics); hierarchy reasoning kept out of the core and materialised; duties as relations over rules; duty preconditions temporal over the event log, which made approval a fact in due2. Their reading of the set operators differs from earlier work (`decisions/0005`). **Used in:** architecture §8.1, `decisions/0005`, normalisation spec § References.
- **Salas, Pareti, and Konstantinidis, *ODRL Policy Comparison Through Normalisation*,** 2026. arXiv:2603.12926.
  **Read:** 2026-10-17 (#55). **Learned:** a constraint normal form (DNF, operators regularised, disjoint intervals) that makes containment set membership. It composes with due2's structural stage 1, but excludes the set operators due2 admits. **Used in:** architecture §8.1; candidate input to #15.
- **Salas et al., *A Formally Grounded ODRL Evaluator: Implementation and Comparison*,** 2026. arXiv:2607.15987.
  **Read:** 2026-10-17 (#55), Defs 1, 3, 5 and Thm 4.1. **Learned:** access control as validity of ω ∪ {e_R}, which coincides with streaming monitoring for permissions, prohibitions and duties. Their Defs 1 and 3 are a candidate for due2's monitoring question (#6), with `U` in place of false. **Used in:** architecture §8.1.
- **Bonatti, Fornara, and Harth,** OPAL@ESWC 2025, CEUR 3977, Table 1 *(complete for the .bib)*.
  **Read:** for `decisions/0005`. **Learned:** a two-valued membership reading of `isPartOf`, `hasPart` and `isA`. **Used in:** `decisions/0005`.
- **Mustafa et al.,** 2026, arXiv:2602.19883 *(complete for the .bib)*.
  **Read:** for `decisions/0005`. **Learned:** a Kleene reading of the set operators by downward and upward closure, the reading closest to due2's. **Used in:** `decisions/0005`.
- **Rodríguez-Doncel,** W3C ODRL workshop open-issues paper, 2026, item R-V2 *(complete for the .bib)*.
  **Read:** for `decisions/0005`. **Learned:** the set-membership ambiguity is an acknowledged open issue in the WG. **Used in:** `decisions/0005`.
- **Slabbinck, Rojas, Esteves, Colpaert, and Verborgh, *Interoperable Interpretation and Evaluation of ODRL Policies*,** ESWC 2025 (Resource Track). <https://ruben.verborgh.org/publications/slabbink_eswc_2025/>. The ODRL Compliance Report Model: <https://github.com/odrl-force/ODRL-Compliance-Report-Model> (`https://w3id.org/force/compliance-report#`). The test suite: <https://github.com/SolidLabResearch/ODRL-Test-Suite>.
  **Read:** suite vendored 2026-10-11; report model ontology and the 68 expected reports read 2026-10-17 (#60). **Learned:** a per-rule, per-premise report (activation, satisfaction, attempt; performance and deontic state for monitoring) that is two-valued: missing information is unsatisfied. It has no overall decision and no conflict resolution. **Used in:** `conformance/external/README.md` (Findings; § Traces compared), the `force-*` cases.
- **OVAL, DIPS-Tools/ODRL-Engine** (Southampton), code at `40b8ac6`. <https://github.com/DIPS-Tools/ODRL-Engine>.
  **Read:** suite vendored 2026-10-11, refreshed 2026-10-16; `ODRL_Evaluator.py` read (never run) 2026-10-16/17. **Learned:** an access-control mode returning accept, reject or `None`, the matched rules with their null-only *conditional* conditions and unfulfilled duties, and an English explanation list; evaluator switches for duty and default semantics. Upstream defects reported as ODRL-Engine#8 and #9. **Used in:** architecture §8.1, `conformance/external/README.md`, the `oval-*` cases.
- **W3C ODRL Community Group, formal-semantics examples,** `github.com/w3c/odrl` `formal-semantics/examples/` at `1db8e6b`.
  **Read:** vendored 2026-10-11. **Learned:** compliance reports with `activationState`, `controlState` and `satisfactionState` (`Not-Satisfied`), two-valued like FORCE's; policy-level default behaviour. **Used in:** the `w3c-fs-*` cases, `conformance/external/README.md`.
- **DPROD Contracts** (EKGF), `github.com/EKGF/dprod`, branch `develop`, `dprod-contracts/`.
  **Read:** vendored; `formal-semantics.md` throughout. **Learned:** an ODRL profile for data contracts with deterministic evaluation; six documented exceptions where due2 answers differently. **Used in:** `decisions/0001`, `due2-profiles.md` §8, architecture §8.3.

## 2. Explaining a decision: causality, formal XAI, provenance

Surveyed 2026-10-17 for #59 (the `unknown` role and `verdict_range`), #58 (a witness for `Indeterminate`), #60, and #61 (remedies). The outcome is `decisions/0011`.

- **Halpern and Pearl, *Causes and Explanations: A Structural-Model Approach. Part I: Causes*,** British Journal for the Philosophy of Science 56, 2005. **Halpern, *A Modification of the Halpern–Pearl Definition of Causality*,** IJCAI 2015 (<https://www.cs.cornell.edu/home/halpern/papers/newcause.pdf>). **Halpern, *Actual Causality*,** MIT Press 2016.
  **Read:** 2026-10-17, definitions and survey material, not the full book. **Learned:** actual causation is counterfactual dependence under a contingency. A due2 variable that, flipped alone, changes some completion's verdict is a cause in this sense under the contingency that fixes the others. due2 has no actual world, only completions, so we use dependence over all of them. **Used in:** `decisions/0011`, workflows §6.4.
- **Chockler and Halpern, *Responsibility and Blame: A Structural-Model Approach*,** JAIR 22, 2004.
  **Read:** 2026-10-17, the definition. **Learned:** degree of responsibility 1/(k+1), with k the fewest changes that make the outcome counterfactually depend on the variable. due2 reports membership (responsibility > 0), not degree. **Used in:** `decisions/0011` (Rejected: scores).
- **Aleksandrowicz, Chockler, Halpern, and Ivrii, *The Computational Complexity of Structure-Based Causality*,** JAIR 2017 (AAAI 2014). arXiv:1412.3076.
  **Read:** 2026-10-17, abstract. **Learned:** deciding actual causation is NP-complete in binary models under the modified definition, which is why W3 bounds the computation as it bounds the frontier. **Used in:** `decisions/0011`.
- **O'Donnell, *Analysis of Boolean Functions*,** Cambridge University Press 2014.
  **Learned:** the influence of variable i on f is the probability that flipping i changes f; it is non-zero iff i is relevant (essential). The pivotal literals of due2 are the relevant variables of the verdict function restricted to the completions; Banzhaf power is the same influence. **Used in:** `decisions/0011`.
- **Marques-Silva, *Logic-Based Explainability in Machine Learning*,** Reasoning Web 2022. arXiv:2211.00541.
  **Read:** 2026-10-17, the definitions. **Learned:** abductive explanations (AXp: subset-minimal sufficient reasons, prime implicants) and contrastive explanations (CXp: minimal changes that switch the outcome), dual by minimal hitting sets (Ignatiev, Narodytska, Asher, and Marques-Silva, *From Contrastive to Abductive Explanations and Back Again*, AI*IA 2020). A literal is relevant iff it is in some AXp. The Pending frontier is already an abductive answer; remedies (#61) would be the AXp and CXp of the other verdicts. **Used in:** `decisions/0011`, #61.
- **Izza, Ignatiev, Stuckey, and Marques-Silva, *Delivering Inflated Explanations*,** AAAI 2024. arXiv:2306.15272.
  **Read:** 2026-10-17, abstract. **Learned:** an explanation may give each feature a set of values that keep the decision, not one value. That is the shape a remedy over an enumerated or ranged fact would take, and it relates to domain-aware completion (#25). **Used in:** #61.
- **Buneman, Khanna, and Tan, *Why and Where: A Characterization of Data Provenance*,** ICDT 2001. **Green, Karvounarakis, and Tannen, *Provenance Semirings*,** PODS 2007 (<https://www.cs.ucdavis.edu/~green/papers/pods07.pdf>).
  **Read:** 2026-10-17, framework only. **Learned:** why-provenance (minimal witnesses) and its generalisation to semiring annotations, with Datalog as a fixed point. due2's `basis` is why-provenance of a finding. We do not adopt the polynomial machinery: the trace records the determining parts, not every derivation. **Used in:** `decisions/0011` (Context).
- **Chapman and Jagadish, *Why Not?*,** SIGMOD 2009.
  **Learned:** why-not provenance: why an expected answer is missing. due2's `eliminated` answers why-not for a candidate removed by conflict, and remedies (#61) generalise it. **Used in:** #61.
- **Imieliński and Lipski, *Incomplete Information in Relational Databases*,** JACM 1984. **Libkin, *How to Define Certain Answers*,** IJCAI 2015.
  **Read:** 2026-10-17, abstract. **Learned:** certain answers, those true in every completion of an incomplete database, are what due2's definite verdict is (invariance over completions, workflows §6.4). Libkin's critique of one-size-fits-all certain answers is worth reading before domain-aware completion (#25). **Used in:** `decisions/0011` (Context).
- **Cabalar, Fandinno, and Fink, *Causal Graph Justifications of Logic Programs*,** TPLP 2014. arXiv:1409.7281. **Cabalar, Fandinno, and Muñiz, *A System for Explainable Answer Set Programming* (xclingo),** ICLP 2020. arXiv:2009.10242.
  **Read:** 2026-10-17, abstracts. **Learned:** justifications of an atom in an answer set as causal terms (product for joint, sum for alternative causes), and xclingo, which builds derivation trees from comment annotations. Not adopted as a dependency: due2's trace is already the derivation (`decisions/0010`). A candidate for rendering clingo-i's derivations later. **Used in:** `decisions/0011` (Rejected).
- ***An XAI View on Explainable ASP: Methods, Systems, and Perspectives*,** 2026. arXiv:2601.14764 *(complete for the .bib)*.
  **Read:** 2026-10-17, abstract only. **Learned:** a survey of ASP explanation methods against XAI user needs; read in full before #47. **Used in:** —.

## 3. Policy engines: what they report

- **OASIS, *eXtensible Access Control Markup Language (XACML) 3.0*,** 2013.
  **Read:** 2026-10-17, the extended Indeterminate and missing-attribute status. **Learned:** `Indeterminate{P}`, `{D}`, `{DP}` record which decisions an indeterminate rule could have produced, because a rule that might match cannot override, but makes the result uncertain. The same reasoning is behind due2's "`U` atoms eliminate nothing" (workflows §6.2) and `verdict_range`. The PDP may name the missing attribute, which is the `unknown` role. **Used in:** `decisions/0011`.
- **Cutler et al., *Cedar: A New Language for Expressive, Fast, Safe, and Analyzable Authorization*,** OOPSLA 2024. Docs: <https://docs.cedarpolicy.com/auth/authorization.html>; partial evaluation in the `cedar-policy` crate (`PartialResponse`).
  **Read:** 2026-10-17, the authorization docs. **Learned:** the response is the decision plus its *determining policies*: the satisfied permits for Allow, the satisfied forbids for Deny, empty for a default Deny. That is due2's `verdict_basis` for `Permit` and `Deny`, and the empty basis of `NotApplicable`. Partial evaluation returns residual policies over unknowns, the analogue of a remedy. **Used in:** `decisions/0011`, #61.

## 4. Logic

- **Kleene, *Introduction to Metamathematics*,** North-Holland 1952. The strong three-valued connectives due2 evaluates with (workflows §2).

## 5. Documentation practice

- **Procida, *Diátaxis*,** <https://diataxis.fr/>.
  **Read:** 2026-10-17, the overview and the four kinds. **Learned:** tutorials, how-to guides, reference, and explanation serve different needs and fail when mixed. A design note that is reference in form but explanatory in purpose loses both readers. **Used in:** `ways-of-working.md` §15.2, the `technical-writing` skill.
- **Goodger and van Rossum, *PEP 257 – Docstring Conventions*,** 2001. <https://peps.python.org/pep-0257/>.
  **Read:** 2026-10-17, in full. **Learned:** a one-line imperative summary, then behaviour, arguments, return values, side effects, and exceptions. A docstring does not repeat the signature. **Used in:** `ways-of-working.md` §15.8.
- **Google, *Python Style Guide*, §3.8 Comments and Docstrings.** <https://google.github.io/styleguide/pyguide.html>.
  **Read:** 2026-10-17, §3.8. **Learned:** `Args:`, `Returns:`, and `Raises:` sections; comment the tricky parts; never describe the code. **Used in:** `ways-of-working.md` §15.8, the skill's Python template.
- **Google, *Developer Documentation Style Guide*, highlights.** <https://developers.google.com/style/highlights>.
  **Read:** 2026-10-17, the highlights page. **Learned:** second person, active voice, present tense, sentence-case headings, and code font for names; consistent terminology. **Used in:** the skill's house-style item.
- **Ousterhout, *A Philosophy of Software Design*,** Yaknyam Press 2018 *(complete for the .bib)*. Read through a summary: <https://danlebrero.com/2021/02/24/philosophy-of-software-design-summary/>.
  **Read:** 2026-10-17, the summary's chapters on comments, not the book. **Learned:** comments describe what the code cannot say; interface comments (what and why) are separate from implementation comments (how, and the tricks); write the comments first. **Used in:** `ways-of-working.md` §15.4, §15.8.
- **Knuth, *Literate Programming*,** The Computer Journal 27(2), 1984 *(complete for the .bib)*. Read through <https://en.wikipedia.org/wiki/Literate_programming>.
  **Read:** 2026-10-17, the secondary summary, not the paper. **Learned:** a program is written to be read by people, with the argument in the order a reader needs it. due2 takes the aim, not the tangle-and-weave tooling. **Used in:** `ways-of-working.md` §15.1.
- **Potassco, *clindocs*** (formerly `mkdoclingo`), version 1.5.2, MIT. <https://github.com/potassco/clindocs>, <https://docs.potassco.org/clindocs/>.
  **Read:** 2026-10-17, the README, the predicate-documentation page, and the 1.5.2 sdist's handler and templates (as data, not run); then installed and built over clingo-i. **Learned:** a mkdocstrings handler (`asp`) that documents an ASP encoding from `%*! pred(Args) … *%` blocks, which clingo reads as block comments. `%#` and `%##` lines become headings. It marks input predicates (used, not defined) and output predicates (`#show`), and generates a glossary and a dependency graph. Tuple arguments are not supported. Its predicate table shows a block only up to the first full stop, so a dotted name in the first sentence cuts the summary. It parses through tree-sitter-clingo, and under tree-sitter 0.26 on Python 3.14 the build segfaults; 0.25 works. **Used in:** `ways-of-working.md` §15.8, §15.10 (the doc-block format; the generated reference, provisional); `spikes/clingo-i/docs/`, `tests/test_docs.py`.
- **mkdocstrings, pdoc, and Sphinx autodoc,** compared in UCL ARC's *Python tooling: documentation*. <https://github-pages.arc.ucl.ac.uk/python-tooling/pages/docs.html>.
  **Read:** 2026-10-17, the comparison page. **Learned:** all three generate reference documentation from docstrings: Sphinx autodoc is the most mature, pdoc the simplest, and mkdocstrings is Markdown-native under MkDocs, where clindocs also runs. **Used in:** `ways-of-working.md` §15.10: mkdocstrings, picked provisionally because clindocs runs under the same MkDocs build; `spikes/clingo-i/docs/python.md`.

## To read

- arXiv:2601.14764 in full (§2), before #47.
- OPA's decision explanations (`--explain`, partial evaluation), for #61.
- Cedar's partial evaluation (the residuals' format), for #61.
- From `formalisation-review.md` (not yet read by us): Isabelle/HOL and Sledgehammer; Alloy 6; cedar-spec's Lean proofs, and why Cedar moved from Dafny; K-relations over the Kleene lattice (with Green–Karvounarakis–Tannen, §2). Read when the review's trigger is reached (about 100 passing vectors).
