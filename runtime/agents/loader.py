from dataclasses import dataclass
from pathlib import Path

from exception.error_code import BizErrorCode
from runtime.tools.skill_definition import SkillDefinition
from runtime.tools.skill_loader import SkillLoader
from runtime.tools.skill_registry import SkillRegistry


@dataclass(frozen=True)
class AgentDefinition:
    """
    Agent 定义。

    Attributes:
        agent_id (str): Agent ID。
        files (dict[str, str]): Agent Markdown 文件内容。
        skills (dict[str, SkillDefinition]): Agent Skill 定义。
        skill_registry (SkillRegistry): Agent Skill 注册表。
        agent_dir (Path): Agent 资产目录。
        kind (str): Agent 类型，main 或 worker。
    """

    agent_id: str
    files: dict[str, str]
    skills: dict[str, SkillDefinition]
    skill_registry: SkillRegistry
    agent_dir: Path
    kind: str


class AgentLoader:
    """
    Agent Markdown 资产加载器。

    Attributes:
        root_dir (Path): 项目根目录。
        required_files (tuple[str, ...]): 第一阶段必要 Agent 文件。
    """

    required_files = (
        "SOUL.md",
        "Agent.md",
        "Instruction.md",
        "tools.md",
        "output.md",
        "harness.md",
    )

    def __init__(self, root_dir: Path | None = None) -> None:
        """
        初始化 AgentLoader。

        Args:
            root_dir (Path | None): 项目根目录。
        """
        self.root_dir = root_dir or Path.cwd()
        self.skill_loader = SkillLoader()

    def load_main_agent(self) -> AgentDefinition:
        """
        加载 main agent。

        Returns:
            AgentDefinition: Agent 定义。

        Raises:
            BizException: Agent 文件缺失。
        """
        return self.load_agent("main")

    def load_agent(self, agent_id: str) -> AgentDefinition:
        """
        按 Agent ID 加载 Agent。

        Args:
            agent_id (str): Agent ID，main 或 workers 下的目录名。

        Returns:
            AgentDefinition: Agent 定义。

        Raises:
            BizException: Agent 文件缺失。
        """
        agent_dir, kind = self._resolve_agent_dir(agent_id)
        if not agent_dir.exists():
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(f"{agent_dir} 不存在")
        files: dict[str, str] = {}
        missing_files: list[str] = []
        for filename in self.required_files:
            file_path = agent_dir / filename
            if not file_path.exists():
                missing_files.append(filename)
                continue
            files[filename] = file_path.read_text(encoding="utf-8")
        if missing_files:
            raise BizErrorCode.AGENT_LOAD_ERROR.exception(
                f"{agent_id} agent 文件缺失: {', '.join(missing_files)}"
            )
        skills = self.skill_loader.load_from_agent_dir(agent_dir)
        return AgentDefinition(
            agent_id=agent_id,
            files=files,
            skills=skills,
            skill_registry=SkillRegistry(skills),
            agent_dir=agent_dir,
            kind=kind,
        )

    def load_workers(self) -> dict[str, AgentDefinition]:
        """
        扫描并加载所有 Worker Agent。

        Returns:
            dict[str, AgentDefinition]: worker_id 到 Agent 定义的映射。
        """
        workers_dir = self.root_dir / "agents" / "workers"
        if not workers_dir.exists():
            return {}
        workers: dict[str, AgentDefinition] = {}
        for worker_dir in sorted(item for item in workers_dir.iterdir() if item.is_dir()):
            if worker_dir.name.startswith("."):
                continue
            workers[worker_dir.name] = self.load_agent(worker_dir.name)
        return workers

    def _resolve_agent_dir(self, agent_id: str) -> tuple[Path, str]:
        """
        解析 Agent 目录。

        Args:
            agent_id (str): Agent ID。

        Returns:
            tuple[Path, str]: Agent 目录和类型。
        """
        if agent_id == "main":
            return self.root_dir / "agents" / "main", "main"
        return self.root_dir / "agents" / "workers" / agent_id, "worker"
