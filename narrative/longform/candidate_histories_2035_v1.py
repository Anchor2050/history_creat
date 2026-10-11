"""Competing concrete histories generated from the frozen 2030-2035 trunk.

This module does not reopen the trunk and does not choose a single literary winner.
It creates auditable branch histories and keeps truth, goodness and beauty separate.
"""
from copy import deepcopy

from .trunk_replay_2035_pass_01 import REPLAY_2030_2035


def _replace(history, event_id, replacement):
    out = []
    for event in history:
        out.append(deepcopy(replacement) if event["id"] == event_id else deepcopy(event))
    return out


def _drop(history, *event_ids):
    dropped = set(event_ids)
    return [deepcopy(e) for e in history if e["id"] not in dropped]


def _append(history, *events):
    out = [deepcopy(e) for e in history]
    out.extend(deepcopy(e) for e in events)
    out.sort(key=lambda e: (e["date"], e["id"]))
    return out


def _world(world_id, premise, history, review, attack):
    return {
        "world_id": world_id,
        "premise": premise,
        "history": history,
        "review": review,
        "attack": attack,
        "status": "candidate_noncanonical",
    }


def candidate_worlds():
    base = deepcopy(REPLAY_2030_2035)

    # W1: preserve the first replay only as a reference world. It is no longer privileged.
    w1 = _world(
        "w1_reference_pressure",
        "Care binds Chen, Lin leaves an option unused, Xu receives late recognition.",
        base,
        {"truth": 4, "goodness": 4, "beauty": 4, "closure_risk": 2, "shock_dependence": 2},
        "Reference only; several events were already demoted from universal claims.",
    )

    # W2: Lin actually exercises mobility. The move is useful but carries bundle losses.
    h = _replace(base, "h36", {
        "id": "h36", "date": "2032-03-18", "actor": "lin_jing", "kind": "mobility",
        "choice": "申请并接受外地跨机构岗位，先租住一年，不出售北京关系网络",
        "cost": {"lin_jing": "失去部分熟人协作、福利连续性和照护可达性；搬迁成本上升"},
        "causes": ["h31"], "memory_add": ["mobility_exercised_bundle_loss"],
    })
    h = _replace(h, "h37", {
        "id": "h37", "date": "2032-08-27", "actor": "lin_jing", "kind": "relationship",
        "choice": "新城市工作更自由，却在母亲住院时发现跨城照护比预想昂贵，向陈岚隐瞒后悔",
        "cost": {"lin_jing": "自主增加但照护与关系协调恶化", "relationship": "与母亲的争执增加"},
        "causes": ["r06", "r07", "h36"], "memory_add": ["mobility_is_bundle_exchange"],
    })
    h = _replace(h, "h38", {
        "id": "h38", "date": "2032-12-09", "actor": "lin_jing", "kind": "repair",
        "choice": "承认迁移确实买到工作拒绝权，也同时卖掉了近距离照护和一部分关系资本",
        "cost": {"lin_jing": "无法再把迁移叙述成单纯胜利"},
        "causes": ["h37"], "memory_add": ["freedom_has_bundle_price"],
    })
    w2 = _world(
        "w2_mobility_exercised",
        "Lin uses the option instead of losing it; mobility succeeds partially and reprices care.",
        h,
        {"truth": 4, "goodness": 4, "beauty": 5, "closure_risk": 1, "shock_dependence": 1},
        "Attacks the flattering claim that unused optionality was the only credible Lin path.",
    )

    # W3: better formal care weakens Chen's squeeze. Good policy changes plot without erasing tradeoffs.
    h = _replace(base, "h33", {
        "id": "h33", "date": "2031-02-14", "actor": "chen_lan", "kind": "care",
        "choice": "父亲手术后通过更成熟的长期照护服务减少亲自往返，只承担关键协调",
        "cost": {"chen_lan": "现金支出增加，紧急协调仍不可外包"},
        "causes": ["h32"], "memory_add": ["formal_care_recovers_average_time_not_robustness"],
    })
    h = _replace(h, "h42", {
        "id": "h42", "date": "2034-07-26", "actor": "chen_lan", "kind": "career",
        "choice": "接受跨城晋升，但要求两地办公并预留照护应急日",
        "cost": {"chen_lan": "通勤和管理负担显著增加", "organization": "承担弹性安排成本"},
        "causes": ["h33"], "memory_add": ["care_policy_changes_conversion_rate"],
    })
    w3 = _world(
        "w3_care_relief",
        "Care institutions improve enough to change Chen's exact life path.",
        h,
        {"truth": 5, "goodness": 5, "beauty": 3, "closure_risk": 2, "shock_dependence": 1},
        "Tests whether the trunk survives a materially kinder institutional future.",
    )

    # W4: recognition reaches Xu during a period of low capacity.
    h = _replace(base, "h44", {
        "id": "h44", "date": "2035-03-21", "actor": "xu_hang", "kind": "recognition_mismatch",
        "choice": "职业标准开始采用他的失败档案，但他因长期失眠和焦虑减少公开工作与晋升申请",
        "cost": {"xu_hang": "社会用途上升时个人收入和地位转换反而变慢"},
        "causes": ["h35", "h41"], "memory_add": ["recognition_arrives_during_low_capacity"],
    })
    h = _replace(h, "h46", {
        "id": "h46", "date": "2035-12-06", "actor": "ensemble", "kind": "ordinary",
        "choice": "陈岚在培训会上引用许航的档案，林静会后才发现许航没有到场",
        "cost": {"ensemble": "承认公共价值可以脱离创作者当下的私人繁荣"},
        "causes": ["h40", "h44", "h45"], "memory_add": ["usefulness_can_outlive_capacity_to_claim_it"],
    })
    w4 = _world(
        "w4_recognition_incapacity",
        "Xu becomes institutionally useful at the same time he is least able to capitalize on recognition.",
        h,
        {"truth": 4, "goodness": 4, "beauty": 5, "closure_risk": 1, "shock_dependence": 1},
        "Direct attack on delayed-merit payoff and on recognition as narrative compensation.",
    )

    # W5: Xu's refusal does lasting relational damage; there is no quick moral reconciliation.
    h = _replace(base, "h39", {
        "id": "h39", "date": "2033-05-12", "actor": "xu_hang", "kind": "cross_actor",
        "choice": "拒绝为林静项目签署无法复核的数据来源声明，并拒绝私下给她一个模糊的口头背书",
        "cost": {"lin_jing": "项目延期并失去合作窗口", "xu_hang": "两人的私人关系中断"},
        "causes": ["r15", "h35", "h38"], "memory_add": ["integrity_can_break_relationship"],
    })
    h = _replace(h, "h40", {
        "id": "h40", "date": "2033-09-01", "actor": "lin_jing", "kind": "earned_change",
        "choice": "独自把项目缩到可验证范围，却不再把新标准归功于许航",
        "cost": {"lin_jing": "论文影响力下降且友情没有修复"},
        "causes": ["h39"], "memory_add": ["good_rule_survives_without_reconciliation"],
    })
    h = _replace(h, "h46", {
        "id": "h46", "date": "2035-12-06", "actor": "ensemble", "kind": "nonmeeting",
        "choice": "三人本应参加同一场活动，林静提前离场，许航晚到，陈岚分别见了他们",
        "cost": {"ensemble": "共同历史存在，但关系没有被故事强行修复"},
        "causes": ["h40", "h44", "h45"], "memory_add": ["shared_history_without_reunion"],
    })
    w5 = _world(
        "w5_friendship_rupture",
        "A defensible refusal permanently damages a friendship while the evidentiary standard survives.",
        h,
        {"truth": 4, "goodness": 3, "beauty": 5, "closure_risk": 1, "shock_dependence": 1},
        "Attacks the temptation to make moral correctness heal relationships automatically.",
    )

    # W6: Chen's paid-training project fails completely for several years.
    h = _replace(base, "h34", {
        "id": "h34", "date": "2031-06-20", "actor": "chen_lan", "kind": "failed_good",
        "choice": "预算收紧后带薪训练名额全部取消，陈岚没有保住项目",
        "cost": {"applicants": "已有候选人失去机会", "chen_lan": "此前承诺伤害个人信誉"},
        "causes": ["h32", "h33"], "memory_add": ["good_institution_can_die"],
    })
    h = _replace(h, "h41", {
        "id": "h41", "date": "2034-01-19", "actor": "chen_lan", "kind": "institutional_echo",
        "choice": "三年后重建更小的训练项目，第一课先讲当年项目如何失败和谁承担了代价",
        "cost": {"organization": "规模远小于最初设想", "chen_lan": "承认自己当年的承诺无法兑现"},
        "causes": ["r17", "h34", "h35"], "memory_add": ["dead_good_project_becomes_training_memory"],
    })
    w6 = _world(
        "w6_training_collapse",
        "Chen's good institution dies, then only part of its memory returns.",
        h,
        {"truth": 5, "goodness": 3, "beauty": 4, "closure_risk": 1, "shock_dependence": 1},
        "Attacks the soft version in which goodness always preserves a seed of institutional continuity.",
    )

    # W7: a correlated climate-care interruption tests coordination robustness.
    h = _append(base, {
        "id": "h42a", "date": "2034-07-18", "actor": "chen_lan", "kind": "correlated_shock",
        "choice": "父亲突发复诊需求时连续高温与交通故障打乱原有照护排班",
        "cost": {"chen_lan": "临时请假、加价出行并取消重要会议", "family": "备用照护同时失效"},
        "causes": ["h33"], "memory_add": ["coordination_robustness_matters_under_correlated_failure"],
    })
    h = _replace(h, "h42", {
        "id": "h42", "date": "2034-07-26", "actor": "chen_lan", "kind": "care",
        "choice": "在冲击后一周拒绝跨城晋升，因为她不再相信原有照护安排能承受相关性故障",
        "cost": {"chen_lan": "失去职位与收入", "organization": "失去熟悉团队的管理者"},
        "causes": ["h33", "h42a"], "memory_add": ["care_caps_mobility_after_coordination_failure"],
    })
    w7 = _world(
        "w7_climate_care_shock",
        "A short correlated infrastructure-care failure changes a career decision without becoming apocalypse.",
        h,
        {"truth": 4, "goodness": 4, "beauty": 5, "closure_risk": 2, "shock_dependence": 4},
        "Useful stress test but must not be selected merely because a shock produces drama.",
    )

    # W8: no spectacular shock; the era is felt through attrition and ordinary delays.
    h = _drop(base, "h42", "h43", "h44", "h46")
    h = _append(h,
        {
            "id": "h42q", "date": "2034-07-26", "actor": "chen_lan", "kind": "ordinary",
            "choice": "没有出现决定性晋升机会；她只是连续第三年把年假拆成零碎照护日",
            "cost": {"chen_lan": "长期无法获得完整休息，也没有一个可指认的重大牺牲时刻"},
            "causes": ["h33"], "memory_add": ["care_erosion_without_climax"],
        },
        {
            "id": "h43q", "date": "2034-11-15", "actor": "lin_jing", "kind": "ordinary",
            "choice": "林静又续了一次租约，发现自己已经两年没有认真查看外地岗位",
            "cost": {"lin_jing": "选择权没有突然消失，只是逐渐变得陌生"},
            "causes": ["h38"], "memory_add": ["option_decay_without_decisive_failure"],
        },
        {
            "id": "h44q", "date": "2035-03-21", "actor": "xu_hang", "kind": "ordinary",
            "choice": "一个培训手册匿名采用了他的验证清单，没有带来职级变化",
            "cost": {"xu_hang": "社会用途增加但本人甚至不知道传播范围"},
            "causes": ["h35", "h41"], "memory_add": ["recognition_can_be_diffuse_and_ownerless"],
        },
        {
            "id": "h46q", "date": "2035-12-06", "actor": "ensemble", "kind": "ordinary",
            "choice": "三人各自在一个普通工作日结束后回家，没有人意识到这一年构成了任何历史节点",
            "cost": {}, "causes": ["h40", "h42q", "h43q", "h44q"],
            "memory_add": ["history_can_accumulate_without_scene_of_recognition"],
        },
    )
    w8 = _world(
        "w8_quiet_erosion",
        "Nothing spectacular happens; options, health, care and recognition change by attrition.",
        h,
        {"truth": 5, "goodness": 4, "beauty": 5, "closure_risk": 0, "shock_dependence": 0},
        "Control against catastrophe bias and against the belief that history must announce itself as plot.",
    )

    return [w1, w2, w3, w4, w5, w6, w7, w8]


def hard_gates(world):
    history = world["history"]
    ids = {e["id"] for e in history}
    chronological = history == sorted(history, key=lambda e: (e["date"], e["id"]))
    causes_exist = all(cause in ids or cause.startswith("r") for e in history for cause in e.get("causes", []))
    costs_are_explicit = all("cost" in e for e in history)
    no_final_settlement = not any(e.get("kind") in {"triumph", "final_victory", "moral_reward"} for e in history)
    return {
        "chronological": chronological,
        "causes_exist": causes_exist,
        "resource_accounting_present": costs_are_explicit,
        "no_final_settlement": no_final_settlement,
    }


def survives(world):
    return all(hard_gates(world).values())


def pareto_frontier(worlds):
    """Return nondominated candidates without creating a scalar literary score.

    Higher truth/goodness/beauty are preferred; lower closure risk and shock dependence
    are preferred. This intentionally permits several incompatible winners.
    """
    survivors = [w for w in worlds if survives(w)]

    def dominates(a, b):
        ar, br = a["review"], b["review"]
        better_or_equal = (
            ar["truth"] >= br["truth"] and
            ar["goodness"] >= br["goodness"] and
            ar["beauty"] >= br["beauty"] and
            ar["closure_risk"] <= br["closure_risk"] and
            ar["shock_dependence"] <= br["shock_dependence"]
        )
        strictly_better = (
            ar["truth"] > br["truth"] or
            ar["goodness"] > br["goodness"] or
            ar["beauty"] > br["beauty"] or
            ar["closure_risk"] < br["closure_risk"] or
            ar["shock_dependence"] < br["shock_dependence"]
        )
        return better_or_equal and strictly_better

    return [w for w in survivors if not any(dominates(other, w) for other in survivors if other is not w)]


def deep_replay_shortlist():
    worlds = candidate_worlds()
    # Deliberately include structural diversity rather than simply taking every frontier member.
    wanted = {
        "w2_mobility_exercised",
        "w4_recognition_incapacity",
        "w5_friendship_rupture",
        "w8_quiet_erosion",
    }
    return [w for w in worlds if w["world_id"] in wanted and survives(w)]
