"""Continuous replay pass 01 over the converged primary trunk.

Each node inherits prior costs and relationship/institution memory. This remains
a noncanonical replay proposal until actions are replayed through World authority.
"""

TRUNK_REPLAY_PASS_01 = [
{"id":"r01","date":"2026-03-20","actor":"chen_lan","choice":"申请行政例外，保住送审流程","rejected":"硬扛并期待导师额外兜底","cost":{"lin_jing":"同周期少一个行政窗口","chen_lan":"承认自己需要帮助"},"memory_add":["chen_used_exception","lin_paid_indirect_cost"],"causes":[]},
{"id":"r02","date":"2026-04-15","actor":"lin_jing","choice":"拒绝一次可接受的方法讨论，试图证明独立","rejected":"带着具体问题去讨论","cost":{"lin_jing":"多绕一个月"},"memory_add":["lin_confuses_autonomy_with_isolation"],"causes":["r01"]},
{"id":"r03","date":"2026-05-08","actor":"chen_lan","choice":"不追加新项目，只做普通收尾","rejected":"把空档填满以缓解焦虑","cost":{},"memory_add":["boring_week_preserved"],"causes":["r01"]},
{"id":"r04","date":"2026-07-01","actor":"chen_lan","choice":"毕业离校并接受外部求职不确定性","rejected":"继续以学生身份拖延寻找更完美机会","cost":{"wu_cheng":"失去可靠收尾者"},"memory_add":["chen_first_graduation"],"causes":["r01","r03"]},
{"id":"r05","date":"2026-09-18","actor":"chen_lan","choice":"接受研究服务企业岗位，换取现金流与更明确边界","rejected":"继续等待学术岗位","cost":{"chen_lan":"承担客户责任"},"memory_add":["chen_material_rise"],"causes":["r04"]},
{"id":"r06","date":"2027-01-20","actor":"chen_lan","choice":"在租房讨论里用收入标准评价林静","rejected":"只陈述自己的住房偏好","cost":{"relationship":"林静感到自己的生活被判定为失败"},"memory_add":["friendship_income_wound"],"causes":["r05"]},
{"id":"r07","date":"2027-04-07","actor":"chen_lan","choice":"道歉并承认自己把收入标准带进别人生活","rejected":"用'我是为你好'辩护","cost":{"chen_lan":"放弃道德制高点"},"memory_add":["friendship_repair_without_erasure"],"causes":["r06"]},
{"id":"r08","date":"2027-06-04","actor":"chen_lan","choice":"继续学习agent工作流，但明确减少社交承诺","rejected":"嘴上都答应再不断取消","cost":{"relationship":"与林静见面减少"},"memory_add":["success_creates_time_poverty"],"causes":["r05","r07"]},
{"id":"r09","date":"2027-09-10","actor":"chen_lan","choice":"把季度投入scope/verification/client responsibility","rejected":"继续追可计费速度","cost":{"chen_lan":"错过一次晋升"},"memory_add":["chen_missed_promotion_for_retraining"],"causes":["r08"]},
{"id":"r10","date":"2027-10-11","actor":"lin_jing","choice":"停止追逐技术炫技，把时间转向问题选择和证据边界","rejected":"与AI比执行速度","cost":{"lin_jing":"短期产出不显眼"},"memory_add":["lin_reprices_autonomy"],"causes":["r02","r06"]},
{"id":"r11","date":"2028-02-18","actor":"chen_lan","choice":"在客户错误中承担复核责任并公开限制","rejected":"把错误完全推给agent或下属","cost":{"chen_lan":"短期声誉风险"},"memory_add":["chen_owns_failure"],"causes":["r09"]},
{"id":"r12","date":"2028-03-22","actor":"lin_jing","choice":"拒绝高薪但长期隐形验证劳动的岗位","rejected":"把名头和工资当成唯一上升","cost":{"lin_jing":"失去更高起薪"},"memory_add":["lin_costly_refusal"],"causes":["r10"]},
{"id":"r13","date":"2028-04-20","actor":"gu_wei","choice":"把失败审计完整交给许航负责","rejected":"给许航一个更漂亮但空洞的署名","cost":{"gu_wei":"短期考核不好看","xu_hang":"论文产出变慢"},"memory_add":["xu_failure_training"],"causes":[]},
{"id":"r14","date":"2028-11-09","actor":"xu_hang","choice":"接受验证型岗位机会，把失败档案作为作品集","rejected":"隐藏未复现历史只展示成功","cost":{"xu_hang":"职业标签更窄"},"memory_add":["failure_becomes_capital"],"causes":["r13"]},
{"id":"r15","date":"2029-05-17","actor":"xu_hang","choice":"指出林静项目自动分析链的provenance缺口","rejected":"为了关系和进度默认通过","cost":{"lin_jing":"项目延期","xu_hang":"承担不讨喜角色"},"memory_add":["trust_through_costly_verification"],"causes":["r10","r14"]},
{"id":"r16","date":"2029-08-30","actor":"chen_lan","choice":"保留带薪试用与训练预算","rejected":"用无薪trial work转嫁筛选成本","cost":{"chen_lan":"团队少接一个项目"},"memory_add":["chen_refuses_unpaid_trial"],"causes":["r01","r11"]},
{"id":"r17","date":"2029-12-07","actor":"xu_hang","choice":"允许旧未复现报告成为新组培训材料","rejected":"把早期失败从履历中彻底删除","cost":{},"memory_add":["failure_reinterpreted"],"causes":["r13","r14","r15"]},
{"id":"r18","date":"2030-01-17","actor":"lin_jing","choice":"和陈岚共同拒绝回答'谁混得最好'","rejected":"把各自生活重新折算成收入或头衔","cost":{"relationship":"承认彼此无法互相证明"},"memory_add":["winner_question_retired"],"causes":["r06","r07","r12","r16"]},
]

def validate_continuity(nodes=TRUNK_REPLAY_PASS_01):
    seen=set()
    errors=[]
    for node in nodes:
        if node["id"] in seen: errors.append(("duplicate",node["id"]))
        unknown=[c for c in node.get("causes",[]) if c not in seen]
        if unknown: errors.append(("future_or_unknown_cause",node["id"],unknown))
        seen.add(node["id"])
    required={"bad_choice":False,"boring":False,"relationship_cost":False,"institutional_cost":False,"delayed_echo":False}
    required["bad_choice"]=any(n["id"] in {"r02","r06"} for n in nodes)
    required["boring"]=any(n["id"]=="r03" for n in nodes)
    required["relationship_cost"]=any("relationship" in n.get("cost",{}) for n in nodes)
    required["institutional_cost"]=any(any(k in n.get("cost",{}) for k in ("wu_cheng","gu_wei")) for n in nodes)
    required["delayed_echo"]=any(n["id"]=="r18" and "r06" in n.get("causes",[]) for n in nodes)
    return {"valid":not errors and all(required.values()),"errors":errors,"required":required,"nodes":len(nodes)}
