# Topology compatibility and curriculum v2 — we-the-people-omega-layer-a

Version 2 adapts the explicit-molecular-graph teaching pattern to this repository's actual role. This is documentation and a learning/decision framework; it introduces no mathematical engine, runtime dependency or operational permission.

## Repository decision

| Question | Repository-specific answer |
| --- | --- |
| Architectural role | application research |
| Minimum useful mathematics | Typed institutional dependency and event graphs |
| Relationships to preserve | Authority references, workflow stages, scenarios and review records |
| Concrete operation / capstone | Trace one fictional scenario through its declared stages and identify which evidence supports each transition |
| Necessity and scope boundary | Institutional diagrams do not establish legal authority or validated public outcomes |

The decision is a source-based recommendation, not measured proof that a new specialty improves this repository. Start with the existing implementation and compare any proposed abstraction against a simpler alternative.

## Six-criterion compatibility scorecard

Complete one scorecard per proposed candidate and per concrete operation. Leave unmeasured entries unknown. Scores are human judgments from 0 (no fit) to 5 (strong evidenced fit); unknown is not zero. Do not sum an incomplete card. A total out of 30 is a heuristic, not adoption approval, and feasibility or necessity can veto a high total.

| Criterion | Score | Required evidence |
| --- | --- | --- |
| Structural compatibility | Not yet scored | Map the repository objects and the relationships above without losing direction, labels, units or missingness. |
| Transformation support | Not yet scored | Demonstrate the capstone operation on accepted and rejected inputs. |
| Invariant preservation | Not yet scored | State the property preserved and supply a counterexample or perturbation. |
| Computational feasibility | Not yet scored | Measure size, time and memory on bounded fixtures; record limits. |
| Integration compatibility | Not yet scored | Verify existing schemas, APIs and neighboring contracts remain compatible. |
| Mathematical necessity | Not yet scored | Compare with typed institutional dependency and event graphs and explain the additional capability, if any. |

## Curriculum

Prerequisites: basic programming, sets, functions and graph vocabulary. Work in six competency-gated sessions, approximately 60–90 minutes each; empirical evaluation is a separate research activity.

| Session | Learning objective | Exercise | Completion evidence |
| --- | --- | --- | --- |
| 1. Model | Identify authority references, workflow stages, scenarios and review records. | Draw a minimal valid example and one excluded relationship. | Annotated object/relation inventory with explicit assumptions. |
| 2. Contract | Distinguish schema validity from substantive correctness. | Trace validation and propose malformed, missing and boundary inputs. | Input-to-rejection table grounded in current source. |
| 3. Operation | Explain typed institutional dependency and event graphs. | Trace one fictional scenario through its declared stages and identify which evidence supports each transition. | Hand trace compared with existing software, or a clearly labeled specification when no runtime exists. |
| 4. Preservation | State what a transformation must preserve. | Rename identifiers, reorder records, then alter one meaningful relation; predict each effect under the actual contract. | Separate invariant, expected change and unsupported transformation. |
| 5. Comparison | Justify mathematical necessity and cost. | Complete the six-criterion card for the existing approach and one proposed alternative; record unknowns honestly. | Evidence-backed recommendation with baseline and explicit veto conditions. |
| 6. Reproduction | Communicate the bounded result. | Reproduce the capstone using existing offline fixtures and record software version, inputs, outputs and limitations. | Reviewable notebook or report distinguishing computation, replay, independent evaluation and authorization. |

## Source-linked reading laboratory

The table is a guided selection of source lines, not an assertion that the whole repository is covered. Line numbers refer to the inspected source blob `e454ed2545e9ceaa11c3f4d127c35c477670ff68` in [layer-b/civic_portfolio/__main__.py](../../layer-b/civic_portfolio/__main__.py). Recheck anchors after source changes.

| Line | Statement | Learning check |
| --- | --- | --- |
| [32](../../layer-b/civic_portfolio/__main__.py#L32) | `def strict_json(raw):` | State the input/output contract and trace one normal and one failing case. |
| [33](../../layer-b/civic_portfolio/__main__.py#L33) | `def pairs(items):` | State the input/output contract and trace one normal and one failing case. |
| [37](../../layer-b/civic_portfolio/__main__.py#L37) | `raise ValueError('duplicate JSON key')` | Construct the triggering input and explain why rejection preserves the contract. |
| [39](../../layer-b/civic_portfolio/__main__.py#L39) | `return result` | Predict the returned value and distinguish a computed result from authorization. |
| [41](../../layer-b/civic_portfolio/__main__.py#L41) | `def reject(value):` | State the input/output contract and trace one normal and one failing case. |
| [42](../../layer-b/civic_portfolio/__main__.py#L42) | `raise ValueError('nonfinite JSON constant')` | Construct the triggering input and explain why rejection preserves the contract. |
| [43](../../layer-b/civic_portfolio/__main__.py#L43) | `return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)` | Predict the returned value and distinguish a computed result from authorization. |
| [46](../../layer-b/civic_portfolio/__main__.py#L46) | `def server(store, port=8765):` | State the input/output contract and trace one normal and one failing case. |
| [65](../../layer-b/civic_portfolio/__main__.py#L65) | `class Handler(BaseHTTPRequestHandler):` | State the input/output contract and trace one normal and one failing case. |
| [66](../../layer-b/civic_portfolio/__main__.py#L66) | `def log_message(self, *_):` | State the input/output contract and trace one normal and one failing case. |
| [69](../../layer-b/civic_portfolio/__main__.py#L69) | `def send(self, status, body, kind='application/json; charset=utf-8',download_name=None):` | State the input/output contract and trace one normal and one failing case. |
| [81](../../layer-b/civic_portfolio/__main__.py#L81) | `def dispatch(self, mutation=False):` | State the input/output contract and trace one normal and one failing case. |
| [96](../../layer-b/civic_portfolio/__main__.py#L96) | `raise ValueError('request body is empty or too large')` | Construct the triggering input and explain why rejection preserves the contract. |
| [99](../../layer-b/civic_portfolio/__main__.py#L99) | `raise ValueError('request must be an object')` | Construct the triggering input and explain why rejection preserves the contract. |
| [213](../../layer-b/civic_portfolio/__main__.py#L213) | `if set(data)!={'actor'} or not isinstance(data.get('actor'),str) or not data['actor'].strip() or len(data['actor'])>200:raise ValueError('actor required, at most 200 characters')` | Construct the triggering input and explain why rejection preserves the contract. |
| [223](../../layer-b/civic_portfolio/__main__.py#L223) | `if set(data)!={'actor'}:raise ValueError('actor required')` | Construct the triggering input and explain why rejection preserves the contract. |
| [381](../../layer-b/civic_portfolio/__main__.py#L381) | `def do_GET(self):` | State the input/output contract and trace one normal and one failing case. |
| [384](../../layer-b/civic_portfolio/__main__.py#L384) | `def do_POST(self):` | State the input/output contract and trace one normal and one failing case. |
| [387](../../layer-b/civic_portfolio/__main__.py#L387) | `return ThreadingHTTPServer(('127.0.0.1', port), Handler)` | Predict the returned value and distinguish a computed result from authorization. |
| [390](../../layer-b/civic_portfolio/__main__.py#L390) | `def main(argv=None):` | State the input/output contract and trace one normal and one failing case. |
| [430](../../layer-b/civic_portfolio/__main__.py#L430) | `if args.output.exists():raise ValueError('output exists; refusing to overwrite')` | Construct the triggering input and explain why rejection preserves the contract. |
| [434](../../layer-b/civic_portfolio/__main__.py#L434) | `if not sep or not seq.isdigit():raise ValueError('snapshot must be SYN-RUN:sequence')` | Construct the triggering input and explain why rejection preserves the contract. |
| [449](../../layer-b/civic_portfolio/__main__.py#L449) | `raise ValueError('source file is too large')` | Construct the triggering input and explain why rejection preserves the contract. |
| [464](../../layer-b/civic_portfolio/__main__.py#L464) | `return 1` | Predict the returned value and distinguish a computed result from authorization. |
## Assessment and verification

A learner must explain the model, trace the capstone, identify a counterexample and state the scope boundary. Assess these four competencies equally; a numerical score cannot compensate for an unsupported scientific or operational claim.

Relevant existing checks:

- [tests/test_benefits_pilot.py](../../tests/test_benefits_pilot.py)
- [tests/test_cross_layer_exchange.py](../../tests/test_cross_layer_exchange.py)
- [tests/test_review_validation.py](../../tests/test_review_validation.py)

Follow [README](../../README.md) for environment and installed-package instructions. Read scripts before execution; source-reading exercises do not authorize provider calls, model downloads, live orders, hardware actions or messages. Synthetic fixtures establish software behavior only. This documentation change does not report those exercises as already executed.

## Interoperability and adoption gate

Retain explicit domain contracts. Shared assurance records should refer to domain evidence and its assumptions rather than relabeling graph reachability, homology, statistical calibration and epistemic acceptance as interchangeable quantities. The canonical ResearchOs controller remains owned by ResearchOs; this curriculum does not create another controller fork.

Adopt additional mathematics only after a versioned experiment demonstrates a useful operation, the scorecard has evidence, the simpler baseline is inadequate and existing conformance checks remain satisfied. Institutional diagrams do not establish legal authority or validated public outcomes.
