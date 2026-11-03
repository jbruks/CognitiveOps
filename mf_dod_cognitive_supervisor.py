"""Event-triggered GPT L3/L4 mission supervisor; NO physical control imports.

Handles persistent navigation uncertainty only. L3 may HOLD or request L4
replanning. L4 may reorder ONLY remaining human-approved GPS targets.
"""
class CognitiveSupervisor:
    def __init__(self, service, intent, hold_threshold=3, max_replans=1):
        if hold_threshold < 1 or max_replans < 0:
            raise ValueError("Invalid thresholds")
        self.service=service
        self.intent=intent
        self.hold_threshold=hold_threshold
        self.max_replans=max_replans
        self.blocked_id=None
        self.blocked_count=0
        self.replans=0

    def reset(self):
        self.blocked_id=None
        self.blocked_count=0

    def review(self, current, remaining, navigation, tactical):
        """Return (decision, reordered_remaining, trace).

        CONTINUE: no change. HOLD: halt mission. REPLAN: skip current target
        and continue only with the previously approved remaining destinations.
        This method must run after the physical cycle's STOP, not during motion.
        """
        remaining=list(remaining)
        if (navigation.get("status")=="OBSERVING_MANUAL_MOTION"
                and tactical.get("action") not in ("HOLD","STOP")):
            self.reset()
            return "CONTINUE",remaining,[]
        if self.blocked_id!=current.objective_id:
            self.blocked_id=current.objective_id
            self.blocked_count=0
        self.blocked_count+=1
        if self.blocked_count<self.hold_threshold:
            return "CONTINUE",remaining,[]

        self.reset()
        context={"mission":self.intent,
                 "current":{"id":current.objective_id,"purpose":current.purpose,
                            "latitude":current.latitude,"longitude":current.longitude},
                 "navigation":navigation,"tactical":tactical,
                 "remaining_approved_ids":[x.objective_id for x in remaining]}
        l3=self.service.infer("L3",
            "Persistent difficulty reported. Choose HOLD or REQUEST_L4_REPLAN. "
            "No motor instructions, coordinates, or claims of reachability.",
            context,("HOLD","REQUEST_L4_REPLAN"))
        decision=l3.output["decision"]
        events=[{"event":"L3_REVIEW","objective_id":current.objective_id,
                 "decision":decision,"reason":l3.output["reason"],
                 "request_id":l3.request_id,"model":l3.model,"provider":l3.provider}]
        if decision=="HOLD":
            return "HOLD",remaining,events
        if self.replans>=self.max_replans or not remaining:
            events.append({"event":"REPLAN_NOT_POSSIBLE","reason":"LIMIT_OR_NO_REMAINING_TARGETS"})
            return "HOLD",remaining,events
        l4=self.service.plan_objectives(self.intent,
            [{"objective_id":x.objective_id,"purpose":x.purpose} for x in remaining],
            context={"blocked_objective":current.objective_id,
                     "blocked_reason":l3.output["reason"],
                     "approved_targets_only":True})
        order=l4.output["objective_ids"]
        expected={x.objective_id for x in remaining}
        if (not isinstance(order,list) or len(order)!=len(remaining)
                or len(set(order))!=len(order) or set(order)!=expected):
            raise ValueError("L4 tried to change approved destination set")
        by_id={x.objective_id:x for x in remaining}
        self.replans+=1
        events.append({"event":"L4_REPLAN","excluded_objective":current.objective_id,
                       "order":order,"reason":l4.output["reason"],
                       "request_id":l4.request_id,"model":l4.model,"provider":l4.provider})
        return "REPLAN",[by_id[x] for x in order],events
