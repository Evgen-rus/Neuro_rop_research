# R01 decision-gate fact aggregation prototype

`gate_records()` accepts adjudicated E05 YES events with an explicit `gate_id`, and stores the latest non-null `customer_role`, `decision_action`, and `checkpoint` for that gate, with source event IDs. Events without a reliable gate link remain `unresolved`. The event classifier supplies facts, not a latest whole-deal gate or a count of unresolved gates.

The current E05 agreement is high for the binary event label, while NO coverage and literal agreement for decision action/checkpoint are inadequate for a stable gate-state output. Gate identity, field normalization, conflict handling and temporal ordering require a separate validated contract before Jev use.
