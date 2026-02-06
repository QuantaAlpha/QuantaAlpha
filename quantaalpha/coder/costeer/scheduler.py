import random

from quantaalpha.coder.costeer.evolvable_subjects import EvolvingItem
from quantaalpha.coder.costeer.knowledge_management import (
    CoSTEERQueriedKnowledge,
)
from quantaalpha.core.evaluation import Scenario
from quantaalpha.log import logger


def random_select(
    to_be_finished_task_index: list,
    evo: EvolvingItem,
    selected_num: int,
    queried_knowledge: CoSTEERQueriedKnowledge,
    scen: Scenario,
):

    to_be_finished_task_index = random.sample(
        to_be_finished_task_index,
        selected_num,
    )

    logger.info(f"The random selection is: {to_be_finished_task_index}")
    return to_be_finished_task_index
