# CP-SAT Allocation Optimiser Integration Plan

## Purpose

Replace the current order-dependent greedy allocation with an opt-in exact
optimiser that:

- produces the best legal allocation for a completed, in-progress, or planned
  transcript;
- returns useful partial allocations when the transcript cannot satisfy every
  requirement;
- respects major, TC/TE, Common Curriculum, internship, specialisation,
  overlap, capstone, alias, SEP, and residency rules;
- explains deficits and important allocation choices;
- remains deterministic and compatible with manual allocations and the current
  audit contract; and
- is always checked by the existing audit/evaluation layer before being
  reported as valid.

The intended production solver is Google OR-Tools CP-SAT. A small exhaustive
solver will be retained as a correctness oracle for bounded test cases.

## Current Baseline

The current `plan_allocations()` algorithm:

1. allocates fixed EE major core courses;
2. chooses `EE2028` before `EE2026` for the major digital choice;
3. takes the first three alphabetically eligible TCs;
4. takes the first two remaining eligible TEs; and
5. sends every unallocated course to residual UE.

This is deterministic but not globally optimal. A course eligible for both TC
and TE can be consumed by TC even when TE is scarcer. The optimiser must make
these choices globally rather than requirement by requirement.

Several surrounding issues must also be handled explicitly:

- transcript attempts are not centrally normalized or deduplicated;
- course status is not consistently used by all calculations;
- some aggregate requirement statuses currently default to `PASS`;
- internal-to-public requirement ID mapping can collapse multiple internal
  requirements onto the same public ID;
- specialisation inference can activate optional areas implicitly; and
- many rule implementations are hard-coded evaluators rather than declarative
  constraints.

These are not all solver problems, but leaving them unresolved would allow the
solver to optimize an incorrect or ambiguous problem.

## Design Principles

1. **Legality is hard; completion is optimised.** An ineligible allocation is
   forbidden. An incomplete transcript gets shortfall variables instead of an
   infeasible solver result.
2. **One rule, two implementations, mandatory parity.** Until audit evaluators
   and solver encoders share a declarative rule representation, every encoded
   rule must have evaluator-versus-solver parity tests.
3. **Final audit remains authoritative.** Every solver result is passed through
   manual allocation validation and the existing audit evaluators.
4. **No silent model drift.** A solver result rejected by the evaluator is a
   `MODEL_MISMATCH`, not an ordinary student audit failure.
5. **Lexicographic objectives over giant weights.** Solve one objective stage
   at a time and lock the optimum before moving to the next stage.
6. **Optional goals are explicit.** A partial specialisation is not selected
   automatically unless the user asks to optimize for or discover it.
7. **Deterministic by default.** Stable candidate ordering, fixed solver
   settings, and a final deterministic tie-break are part of the contract.
8. **Greedy remains available.** It is a fast fallback and backward-compatible
   strategy, not removed during the initial rollout.
9. **Protect transcript privacy.** Use synthetic fixtures that reproduce rule
   shapes; do not commit identifiable transcripts.

## Target Architecture

```text
Transcript YAML
      |
      v
Transcript normalizer
  - canonical attempts
  - status policy
  - alias groups
  - deduplication
      |
      v
Candidate builder <------ Config + allocation choice rules
  - course/requirement edges
  - legal double-count edges
  - path and source metadata
      |
      v
Solver-independent AllocationProblem
      |
      +--------------------+
      |                    |
      v                    v
CP-SAT solver       Exhaustive test oracle
      |                    |
      +---------+----------+
                |
                v
OptimizationResult
  - allocations
  - shortfalls
  - objective vector
  - selected paths
  - alternatives
  - solver status
                |
                v
Manual validation + existing audit evaluators
                |
                v
Text / JSON / YAML reporting
```

Suggested modules:

```text
degree_auditor/
  optimization/
    __init__.py
    models.py
    normalization.py
    candidates.py
    objectives.py
    rule_registry.py
    cp_sat.py
    exhaustive.py
    alternatives.py
    explanations.py
```

Keep `degree_auditor/allocation.py` as the public strategy dispatcher and home
of the legacy greedy implementation until migration is complete.

## Solver Model

### Sets

- `C`: normalized course attempts or credit-bearing course instances.
- `R`: canonical allocation requirements or slots.
- `S`: configured specialisations.
- `P[s]`: paths available for specialisation `s`.
- `A`: canonical alias/duplicate-credit groups.

### Primary Variables

```text
x[c, r]       Boolean: course c is allocated to requirement r
sat[r]        Boolean: requirement r is satisfied
short[r]      Integer: missing units or course count for r
select[s]     Boolean: specialisation s is selected
path[s, p]    Boolean: path p is selected for specialisation s
overlap[s]    Integer: overlap units consumed by specialisation s
distinct[s]   Integer: distinct units counted by specialisation s
cap_lock[s]   Boolean: capstone lock is active for specialisation s
risk[c, r]    Constant or derived penalty for uncertain mappings/approvals
```

Use Boolean assignment variables multiplied by the course's normalized unit
value. Courses are indivisible in the initial model. If a future policy permits
partial allocation of a course's units, add explicit integer unit variables for
only those rule types rather than making every assignment splittable.

### Hard Constraint Families

- Candidate eligibility: create `x[c, r]` only for a legal candidate edge.
- Course-instance capacity: one primary use unless an explicitly allowed
  double-count relation is active.
- Allocation units do not exceed the normalized attempt units.
- Alias/cross-list duplicate groups cannot receive duplicate credit.
- Exactly one of `EE2026` and `EE2028` fills the digital choice when available
  and required.
- TC and TE use of the same course instance is mutually exclusive.
- Effective-term gates such as `EE3033`.
- Non-EE TE exclusions and cohort carve-outs.
- SEP approval and mapping eligibility.
- Path activation and path exclusivity.
- Specialisation overlap, distinct-unit, capstone-lock, and SEP-reuse limits.
- Common Curriculum branch legality and TC-in-lieu exclusivity.
- Internship combination, UROP cap, poly/APC, and CEG-only restrictions.

### Soft Completion Targets

Each incomplete mandatory requirement receives a non-negative shortfall:

```text
allocated_units[r] + short[r] >= required_units[r]
allocated_count[r] + short_count[r] >= required_count[r]
```

`sat[r]` is linked to a zero shortfall. Parent programme status is derived from
canonical leaf requirements instead of being independently optimized. This
prevents duplicate public IDs and parent/child requirements from distorting the
objective.

### Lexicographic Objective

Solve and lock these stages in order:

1. Minimise the number of failed mandatory leaf requirements.
2. Minimise total mandatory shortfall, using units and counts in separate
   normalized components.
3. Maximise mandatory major and Common Curriculum coverage before optional
   specialisation coverage.
4. Maximise the explicitly requested goal, such as a chosen specialisation.
5. Minimise unapproved, unknown, or human-review-dependent uses.
6. Minimise unnecessary double-counting and consumed overlap budget.
7. Preserve scarce/flexible courses when a less-flexible course can fill the
   same requirement.
8. Apply a stable course-code and requirement-ID tie-break.

Do not encode these priorities as one set of very large weights. For each
stage, solve, record the optimum, add an equality fixing that optimum, and then
solve the next stage.

### Solver Result States

Expose at least:

- `OPTIMAL`: all objective stages were proven optimal.
- `FEASIBLE`: a legal allocation was found but optimality was not proven,
  usually because of a time limit.
- `INFEASIBLE`: the legality model itself has no solution; this should be rare
  because completion uses shortfall variables.
- `MODEL_INVALID`: CP-SAT rejected the generated model.
- `MODEL_MISMATCH`: solver output failed existing validation/evaluation.
- `UNKNOWN`: no conclusion before the limit.

An audit may legitimately be `FAIL` while the optimization result is
`OPTIMAL`: that means the best possible allocation still has academic
shortfalls.

## Pass 0: Baseline Contract and Decision Record

### Goals

- Freeze current behavior before introducing solver changes.
- Define what “best allocation” means.
- Define compatibility and rollout policy.

### Work

- Add an architecture decision record covering:
  - CP-SAT as the production solver;
  - exhaustive search as a bounded test oracle;
  - direct runtime dependency versus an optional optimizer extra;
  - deterministic default solver settings;
  - the lexicographic objective contract;
  - greedy remaining the default during the opt-in period.
- Introduce solver-independent API sketches:

  ```python
  class AllocationStrategy(StrEnum):
      greedy = "greedy"
      cp_sat = "cp-sat"

  class OptimizationGoal(StrictModel):
      mode: Literal["graduation", "specialisation", "preserve_flexibility"]
      specialisation_id: str | None = None

  class OptimizationResult(StrictModel):
      status: str
      allocations: list[Allocation]
      shortfalls: list[RequirementShortfall]
      objective_values: dict[str, int]
      selected_paths: dict[str, str]
      warnings: list[str]
  ```

- Capture current greedy allocations in focused regression tests.
- Add a synthetic fixture with the same TC/TE scarcity shape as the transcript
  used during exploration:
  - one unused digital-choice course eligible for TC;
  - one course eligible for both TC and TE;
  - one TE-only course.
- Record that the improved allocation must satisfy TE and leave only TC short.

### Tests

- Existing full suite remains green.
- Greedy snapshot remains unchanged.
- Objective policy tests document how equal total shortfalls are broken.

### Exit Criteria

- API and objective semantics are agreed and tested without adding OR-Tools.
- No CLI behavior changes.

## Pass 1: Transcript Normalization and Attempt Policy

### Goals

- Ensure every allocator and residency calculation sees a consistent set of
  course instances.

### Work

- Add a normalized transcript representation with a stable `attempt_id`.
- Define explicit policies for:
  - completed, in-progress, and planned attempts;
  - repeated attempts and latest-attempt selection;
  - failed/withdrawn attempts if those statuses are added later;
  - zero-unit administrative courses;
  - aliases and cross-listed courses;
  - approved, pending, unknown, and rejected SEP mappings;
  - transfer blocks without course-level mappings.
- Default audit optimization to completed courses.
- Permit planned/in-progress scenarios only through explicit options.
- Update total-unit, residency, and level-1000 helpers to consume normalized
  attempts rather than the raw list.
- Preserve original transcript rows for reporting and provenance.

### Tests

- Repeated `IP` then completed attempt counts once.
- Planned courses are excluded by default and included only when requested.
- Zero-unit courses never satisfy unit-bearing requirements.
- Alias twins cannot create two credit-bearing instances.
- Unknown transfer blocks contribute only to rules that explicitly permit
  unmapped credit.

### Exit Criteria

- All allocation and unit calculations use the same normalized snapshot.
- No double-counting from repeated attempts.

## Pass 2: Candidate Graph and Canonical Requirement Registry

### Goals

- Build a deterministic, solver-independent allocation problem.
- Eliminate internal/public ID ambiguity before optimization.

### Work

- Introduce canonical requirement keys distinct from reporting aliases.
- Produce one candidate edge per legal `(attempt_id, requirement_key)` pair.
- Reuse `allocation_choices_for_course()` and eligibility helpers where
  possible, but attach structured reasons and source constraint IDs.
- Include candidate metadata:
  - units;
  - primary/double-count/residual role;
  - source and approval status;
  - effective course code and alias group;
  - specialisation/path membership;
  - topic tags;
  - risk and flexibility scores.
- Generate residual UE as an explicit fallback edge, not a post-processing
  catch-all.
- Add deterministic problem serialization for debugging and snapshot tests.

### Tests

- Candidate edges match interactive-allocation choices.
- Candidate ordering is stable across transcript/config ordering.
- Every edge has a canonical requirement key and traceable rule/source.
- No candidate is generated for a known-ineligible manual allocation.
- Public ID collisions do not merge distinct internal decision variables.

### Exit Criteria

- The same `AllocationProblem` can be consumed by greedy, exhaustive, and
  CP-SAT implementations.

## Pass 3: Exhaustive Solver and Objective Oracle

### Goals

- Create an exact reference implementation for small problems.
- Prove objective semantics independently of CP-SAT.

### Work

- Implement depth-first enumeration with:
  - most-constrained-course-first branching;
  - immediate legality pruning;
  - shortfall lower bounds;
  - lexicographic branch-and-bound;
  - deterministic branch ordering.
- Limit the oracle by candidate-edge count and fail clearly when a case is too
  large.
- Return the same `OptimizationResult` shape planned for CP-SAT.
- Add a scorer that accepts a completed allocation and produces the canonical
  objective tuple.

### Tests

- Enumerate all allocations for small TC/TE, choice, alias, and overlap cases.
- Verify the synthetic scarcity case chooses two TEs and one TC.
- Verify reordered inputs produce the same optimum.
- Verify tied optima resolve through the deterministic tie-break.

### Exit Criteria

- Small cases have a trusted exact optimum and objective vector.
- Future CP-SAT tests can compare allocations or objective values to the oracle.

## Pass 4: CP-SAT Foundation and Basic Legality

### Goals

- Add OR-Tools and produce legal allocations from the candidate graph.

### Work

- Add a tested OR-Tools runtime dependency and refresh `uv.lock`.
- Implement variable creation with stable names derived from canonical IDs.
- Encode:
  - candidate selection;
  - course-instance primary-use capacity;
  - units within attempt limits;
  - residual fallback;
  - alias-group duplicate-credit prevention;
  - permitted versus forbidden double-count relations.
- Add configurable solver settings:
  - time limit;
  - fixed random seed;
  - deterministic single-worker default;
  - optional diagnostic logging.
- Convert a solution back to existing `Allocation` objects.
- Run `validate_manual_allocations()` on every returned allocation.

### Tests

- CP-SAT feasibility matches the exhaustive oracle.
- No ineligible or over-unit allocation can be produced.
- Alias and single-instance constraints hold.
- Solver variable/model output is deterministic in tests.
- Invalid generated models return `MODEL_INVALID` cleanly.

### Exit Criteria

- CP-SAT can solve generic candidate-assignment problems but is not yet exposed
  through the default CLI.

## Pass 5: Shortfalls and Lexicographic Optimization

### Goals

- Make incomplete transcripts return the provably best partial allocation.

### Work

- Add satisfaction and shortfall variables for count- and unit-based targets.
- Define the canonical mandatory leaf-requirement set.
- Implement sequential objective solves with optimum locking.
- Add flexibility/scarcity scoring:
  - fewer candidate destinations means less-flexible;
  - approval-dependent edges receive risk penalties;
  - consuming a highly flexible course is penalized when a less-flexible course
    could fill the same target.
- Return objective values and proof status after every stage.
- Define timeout behavior:
  - keep the best legal incumbent;
  - report which stages were proven optimal;
  - never label a merely feasible solution optimal.

### Tests

- Objective vector matches exhaustive search on bounded cases.
- One failed requirement is preferred over two even when total missing course
  slots are equal.
- Lower total shortfall breaks ties after failed-requirement count.
- Risk, overlap, flexibility, and deterministic stages break only later ties.
- Tight time limits return a legal `FEASIBLE` result with honest metadata.

### Exit Criteria

- CP-SAT reliably improves on greedy in known scarcity cases.
- Partial audits have explicit and correct deficits.

## Pass 6: EE Major, Digital Choice, TC, and TE

### Goals

- Deliver the first user-visible optimal strategy for the current core auditor.

### Work

- Encode:
  - fixed EE major core;
  - exactly one digital/microcontroller choice;
  - the unused choice course's TC eligibility;
  - TC minimum and closed pool;
  - TE minimum and pool/exclusions;
  - TC/TE mutual exclusion;
  - `EE3033` effective-term gate;
  - non-EE TE exclusions and cohort carve-outs;
  - NUS-versus-SEP TE restrictions;
  - SEP-to-TC approval/mapping rules.
- Add parity tests for every associated constraint ID.
- Add opt-in CLI support:

  ```bash
  uv run degree-auditor plan-allocation \
    --strategy cp-sat \
    --goal graduation \
    --config configs/nus_ee_ay24_jc \
    --transcript transcript.yaml \
    --out allocation.yaml
  ```

- Keep `--strategy greedy` as the default.
- Include solver status and objective summary in terminal output.

### Tests

- Existing major, TC/TE, SEP, alias, and date-gate fixtures.
- Exhaustive-oracle parity for all small combinations.
- Synthetic scarcity case reduces failed requirements relative to greedy.
- Generated allocation round-trips through `audit --allocation`.
- CLI exit behavior remains 0 for a written legal plan even if academic
  shortfalls remain; the optional immediate audit retains exit code 2.

### Exit Criteria

- CP-SAT is a supported opt-in replacement for core greedy allocation.
- Every core solver result passes existing validators and audit rules.

## Pass 7: Common Curriculum, UE, and Degree Totals

### Goals

- Optimize Common Curriculum branches and stop reporting aggregate completion
  from default statuses.

### Work

- Encode:
  - GESS and other GE pillars;
  - fixed Common Curriculum courses;
  - `CDE2501` GESS/Sustainable Futures branch;
  - Systems Thinking and Creating Narratives TC-in-lieu;
  - Sustainable Futures substitution conditions;
  - RC/UTCP/NUSC/RVRC/poly human-review restrictions;
  - pillar single-instance and over-allocation rules;
  - UE residual allocation and capacity;
  - Common Curriculum, major, UE, and 160-unit totals.
- Replace aggregate default passes with statuses derived from normalized
  attempts and optimized allocations.
- Ensure TC-in-lieu is unit-neutral and does not inflate the 160-unit total.
- Decide whether human-review branches are:
  - hard-disabled by default; or
  - allowed with an explicit risk penalty and warning.

### Tests

- All Common Curriculum edge cases and branch combinations.
- No course satisfies two incompatible pillars.
- UE does not absorb courses already used exclusively elsewhere.
- Degree totals match normalized credit-bearing attempts.
- Aggregate requirements no longer pass with zero allocated units.
- Solver and evaluator parity for all Common Curriculum constraints.

### Exit Criteria

- Graduation-first optimization covers major plus Common Curriculum totals
  without misleading aggregate passes.

## Pass 8: Internship and Level-1000 Rules

### Goals

- Integrate variable-unit internship combinations and programme caps.

### Work

- Encode:
  - valid internship course combinations;
  - the 10-unit major internship target;
  - UROP/UREx 4-unit major cap;
  - internship overflow to UE;
  - poly-direct-entry APC conditions;
  - CEG-only exclusions;
  - `EG2605`/`CDE2605` aliases;
  - the level-1000 maximum.
- Keep whole-course allocation unless a source rule explicitly permits unit
  splitting.
- Make overflow an optimizer decision only where multiple legal placements
  exist.

### Tests

- Existing internship and level-1000 fixtures.
- Variable-unit courses contribute exact units.
- UROP excess cannot inflate major internship satisfaction.
- Overflow placement is deterministic and audit-valid.
- Exhaustive parity for bounded internship combinations.

### Exit Criteria

- Graduation-first optimization covers all non-specialisation programme areas.

## Pass 9: Explicit Specialisation Selection and Paths

### Goals

- Optimize a requested specialisation without activating accidental partial
  specialisations.

### Work

- Require one of:
  - `--specialisation ID`;
  - a transcript/config activation flag; or
  - explicit `--discover-specialisations`.
- Encode:
  - specialisation selection;
  - exactly one active path where required;
  - core, elective, project, basket, count, and unit requirements;
  - topic-tagged project options;
  - iDP-dependent paths;
  - corrected AE, Industry 4.0, IoT, Robotics, SPT, SET, and MQM structures.
- When discovering specialisations, solve each candidate goal independently
  rather than maximizing the number of implicitly selected partial
  specialisations.
- Report `PASS`, best shortfall, and selected path for each requested scenario.

### Tests

- All existing specialisation and path fixtures.
- No specialisation is selected solely because one transcript course appears
  in its basket.
- Explicit goals choose the correct path.
- Topic and activation flags are enforced.
- Path results match the exhaustive oracle on small cases.

### Exit Criteria

- A user can request an optimal allocation for a named specialisation.
- Default graduation optimization remains free of accidental specialisation
  failures.

## Pass 10: Overlap, Capstone Lock, and Specialisation SEP Rules

### Goals

- Complete the globally coupled specialisation rules.

### Work

- Encode overlap indicators for course instances counted both inside and
  outside a selected specialisation.
- Encode:
  - maximum 8 overlap units;
  - minimum 12 distinct units;
  - residual UE as non-overlap;
  - EE4002D/R capstone lock consuming the overlap budget;
  - no further TE or other overlap after capstone lock;
  - single capstone instance restrictions across specialisations;
  - maximum specialisation SEP units;
  - no SEP course reuse across specialisations;
  - SEP forbidden paths when capstone policy requires it;
  - `CDE4301` versus iDP second-major conflicts;
  - SPT `EG4301` exclusion.
- Link every encoder to the public/internal constraint registry and source ref.

### Tests

- All overlap, capstone, SEP-specialisation, and single-instance cases.
- Boundary tests at 0, 4, 8, and 12 overlap/distinct units.
- Multiple selected-specialisation scenarios.
- Solver/evaluator parity for every globally coupled constraint.
- CP-SAT and exhaustive objective parity on reduced configurations.

### Exit Criteria

- All currently modeled specialisation legality rules are represented in the
  solver.

## Pass 11: Alternatives and Explanations

### Goals

- Show users meaningful choices instead of one opaque optimum.

### Work

- Add `--top-k N` using iterative no-good constraints.
- Distinguish:
  - equivalent optima;
  - alternatives with the same academic shortfall but different flexibility;
  - alternatives optimized for different specialisations.
- Add diversity constraints so top-k results do not differ only in residual UE
  ordering.
- Produce structured explanations:
  - requirement shortfalls;
  - selected and rejected major choice;
  - scarce course assignments;
  - double-count and overlap usage;
  - active path and capstone lock;
  - SEP/human-review risk;
  - objective difference from greedy.
- For each missing requirement, list:
  - missing count/units;
  - transcript courses that were eligible but consumed elsewhere;
  - whether reassignment could satisfy it;
  - whether additional coursework is unavoidable.

### Tests

- No duplicate alternatives.
- Alternatives are ordered by the canonical objective vector.
- Explanations match actual decision variables and audit results.
- Scarcity case explains why the dual-eligible course is assigned to TE.
- Reordered input produces identical alternatives and explanations.

### Exit Criteria

- Users can understand both the selected allocation and its remaining deficits.

## Pass 12: CLI, API, and Contract Finalization

### Goals

- Make optimization a stable public feature without breaking existing
  consumers.

### Work

- Finalize CLI options:

  ```text
  --strategy greedy|cp-sat
  --goal graduation|preserve-flexibility|specialisation
  --specialisation ID
  --include-status completed|in-progress|planned
  --time-limit SECONDS
  --top-k N
  --require-optimal
  --solver-log
  ```

- Consider a dedicated command:

  ```bash
  degree-auditor optimize-allocation ...
  ```

  Keep `plan-allocation --strategy cp-sat` as an alias or compatibility path.

- Extend JSON/YAML output under a new optional `optimization` object:

  ```yaml
  optimization:
    strategy: cp-sat
    status: OPTIMAL
    objective_values: {}
    shortfalls: []
    selected_paths: {}
    alternatives: []
    elapsed_ms: 0
  ```

- Do not change the existing `allocations` row shape.
- Define exit codes for:
  - legal plan written;
  - audit shortfall;
  - invalid input;
  - solver/model error;
  - `--require-optimal` timeout.
- Add Rich text summaries and source-aware explanations.

### Tests

- Backward-compatible JSON/YAML contract tests.
- CLI tests for every solver state and exit code.
- Greedy output remains unchanged when strategy is omitted.
- CP-SAT output round-trips through manual allocation YAML.
- Text, JSON, and YAML outputs describe the same objective and shortfalls.

### Exit Criteria

- The optimizer has a documented, versioned public interface.

## Pass 13: Hardening, Performance, and Default Rollout

### Goals

- Establish confidence for making CP-SAT the default.

### Work

- Add benchmark fixtures representing:
  - typical transcript;
  - all seven specialisations;
  - many SEP mappings;
  - alias-heavy candidate graphs;
  - maximum reasonable planned-course scenario.
- Track:
  - candidate edge count;
  - variable and constraint count;
  - solve time per objective stage;
  - optimality status;
  - memory usage;
  - post-audit mismatch count.
- Add randomized and metamorphic tests:
  - input ordering;
  - irrelevant-course addition;
  - dominated candidate addition;
  - equivalent alias substitution;
  - extra eligible course cannot worsen the optimum;
  - relaxing a rule cannot worsen the objective.
- Run optimizer outputs against every structured and black-box fixture.
- Add diagnostic model export for development, excluding transcript PII by
  default.
- Define controlled fallback behavior:
  - greedy fallback only when explicitly allowed;
  - never hide `MODEL_MISMATCH`;
  - surface `FEASIBLE` versus `OPTIMAL`.
- Update README and remove CP-SAT from Future Work.
- Switch the default strategy only after acceptance criteria are met.

### Acceptance Criteria for Default Switch

- Existing full test suite remains green.
- All applicable black-box cases are active with no optimizer-specific xfails.
- CP-SAT matches the exhaustive oracle on every bounded case.
- Zero solver/evaluator mismatches across the full fixture suite.
- Repeated runs are byte-for-byte deterministic under default settings.
- Typical transcripts are proven optimal within the agreed default time limit.
- Timeout and unavailable-solver behavior are documented and tested.
- Greedy remains explicitly selectable for troubleshooting.

## Rule Encoder Registry

To prevent optimizer/auditor drift, introduce a registry keyed by the existing
constraint or requirement type:

```python
class RuleEncoder(Protocol):
    rule_ids: frozenset[str]

    def add_constraints(
        self,
        problem: AllocationProblem,
        model: CpModel,
        variables: SolverVariables,
    ) -> None: ...
```

Each encoder must declare:

- internal and public rule IDs;
- source refs;
- supported parameter shape;
- generated variable/constraint names;
- evaluator parity fixtures; and
- whether the rule is hard legality, a completion target, or reporting-only.

Unknown rule-bearing config must fail optimizer construction rather than be
silently ignored. Reporting-only rules can be explicitly registered as such.

## Verification Strategy

### Unit Tests

- normalization;
- candidate generation;
- objective scoring;
- individual encoders;
- solution conversion;
- explanation generation.

### Parity Tests

For each rule:

1. construct a bounded transcript and candidate graph;
2. enumerate legal and illegal allocations;
3. compare solver feasibility with the current evaluator;
4. compare final CP-SAT optimum with exhaustive search; and
5. run the chosen allocation through `audit()`.

### Metamorphic Tests

- Reordering courses/config does not change results.
- Adding an irrelevant course does not change non-UE assignments.
- Adding a legal option cannot worsen the objective.
- Removing an option cannot improve the objective.
- Increasing a requirement cannot reduce its reported shortfall.
- Relaxing an overlap/SEP limit cannot worsen the optimum.

### Regression Fixtures

Create synthetic fixtures for:

- dual-eligible TC/TE scarcity;
- both digital-choice alternatives;
- CDE2501 branches;
- internship/UROP combinations;
- each specialisation path;
- capstone lock;
- cross-specialisation overlap;
- SEP approval and residency boundaries;
- repeated/aliased attempts;
- incomplete transcripts with multiple equivalent best allocations.

## Performance and Determinism Defaults

- Use integer coefficients only.
- Give every variable and constraint a stable name.
- Sort courses, requirements, paths, and candidates before model creation.
- Use one search worker in deterministic test/default mode.
- Use a fixed random seed.
- Expose additional workers only as an explicit performance option.
- Apply a final deterministic tie-break so equivalent optima produce stable
  allocation YAML.
- Record solver wall time and proof status, but exclude volatile timing fields
  from deterministic snapshot comparisons.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Solver rules diverge from audit rules | Encoder registry, parity tests, mandatory post-audit |
| Incomplete transcript becomes infeasible | Shortfall variables for completion targets |
| Giant weighted objective behaves unexpectedly | Sequential lexicographic solves |
| Optional specialisations create surprise failures | Explicit selection/discovery modes |
| Public/internal ID collisions distort scoring | Canonical requirement registry and leaf-only objectives |
| Repeated attempts inflate units | Normalize and deduplicate before candidate generation |
| Solver timeout is reported as optimal | Preserve CP-SAT proof status per objective stage |
| Parallel solving changes chosen optimum | Deterministic default settings and final tie-break |
| Top-k results are cosmetic duplicates | Diversity constraints on meaningful assignments |
| OR-Tools increases install size | Record dependency decision and test clean installation |
| Private transcripts enter fixtures/logs | Synthetic fixtures and redacted diagnostic exports |

## Definition of Done

The integration is complete when:

- `plan-allocation` can produce a proven-optimal, audit-valid allocation;
- incomplete transcripts receive an optimal partial allocation and precise
  shortfalls;
- the solver covers all rule families currently enforced by the auditor;
- requested specialisation goals and paths are optimized explicitly;
- top alternatives and explanations are deterministic and accurate;
- every solver result is validated by the existing audit layer;
- bounded cases match the exhaustive oracle;
- all existing and optimizer-specific tests pass;
- normal CLI and contract compatibility is preserved; and
- CP-SAT can safely become the default while greedy remains available.
