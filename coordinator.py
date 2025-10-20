import argparse
import asyncio
from abc import ABC, abstractmethod

import src.debt.agent_create_sheet
import src.debt.agent_get_req
import src.debt.agent_send_debt2
import src.debt.agent_read_sheet
import src.debt.agent_mng_report
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
            where name = '{self.NAME}'
        """
        await execute_command(sql, status)

    @abstractmethod
    async def run_agent(self):
        raise NotImplementedError


class BaseAgent(Agent, ABC):
    CHECK_AGENTS = {
        'REQ_AGENT': ('REQ_AGENT', 'RESP_AGENT'),
        'RESP_AGENT': ('REQ_AGENT', 'RESP_AGENT'),
        'REP_R_AGENT': ('REP_C_AGENT', 'REP_R_AGENT'),
        'REP_C_AGENT': ('REP_C_AGENT', 'REP_R_AGENT'),
        'REP_MNG_AGENT': ('REP_MNG_AGENT', '')
    }

    async def is_agent_running(self) -> bool:
        check_agents = self.CHECK_AGENTS[self.NAME]
        sql = f"""
            select sum(STATUS)
            from agents
            where name IN {check_agents} 
        """
        if f := await select_command(sql):
            return bool(f[0][0])
        raise ValueError


class ReqAgent(BaseAgent):
    NAME = 'REQ_AGENT'

    async def run_agent(self):
        await src.debt.agent_get_req.worker()


class RespAgent(BaseAgent):
    NAME = 'RESP_AGENT'

    async def run_agent(self):
        await src.debt.agent_send_debt2.worker()


class ReadSpreadsheetAgent(BaseAgent):
    NAME = 'REP_R_AGENT'

    async def run_agent(self):
        await src.debt.agent_read_sheet.handler()


class CreateSpreadsheetAgent(BaseAgent):
    NAME = 'REP_C_AGENT'

    async def run_agent(self):
        await src.debt.agent_create_sheet.handler()


class CreateMngReportAgent(BaseAgent):
    NAME = 'REP_MNG_AGENT'

    async def run_agent(self):
        await src.debt.agent_mng_report.handler()


async def start_agent(agent: BaseAgent):
    if not await agent.is_agent_running():
        await agent.mark_agent_run(1)
        try:
            await agent.run_agent()
        except Exception as e:
            logger.error(e)
            raise
        finally:
            await agent.mark_agent_run(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Вызов функции')
    subparser = parser.add_subparsers(dest='command', help='Доступные функции')
    subparser.add_parser('get')
    subparser.add_parser('send')
    subparser.add_parser('create')
    subparser.add_parser('read')
    subparser.add_parser('mng')

    args = parser.parse_args()

    match args.command:
        case 'get':
            asyncio.run(start_agent(ReqAgent()))
        case 'send':
            asyncio.run(start_agent(RespAgent()))
        case 'create':
            asyncio.run(start_agent(CreateSpreadsheetAgent()))
        case 'read':
            asyncio.run(start_agent(ReadSpreadsheetAgent()))
        case 'mng':
            asyncio.run(start_agent(CreateMngReportAgent()))
        case _:
            parser.print_help()
