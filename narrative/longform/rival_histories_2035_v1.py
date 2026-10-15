"""Two continuous rival histories after structural convergence.

Alpha and Beta are mutually competing lived histories, not scenario summaries.
Resource deltas are ordinal engineering parameters (-2..+2), not empirical units and
must never be presented as measured forecasts.
"""
from copy import deepcopy

STATE_KEYS = (
    "money", "usable_time", "housing_security", "health_capacity", "care_robustness",
    "mobility", "status", "welfare_continuity", "bargaining_power", "trust",
    "exercisable_options",
)

ZERO = {k: 0 for k in STATE_KEYS}


def event(event_id, date, actor, choice, causes, delta, cost, knowledge):
    unknown = set(delta) - set(STATE_KEYS)
    if unknown:
        raise ValueError(f"unknown state keys: {sorted(unknown)}")
    return {
        "id": event_id,
        "date": date,
        "actor": actor,
        "choice": choice,
        "causes": list(causes),
        "delta": {**ZERO, **delta},
        "cost": cost,
        "knowledge": knowledge,
        "parameter_type": "ordinal_engineering_delta",
    }


ALPHA_QUIET_RUPTURE = [
    event("a30_1", "2030-04-11", "lin_jing",
          "续租一年，保留外地申请可能，但没有设定必须离开的期限", ["r12", "r18"],
          {"money": 1, "housing_security": -1, "mobility": 1, "exercisable_options": 1},
          "省下首付锁定，但继续承受租约与房东不确定性",
          "她只知道买房会降低短期流动性，不知道未来是否真的会搬"),
    event("a30_2", "2030-09-06", "chen_lan",
          "把一部分招聘预算转成带薪训练名额", ["r16"],
          {"status": 1, "usable_time": -1, "bargaining_power": -1, "trust": 1},
          "短期项目交付减少，且把自己绑定到一项容易被砍的承诺",
          "她把预算理解为至少还能维持两年，不知道次年会收紧"),
    event("a31_1", "2031-02-14", "chen_lan",
          "父亲手术后购买部分服务，同时自己承担关键协调", ["a30_2"],
          {"money": -1, "usable_time": -2, "care_robustness": -1, "health_capacity": -1,
           "exercisable_options": -1},
          "钱能买到平均照护小时，却买不到所有紧急协调",
          "她以为最难的是术后前三个月，不知道照护会转成慢性安排"),
    event("a31_2", "2031-06-20", "chen_lan",
          "预算收紧后保留已有学员，停止新增名额", ["a30_2", "a31_1"],
          {"status": -1, "trust": -1, "bargaining_power": -1},
          "没有被录取的年轻人承担了制度收缩的代价",
          "她不知道项目是暂时冻结还是会逐渐失去组织支持"),
    event("a31_3", "2031-11-03", "xu_hang",
          "接受验证岗位正式职级，工资改善有限", ["r14", "r17"],
          {"money": 1, "status": 1, "bargaining_power": 1, "usable_time": -1},
          "职业合法性增加，同时再训练和责任增加",
          "他以为正式职级至少意味着验证工作开始被长期需要"),
    event("a32_1", "2032-03-18", "lin_jing",
          "看到外地岗位但没有申请，告诉自己下一轮更合适", ["a30_1"],
          {"mobility": -1, "trust": -1, "exercisable_options": -1},
          "没有立即损失收入，却让一个真实选项转成假设性选项",
          "她不知道自己之后会越来越少看外地岗位"),
    event("a32_2", "2032-08-27", "lin_jing",
          "把对自身停滞的羞耻转成对陈岚生活方式的讽刺", ["r06", "a32_1"],
          {"trust": -2, "health_capacity": -1},
          "旧的收入比较伤口换了语言，没有消失",
          "她当时认为冲突只是一次情绪失控"),
    event("a32_3", "2032-12-09", "lin_jing",
          "向陈岚承认自己真正害怕的是选择越来越少", ["a32_2"],
          {"trust": 1, "health_capacity": 1},
          "修复了一部分关系，却没有恢复已经失去的岗位窗口",
          "她仍然不知道问题来自恐惧、习惯还是现实约束各占多少"),
    event("a33_1", "2033-05-12", "xu_hang",
          "拒绝为林静无法复核的数据来源签字，也拒绝私下口头兜底", ["r15", "a31_3", "a32_3"],
          {"trust": -2, "status": 1, "bargaining_power": 1},
          "林静项目延期并失去合作窗口，两人的私人关系中断",
          "许航只知道这次背书不可撤回，不知道拒绝会伤到几年以后"),
    event("a33_2", "2033-09-01", "lin_jing",
          "独自把项目缩到可验证范围，不再把新标准归功于许航", ["a33_1"],
          {"status": -1, "trust": -1, "bargaining_power": 1},
          "论文更小、更慢，关系没有因此修复",
          "她只确认了较小的结论能活下来，不知道外界是否在意删掉的漂亮结论"),
    event("a34_1", "2034-01-19", "chen_lan",
          "把组织内验证失败记录加入训练材料，包括自己项目被砍的记录", ["a31_2", "a31_3"],
          {"trust": 1, "status": 1, "usable_time": -1},
          "培训效率短期下降，暴露组织过去的难看记录",
          "她不知道这种训练会不会被上级视为过度谨慎"),
    event("a34_2", "2034-07-26", "chen_lan",
          "没有出现决定性晋升窗口，只是把年假继续拆成零碎照护日", ["a31_1"],
          {"usable_time": -1, "health_capacity": -1, "care_robustness": 1,
           "exercisable_options": -1},
          "家庭安排更稳，却多年没有完整休息，也没有一个可被歌颂的牺牲时刻",
          "她只把这理解成今年比较忙"),
    event("a34_3", "2034-11-15", "lin_jing",
          "又续一次租约，发现自己已经两年没有认真查看外地岗位", ["a32_3"],
          {"housing_security": -1, "mobility": -1, "exercisable_options": -1},
          "选择权没有突然消失，只是逐渐变得陌生",
          "她第一次意识到维护选择本身需要行动"),
    event("a35_1", "2035-03-21", "xu_hang",
          "失败档案和验证清单开始被培训材料采用，但他因长期失眠和焦虑减少公开工作", ["a31_3", "a34_1"],
          {"status": 1, "health_capacity": -2, "usable_time": -1, "exercisable_options": -1},
          "公共用途上升时，个人兑现认可的能力下降",
          "他不知道材料已经跨到多少组织，只知道自己暂时不想再承担更多公开责任"),
    event("a35_2", "2035-08-30", "lin_jing",
          "搬家整理旧材料，扔掉大部分招聘启事，只留下一张当年没有申请的岗位截图", ["a30_1", "a32_1", "a34_3"],
          {"trust": 0, "exercisable_options": 0},
          "没有改变现实资源，只改变她如何解释过去",
          "她仍不知道当时申请是否真的会更好"),
    event("a35_3", "2035-12-06", "ensemble",
          "陈岚在培训会上引用许航整理的失败材料；林静提前离场，许航因为状态不好没有出席", ["a33_2", "a34_1", "a35_1"],
          {"trust": -1},
          "共同历史被同一制度使用，但三人没有获得重逢或和解",
          "任何人都看不到另外两人的完整账本"),
]


BETA_EXERCISED_MOBILITY = [
    event("b30_1", "2030-04-11", "lin_jing",
          "续租并明确把两年内跨城申请写进自己的计划", ["r12", "r18"],
          {"money": 1, "housing_security": -1, "mobility": 1, "exercisable_options": 1},
          "继续承担租赁不确定性来换取迁移空间",
          "她只知道自己不愿现在买房，不知道目标城市最终是什么"),
    event("b30_2", "2030-09-06", "chen_lan",
          "把一部分招聘预算转成带薪训练名额", ["r16"],
          {"status": 1, "usable_time": -1, "trust": 1},
          "项目交付减少并形成未来承诺",
          "她不知道次年预算和家庭照护会同时收紧"),
    event("b31_1", "2031-02-14", "chen_lan",
          "父亲手术后购买部分照护服务并亲自协调", ["b30_2"],
          {"money": -1, "usable_time": -2, "health_capacity": -1, "care_robustness": -1},
          "现金与时间同时下降",
          "她仍把这看成阶段性问题"),
    event("b31_2", "2031-06-20", "chen_lan",
          "预算收紧时保留已有学员但暂停扩张", ["b30_2", "b31_1"],
          {"status": -1, "trust": -1},
          "下一批申请者失去名额",
          "她不知道组织会不会在下一周期恢复预算"),
    event("b31_3", "2031-11-03", "xu_hang",
          "接受验证岗位正式职级但市场溢价有限", ["r14", "r17"],
          {"money": 1, "status": 1, "bargaining_power": 1, "usable_time": -1},
          "责任增长快于收入增长",
          "他仍相信经验积累可能在以后提高议价能力"),
    event("b32_1", "2032-03-18", "lin_jing",
          "申请并接受外地跨机构岗位，先租一年试住", ["b30_1"],
          {"money": 1, "mobility": 2, "status": 1, "bargaining_power": 1,
           "welfare_continuity": -1, "trust": -1, "care_robustness": -1,
           "exercisable_options": 1},
          "工作拒绝权上升，同时失去北京部分关系资本与家庭近距离协调能力",
          "她只掌握岗位和租房信息，低估了跨城照护和关系维护的交易成本"),
    event("b32_2", "2032-08-27", "lin_jing",
          "母亲临时住院时第一次为跨城往返和请假付出高成本", ["b32_1"],
          {"money": -1, "usable_time": -2, "health_capacity": -1, "care_robustness": -1},
          "迁移带来的自主没有消失，但它不再是免费的",
          "她不知道这种家庭需求会不会成为常态"),
    event("b32_3", "2032-12-09", "lin_jing",
          "承认新工作确实更自由，也承认自己卖掉了部分近距离照护和熟人网络", ["b32_2"],
          {"trust": 1, "health_capacity": 1},
          "无法再把迁移解释成单向升级",
          "她仍未决定一年试住后是否长期留下"),
    event("b33_1", "2033-05-12", "xu_hang",
          "拒绝为林静远程项目中的不可复核数据来源签字", ["r15", "b31_3", "b32_3"],
          {"trust": -1, "status": 1, "bargaining_power": 1},
          "项目延期，跨城沟通让误解更难及时修复",
          "许航不知道林静所在机构内部对延期的容忍度"),
    event("b33_2", "2033-09-01", "lin_jing",
          "缩小项目范围并保住可验证部分", ["b33_1"],
          {"status": -1, "bargaining_power": 1, "trust": 0},
          "失去速度和更漂亮的结论",
          "她只知道较小结果能被复核，不知道这次妥协会怎样影响晋升"),
    event("b34_1", "2034-01-19", "chen_lan",
          "把验证失败记录纳入训练", ["b31_2", "b31_3"],
          {"trust": 1, "status": 1, "usable_time": -1},
          "培训更慢且短期不讨巧",
          "她不知道组织会不会长期保留这种训练"),
    event("b34_2", "2034-07-26", "lin_jing",
          "收到北京旧网络的回流机会，却因为当前城市工作弹性更高而暂时留下", ["b32_1", "b32_3"],
          {"mobility": -1, "bargaining_power": 1, "care_robustness": -1, "exercisable_options": 0},
          "她主动放弃一次回流窗口，换取当前工作的拒绝权",
          "她不知道未来父母健康变化会不会让这个决定显得昂贵"),
    event("b34_3", "2034-11-15", "chen_lan",
          "谈起林静的迁移时说自己羡慕她能真正动过一次，但并不羡慕两地照护", ["b31_1", "b34_2"],
          {"trust": 1},
          "两人终于承认比较的是不同资源",
          "这没有回答谁的生活更好"),
    event("b35_1", "2035-03-21", "xu_hang",
          "验证责任被更正式地写入职业流程，但工资与职级变化有限", ["b31_3", "b34_1"],
          {"status": 1, "bargaining_power": 1, "usable_time": -1},
          "社会需求增加并不自动转成个人市场溢价",
          "他不知道未来两年市场会不会重新定价"),
    event("b35_2", "2035-08-30", "lin_jing",
          "在外地第四次续租时不再把自己称为临时试住者", ["b32_1", "b34_2"],
          {"housing_security": 1, "mobility": -1, "welfare_continuity": 1,
           "exercisable_options": -1},
          "稳定性上升，同时原本的高流动性开始自然下降",
          "她不知道这算扎根还是另一次选择衰减"),
    event("b35_3", "2035-12-06", "ensemble",
          "一次线上会议结束后，三个人分别留在不同城市继续处理自己的工作和家庭安排", ["b33_2", "b34_3", "b35_1", "b35_2"],
          {"trust": 0},
          "没有结算谁赢了；共同语言只剩下每个人当前还能行使哪些选择",
          "他们彼此都只看到别人生活的一部分"),
]


def validate(history):
    ids = {e["id"] for e in history}
    return {
        "chronological": history == sorted(history, key=lambda e: (e["date"], e["id"])),
        "causes_resolve": all(c in ids or c.startswith("r") for e in history for c in e["causes"]),
        "state_vectors_complete": all(set(e["delta"]) == set(STATE_KEYS) for e in history),
        "engineering_parameters_labeled": all(e["parameter_type"] == "ordinal_engineering_delta" for e in history),
        "local_information_present": all(bool(e["knowledge"]) for e in history),
    }


def ledger(history):
    states = {}
    snapshots = []
    for e in history:
        actors = [e["actor"]] if e["actor"] != "ensemble" else []
        for actor in actors:
            states.setdefault(actor, deepcopy(ZERO))
            for key, value in e["delta"].items():
                states[actor][key] += value
        snapshots.append({"event_id": e["id"], "date": e["date"], "states": deepcopy(states)})
    return snapshots


RIVAL_HISTORIES = {
    "alpha_quiet_rupture": ALPHA_QUIET_RUPTURE,
    "beta_exercised_mobility": BETA_EXERCISED_MOBILITY,
}
