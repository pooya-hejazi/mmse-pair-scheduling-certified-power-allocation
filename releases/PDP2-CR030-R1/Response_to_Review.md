# Response to the supplied deep review

Artifact: PDP2-CR030-R1. Local revision prepared on 2 November 2026.

This response covers all 58 detailed review rows, the eight acceptance groups and all 22 checklist items. The review is valuable, but missing supplementary files in its input must be distinguished from missing proofs: the previous package already contained S1–S14. The new delivery makes the supplement visible as a standalone PDF and adds S15.

No channel generation, optimizer campaign or training was performed for this revision. Stored scientific results and all 3,627 reproduction payloads are unchanged. Bounded analytic checks and saved-data statistical replay are separate validation operations. Pricing still adds no achieved-rate gain over corresponding unpriced search and no main/scale 0.01-nat success. The all-zero original ASU failure and the separate correction/postprocessing deviation remain disclosed.

The article retains the 13-page initial-submission layout; the supplement has 32 pages. The final delivery includes the revised article/source ZIP, supplement/source/code/results ZIP, selected-reference exports and cover letter. Public release and author-controlled submission declarations remain separate. Historical generator VCS/scenario tags, BLAS build and separate HiGHS version were not captured and are not invented; installed-source/input hashes and recorded runtime metadata are supplied.

The initial planning audit failed solely because its read-only boundary was ineffective. The protected second planning attempt passed three reflections; the first failure remains recorded. Scientific/manuscript acceptance is reported separately in the independent final review.

## R01: Abstract grammar

The abstract now uses a complete grammatical statement of fixed-power scheduling hardness. The precise NP-completeness statement first appears after the decision-language definition.

Evidence: abstract.tex, model-analysis.tex, IDEAL-MMSE-PAIR.

## R02: Positive powers

The abstract and introduction specify strictly positive bounded transmit powers.

Evidence: abstract.tex, introduction.tex.

## R03: Seventeen candidates

The abstract states that rectangular pricing requires at most seventeen candidate points; the theorem and supplement distinguish this characterization from precision-dependent certified computation.

Evidence: abstract.tex, model-analysis.tex Theorem3, full-proofs.tex D6–D8.

## R04: Negative empirical result

The abstract explicitly states no achieved-rate improvement over unpriced search and no 0.01-nat target success. The adverse result is unchanged.

Evidence: abstract.tex, evaluation-results.tex.

## R05: Exactly-once service

The introduction now says serving every user exactly once.

Evidence: introduction.tex.

## R06: Article roadmap

A concise roadmap identifies Sections II–VIII and the directly relevant supplementary sections.

Evidence: introduction.tex, final paragraph.

## R07: Supplement availability

The original delivery already included the full supplement. The new folder additionally provides a standalone 32-page Supplementary_Material.pdf, and the ZIP contains that PDF plus every source. Missing material in the review input is distinguished from a missing proof.

Evidence: Supplementary_Material.pdf, Supplementary_Materials.zip/source.

## R08: Transmitted symbols

The signal model explicitly defines the complex Gaussian symbol distribution, unit variance and independence.

Evidence: model-analysis.tex, received signal.

## R09: Whitening wording

The scalar-noise explanation attributes channel division to whitening and excludes reapplication of path loss.

Evidence: model-analysis.tex, received signal.

## R10: Normalized received power

The zero-gain convention now uses normalized received power, distinguishing it from transmitted watts.

Evidence: model-analysis.tex, channel summaries.

## R11: Generic correlation

The generic pair-rate function is introduced with x,y>=0 and r in [0,1].

Evidence: model-analysis.tex, pair log-rate.

## R12: Log-rate units

The generic rate is stated in nats per channel use.

Evidence: model-analysis.tex, pair log-rate.

## R13: Selected pair

The selected pair e_s is defined before the aggregate SE equation.

Evidence: model-analysis.tex, sum-SE definition.

## R14: Aggregate and occupied-band SE

Q and Q/S are distinguished with their units and resource-bandwidth normalization. The supplement also distinguishes stored tones from actually occupied tones.

Evidence: model-analysis.tex, sum-SE definition, revision-details.tex R1.

## R15: Binary domain

The binary domain was already explicit in the sentence introducing z and remains so; it need not be duplicated beneath the constraints.

Evidence: model-analysis.tex, joint continuous problem.

## R16: Continuous measure primal

The main gives the measure-relaxation definition and points to the displayed primal D9, its incidence/moment constraints, Dirac embedding and integrated weak-duality argument.

Evidence: model-analysis.tex, full-proofs.tex D9.

## R17: Formal decision language

IDEAL-MMSE-PAIR is defined before Theorem 1 with the explicit alphabet-index table, unit powers/noise, threshold and malformed-input rejection. Abstract/introduction summarize hardness without an earlier undefined NP-completeness declaration.

Evidence: model-analysis.tex, IDEAL-MMSE-PAIR.

## R18: Bounded-degree 3DM citation

The existing primary source is appropriate: Dyer–Frieze (1985), Sec.2, statement(2.1), printed p.141 gives the exact perfect planar variant with every element in two or three triples. This locator and restriction are now explicit; no unverified replacement citation is inserted.

Evidence: model-analysis.tex Theorem1, full-proofs.tex D1, discovery/astra-theory.md.

## R19: Polynomial NP verification

The schedule certificate, constant local rational-factor size, O(K)-bit product and polynomial comparison with 2^K are stated. No NP-membership claim for unrestricted continuous thresholds is added.

Evidence: model-analysis.tex, Theorem1 proof sketch.

## R20: Alphabet and separation

The existing constructive alphabet and positive constant gaps were already in S1/S11. The finite alphabet is now specified deterministically, the input-size bound is explicit and main pointers identify D1–D3. A long vector enumeration is unnecessary for this fixed algorithmically specified alphabet.

Evidence: technical-supplement.tex A1–A3, full-proofs.tex D1–D3.

## R21: Forest representation reference

The proposed rejection of AIM2008 was not adopted: its Theorem 3.16, p.1639 directly gives the tree-complement antecedent. The main now states that locator and distinguishes the additional rational-unit finite-family construction.

Evidence: model-analysis.tex, after Theorem1, technical-supplement.tex.

## R22: Hessian and sharp boundary

Full Hessian and determinant formulas were already available as D4–D5 and all coefficients in S2. Precise pointers and boundary details were strengthened; new symbolic/finite-point tests below, at and above the threshold pass.

Evidence: full-proofs.tex D4–D5, technical-supplement.tex S2, checks/theory-regression.json.

## R23: Negative definiteness

The statement now gives the explicit finite-point matrix inequality over the nonnegative quadrant.

Evidence: model-analysis.tex Theorem2.

## R24: Pricing polynomial definitions

The proof sketch now points directly to the explicit B,C and Pi formulas in D6–D8.

Evidence: model-analysis.tex Theorem3, full-proofs.tex D6–D8.

## R25: Power-budget collision

The elimination polynomial is renamed Pi throughout main and supplementary proof; P remains the power budget.

Evidence: model-analysis.tex, full-proofs.tex.

## R26: Coordinates and clipping

Coordinates j in {x,y}, their interval/price symbols and clip are explicitly defined.

Evidence: model-analysis.tex Theorem3.

## R27: Validated lower value

L is defined as a rigorously validated feasible lower enclosure before its use in the bound statement.

Evidence: model-analysis.tex Proposition1.

## R28: Fixed-pair gain notation

The example uses gain symbols for the fixed users, avoiding an unexplained indexing convention.

Evidence: model-analysis.tex Proposition1 discussion.

## R29: Both convex terms

g_x and g_y are explicitly defined and their convexity is attributed to those two terms.

Evidence: model-analysis.tex affine majorants.

## R30: Best-bound termination

The suggested unqualified fairness lemma is replaced by a direct finite-epsilon proof with evaluated feasible lower corners, finite assignment roots and longest-edge subdivision. Experimental finite caps and fixed precision remain outside that unrestricted convergence statement.

Evidence: model-analysis.tex Proposition2, full-proofs.tex final convergence subsection.

## R31: Retained upper bound

U is defined as the minimum retained validated global upper bound, including fallback and available complete bounds.

Evidence: model-analysis.tex bound/checker definitions.

## R32: Checker reproducibility

S12 now supplies canonical serialization, exact stored-value reconstruction, the independent 100-bit/40-term log enclosure M5, rejection/deadline behavior and the actual certificates replay command. The finite-candidate oracle remains a separate algorithm.

Evidence: checked-procedures.tex M5, revision/CERTIFICATE_API_AND_TRUST.md.

## R33: DeepMIMO identity and axes

Version 0.2.9, X–Y–Z axis order, full configs, installed-source and input hashes are archived. Historical VCS commit and semantic scenario tags were not recorded; exact hashes replace invented labels, with the limitation explicit.

Evidence: revision-details.tex S15, revision/PROVENANCE.json, GENERATOR_CONFIGS.json.

## R34: Normalization and bandwidth

The actual no_LPF code uses sqrt(path_power/NFFT); sqrt512 removes that path-amplitude factor, not an inferred IFFT convention. The 32 stored tones occupy 3.125 MHz in aggregate, while evaluated 4/8-tone cases occupy 0.390625/0.78125 MHz.

Evidence: revision-details.tex R1, evaluation.tex.

## R35: Case provenance

A 32-case manifest records case IDs, seeds, generator row ranges, selected pool offsets, FFT indices, case/channel/pool hashes. Offsets are not mislabeled as physical row IDs.

Evidence: revision/CASE_MANIFEST.json, GENERATOR_CONFIGS.json.

## R36: Matching–WMMSE details

Already available equations are now numbered M1–M4 and supplemented by Algorithm S1, exact seeds, all starts, assignment scores, bisection/repair, stopping and exchange limits. The retained equation-to-code map identifies implementation functions.

Evidence: checked-procedures.tex, revision/MATCHING_EQUATION_CODE_MAP.md.

## R37: Allowance comparison

The comparator caption explicitly distinguishes 18 s at K=8 from 28 s at K=16 and states equality only within each size.

Evidence: evaluation.tex comparator table.

## R38: Historical environment

The recorded CPU, 20/28 core counts, RAM, OS build, Python/libraries, distribution hashes and single-thread policy are archived. Historical BLAS build and an independently recorded HiGHS version remain explicitly unknown. No current installation is misrepresented as historical evidence.

Evidence: revision-details.tex, revision/PROVENANCE.json.

## R39: Statistical citations

Primary Clopper–Pearson and Efron references and the official NIST general Bonferroni construction are cited at the method introductions.

Evidence: evaluation.tex, references.bib, revision/REFERENCE_ADDITIONS.json.

## R40: Estimand and intervals

The main names the equal-scene discordance estimand; S15 gives R2–R3, endpoint arithmetic, missing-case rules and exact paired-bootstrap seed/draw order. The original inference is unchanged.

Evidence: evaluation.tex, revision-details.tex R2–R3.

## R41: Execution counts

The paper explicitly decomposes 128 executions into 96 main, 24 scale and 8 analytic reliability runs, separate from eight original mechanism cases.

Evidence: evaluation-results.tex, revision-details.tex.

## R42: Receipt versus check

Receipt publication and mathematical reconstruction are distinguished; 417 is a cache-hit count after per-receipt integrity/timing verification, not an unexplained total of checks.

Evidence: evaluation-results.tex, checked-procedures.tex, revision-details.tex.

## R43: Jain attribution

The original 1984 DEC TR-301 source is cited; its 1998 archival posting is distinguished from the report date.

Evidence: evaluation-results.tex, references.bib Jain1984.

## R44: Minimum-user rate evidence

The main wording is narrowed to discussed comparisons, and a supplementary table reports mean minimum-user SE and Jain index for both scenarios and all four main arms.

Evidence: fairness-summary.tex, revision-details.tex.

## R45: Relative-regret meaning

The main explicitly derives (V_C-L)/V_C <= (U-L)/L for L>0, explaining that the plotted percentage is a conservative bound rather than measured loss.

Evidence: evaluation-results.tex, sixteen-user results.

## R46: CSI/GPU evidence

These adverse results were already documented in S5/S6 and remain in the delivered supplement. The discussion preserves them and does not present new acceleration or learned-CSI claims.

Evidence: scope-evidence.tex, supplement S5–S6.

## R47: AI disclosure

The acknowledgment identifies Codex/GPT-6/Astra, the specific main/supplement sections and types of assistance. It does not invent independent human verification or final coauthor approval.

Evidence: acknowledgments.tex, revision/REFERENCE_ADDITIONS.json.

## R48: Artifact identity and public release

PDP2-CR030-R1 has complete scientific-file hashes plus archive/delivery manifests. This supplies a fixed local artifact identity. Public visibility/release verification remains an explicitly separate blocker; no DOI, upload or public-access claim is fabricated.

Evidence: acknowledgments.tex, revision/REPRODUCTION_MANIFEST.json, DELIVERY_MANIFEST.json.

## R49: Physical model example

The AP labels now say evaluated example/M=8; the main retains general receive dimension and identifies the drawing as illustrative geometry.

Evidence: images/system-pairing.pdf/.svg, model-analysis.tex.

## R50: Diagram typography

Both physical diagrams were regenerated as PDF/SVG with a consistent font and 8-point labels in the native 3.25-inch figure, visually checked at article column width. Long labels were split to avoid overlap.

Evidence: draw_system.py, images/system-mmse.pdf/.svg.

## R51: Status figure and names

Figure 3 shows the observed nonzero category with full method names. Its caption explicitly records zero target successes/errors/missing outcomes; no observations are dropped.

Evidence: plot_figures.py, images/fig01-certification.pdf/.svg.

## R52: Target-line annotation

The gap CDF directly labels the 0.01-nat target; marker and line styles are redundant for grayscale.

Evidence: images/fig02-gap-ecdf.pdf/.svg.

## R53: Zero rate differences

Hollow triangles drawn over the zero reference line expose Full–Grid equality without changing vertical values.

Evidence: images/fig03-rate-differences.pdf/.svg.

## R54: Runtime names and definition

Figure 6 uses full method names and parent-process wall-clock wording; the caption states startup/search/check/persistence accounting.

Evidence: images/fig04-charged-duration.pdf/.svg, evaluation-results.tex.

## R55: Floor censoring

Open downward triangles mark sub-floor enclosures; horizontal offsets distinguish coincident cases, with no fabricated zero or altered gap value.

Evidence: images/fig05-curvature-mechanism.pdf/.svg.

## R56: Fairness zoom

The O1 panel magnifies 0.98–1; all observations are asserted within view. The complete supplementary fairness/minimum-rate table preserves the numeric context.

Evidence: images/fig06-fairness.pdf/.svg, fairness-summary.tex.

## R57: Equal scale rates

Open/filled markers and explicitly disclosed small horizontal offsets show Grid/Grid+pricing equality without changing achieved rates.

Evidence: images/fig07-scale-rates.pdf/.svg.

## R58: Scale bar values

Bars carry one-decimal values and distinct hatches; captions explain relative-regret bounds and complete pricing coverage.

Evidence: images/fig08-scale-certificates.pdf/.svg.

## Additional checklist and presentation conventions

The compact notation table is in S15, while essential symbols remain defined at first use in the main. Table I is titled “Comparison with the closest prior work,” with scope limitations in a note. The reference-algorithm summary is retained in Section V; exact Matching–WMMSE pseudocode is Algorithm S1. Main performance plots use Grid, Curvature, Full, Matching–WMMSE and Grid+pricing consistently. Mechanism controls retain the distinct Reference arm because it is a different experiment, not a synonym for Grid. The historical four-AP supplement is explicitly separate and preserves historical method meanings.

The ten current main figures are supplied as vector PDF and SVG, with consistent typography and grayscale-redundant markers, lines or hatches. Horizontal display offsets never change measured rates/gaps. SE summaries use three/four decimals, gap means three decimals and reported confidence limits four decimals; the 0.01-nat SE conversions are rounded to 0.00361/0.00180 bit/s/Hz. Case/config/serialization constants and hashes retain exact digits where reproducibility requires them.

The current IEEE/TCOM author instructions were checked from the official policy page. The applicable initial limit remains 13 pages, two columns, 10-point body and one-inch margins; no 16-page journal-revision allowance is claimed. AI assistance is disclosed by system, section and role. The new acknowledgment deliberately avoids the review's suggested claim that the human authors independently verified every result, because that confirmation has not been supplied.

Existing bibliography entries used in the supplement are retained even when absent from the main. The two author-paper and three closest-external-paper exports remain separate and all five are cited substantively. The corresponding-author identity and cover-letter factual scope are preserved; no submission, message, public upload or payment occurred.
