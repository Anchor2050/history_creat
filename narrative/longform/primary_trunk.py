"""Concentrated historical trunk after focused replay batch 02.

This is a noncanonical construction target. It combines the two nondominated
histories (022 and 025) while importing only the strongest supporting motifs from
010/032. It is a replay plan, not a mutation of World history.
"""

PRIMARY_TRUNK = {
    "status": "noncanonical_convergence_target",
    "source_worlds": ["world-022", "world-025"],
    "supporting_lenses": {
        "world-010": "Xu Hang: failure logs, verification and responsibility become capital as execution gets cheap.",
        "world-032": "Era form: no single revolution day; the old ladder disappears across ordinary job ads and workflows.",
    },
    "title_candidates": ["第二次毕业", "两种上升", "那些普通的年份"],
    "historical_question": "当执行越来越便宜，什么仍值得一个人用几年人生去换？",
    "acts": [
        {
            "years": "2026",
            "name": "同一张桌子",
            "beats": [
                "Chen and Lin share a small academic world but compete for real time, attention and administrative capacity.",
                "Chen finishes the doctorate under family/cash pressure; Lin pays some indirect cost even when Chen's need is legitimate.",
                "Xu records a failed reproduction while everyone still treats AI mostly as a tool.",
                "No one yet knows which of these small habits will become valuable."
            ],
            "motifs": ["分开", "清单", "同一张桌子", "未复现"]
        },
        {
            "years": "2026-2027",
            "name": "第一次上升",
            "beats": [
                "Chen leaves academia and experiences visible material victory: income, autonomy and organizational access rise.",
                "Lin stays on the slower research route and briefly appears to be losing.",
                "Their friendship absorbs a class-like difference in spending power and time.",
                "AI agents begin to compress routine implementation work."
            ],
            "motifs": ["账单", "赢家", "价格", "招聘启事"]
        },
        {
            "years": "2027-2028",
            "name": "第二次毕业",
            "beats": [
                "The work Chen is finally paid well to do becomes cheaper through agentic workflows.",
                "She chooses retraining in scope, verification, client responsibility and refusal; she misses one promotion cycle.",
                "Lin stops competing on technical virtuosity and moves toward problem choice, evidence boundaries and research autonomy.",
                "Xu's slow failure archive begins to look less like weakness and more like infrastructure."
            ],
            "motifs": ["第二次毕业", "责任", "拒绝", "记录"]
        },
        {
            "years": "2028-2029",
            "name": "责任变贵",
            "beats": [
                "An AI-assisted client failure makes verification and accountable judgment visibly scarce.",
                "Chen becomes valuable for owning failure rather than only producing output.",
                "Lin rejects a prestigious role that would turn her into invisible verification labor and accepts a slower, more autonomous path.",
                "Xu prevents a plausible but non-reproducible result from being submitted, costing the project time."
            ],
            "motifs": ["责任", "未复现", "拒绝", "价格"]
        },
        {
            "years": "2029-2030",
            "name": "两种自由",
            "beats": [
                "Chen gains management power and refuses unpaid trial labor even at real budget cost.",
                "Lin gains the right to decide what she will not claim and what work she will refuse.",
                "The old 'who won?' question returns; the friends stop treating each other's lives as verdicts on their own choices.",
                "They look back at ordinary 2026 job ads and realize that an era had already begun to end."
            ],
            "motifs": ["赢家", "窗口", "招聘启事", "正常的一天"]
        }
    ],
    "truth_constraints": [
        "Every era wave must enter through jobs, prices, tools, institutions or relationships.",
        "No future-wave scenario is narrated as guaranteed history before it happens.",
        "Money, time, permissions, consent and information paths remain Python-authoritative.",
        "No person is rewarded merely for virtue; good conduct must remain costly or uncertain.",
        "Xu's validation arc may not become a magical career guarantee.",
    ],
    "goodness_tests": [
        "Chen refuses unpaid trial work and absorbs a budget consequence.",
        "Lin does not use autonomy as moral superiority over Chen's material ambition.",
        "Chen does not treat income as proof that Lin chose wrongly.",
        "Xu protects others from unverifiable work even when this costs time/status.",
    ],
    "beauty_structure": [
        "Graduation recurs as literal graduation and technological second graduation.",
        "The 2026 scarce window returns later as an opportunity Chen can open but not guarantee.",
        "Failed reproduction returns years later as professional capital.",
        "The question 'who is winning?' returns after its terms have changed.",
        "Era change is recognized retrospectively through ordinary days rather than a single announcement.",
    ],
    "do_not_optimize": [
        "body count",
        "bankruptcy count",
        "betrayal count",
        "number of AI announcements",
        "number of promotions",
        "single happiness/utility score",
    ],
}
