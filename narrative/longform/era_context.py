"""Era context for high-cost replay.

Observed anchors are dated facts known by the simulated date. Future waves are
scenario branches with probabilities/conditions, never asserted as facts.
"""
from copy import deepcopy

OBSERVED_2026 = [
 {"id":"china_ai_plus","date":"2025-08-27","domain":"technology_policy","scope":"china","fact":"China's AI+ policy calls for deep AI integration across science, industry, consumption, public services and governance.","effects":{"ai_adoption":.12,"task_recomposition":.08},"source":"State Council AI+ action"},
 {"id":"graduate_employment_2026","date":"2026-02-13","domain":"labor","scope":"china","fact":"2026 graduate-employment policy emphasizes private firms, advanced manufacturing, modern services, skills and employment support.","effects":{"graduate_competition":.08,"nonacademic_options":.05},"source":"MOHRSS/finance graduate employment notice"},
 {"id":"national_recruitment_2026","date":"2026-05-12","domain":"labor","scope":"china","fact":"The 2026 national recruitment campaign expands graduate hiring across SOEs, private firms, manufacturing and services.","effects":{"nonacademic_options":.06},"source":"MOE eight-department recruitment action"},
 {"id":"agentic_work_2026","date":"2026-06-25","domain":"technology","scope":"global","fact":"AI agents increasingly execute delegated multi-step knowledge-work tasks rather than only short chatbot interactions.","effects":{"agent_capability":.15,"routine_knowledge_work_pressure":.08},"source":"OpenAI economic research"},
 {"id":"genai_jobs_2026","date":"2026-06-01","domain":"labor_technology","scope":"global","fact":"Evidence shows real but uneven GenAI productivity gains; broad displacement remains limited while younger-worker opportunity and job quality are emerging risks.","effects":{"productivity_dispersion":.08,"junior_role_pressure":.08},"source":"ILO GenAI evidence review"},
 {"id":"ai_task_crossover_2026","date":"2026-09-16","domain":"work_organization","scope":"global","fact":"Workers increasingly use AI for recurring tasks outside their historical occupational boundaries.","effects":{"task_boundary_blur":.10,"skill_portability":.06},"source":"OpenAI Work at the Frontier"},
 {"id":"frontier_math_2026","date":"2026-10-06","domain":"science","scope":"global","fact":"Frontier AI systems are being used on research-level mathematics and formal proof workflows.","effects":{"research_automation_pressure":.10,"formalization_value":.10},"source":"OpenAI mathematics research release"},
 {"id":"professional_computer_agents_2026","date":"2026-10-06","domain":"technology","scope":"global","fact":"Frontier agents are being trained and evaluated on specialized professional software and multi-step business workflows.","effects":{"agent_capability":.10,"service_automation":.08},"source":"OpenAI computer-use research"},
 {"id":"china_homebuyer_support_2026","date":"2026-10-01","domain":"housing","scope":"china","fact":"A one-year first-home mortgage interest subsidy began for qualifying purchases, reducing financing cost for some households.","effects":{"home_purchase_affordability":.05},"source":"China fiscal/financial homebuyer subsidy"},
]

FUTURE_WAVES = [
 {"id":"agents_become_standard_coworkers","window":"2027-2029","domain":"technology_labor","status":"scenario","direction":"mixed","conditions":["agent reliability improves","tool access expands","firms redesign workflows"],"possible_effects":{"routine_knowledge_work_pressure":.18,"small_team_leverage":.16,"junior_training_loss":.10}},
 {"id":"ai_science_acceleration","window":"2027-2030","domain":"science","status":"scenario","direction":"mixed","conditions":["verification improves","domain tools connect to agents"],"possible_effects":{"research_cycle_speed":.18,"method_skill_repricing":.14,"reproducibility_value":.12}},
 {"id":"graduate_role_recomposition","window":"2027-2030","domain":"labor","status":"scenario","direction":"mixed","conditions":["automation substitutes entry tasks","new AI-complementary roles expand"],"possible_effects":{"junior_role_pressure":.14,"ai_complement_skill_premium":.16}},
 {"id":"china_industrial_upgrade","window":"2026-2030","domain":"economy_industry","status":"scenario","direction":"mixed","conditions":["advanced manufacturing and digital-economy investment persists"],"possible_effects":{"technical_industry_options":.14,"regional_job_reallocation":.08}},
 {"id":"housing_balance_sheet_repair","window":"2027-2030","domain":"housing_macro","status":"scenario","direction":"mixed","conditions":["support policies transmit","household confidence stabilizes"],"possible_effects":{"housing_burden":-.08,"mobility":.06}},
 {"id":"compute_energy_constraint","window":"2027-2030","domain":"technology_infrastructure","status":"scenario","direction":"negative","conditions":["frontier compute demand outpaces cheap supply"],"possible_effects":{"ai_access_inequality":.12,"research_cost_pressure":.08}},
 {"id":"automation_dividend","window":"2028-2030","domain":"economy","status":"scenario","direction":"positive","conditions":["productivity gains diffuse beyond frontier firms"],"possible_effects":{"real_income_opportunity":.10,"new_service_creation":.12}},
]

def context_as_of(day):
    return {"observed":[deepcopy(x) for x in OBSERVED_2026 if x["date"]<=day],"future_scenarios":deepcopy(FUTURE_WAVES),"rule":"observed facts may constrain the world; future waves are branches, never facts"}
