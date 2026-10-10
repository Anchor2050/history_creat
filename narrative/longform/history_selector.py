"""Select replayed histories by truth, goodness and beauty without one total score.

Truth is structural credibility, goodness is costly agency-respecting conduct,
and beauty is form: recurrence, reversal, compression and earned contrast.
No axis may compensate for a hard truth failure.
"""

AXES = ("truth", "goodness", "beauty")


def assess_history(history):
    events = history.get("events", [])
    if not events:
        raise ValueError("history needs events")
    unsupported = sum(not e.get("causes") and e.get("kind") not in {"external_wave", "initial_condition"} for e in events)
    impossible = sum(bool(e.get("authority_violation")) for e in events)
    cross_actor = sum(len(set(e.get("actors", []))) >= 2 for e in events)
    delayed = sum(e.get("delay_weeks", 0) >= 13 for e in events)
    costly_good = sum(bool(e.get("costly_good")) for e in events)
    autonomy = sum(bool(e.get("respects_agency")) for e in events)
    coerced = sum(bool(e.get("coercive_good")) for e in events)
    motif_returns = len(set(x for e in events for x in e.get("motifs", []) if sum(x in z.get("motifs", []) for z in events) >= 2))
    reversals = sum(bool(e.get("earned_reversal")) for e in events)
    exposition = sum(bool(e.get("trend_as_exposition")) for e in events)
    n = len(events)
    truth = max(0.0, 1.0 - unsupported / n - impossible)
    # Normalize evidence by history length so longer replays cannot win by counting
    # more moral or aesthetic beats. Costly goodness matters more than verbal virtue.
    costly_rate = min(1.0, costly_good / max(1.0, n / 4.0))
    agency_rate = min(1.0, autonomy / max(1.0, n / 2.0))
    goodness = max(0.0, min(1.0,
        .70 * costly_rate + .30 * agency_rate - .45 * coerced / n
    ))
    # Beauty rewards recurring form and earned reversal, with explicit caps.
    motif_rate = min(1.0, motif_returns / 8.0)
    reversal_rate = min(1.0, reversals / 4.0)
    delayed_rate = min(1.0, delayed / 2.0)
    ensemble_rate = min(1.0, cross_actor / 8.0)
    beauty = max(0.0, min(1.0,
        .30 * motif_rate + .30 * reversal_rate
        + .15 * delayed_rate + .25 * ensemble_rate
        - .25 * exposition / n
    ))
    return {"truth":round(truth,3),"goodness":round(goodness,3),"beauty":round(beauty,3),
            "hard_truth_failure": bool(impossible or truth < .72),
            "evidence":{"unsupported":unsupported,"authority_violations":impossible,"cross_actor":cross_actor,"delayed":delayed,"costly_good":costly_good,"agency":autonomy,"coercive_good":coerced,"motif_returns":motif_returns,"earned_reversals":reversals,"trend_exposition":exposition}}


def pareto_histories(histories, limit=6):
    rows=[{"history":h,"assessment":assess_history(h)} for h in histories]
    rows=[r for r in rows if not r["assessment"]["hard_truth_failure"]]
    def dominates(a,b):
        return all(a[k]>=b[k] for k in AXES) and any(a[k]>b[k] for k in AXES)
    front=[r for r in rows if not any(o is not r and dominates(o["assessment"],r["assessment"]) for o in rows)]
    front.sort(key=lambda r:(-r["assessment"]["truth"],-r["assessment"]["goodness"],-r["assessment"]["beauty"],r["history"].get("world_id","")))
    return front[:limit]


def extract_history_line(history):
    """Compress an accepted history to causal beats, not prose chapters."""
    return {"world_id":history.get("world_id"),"title":history.get("title"),"premise":history.get("premise"),
            "beats":[{"date":e.get("date"),"kind":e.get("kind"),"actors":e.get("actors",[]),"change":e.get("change"),"causes":e.get("causes",[]),"era":e.get("era",[])} for e in history.get("events",[]) if e.get("keep",True)],
            "unresolved":history.get("unresolved",[])}
