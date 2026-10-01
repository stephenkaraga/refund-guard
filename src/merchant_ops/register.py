"""Register the merchant_ops domain and agents with tau2's registry.

tau2 keeps a global registry. We add to it at runtime instead of forking tau2,
so this repo can pin an upstream release and stay easy to upgrade.
"""

from tau2.registry import registry

from merchant_ops.agent.graph_agent import create_baseline_agent, create_guarded_agent
from merchant_ops.domain.environment import get_environment, get_tasks, get_tasks_split
from merchant_ops.domain.utils import DOMAIN_NAME

BASELINE_AGENT = "mo_baseline"
GUARDED_AGENT = "mo_guarded"


def set_judge_llm(model: str) -> None:
    """Choose the model that grades NL assertions.

    tau2 v1.0.1 hardcodes the judge to an OpenAI model in tau2.config and
    exposes no setting for it, so we override the evaluator module's constant.
    """
    import tau2.evaluator.evaluator_nl_assertions as nl_eval

    nl_eval.DEFAULT_LLM_NL_ASSERTIONS = model


def register() -> None:
    """Idempotently register the domain, its tasks and both agents."""
    if DOMAIN_NAME not in registry.get_domains():
        registry.register_domain(get_environment, DOMAIN_NAME)
    if DOMAIN_NAME not in registry.get_task_sets():
        registry.register_tasks(get_tasks, DOMAIN_NAME, get_task_splits=get_tasks_split)
    agents = registry.get_agents()
    if BASELINE_AGENT not in agents:
        registry.register_agent_factory(create_baseline_agent, BASELINE_AGENT)
    if GUARDED_AGENT not in agents:
        registry.register_agent_factory(create_guarded_agent, GUARDED_AGENT)
