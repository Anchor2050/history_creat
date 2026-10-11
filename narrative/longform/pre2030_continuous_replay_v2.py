"""Continuous lived-history repair for 2026-01 through 2030-01.

This file does not replace TRUNK_REPLAY_PASS_01. It keeps the original r01-r18
spine and inserts connective events needed to earn the 2030 state carried into
the frozen 2030-2035 trunk.

All added events are non-prophetic: actors know only current leases, cash,
benefits, family routines, work offers and relationships. Ordinary events are
allowed to matter without becoming set pieces.
"""

CONNECTIVE_2026_2030 = [
    {
        "id": "p01", "date": "2026-08-28", "actor": "chen_lan", "kind": "money_family",
        "choice": "拿到稳定工资后先补自己的现金缓冲，并开始固定承担一小部分家庭日常支出，而没有立刻升级住房",
        "known_now": ["工资比学生期稳定", "家庭过去偶有转账支持", "新工作仍在试用后的早期阶段"],
        "cost": {"chen_lan": ["可自由消费的收入少于工资涨幅看起来那么多"]},
        "state_delta": {"cash_buffer": "+", "family_claims": "+", "housing_lock_in": "0"},
        "causes": ["r04", "r05"],
        "future_not_known": ["2031父亲是否生病", "公司是否长期稳定"],
    },
    {
        "id": "p02", "date": "2026-11-12", "actor": "lin_jing", "kind": "housing",
        "choice": "续住交通方便但条件一般的租房，没有为了每月少一点房租搬到更远处",
        "known_now": ["研究日程不稳定", "通勤时间会直接吃掉研究时间", "她没有购房能力也没有近期购房计划"],
        "cost": {"lin_jing": ["继续承担租金压力", "居住条件没有改善"]},
        "state_delta": {"cash_buffer": "-", "usable_time": "+", "mobility": "+", "housing_security": "0"},
        "causes": ["r02"],
        "future_not_known": ["以后是否离开北京", "租房最终代表自由还是不稳定"],
    },
    {
        "id": "p03", "date": "2027-03-05", "actor": "lin_jing", "kind": "relationship_ordinary",
        "choice": "收入比较争执后第一次见面仍选两人过去常去的普通餐馆，并把账各付各的",
        "known_now": ["r06已经伤到林静", "陈岚尚未完成正式道歉", "两人都没有打算绝交"],
        "cost": {"relationship": ["见面变得有意识，不再像学生时期自然"]},
        "state_delta": {"lin_chen_trust": "slightly_down", "comparison_sensitivity": "+"},
        "causes": ["r06"],
        "future_not_known": ["这段友谊会不会恢复"],
    },
    {
        "id": "p04", "date": "2027-07-23", "actor": "chen_lan", "kind": "family_coordination",
        "choice": "父母处理一次普通体检和报销手续时，陈岚远程帮着约时间、整理材料，没有请整天假回家",
        "known_now": ["父母目前能自理", "流程需要有人熟悉手机和材料", "她的工作日时间已经变贵"],
        "cost": {"chen_lan": ["一个晚上和次日上午被切碎", "第一次明显感到工资不能直接换回完整时间"]},
        "state_delta": {"care_coordination": "+", "usable_time_variance": "+"},
        "causes": ["p01", "r08"],
        "future_not_known": ["未来是否出现急性照护需求"],
    },
    {
        "id": "p05", "date": "2027-12-16", "actor": "ensemble", "kind": "boring_interval",
        "choice": "没有发生决定人生的大事；陈岚继续训练、林静推进慢项目、许航做低可见度复现，三人都只是把普通月份过完",
        "known_now": ["职业不确定性存在", "没有人掌握未来赢家信息"],
        "cost": {"chen_lan": ["疲劳积累"], "lin_jing": ["机会成本继续累积"], "xu_hang": ["履历增长不显眼"]},
        "state_delta": {"time_passed": "+", "dramatic_shock": "0"},
        "causes": ["r09", "r10"],
        "future_not_known": ["这些看似平淡的适应是否有回报"],
    },
    {
        "id": "p06", "date": "2028-01-27", "actor": "xu_hang", "kind": "housing_money",
        "choice": "在职业方向不明时续住较便宜且通勤更长的房间，没有搬去离单位更近的新房",
        "known_now": ["复现工作占用时间但职业回报不清晰", "现金缓冲有限", "近期可能换岗"],
        "cost": {"xu_hang": ["每周损失更多通勤时间", "居住条件保持一般"]},
        "state_delta": {"cash_buffer": "+", "usable_time": "-", "location_lock_in": "low"},
        "causes": ["p05"],
        "future_not_known": ["验证工作以后是否值钱"],
    },
    {
        "id": "p07", "date": "2028-06-15", "actor": "lin_jing", "kind": "mobility_probe",
        "choice": "回复一次外地研究机构的非正式询问，认真问了项目自主权、合同长度和数据权限，但没有立即投正式申请",
        "known_now": ["r12之后她不愿再把高工资等同于好岗位", "外地生活成本可能更低", "岗位边界还不清楚"],
        "cost": {"lin_jing": ["花时间准备材料却没有确定回报"]},
        "state_delta": {"external_network": "+", "mobility_option": "+", "current_income": "0"},
        "causes": ["r10", "r12"],
        "future_not_known": ["外地城市是否更适合她", "以后是否真的迁移"],
    },
    {
        "id": "p08", "date": "2028-09-14", "actor": "chen_lan", "kind": "health_time",
        "choice": "连续几个月高强度训练和客户工作后，她放弃接第二个周末项目，把周末重新留出一部分",
        "known_now": ["收入已经能覆盖日常与固定家庭支出", "睡眠和注意力开始明显受影响", "晋升仍不确定"],
        "cost": {"chen_lan": ["少一笔额外收入", "在同事眼里短期不够进取"]},
        "state_delta": {"physical_capacity": "+", "usable_time": "+", "income_growth": "-"},
        "causes": ["r09", "r11", "p04"],
        "future_not_known": ["放慢是否会损害长期职业机会"],
    },
    {
        "id": "p09", "date": "2028-12-21", "actor": "xu_hang", "kind": "job_benefits",
        "choice": "最终接受验证型岗位时，把稳定工资和连续医保也计入决定，没有把这次选择解释成对验证使命的信仰",
        "known_now": ["失败档案开始能被雇主看懂", "传统论文路径仍更有身份感", "自己的现金缓冲不适合长期等待"],
        "cost": {"xu_hang": ["职业标签变窄", "更难维持传统研究者身份叙事"]},
        "state_delta": {"cash_security": "+", "medical_insurance_continuity": "+", "status_ambiguity": "+"},
        "causes": ["r13", "r14", "p06"],
        "future_not_known": ["验证以后是否获得高溢价"],
    },
    {
        "id": "p10", "date": "2029-02-22", "actor": "lin_jing", "kind": "housing",
        "choice": "家里再次问买房时，她只续一年租约，并为押金、搬家可能性和下一次续租预留现金",
        "known_now": ["房子可以提供稳定感", "自己仍在看不同机构机会", "买房会显著减少流动现金"],
        "cost": {"lin_jing": ["继续承担租约不确定性", "需要长期留一笔不能随便花的钱"]},
        "state_delta": {"cash_buffer": "reserved", "mobility_option": "+", "housing_security": "medium", "housing_lock_in": "low"},
        "causes": ["p02", "p07", "r12"],
        "future_not_known": ["不买房最终是好决定还是错过资产机会"],
    },
    {
        "id": "p11", "date": "2029-03-29", "actor": "chen_lan", "kind": "family_coordination",
        "choice": "一次普通门诊复查碰上工作周，她和父母先用电话把交通、挂号和报销分工说清，只在关键时段在线处理",
        "known_now": ["父母仍能承担大部分自理", "她已经形成帮忙处理复杂流程的角色", "公司允许有限度调班"],
        "cost": {"chen_lan": ["会议安排被压缩", "家庭默认她懂流程的期待进一步固定"]},
        "state_delta": {"care_coordination": "+", "coordination_robustness": "+", "default_helper_role": "+"},
        "causes": ["p04", "p08"],
        "future_not_known": ["将来服务体系能否替代这种协调", "父母健康轨迹"],
    },
    {
        "id": "p12", "date": "2029-06-09", "actor": "lin_jing", "kind": "relationship_work",
        "choice": "许航指出来源链问题后，林静没有立即把私人关系修复成原样，只要求他列出能确认和不能确认的部分",
        "known_now": ["项目已经因r15延期", "两人都知道继续合作仍有现实价值", "林静仍觉得这次阻断很难受"],
        "cost": {"relationship": ["信任变得更专业化、更少轻松感"]},
        "state_delta": {"lin_xu_epistemic_trust": "+", "lin_xu_personal_ease": "-"},
        "causes": ["r15"],
        "future_not_known": ["2033是否会再次发生更严重的证据冲突"],
    },
    {
        "id": "p13", "date": "2029-09-27", "actor": "chen_lan", "kind": "institution_budget",
        "choice": "保留带薪试用后，把一个原本准备外包的低优先级项目往后排，没有要求学员用无薪劳动填缺口",
        "known_now": ["团队预算有限", "她已有一定排期权", "短期交付数量会更难看"],
        "cost": {"organization": ["可计费项目减少"], "chen_lan": ["要向上级解释预算选择"]},
        "state_delta": {"institutional_trust": "+", "discretionary_budget": "-", "junior_cost_externalization": "-"},
        "causes": ["r11", "r16"],
        "future_not_known": ["下一轮预算是否允许继续这么做"],
    },
    {
        "id": "p14", "date": "2029-10-26", "actor": "xu_hang", "kind": "ordinary_life",
        "choice": "验证岗位稳定后仍没有立刻换更好的房子，而是先补现金缓冲并缩短一部分通勤，用偶尔打车换回加班后的睡眠",
        "known_now": ["收入比此前稳定", "职业溢价仍有限", "长通勤已经开始侵蚀恢复时间"],
        "cost": {"xu_hang": ["现金积累速度稍慢"]},
        "state_delta": {"cash_buffer": "+", "physical_capacity": "+", "housing_status": "0"},
        "causes": ["p06", "p09"],
        "future_not_known": ["是否值得长期留在这条职业线上"],
    },
    {
        "id": "p15", "date": "2029-11-22", "actor": "lin_jing", "kind": "welfare_mobility",
        "choice": "又收到一次外地机会时，她先问合同衔接、医保社保转移和入职空档，而不是只问薪资和头衔",
        "known_now": ["她有外地网络但没有决定迁移", "一旦出现合同空档，现金和医疗保障都会承压", "现租约将在2030年春天进入下一次决策点"],
        "cost": {"lin_jing": ["准备和比较成本增加", "一些看起来诱人的岗位因此变得没那么简单"]},
        "state_delta": {"mobility_option_quality": "+", "naive_mobility": "-", "benefit_awareness": "+"},
        "causes": ["p07", "p10"],
        "future_not_known": ["2030以后是否真的搬走"],
    },
    {
        "id": "p16", "date": "2029-12-28", "actor": "ensemble", "kind": "quiet_contact",
        "choice": "年底没有进行总结人生的聚会；三人只是各自忙完工作，零散交换消息，旧关系仍在但频率已经和学生时代不同",
        "known_now": ["陈岚时间最碎", "林静还在权衡下一轮租约和机会", "许航刚获得一点职业稳定"],
        "cost": {"relationship": ["亲密关系需要维护但没有人拥有无限时间"]},
        "state_delta": {"relationship_frequency": "-", "relationship_persistence": "+"},
        "causes": ["p03", "p12", "p13", "p14", "p15", "r17"],
        "future_not_known": ["下一次比较会不会重新伤人"],
    },
]

# State carried into January 2030. Values are qualitative because the original
# history never established exact RMB amounts; false numerical precision would
# be less truthful than bounded categories.
HANDOFF_2030_01 = {
    "lin_jing": {
        "income_buffer": "moderate income; some liquid cash deliberately reserved for lease/move discontinuity",
        "housing": "renter; acceptable access and low lock-in; next lease decision due in spring 2030",
        "usable_time": "more self-directed than Chen, but research and option maintenance consume real time",
        "health_capacity": "ordinary capacity; no dramatic illness seeded",
        "care": "no acute care obligation established; family expectations about housing remain active",
        "mobility": "real but costly: two external probes, documents/network maintained, benefit discontinuity understood",
        "status": "slower conventional rise; stronger control over claims and work boundaries",
        "bargaining_refusal_power": "medium and increasing, materially dependent on cash/lease/institution position",
        "benefits": "currently continuous; cross-city continuity is a known friction rather than an abstraction",
        "trust": {"chen_lan": "repaired but comparison-sensitive", "xu_hang": "higher epistemic trust, lower ease after costly disagreement"},
        "provenance": ["r10", "r12", "p02", "p07", "p10", "r15", "p12", "p15", "r18"],
    },
    "chen_lan": {
        "income_buffer": "highest of the three; family support and humane team choices absorb part of the gain",
        "housing": "stable and affordable to her; not canonically converted into ownership",
        "usable_time": "scarcer than income suggests; improved somewhat after setting work limits",
        "health_capacity": "ordinary but workload-sensitive; sleep/recovery already constrain extra projects",
        "care": "parents self-manage most needs; Chen has become the default digital/administrative coordinator",
        "mobility": "nominally available but already entangled with family coordination and managerial responsibility",
        "status": "visible organizational authority and clearer commercial value",
        "bargaining_refusal_power": "high inside team, still budget-bounded",
        "benefits": "stable through employment",
        "trust": {"lin_jing": "friendship repaired without erasing income wound", "organization": "enough discretion to protect paid training once, not permanently"},
        "provenance": ["r05", "p01", "r06", "r07", "r09", "r11", "p08", "p11", "r16", "p13", "r18"],
    },
    "xu_hang": {
        "income_buffer": "stable specialist income; buffer rebuilding after uncertain years",
        "housing": "low-cost renter; some time sacrificed to commuting, no strong property lock-in",
        "usable_time": "verification work is paid but cognitively demanding; commute/recovery remain material",
        "health_capacity": "ordinary; sleep/recovery managed pragmatically, no future episode prewritten",
        "care": "no major family-care branch established before 2030; absence is uncertainty, not proof of none forever",
        "mobility": "moderate; specialist portfolio is portable but narrow identity and benefits favor continuity",
        "status": "legible specialist, still below agenda-setting roles",
        "bargaining_refusal_power": "medium-low; can refuse evidentiary shortcuts more readily than he can set the institution's agenda",
        "benefits": "stable medical-insurance continuity is part of why he accepted the job",
        "trust": {"lin_jing": "costly professional trust; disagreement has already delayed her work", "gu_wei": "built through unattractive failure work"},
        "provenance": ["r13", "r14", "p06", "p09", "r15", "p12", "r17", "p14"],
    },
}

BRIDGE_TO_FROZEN_2030_2035 = {
    # h31: Lin renews rather than buys in April 2030.
    "h31": ["p02", "p07", "p10", "p15", "r12", "r18"],
    # h32: Chen converts some hiring budget into paid training in September 2030.
    "h32": ["r11", "r16", "p13"],
    # h33: a 2031 acute care episode is not caused by earlier illness; only the
    # coordination role and time/cash transmission channel are pre-existing.
    "h33": ["p01", "p04", "p11"],
    # h35 / later Xu recognition rests on a material job decision, not prophecy.
    "h35": ["r13", "r14", "p09", "r17", "p14"],
    # Later Lin/Xu evidentiary conflict has a smaller 2029 predecessor.
    "h39": ["r15", "p12"],
}


def validate_pre2030_bridge():
    ids = {x["id"] for x in CONNECTIVE_2026_2030}
    errors = []
    required_domains = {
        "housing": any(x["kind"] in {"housing", "housing_money"} for x in CONNECTIVE_2026_2030),
        "family_coordination": any(x["kind"] == "family_coordination" for x in CONNECTIVE_2026_2030),
        "health_time": any(x["kind"] == "health_time" for x in CONNECTIVE_2026_2030),
        "mobility": any(x["kind"] in {"mobility_probe", "welfare_mobility"} for x in CONNECTIVE_2026_2030),
        "welfare": any("benefit" in x["kind"] or "welfare" in x["kind"] for x in CONNECTIVE_2026_2030),
        "quiet_interval": any(x["kind"] in {"boring_interval", "quiet_contact"} for x in CONNECTIVE_2026_2030),
        "relationship": any(x["kind"] in {"relationship_ordinary", "relationship_work", "quiet_contact"} for x in CONNECTIVE_2026_2030),
    }
    for actor, state in HANDOFF_2030_01.items():
        for field in ("income_buffer", "housing", "usable_time", "health_capacity", "care", "mobility", "status", "bargaining_refusal_power", "benefits", "trust", "provenance"):
            if field not in state:
                errors.append(("missing_handoff_field", actor, field))
    for hid, causes in BRIDGE_TO_FROZEN_2030_2035.items():
        if not causes:
            errors.append(("empty_bridge", hid))
    return {
        "valid": not errors and all(required_domains.values()),
        "errors": errors,
        "required_domains": required_domains,
        "connective_nodes": len(ids),
        "handoff_characters": len(HANDOFF_2030_01),
    }
