"""First 2031-2035 continuation of the converged trunk.

Noncanonical proposals. These are deliberately ordinary and costly; later passes
must replay them through authority, household and information constraints.
"""

TRUNK_2031_2035_PASS_01 = [
{"id":"r19","date":"2031-02-14","actor":"chen_lan","choice":"拒绝把团队培训预算全部并入可计费项目","rejected":"用项目收入考核覆盖所有新人训练","cost":{"chen_lan":"季度利润率更难看"},"memory_add":["training_budget_is_real_cost"],"causes":["r16"],"conditional_on":["budget_authority"]},
{"id":"r20","date":"2031-06-03","actor":"lin_jing","choice":"父亲检查异常后先回家一周确认照护需求，不立即辞职","rejected":"把照护危机直接等同于永久返乡","cost":{"lin_jing":"错过一次线下合作会"},"memory_add":["care_information_before_sacrifice"],"causes":["r12"],"conditional_on":["parent_health_shock"]},
{"id":"r21","date":"2031-09-19","actor":"xu_hang","choice":"拒绝把验证结论改成客户更喜欢的措辞","rejected":"用模糊语言保住合同","cost":{"xu_hang":"项目续约概率下降"},"memory_add":["verification_without_price_guarantee"],"causes":["r15"],"conditional_on":[]},
{"id":"r22","date":"2032-01-08","actor":"chen_lan","choice":"普通地工作、报销、看父母门诊，没有职业转折","rejected":"人为制造转折","cost":{},"memory_add":["ordinary_time_2032"],"causes":["r19"],"conditional_on":[]},
{"id":"r23","date":"2032-07-27","actor":"lin_jing","choice":"把一次外地岗位报价当作照护与住房的联合问题计算","rejected":"只比较工资和头衔","cost":{"lin_jing":"放弃薪资最高的方案"},"memory_add":["mobility_is_household_choice"],"causes":["r20"],"conditional_on":["city_switch_offer"]},
{"id":"r24","date":"2032-11-12","actor":"chen_lan","choice":"发现自己有管理头衔但没有足够预算后，明确告诉候选人岗位不能承诺长期培养","rejected":"用未来可能有预算诱导候选人接受低薪","cost":{"chen_lan":"失去一名优秀候选人"},"memory_add":["authority_without_budget"],"causes":["r19"],"conditional_on":["tight_budget"]},
{"id":"r25","date":"2033-04-06","actor":"xu_hang","choice":"接受验证工作社会价值高但涨薪有限这一现实，保留一部分时间做问题定义","rejected":"把全部身份锁死为审核员","cost":{"xu_hang":"短期绩效下降"},"memory_add":["value_price_gap_named"],"causes":["r21"],"conditional_on":[]},
{"id":"r26","date":"2033-08-18","actor":"lin_jing","choice":"使用可获得的照护服务购买部分家庭时间","rejected":"把亲自照护等同于孝顺的唯一形式","cost":{"lin_jing":"现金支出增加","family":"出现关于外包照护的争执"},"memory_add":["welfare_service_becomes_time"],"causes":["r20","r23"],"conditional_on":["care_service_available"]},
{"id":"r27","date":"2034-02-23","actor":"chen_lan","choice":"在订单下降时缩小带薪训练规模但拒绝改成无薪试工","rejected":"把企业风险全部转给新人","cost":{"organization":"少招人","chen_lan":"善意没有完整实现"},"memory_add":["goodness_can_shrink_without_reversing"],"causes":["r16","r19","r24"],"conditional_on":["demand_shock"]},
{"id":"r28","date":"2034-10-05","actor":"lin_jing","choice":"一次项目成功后不把它解释成自己当年选择自主路线必然正确","rejected":"用结果证明陈岚当年的路线错误","cost":{},"memory_add":["no_retrospective_moral_victory"],"causes":["r18","r23","r26"],"conditional_on":[]},
{"id":"r29","date":"2035-03-16","actor":"xu_hang","choice":"把新人带进一次真实失败审计并给出署名与责任边界","rejected":"只让新人做不可见清理劳动","cost":{"xu_hang":"交付速度下降"},"memory_add":["training_ladder_rebuilt_locally"],"causes":["r13","r17","r25"],"conditional_on":["has_junior"]},
{"id":"r30","date":"2035-09-21","actor":"chen_lan","choice":"承认收入、职位和时间自由从未同时达到峰值","rejected":"给自己的人生做单一赢家结论","cost":{},"memory_add":["success_bundle_stays_unbundled"],"causes":["r05","r09","r16","r24","r27"],"conditional_on":[]},
{"id":"r31","date":"2035-10-18","actor":"lin_jing","choice":"和陈岚、许航吃一顿普通饭，只讨论最近谁有时间，不讨论谁成功","rejected":"重新排名三个人的人生","cost":{},"memory_add":["time_replaces_rank_as_daily_question"],"causes":["r18","r28","r30"],"conditional_on":[]},
]

ROBUST_CANDIDATES = {
    "success_bundle_unbundles": ["r24","r30"],
    "care_changes_feasible_sets": ["r20","r23","r26"],
    "social_value_market_price_gap": ["r21","r25"],
    "goodness_requires_resources": ["r19","r24","r27"],
    "training_ladders_are_institutional_choices": ["r19","r27","r29"],
}

CONDITIONAL_BRANCHES = {
    "care_service_converts_cash_to_time": ["r26"],
    "paid_training_survives_downturn": ["r27"],
    "xu_can_rebuild_junior_ladder": ["r29"],
}
