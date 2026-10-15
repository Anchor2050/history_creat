"""History capture pass 01: turn replay decisions into lived historical intervals.

The unit is no longer an isolated dramatic beat. A captured interval contains
material state, ordinary time, a choice, inherited memory, external pressure,
and a later reinterpretation. This remains noncanonical until World-authority
replay accepts the underlying actions.
"""

HISTORY_CAPTURE_PASS_01 = [
{
"period":"2026-03/2026-07","title":"毕业以前，世界还很小",
"foreground":["chen_lan","lin_jing"],
"material_change":"Chen uses a scarce administrative exception while family care and thesis work compress cash/time; Lin loses the same-cycle window and then wastes a month proving she can work alone.",
"ordinary_life":["报销","宿舍晚饭","论文图表","导师消息","家里转账","打印与送审"],
"era_pressure":"AI is visible mainly as a useful research tool; its labor-market consequence is not yet legible to the characters.",
"choice_memory":["chen_used_exception","lin_paid_indirect_cost","lin_confuses_autonomy_with_isolation"],
"historical_capture":"The important fact is not that anyone wins. A legitimate need by one person already changes another person's feasible set. Their later ideas about independence begin inside this tiny allocation problem.",
"later_reinterpretation":"Years later both will have authority over scarce opportunities and remember this period differently.",
},
{
"period":"2026-07/2027-04","title":"第一次上升",
"foreground":["chen_lan","lin_jing","zhao_ke"],
"material_change":"Chen graduates, enters external research-service work and gets the first visible income jump. Lin remains a student and the difference enters housing, consumption and time.",
"ordinary_life":["通勤","租房信息","客户群消息","招聘网页","周末取消的饭局"],
"era_pressure":"Agentic work is spreading, but Chen initially experiences the new economy as opportunity: faster delivery, more demand and a route out of academic precarity.",
"choice_memory":["chen_first_graduation","chen_material_rise","friendship_income_wound","friendship_repair_without_erasure"],
"historical_capture":"Material improvement is real and morally neutral. The first damage comes when Chen accidentally turns her new purchasing power into a standard for judging Lin's life.",
"later_reinterpretation":"This is the period outsiders would later remember as the moment Chen 'won'; that judgment will age badly.",
},
{
"period":"2027-04/2028-04","title":"第二次毕业开始了，却没人给它发证书",
"foreground":["chen_lan","lin_jing","xu_hang","gu_wei"],
"material_change":"Routine implementation gets cheaper. Chen spends billable time learning scope, verification and client responsibility and misses a promotion; Lin stops competing on technical virtuosity; Xu is assigned slow failure-audit work.",
"ordinary_life":["agent生成的初稿","版本号","客户修改意见","招聘JD的新词","组会里越来越快的demo"],
"era_pressure":"The price of execution begins falling unevenly. Institutions still reward visible output, so people who invest in verification can look temporarily irrational.",
"choice_memory":["success_creates_time_poverty","chen_missed_promotion_for_retraining","lin_reprices_autonomy","xu_failure_training"],
"historical_capture":"The transformation first appears as a mismatch between what is easy to count and what will later matter. No character has enough information to know whether the sacrifice is wise.",
"later_reinterpretation":"This becomes Chen's second graduation only in retrospect; at the time it feels like stalled advancement.",
},
{
"period":"2028-04/2029-05","title":"答案便宜以后",
"foreground":["chen_lan","lin_jing","xu_hang"],
"material_change":"An AI-assisted client failure makes accountable verification commercially visible. Lin rejects a prestigious role built around invisible verification labor. Xu's archive of failed reproductions becomes employable evidence.",
"ordinary_life":["复核表","客户电话","被退回的offer","失败日志","自动生成但无法解释的报告"],
"era_pressure":"AI adoption creates gains and removes routine rungs at the same time. Organizations search for people who can own provenance, boundaries and failure, but do not consistently pay them fairly.",
"choice_memory":["chen_owns_failure","lin_costly_refusal","failure_becomes_capital"],
"historical_capture":"Responsibility becomes scarce before society agrees on how to reward it. The same verification work can be a career moat for one person and invisible labor for another.",
"later_reinterpretation":"The era does not select a single winner; it reprices different biographies differently.",
},
{
"period":"2029-05/2030-01","title":"两种自由",
"foreground":["chen_lan","lin_jing","xu_hang"],
"material_change":"Xu delays Lin's project by exposing a provenance gap. Chen, now with hiring power, keeps paid trial and training budgets at the cost of one project. Lin and Chen finally refuse the old question of who is doing better.",
"ordinary_life":["延期邮件","招聘预算表","正式试用合同","旧同学聚会","几年前收藏的招聘启事"],
"era_pressure":"AI-enabled organizations are now ordinary enough that the novelty has faded; the durable conflicts concern who bears verification, training and transition costs.",
"choice_memory":["trust_through_costly_verification","chen_refuses_unpaid_trial","winner_question_retired"],
"historical_capture":"The moral return is institutional, not sentimental: people who once depended on scarce mercy now decide whether to pass transition costs downward. Their choices do not fix the system, but they change who pays.",
"later_reinterpretation":"Looking back at 2026, they cannot locate a revolution day. They can locate small decisions whose meanings changed as the surrounding price system changed.",
},
]

CAPTURED_HISTORY = {
"working_title":"第二次毕业",
"span":"2026-03/2030-01",
"thesis":"执行越来越便宜时，判断、责任、信任和拒绝的权利被重新定价；时代通过谁承担转型成本进入私人生活。",
"historical_lines":{
 "material":"student precarity -> external income -> automation repricing -> organizational authority",
 "epistemic":"technical execution -> provenance/verification -> responsibility for plausible but unsafe answers",
 "relational":"shared scarcity -> income wound -> repair without erasure -> incomparable forms of freedom",
 "institutional":"receiving exceptions -> controlling opportunities -> deciding whether transition costs are pushed onto juniors",
 "era":"AI as tool -> agentic coworker -> labor repricing -> normalized infrastructure and new accountability scarcity",
},
"anti_fabrication_rules":[
 "Do not turn scenario waves into dated future facts without later evidence.",
 "Do not create a catastrophe merely to make a motif return.",
 "Do not let goodness erase its budget/time/status cost.",
 "Do not let later success retroactively make an earlier risky choice obviously correct.",
 "Preserve ordinary intervals in which history is not recognizable to the people living it.",
],
}

def validate_capture(rows=HISTORY_CAPTURE_PASS_01):
    required={"ordinary":False,"era":False,"memory":False,"reinterpretation":False}
    for row in rows:
        required["ordinary"] |= bool(row.get("ordinary_life"))
        required["era"] |= bool(row.get("era_pressure"))
        required["memory"] |= bool(row.get("choice_memory"))
        required["reinterpretation"] |= bool(row.get("later_reinterpretation"))
    return {"valid":len(rows)>=5 and all(required.values()),"intervals":len(rows),"required":required}
