"""First continuous 2030-2035 replay over the converged trunk.

Noncanonical candidate lived history; later hard-World replay still required.
"""
REPLAY_2030_2035 = [
{"id":"h31","date":"2030-04-11","actor":"lin_jing","kind":"ordinary","choice":"续租而不买房，保留一年迁移窗口","cost":{"lin_jing":"继续承受租约不确定性"},"causes":["r12","r18"],"memory_add":["mobility_kept_open"]},
{"id":"h32","date":"2030-09-06","actor":"chen_lan","kind":"institution","choice":"把一部分招聘预算改成带薪训练名额","cost":{"chen_lan":"本季度可交付项目减少"},"causes":["r16"],"memory_add":["paid_training_attempt"]},
{"id":"h33","date":"2031-02-14","actor":"chen_lan","kind":"care","choice":"父亲手术后每月回家一次并购买部分照护服务","cost":{"chen_lan":"现金和周末时间同时下降"},"causes":["h32"],"memory_add":["income_does_not_buy_all_time"]},
{"id":"h34","date":"2031-06-20","actor":"chen_lan","kind":"failed_good","choice":"预算收紧时保留已有带薪学员但暂停新增名额","cost":{"applicants":"下一批年轻人没有得到名额"},"causes":["h32","h33"],"memory_add":["good_institution_hits_budget_ceiling"]},
{"id":"h35","date":"2031-11-03","actor":"xu_hang","kind":"career","choice":"接受验证岗位正式职级，但工资仍低于产品负责人","cost":{"xu_hang":"社会价值与市场价值继续错位"},"causes":["r14","r17"],"memory_add":["verification_conversion_lag"]},
{"id":"h36","date":"2032-03-18","actor":"lin_jing","kind":"bad_choice","choice":"因担心失去学术身份而错过外地跨机构岗位申请","cost":{"lin_jing":"失去一次更高自主度的岗位窗口"},"causes":["h31"],"memory_add":["mobility_option_not_exercised"]},
{"id":"h37","date":"2032-08-27","actor":"lin_jing","kind":"relationship","choice":"母亲问她为何还不买房时，她把焦虑转成对陈岚生活方式的讽刺","cost":{"relationship":"旧的收入比较伤口以新形式返回"},"causes":["r06","r07","h36"],"memory_add":["winner_question_returns_indirectly"]},
{"id":"h38","date":"2032-12-09","actor":"lin_jing","kind":"repair","choice":"告诉陈岚自己真正害怕的是选择权越来越少","cost":{"lin_jing":"承认自主也会因不行动而消失"},"causes":["h37"],"memory_add":["autonomy_requires_exercise"]},
{"id":"h39","date":"2033-05-12","actor":"xu_hang","kind":"cross_actor","choice":"拒绝为林静项目签署无法复核的数据来源声明","cost":{"lin_jing":"项目再次延期","xu_hang":"关系压力增加"},"causes":["r15","h35","h38"],"memory_add":["trust_is_not_waiver"]},
{"id":"h40","date":"2033-09-01","actor":"lin_jing","kind":"earned_change","choice":"把项目缩小到可验证的数据范围并删去最漂亮的结论","cost":{"lin_jing":"论文影响力和速度下降"},"causes":["h39"],"memory_add":["refusal_becomes_shared_standard"]},
{"id":"h41","date":"2034-01-19","actor":"chen_lan","kind":"institutional_echo","choice":"把验证失败记录纳入学员训练而不只展示成功案例","cost":{"organization":"培训更慢且短期不好看"},"causes":["r17","h34","h35"],"memory_add":["failure_archive_crosses_institutions"]},
{"id":"h42","date":"2034-07-26","actor":"chen_lan","kind":"care","choice":"拒绝一次跨城晋升，因为照护安排无法随迁","cost":{"chen_lan":"失去更高职位和收入"},"causes":["h33"],"memory_add":["care_caps_mobility"]},
{"id":"h43","date":"2034-11-15","actor":"chen_lan","kind":"reversal","choice":"第一次对林静说自己羡慕她仍能搬走","cost":{},"causes":["h38","h42"],"memory_add":["two_freedoms_repriced_again"]},
{"id":"h44","date":"2035-03-21","actor":"xu_hang","kind":"institution","choice":"职业标准终于承认部分验证责任，但岗位仍要求持续再训练","cost":{"xu_hang":"职业安全仍依赖持续学习"},"causes":["h35","h41"],"memory_add":["recognition_arrives_after_need"]},
{"id":"h45","date":"2035-08-30","actor":"lin_jing","kind":"ordinary","choice":"搬家时丢掉十年前的一叠招聘启事，只留下其中一张","cost":{},"causes":["h31","h36","h38","h43"],"memory_add":["ordinary_archive_thins"]},
{"id":"h46","date":"2035-12-06","actor":"ensemble","kind":"recognition","choice":"三人不再讨论谁赢了，只能说清各自把什么换成了什么、又有哪些东西没有换到","cost":{"ensemble":"接受没有单一结算日"},"causes":["h40","h42","h44","h45"],"memory_add":["no_single_adulthood_ledger"]},
]

CORE_CANDIDATES_AFTER_2035 = {
"stable":["adult_success_bundle_decouples","autonomy_is_resource_supported_not_personality_only","social_value_and_market_value_can_diverge_for_years","care_converts_income_success_into_time_and_mobility_constraints","goodness_requires_budget_and_can_fail_without_becoming_false","institutional_asynchrony_changes_exchange_rates_between_life_resources"],
"conditional":["chen_builds_durable_paid_training_system","xu_verification_role_gets_high_market_premium","lin_preserves_high_mobility_through_2035"],
"rejected_as_universal":["ai_makes_responsibility_automatically_more_expensive","higher_income_produces_more_personal_freedom","refusing_status_jobs_preserves_autonomy_by_itself","valuable_work_is_eventually_rewarded_if_one_waits"]}

COUNTERFACTUALS_NEXT = [
"remove h33 care shock and test h42/h43",
"let Lin apply at h36 and test whether mobility really buys autonomy",
"cut all paid training at h34 and test h41",
"give Xu early market premium at h35 and test costly verification at h39",
"strengthen portable welfare after 2030 and retest feasible refusals",
]
