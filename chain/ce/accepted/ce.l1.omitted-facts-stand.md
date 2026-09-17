### CE: ce.l1.omitted-facts-stand

- Status: approved (assumed; pending business confirmation). Promoted after the cycle-6 reviewer found the policy sentence living in anchors.
- Level: L1, observed at L3 simulation of ownership-history on duckdb-native
- Input and simulation context: fixture rows for customer 238 (INACT 2008-03-23 carries no tier) and account 428 (CLOSEACCT 2012-11-15 carries no tax status).
- Projection output: statements with null tier and null tax treatment.
- Corrected output or behavior: the omitted facts stand as last stated on the previous statement of the same thing.
- Classification: ambiguous sketch rule. L1.identity and L1.history entail it by the reading the reviewer accepted for the owner; Jev split 0.46/0.48 between L1 gap and L3 defect, confidence 0.23.
- Proposed generalized sketch change: add to L1.history or as `L1.omitted-facts-stand`: "A change that does not mention a standing fact leaves that fact as it last stood."
- Adjacent behavior not authorized: what a deletion means (L1.hole.deletions); whether an incremental change file's row versions at the batch date (L1.hole.change-effective-time).
- Tempting wrong repair: filling the null from the source's field defaults, or dropping INACT and CLOSEACCT statements because they carry no detail.
- Deterministic assertion: gate rule on `fields_present` (added); audits `*_statement_has_content` (existing).
- Proposed by: coordinator, after the L3 Developer's filed question.
- Approved or rejected by: data-product-owner hat under the review-trigger protocol; recorded in `.oh/metis/issue-8-statement-content-assumed.md`. Business confirmation pending.
- Sketch revision reference: `L1.omitted-facts-stand` added 2026-09-17, listed for job ownership-history.
- Projection revision reference: ownership-history cycle 7.
