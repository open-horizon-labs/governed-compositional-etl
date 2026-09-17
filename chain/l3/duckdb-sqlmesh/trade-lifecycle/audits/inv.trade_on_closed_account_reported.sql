AUDIT (name "inv.trade_on_closed_account_reported", blocking false);

-- L1.closed-account-activity: a trade placed on an account after that account's closing
-- statement is recorded like any other and reported for review, because either the closure or
-- the trade is wrong and only the brokerage can say which. This invariant reports every trade
-- whose pinned account statement -- named by its frozen owning_account_number and
-- owning_account_effective_from, the statement in effect at placed_at -- carries status INAC
-- (the anchored code; on an account statement it means closed, not the customer-side
-- "inactive"). The trade's attribution is unchanged by this report: this audit only reads and
-- names the pinned statement's own status back to the business; it does not drop, re-pin, or
-- unwind anything. Non-blocking: a fired row here is a finding for the business, not a
-- projection defect, so it must not refuse the plan.
SELECT
  m.trade_number,
  m.owning_account_number,
  m.owning_account_effective_from
FROM @this_model AS m
JOIN governed.account AS a
  ON a.account_number = m.owning_account_number
 AND a.effective_from = m.owning_account_effective_from
WHERE a.status = 'INAC';
