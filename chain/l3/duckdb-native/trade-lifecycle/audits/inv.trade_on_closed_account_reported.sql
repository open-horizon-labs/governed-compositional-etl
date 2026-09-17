-- inv.trade_on_closed_account_reported (reports: true, per
-- L1.closed-account-activity): for any trade_number, if the account
-- statement its frozen owning_account_number and owning_account_effective_
-- from pin carries logical.account.status equal to the anchored code INAC
-- (closed, not the customer-side "inactive"), this is reported as a
-- finding for the business, not a projection defect: L1.closed-account-
-- activity says a trade placed on an account after its closing statement
-- is recorded like any other and reported for review, because either the
-- closure or the trade is wrong and only the brokerage can say which. The
-- trade's attribution is read exactly as pinned and is not re-derived,
-- re-pinned, or unwound here. A trade whose pinned statement carries no
-- status at all (an absent input) is not reported by this invariant and
-- does not evaluate to true by default; that silence is a separate
-- question this invariant does not raise. These rows are findings the
-- chain hands the business; the harness counts them as reported, not as
-- violations, and making this audit return nothing to keep a run quiet
-- would itself be the defect.

SELECT
    t.trade_number,
    t.owning_account_number,
    t.owning_account_effective_from,
    a.status AS pinned_account_status
FROM governed.trade AS t
JOIN governed.account AS a
  ON a.account_number = t.owning_account_number
 AND a.effective_from = t.owning_account_effective_from
WHERE a.status = 'INAC';
