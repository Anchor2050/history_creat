"""Focused deep replay batch 02.

Four Tier-A worlds, twelve ambiguous nodes each. These are structured replay
outcomes for historical-line selection, not prose chapters and not canonical
World mutations.
"""

FOCUSED_HISTORIES = [
{
"world_id":"world-022","title":"第二次毕业","premise":"陈岚先完成学历意义上的毕业，随后又在AI重构知识服务业时完成职业意义上的第二次毕业。",
"events":[
{"date":"2026-03-20","kind":"scarcity_choice","actors":["chen_lan","lin_jing"],"change":"陈岚申请行政例外以保住送审节奏，林静同周期失去一个可用行政窗口。","causes":["family_care_pressure","submission_deadline"],"respects_agency":True,"motifs":["窗口","分开"],"keep":True},
{"date":"2026-04-03","kind":"bad_choice","actors":["chen_lan"],"change":"陈岚为了不再欠人情，错误地拒绝一次本可明确计价的小额协作，短期现金压力加重。","causes":["prior_dependence_discomfort"],"earned_reversal":False,"motifs":["分开"],"keep":True},
{"date":"2026-05-08","kind":"boring_non_event","actors":["chen_lan"],"change":"一周没有决定性事件，她只是把论文、报销和家里转账按部就班处理完。","causes":["ordinary_week"],"respects_agency":True,"motifs":["清单"],"keep":True},
{"date":"2026-07-01","kind":"lifecycle_exit","actors":["chen_lan","wu_cheng"],"change":"陈岚毕业离校，正式结束学生身份；吴澄失去一个长期可靠的收尾者。","causes":["thesis_verified","degree_process_completed"],"actors_effected":["wu_cheng"],"earned_reversal":True,"motifs":["毕业","清单"],"keep":True},
{"date":"2026-09-18","kind":"career_entry","actors":["chen_lan","zhao_ke"],"change":"陈岚进入研究服务企业，收入显著改善，但接受了更明确的交付责任。","causes":["prior_project_record","external_hiring"],"era":["agentic_work_2026"],"respects_agency":True,"motifs":["责任","毕业"],"keep":True},
{"date":"2027-03-12","kind":"technology_repricing","actors":["chen_lan","zhao_ke"],"change":"公司把一批统计实现工作交给agent，陈岚第一次发现自己刚获得高薪的那部分能力正在降价。","causes":["agents_become_standard_coworkers"],"era":["agents_become_standard_coworkers"],"motifs":["价格","责任"],"keep":True},
{"date":"2027-06-04","kind":"relationship_cost","actors":["chen_lan","lin_jing"],"change":"陈岚连续学习新工作流后多次取消与林静约好的晚饭；两人第一次因为成功后的时间贫困争执。","causes":["retraining_load","client_deadlines"],"respects_agency":True,"motifs":["时间","欠账"],"keep":True},
{"date":"2027-09-10","kind":"missed_promotion","actors":["chen_lan"],"change":"她把一个季度用于学习scope、verification和客户沟通，因可计费产出下降错过晋升。","causes":["retraining_choice"],"era":["agents_become_standard_coworkers"],"motifs":["第二次毕业","价格"],"keep":True},
{"date":"2028-02-18","kind":"earned_reversal","actors":["chen_lan","zhao_ke"],"change":"一次agent生成的结果在客户现场出错，陈岚因坚持复核链和责任边界成为能收拾局面的人。","causes":["verification_practice","client_failure"],"earned_reversal":True,"costly_good":True,"respects_agency":True,"motifs":["责任","清单"],"keep":True},
{"date":"2028-08-25","kind":"institutional_cost","actors":["chen_lan"],"change":"她拒绝用无薪试工筛年轻候选人，团队因此少做一个项目并真实损失预算。","causes":["memory_of_precarity","hiring_authority"],"costly_good":True,"respects_agency":True,"motifs":["欠账","责任"],"keep":True},
{"date":"2029-03-16","kind":"delayed_echo","actors":["chen_lan","lin_jing"],"change":"三年前林静失去的那个行政窗口以反方向回响：陈岚如今能提供一个企业研究机会，却只能给入口，不能保证结果。","causes":["2026_scarcity_choice","institutional_memory"],"delay_weeks":155,"respects_agency":True,"motifs":["窗口","分开"],"earned_reversal":True,"keep":True},
{"date":"2029-11-02","kind":"second_graduation","actors":["chen_lan"],"change":"陈岚意识到自己的职业价值已经从'做得快'迁移到'知道什么值得做、什么不能交付并为失败负责'。","causes":["automation_repricing","missed_promotion","client_failure"],"era":["agents_become_standard_coworkers","ai_science_acceleration"],"earned_reversal":True,"motifs":["毕业","责任","价格"],"keep":True}
],
"unresolved":["陈岚的管理权会不会再次把她推回无边界劳动","她与林静的关系能否承受长期时间不对称"]
},
{
"world_id":"world-025","title":"两种上升","premise":"陈岚获得收入和组织权力，林静获得研究自主权；二人的上升无法用同一个标尺比较。",
"events":[
{"date":"2026-03-27","kind":"scarcity_choice","actors":["lin_jing","chen_lan"],"change":"林静拿到一次关键导师注意力，陈岚那周只能依赖已有反馈推进。","causes":["advisor_attention_capacity"],"motifs":["位置","时间"],"keep":True},
{"date":"2026-04-15","kind":"bad_choice","actors":["lin_jing"],"change":"林静为了证明独立性，拒绝了一次本可接受的方法讨论，导致论文多绕了一个月。","causes":["autonomy_anxiety"],"respects_agency":True,"motifs":["自己做","位置"],"keep":True},
{"date":"2026-06-12","kind":"boring_non_event","actors":["lin_jing","chen_lan"],"change":"两人都没有转折；一个改图，一个找工作，晚上在宿舍各自刷招聘信息。","causes":["ordinary_week"],"motifs":["同一张桌子"],"keep":True},
{"date":"2026-09-05","kind":"material_divergence","actors":["chen_lan","lin_jing"],"change":"陈岚离校后收入上升，林静仍靠奖助和家庭支持；第一次明显出现消费能力差距。","causes":["chen_external_job","lin_student_status"],"motifs":["账单","同一张桌子"],"keep":True},
{"date":"2027-01-20","kind":"relationship_cost","actors":["lin_jing","chen_lan"],"change":"一次租房讨论里，陈岚下意识用'你其实可以换好一点'评价林静，林静认为自己的选择被当成了失败。","causes":["income_gap","housing_decision"],"respects_agency":False,"motifs":["账单","赢家"],"keep":True},
{"date":"2027-04-07","kind":"repair","actors":["lin_jing","chen_lan"],"change":"陈岚道歉时没有说'我是为你好'，只承认自己把收入标准带进了别人的生活。","causes":["prior_conflict"],"costly_good":True,"respects_agency":True,"motifs":["赢家","分开"],"keep":True},
{"date":"2027-10-11","kind":"technology_repricing","actors":["lin_jing"],"change":"AI让常规实现更廉价，林静把时间从追求技术炫技移向问题选择、数据质量和可验证性。","causes":["research_automation_broadens"],"era":["agents_become_standard_coworkers","ai_science_acceleration"],"motifs":["价格","自己做"],"keep":True},
{"date":"2028-03-22","kind":"institutional_cost","actors":["lin_jing"],"change":"林静拒绝一个名头漂亮但长期承担隐形验证劳动的岗位，失去更高起薪。","causes":["role_scope_review","prior_invisible_labor"],"costly_good":True,"respects_agency":True,"motifs":["拒绝","赢家"],"keep":True},
{"date":"2028-09-14","kind":"earned_reversal","actors":["lin_jing"],"change":"她在一个小团队获得较低收入但更高研究自主权，第一次可以自己决定哪些结论不值得发表。","causes":["institutional_cost","verification_reputation"],"earned_reversal":True,"motifs":["拒绝","位置"],"keep":True},
{"date":"2029-02-01","kind":"material_success","actors":["chen_lan"],"change":"陈岚开始带团队，收入和组织权力达到三人中最高。","causes":["client_responsibility","management_promotion"],"motifs":["赢家","账单"],"keep":True},
{"date":"2029-07-19","kind":"delayed_echo","actors":["lin_jing","chen_lan"],"change":"一次共同朋友聚会又问起'你们谁混得最好'，两人第一次共同拒绝回答这个问题。","causes":["2027_relationship_conflict","divergent_success"],"delay_weeks":130,"costly_good":True,"respects_agency":True,"motifs":["赢家","同一张桌子"],"earned_reversal":True,"keep":True},
{"date":"2030-01-10","kind":"historical_recognition","actors":["lin_jing","chen_lan"],"change":"她们承认彼此都上升了：一个可以买更多东西，一个可以拒绝更多东西；两种自由都真实，也都付过代价。","causes":["material_success","earned_reversal"],"earned_reversal":True,"motifs":["赢家","拒绝","账单"],"keep":True}
],
"unresolved":["研究自主权能否长期抵御收入和家庭压力","陈岚的组织权力是否会侵蚀她曾珍惜的边界"]
},
{
"world_id":"world-010","title":"会做的人越来越多","premise":"执行能力因AI普及而快速贬值，可验证判断、失败记录和责任链变成新的稀缺资本。",
"events":[
{"date":"2026-03-20","kind":"initial_condition","actors":["xu_hang","gu_wei"],"change":"许航公开报告未复现，并保存数据版本差异。","causes":[],"respects_agency":True,"motifs":["未复现","记录"],"keep":True},
{"date":"2026-05-29","kind":"bad_choice","actors":["xu_hang"],"change":"许航看到同龄人借AI快速出结果后，短暂放弃失败日志，试图追速度。","causes":["peer_comparison","automation_anxiety"],"era":["china_ai_plus"],"motifs":["速度","记录"],"keep":True},
{"date":"2026-07-03","kind":"boring_non_event","actors":["xu_hang"],"change":"连续数周没有成果，只是在修环境、核版本、重跑旧实验。","causes":["reproduction_work"],"motifs":["记录"],"keep":True},
{"date":"2026-10-23","kind":"skill_repricing","actors":["xu_hang","gu_wei"],"change":"越来越多常规代码可由AI完成，顾维开始把评价重点移到问题定义、验证和可追溯失败。","causes":["agentic_work_2026","frontier_math_2026"],"era":["agentic_work_2026","frontier_math_2026"],"motifs":["速度","未复现"],"keep":True},
{"date":"2027-03-18","kind":"institutional_cost","actors":["xu_hang"],"change":"许航选择花一个学期建立自动化验证流水线，论文产出暂时落后同组同龄人。","causes":["skill_repricing"],"respects_agency":True,"motifs":["记录","价格"],"keep":True},
{"date":"2027-08-04","kind":"relationship_cost","actors":["xu_hang","chen_lan"],"change":"许航把一次合作邀请写得过于技术化，忽视陈岚刚进入高压商业岗位的时间边界；陈岚拒绝。","causes":["old_same_group_habit","chen_workload"],"respects_agency":True,"motifs":["边界","速度"],"keep":True},
{"date":"2028-01-12","kind":"technology_wave","actors":["xu_hang"],"change":"agent开始承担大量清洗、复现和报告生成，年轻研究者失去部分传统练手机会。","causes":["agents_become_standard_coworkers"],"era":["agents_become_standard_coworkers","graduate_role_recomposition"],"motifs":["第一阶台阶","价格"],"keep":True},
{"date":"2028-04-20","kind":"costly_good","actors":["gu_wei","xu_hang"],"change":"顾维没有替许航争一个漂亮但空洞的署名，而是把一个失败审计完整交给他负责，短期对双方考核都不划算。","causes":["training_choice"],"costly_good":True,"respects_agency":True,"motifs":["未复现","第一阶台阶"],"keep":True},
{"date":"2028-11-09","kind":"earned_reversal","actors":["xu_hang"],"change":"一家研究机构因AI生成结果泛滥而招聘验证负责人，许航的失败档案第一次成为正资产。","causes":["verification_pipeline","market_repricing"],"earned_reversal":True,"era":["ai_science_acceleration"],"motifs":["记录","价格"],"keep":True},
{"date":"2029-05-17","kind":"cross_actor_consequence","actors":["xu_hang","lin_jing"],"change":"许航指出林静项目里一个自动分析链的 provenance 缺口，迫使项目延期，但避免了一次无法复核的提交。","causes":["verification_reputation","lin_project"],"costly_good":True,"respects_agency":True,"motifs":["责任","未复现"],"keep":True},
{"date":"2029-12-07","kind":"delayed_echo","actors":["xu_hang","gu_wei"],"change":"三年前那个'未复现'报告成为新组培训材料；当年的失败被重新解释成职业起点。","causes":["2026_initial_condition","institutional_memory"],"delay_weeks":194,"earned_reversal":True,"motifs":["未复现","第一阶台阶","记录"],"keep":True},
{"date":"2030-03-21","kind":"historical_recognition","actors":["xu_hang"],"change":"许航意识到自己真正稀缺的能力不是比AI做得更多，而是能说清楚为什么一个看似正确的答案仍然不该被相信。","causes":["delayed_echo","cross_actor_consequence"],"earned_reversal":True,"motifs":["责任","记录","价格"],"keep":True}
],
"unresolved":["验证职业会不会也被下一代agent继续自动化","年轻人如何获得已经消失的低阶训练经验"]
},
{
"world_id":"world-032","title":"后来才知道那年已经变了","premise":"没有单一技术革命时刻，人物多年后才意识到普通招聘、工具和工作流程已共同结束一个旧时代。",
"events":[
{"date":"2026-04-10","kind":"initial_condition","actors":["lin_jing","chen_lan","xu_hang"],"change":"三人仍把AI主要当工具：一个用于论文，一个用于外包，一个用于复现。","causes":[],"motifs":["正常的一天","招聘启事"],"keep":True},
{"date":"2026-09-30","kind":"boring_non_event","actors":["lin_jing"],"change":"林静收藏了几个招聘岗位，没有申请；她只是发现其中开始出现AI workflow和verification字样。","causes":["job_search_routine"],"era":["ai_task_crossover_2026"],"motifs":["招聘启事","正常的一天"],"keep":True},
{"date":"2027-02-16","kind":"bad_choice","actors":["lin_jing"],"change":"她以为这些新要求只是短期风潮，继续用旧方式准备岗位材料，错过一次窗口。","causes":["trend_underreaction"],"motifs":["招聘启事","窗口"],"keep":True},
{"date":"2027-07-28","kind":"technology_repricing","actors":["chen_lan"],"change":"陈岚所在企业缩减纯执行型岗位，同时新增小规模验证、客户责任岗位。","causes":["agents_become_standard_coworkers"],"era":["agents_become_standard_coworkers"],"motifs":["招聘启事","价格"],"keep":True},
{"date":"2027-11-03","kind":"relationship_cost","actors":["lin_jing","xu_hang"],"change":"林静抱怨岗位要求越来越怪，许航说这是机会；林静认为他站着说话不腰疼，两人冷了一阵。","causes":["different_exposure_to_ai"],"respects_agency":True,"motifs":["窗口","正常的一天"],"keep":True},
{"date":"2028-03-09","kind":"junior_ladder_loss","actors":["xu_hang"],"change":"许航发现新来的学生几乎不再做过去那种大量低阶复现工作，训练路径发生变化。","causes":["graduate_role_recomposition"],"era":["graduate_role_recomposition"],"motifs":["第一阶台阶","招聘启事"],"keep":True},
{"date":"2028-06-22","kind":"institutional_cost","actors":["gu_wei","xu_hang"],"change":"顾维要求组内所有AI辅助结果保留 provenance 和失败日志，短期显著降低产出速度。","causes":["junior_ladder_loss","verification_need"],"costly_good":True,"respects_agency":True,"motifs":["记录","价格"],"keep":True},
{"date":"2028-12-14","kind":"earned_reversal","actors":["lin_jing"],"change":"林静早年收缩论断、重视证据边界的习惯开始变成招聘优势。","causes":["job_requirement_shift","verification_reputation"],"earned_reversal":True,"motifs":["窗口","招聘启事"],"keep":True},
{"date":"2029-04-02","kind":"external_wave","actors":["chen_lan"],"change":"公司扩张AI相关业务，但同时砍掉一部分旧式研究服务线，陈岚团队一边招聘一边裁撤。","causes":["china_industrial_upgrade","agents_become_standard_coworkers"],"era":["china_industrial_upgrade","agents_become_standard_coworkers"],"motifs":["价格","正常的一天"],"keep":True},
{"date":"2029-08-30","kind":"costly_good","actors":["chen_lan","junior_hires"],"change":"陈岚把预算留给正式带薪试用和训练，而没有把年轻人的学习成本外包给个人。","causes":["junior_ladder_loss","management_authority"],"costly_good":True,"respects_agency":True,"motifs":["第一阶台阶","责任"],"keep":True},
{"date":"2030-01-17","kind":"delayed_echo","actors":["lin_jing","xu_hang","chen_lan"],"change":"他们回看2026年的招聘启事，才发现那些当时不起眼的新词后来成了职业分水岭。","causes":["2026_boring_non_event","job_requirement_shift"],"delay_weeks":171,"earned_reversal":True,"motifs":["招聘启事","正常的一天"],"keep":True},
{"date":"2030-04-11","kind":"historical_recognition","actors":["lin_jing","xu_hang","chen_lan"],"change":"没人能指出旧时代在哪一天结束；他们只能指出很多当时看起来普通的日子。","causes":["delayed_echo","multiple_small_repricings"],"earned_reversal":True,"motifs":["正常的一天","窗口","价格"],"keep":True}
],
"unresolved":["长期时代感会不会压过具体人物","宏观浪潮应保持多大可见度才不变成说明文"]
}
]
