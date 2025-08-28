from abc import ABC, abstractmethod

import src.debt.agent_get_req
import src.debt.agent_send_debt
from src.api.db.db import select_command, execute_command
from src.log.log import logger


class Agent(ABC):
    NAME = None

    @abstractmethod
    async def is_agent_running(self) -> bool:
        raise NotImplementedError

    async def mark_agent_run(self, status: int) -> None:
        sql = f"""
            update agents 
            set status = ?
            where name = {self.NAME}
        """
        await execute_command(sql, status)

    @abstractmethod
    async def run_agent(self):
        raise NotImplementedError


async def start_agent(agent: Agent):
    if not await agent.is_agent_running():
        await agent.mark_agent_run(1)
        try:
            await agent.run_agent()
        except Exception as e:
            logger.error(e)
            raise
        finally:
            await agent.mark_agent_run(0)


class ReqAgent(Agent):
    NAME = 'REQ_AGENT'

    async def is_agent_running(self) -> bool:
        sql = """
            select sum(STATUS)
            from agents
            where name IN ('REQ_AGENT', 'RESP_AGENT')
        """
        if f := await select_command(sql):
            return bool(f[0][0])
        raise ValueError

    async def run_agent(self):
        await src.debt.agent_get_req.worker()


class RespAgent(Agent):
    NAME = 'RESP_AGENT'

    async def is_agent_running(self) -> bool:
        sql = """
            select sum(STATUS)
            from agents
            where name IN ('REQ_AGENT', 'RESP_AGENT')
        """
        if f := await select_command(sql):
            return bool(f[0][0])
        raise ValueError

    async def run_agent(self):
        await src.debt.agent_send_debt.worker()


class ReadSpreadsheetAgent(Agent):
    NAME = 'REP_R_AGENT'

    async def is_agent_running(self) -> bool:
        sql = """
            select sum(STATUS)
            from agents
            where name IN ('REP_C_AGENT', 'REP_R_AGENT')
        """
        if f := await select_command(sql):
            return bool(f[0][0])
        raise ValueError

    async def run_agent(self):
        await src.debt.agent_send_debt.worker()

