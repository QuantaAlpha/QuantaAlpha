"""
The motiviation of the utils is for environment management

Tries to create uniform environment for the agent to run;
- All the code and data is expected included in one folder
"""

# TODO: move the scenario specific docker env into other folders.

import json
import os
import pickle
import subprocess
import uuid
from abc import abstractmethod
from pathlib import Path
from typing import Generic, Optional, TypeVar

import docker
import docker.models
import docker.models.containers
from pydantic import BaseModel
from rich import print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table

from quantaalpha.core.conf import ExtendedBaseSettings, ExtendedSettingsConfigDict
from quantaalpha.log import logger

ASpecificBaseModel = TypeVar("ASpecificBaseModel", bound=BaseModel)


class Env(Generic[ASpecificBaseModel]):
    """
    We use BaseModel as the setting due to the features it provides
    - It provides base typing and checking features.
    - loading and dumping the information will be easier: for example, we can use package like `pydantic-yaml`
    """

    conf: ASpecificBaseModel  # different env have different conf.

    def __init__(self, conf: ASpecificBaseModel):
        self.conf = conf

    @abstractmethod
    def prepare(self):
        """
        Prepare for the environment based on it's configure
        """

    @abstractmethod
    def run(self, entry: str | None, local_path: str | None = None, env: dict | None = None) -> str:
        """
        Run the folder under the environment.

        Parameters
        ----------
        entry : str | None
            We may we the entry point when we run it.
            For example, we may have different entries when we run and summarize the project.
        local_path : str | None
            the local path (to project, mainly for code) will be mounted into the docker
            Here are some examples for a None local path
            - for example, run docker for updating the data in the extra_volumes.
            - simply run the image. The results are produced by output or network
        env : dict | None
            Run the code with your specific environment.

        Returns
        -------
            the stdout
        """


## Local Environment -----


class LocalConf(BaseModel):
    py_bin: str
    default_entry: str


class LocalEnv(Env[LocalConf]):
    """
    Sometimes local environment may be more convinient for testing
    """

    def prepare(self):
        qlib_data_dir = os.environ.get("QLIB_DATA_DIR", 
                         os.environ.get("QLIB_PROVIDER_URI", "~/.qlib/qlib_data/cn_data"))
        qlib_data_path = Path(qlib_data_dir).expanduser().resolve()
        if not qlib_data_path.exists():
            self.run(
                entry=f"python -m qlib.run.get_data qlib_data --target_dir {qlib_data_path} --region cn",
            )
        else:
            print(f"Data already exists at {qlib_data_path}. Download skipped.")

    def run(self, entry: str | None = None, local_path: Optional[str] = None, env: dict | None = None) -> str:
        if env is None:
            env = {}

        if entry is None:
            entry = self.conf.default_entry

        command = str(Path(self.conf.py_bin).joinpath(entry)).split(" ")

        cwd = None
        if local_path:
            cwd = Path(local_path).resolve()
        result = subprocess.run(command, cwd=cwd, env={**os.environ, **env}, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Error while running the command: {result.stderr}")

        return result.stdout


class QlibLocalEnv(LocalEnv):
    """本地运行Qlib环境，替代Docker容器"""
    
    def __init__(self, timeout: int = 3600):
        """
        初始化本地Qlib环境
        
        Args:
            timeout: 命令执行超时时间（秒），默认3600秒（1小时）
        """
        conf = LocalConf(
            py_bin="python",
            default_entry="qrun conf.yaml"
        )
        super().__init__(conf)
        self.timeout = timeout
    
    def prepare(self):
        """确保本地环境已准备就绪"""
        logger.info("Use local environment to run Qlib backtest")
        # 从环境变量读取 Qlib 数据路径
        qlib_data_dir = os.environ.get("QLIB_DATA_DIR",
                         os.environ.get("QLIB_PROVIDER_URI", "~/.qlib/qlib_data/cn_data"))
        qlib_data_path = Path(qlib_data_dir).expanduser()
        if not qlib_data_path.exists():
            logger.warning(f"Qlib数据目录不存在: {qlib_data_path}，请确保已下载数据")
        
    def run(
        self, 
        entry: str | None = None, 
        local_path: Optional[str] = None, 
        env: dict | None = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        在本地运行命令
        
        Args:
            entry: 要执行的命令
            local_path: 工作目录
            env: 环境变量
            timeout: 超时时间（秒），如果为None则使用实例的timeout属性
            **kwargs: 其他参数
            
        Returns:
            命令的标准输出
        """
        if env is None:
            env = {}
        
        # 使用传入的timeout或实例的timeout
        exec_timeout = timeout if timeout is not None else self.timeout
            
        if entry is None:
            entry = self.conf.default_entry
            
        # 记录运行信息
        table = Table(title="Local Run Info", show_header=False)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="bold magenta")
        table.add_row("Entry", entry)
        table.add_row("Working Directory", local_path)
        table.add_row("Timeout", f"{exec_timeout} seconds")
        table.add_row("Environment Variables", "\n".join(f"{k}:{v}" for k, v in env.items()))
        print(table)
        
        # 分割命令
        command = entry.split()
        
        # 设置工作目录
        cwd = None
        if local_path:
            cwd = Path(local_path).resolve()
            
        print(Rule("[bold green]开始本地执行[/bold green]", style="dark_orange"))
        
        try:
            # 运行命令，添加超时
            result = subprocess.run(
                command, 
                cwd=cwd, 
                env={**os.environ, **env}, 
                capture_output=True, 
                text=True,
                timeout=exec_timeout
            )
            
            # 输出结果
            output = result.stdout
            print(output)
            
            if result.stderr:
                print(f"[stderr]: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Command failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            return output
        except subprocess.TimeoutExpired:
            error_msg = f"Command execution timeout after {exec_timeout} seconds"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


## Docker Environment -----


class DockerConf(ExtendedBaseSettings):
    build_from_dockerfile: bool = False
    dockerfile_folder_path: Optional[Path] = (
        None  # the path to the dockerfile optional path provided when build_from_dockerfile is False
    )
    image: str  # the image you want to build
    mount_path: str  # the path in the docker image to mount the folder
    default_entry: str  # the entry point of the image

    extra_volumes: dict | None = {}
    # Sometime, we need maintain some extra data for the workspace.
    # And the extra data may be shared and the downloading can be time consuming.
    # So we just want to download it once.
    network: str | None = "host"  # the network mode for the docker, none
    shm_size: str | None = None
    enable_gpu: bool = True  # because we will automatically disable GPU if not available. So we enable it by default.
    mem_limit: str | None = "48g"  # Add memory limit attribute

    running_timeout_period: int = 3600  # 1 hour


class QlibDockerConf(DockerConf):
    model_config = ExtendedSettingsConfigDict(env_prefix="QLIB_DOCKER_")

    build_from_dockerfile: bool = True
    dockerfile_folder_path: Path = Path(__file__).parent.parent / "scenarios" / "qlib" / "docker"
    image: str = "local_qlib:latest"
    mount_path: str = "/workspace/qlib_workspace/"
    default_entry: str = "qrun conf.yaml"
    extra_volumes: dict = {Path("~/.qlib/").expanduser().resolve(): "/root/.qlib/"}
    shm_size: str | None = "16g"
    enable_gpu: bool = True


class DMDockerConf(DockerConf):
    model_config = ExtendedSettingsConfigDict(env_prefix="DM_DOCKER_")

    build_from_dockerfile: bool = True
    dockerfile_folder_path: Path = Path(__file__).parent.parent / "scenarios" / "data_mining" / "docker"
    image: str = "local_dm:latest"
    mount_path: str = "/workspace/dm_workspace/"
    default_entry: str = "python train.py"
    extra_volumes: dict = {
        Path("~/.rdagent/.data/physionet.org/files/mimic-eicu-fiddle-feature/1.0.0/FIDDLE_mimic3/")
        .expanduser()
        .resolve(): "/root/.data/"
    }
    shm_size: str | None = "16g"


class KGDockerConf(DockerConf):
    model_config = ExtendedSettingsConfigDict(env_prefix="KG_DOCKER_")

    build_from_dockerfile: bool = True
    dockerfile_folder_path: Path = Path(__file__).parent.parent / "scenarios" / "kaggle" / "docker" / "kaggle_docker"
    image: str = "local_kg:latest"
    # image: str = "gcr.io/kaggle-gpu-images/python:latest"
    mount_path: str = "/workspace/kg_workspace/"
    default_entry: str = "python train.py"
    # extra_volumes: dict = {
    #     # TODO connect to the place where the data is stored
    #     Path("git_ignore_folder/data").resolve(): "/root/.data/"
    # }

    running_timeout_period: int = 600
    mem_limit: str | None = (
        "48g"  # Add memory limit attribute # new-york-city-taxi-fare-prediction may need more memory
    )


class MLEBDockerConf(DockerConf):
    model_config = ExtendedSettingsConfigDict(env_prefix="MLEB_DOCKER_")

    build_from_dockerfile: bool = True
    dockerfile_folder_path: Path = Path(__file__).parent.parent / "scenarios" / "kaggle" / "docker" / "mle_bench_docker"
    image: str = "local_mle:latest"
    # image: str = "gcr.io/kaggle-gpu-images/python:latest"
    mount_path: str = "/workspace/data_folder/"
    default_entry: str = "mlebench prepare --all"
    # extra_volumes: dict = {
    #     # TODO connect to the place where the data is stored
    #     Path("git_ignore_folder/data").resolve(): "/root/.data/"
    # }
    mem_limit: str | None = (
        "48g"  # Add memory limit attribute # new-york-city-taxi-fare-prediction may need more memory
    )


# physionet.org/files/mimic-eicu-fiddle-feature/1.0.0/FIDDLE_mimic3
class DockerEnv(Env[DockerConf]):
    # TODO: Save the output into a specific file

    def prepare(self):
        """
        Download image if it doesn't exist
        """
        client = docker.from_env()
        if self.conf.build_from_dockerfile and self.conf.dockerfile_folder_path.exists():
            logger.info(f"Building the image from dockerfile: {self.conf.dockerfile_folder_path}")
            resp_stream = client.api.build(
                path=str(self.conf.dockerfile_folder_path), tag=self.conf.image, network_mode=self.conf.network
            )
            if isinstance(resp_stream, str):
                logger.info(resp_stream)
            with Progress(SpinnerColumn(), TextColumn("{task.description}")) as p:
                task = p.add_task("[cyan]Building image...")
                for part in resp_stream:
                    lines = part.decode("utf-8").split("\r\n")
                    for line in lines:
                        if line.strip():
                            status_dict = json.loads(line)
                            if "error" in status_dict:
                                p.update(task, description=f"[red]error: {status_dict['error']}")
                                raise docker.errors.BuildError(status_dict["error"], "")
                            if "stream" in status_dict:
                                p.update(task, description=status_dict["stream"])
            logger.info(f"Finished building the image from dockerfile: {self.conf.dockerfile_folder_path}")
        try:
            client.images.get(self.conf.image)
        except docker.errors.ImageNotFound:
            image_pull = client.api.pull(self.conf.image, stream=True, decode=True)
            current_status = ""
            layer_set = set()
            completed_layers = 0
            with Progress(TextColumn("{task.description}"), TextColumn("{task.fields[progress]}")) as sp:
                main_task = sp.add_task("[cyan]Pulling image...", progress="")
                status_task = sp.add_task("[bright_magenta]layer status", progress="")
                for line in image_pull:
                    if "error" in line:
                        sp.update(status_task, description=f"[red]error", progress=line["error"])
                        raise docker.errors.APIError(line["error"])

                    layer_id = line["id"]
                    status = line["status"]
                    p_text = line.get("progress", None)

                    if layer_id not in layer_set:
                        layer_set.add(layer_id)

                    if p_text:
                        current_status = p_text

                    if status == "Pull complete" or status == "Already exists":
                        completed_layers += 1

                    sp.update(main_task, progress=f"[green]{completed_layers}[white]/{len(layer_set)} layers completed")
                    sp.update(
                        status_task,
                        description=f"[bright_magenta]layer {layer_id} [yellow]{status}",
                        progress=current_status,
                    )
        except docker.errors.APIError as e:
            raise RuntimeError(f"Error while pulling the image: {e}")

    def _gpu_kwargs(self, client):
        """get gpu kwargs based on its availability"""
        if not self.conf.enable_gpu:
            return {}
        gpu_kwargs = {
            "device_requests": (
                [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])] if self.conf.enable_gpu else None
            ),
        }
        try:
            client.containers.run(self.conf.image, "nvidia-smi", **gpu_kwargs)
            logger.info("GPU Devices are available.")
        except docker.errors.APIError:
            return {}
        return gpu_kwargs

    def __run(
        self,
        entry: str | None = None,
        local_path: str | None = None,
        env: dict | None = None,
        running_extra_volume: dict | None = None,
    ) -> str:
        if env is None:
            env = {}
        client = docker.from_env()
        # import pdb; pdb.set_trace()
        volumns = {}
        if local_path is not None:
            local_path = os.path.abspath(local_path)
            volumns[local_path] = {"bind": self.conf.mount_path, "mode": "rw"}
        if self.conf.extra_volumes is not None:
            for lp, rp in self.conf.extra_volumes.items():
                volumns[lp] = {"bind": rp, "mode": "rw"}
        if running_extra_volume is not None:
            for lp, rp in running_extra_volume.items():
                volumns[lp] = {"bind": rp, "mode": "rw"}

        log_output = ""

        try:
            container: docker.models.containers.Container = client.containers.run(
                image=self.conf.image,
                command=entry,
                volumes=volumns,
                environment=env,
                detach=True,
                working_dir=self.conf.mount_path,
                # auto_remove=True, # remove too fast might cause the logs not to be get
                network=self.conf.network,
                shm_size=self.conf.shm_size,
                mem_limit=self.conf.mem_limit,  # Set memory limit
                **self._gpu_kwargs(client),
            )
            logs = container.logs(stream=True)
            print(Rule("[bold green]Docker Logs Begin[/bold green]", style="dark_orange"))
            table = Table(title="Run Info", show_header=False)
            table.add_column("Key", style="bold cyan")
            table.add_column("Value", style="bold magenta")
            table.add_row("Image", self.conf.image)
            table.add_row("Container ID", container.id)
            table.add_row("Container Name", container.name)
            table.add_row("Entry", entry)
            table.add_row("Env", "\n".join(f"{k}:{v}" for k, v in env.items()))
            table.add_row("Volumns", "\n".join(f"{k}:{v}" for k, v in volumns.items()))
            print(table)
            for log in logs:
                decoded_log = log.strip().decode()
                Console().print(decoded_log, markup=False)
                log_output += decoded_log + "\n"
            print(Rule("[bold green]Docker Logs End[/bold green]", style="dark_orange"))
            container.wait()
            container.stop()
            container.remove()
            return log_output
        except docker.errors.ContainerError as e:
            raise RuntimeError(f"Error while running the container: {e}")
        except docker.errors.ImageNotFound:
            raise RuntimeError("Docker image not found.")
        except docker.errors.APIError as e:
            raise RuntimeError(f"Error while running the container: {e}")

    def run(
        self,
        entry: str | None = None,
        local_path: str | None = None,
        env: dict | None = None,
        running_extra_volume: dict | None = None,
    ):
        if entry is None:
            entry = self.conf.default_entry
        entry_add_timeout = f"timeout {self.conf.running_timeout_period} {entry}"
        return self.__run(entry_add_timeout, local_path, env, running_extra_volume)

    def dump_python_code_run_and_get_results(
        self,
        code: str,
        dump_file_names: list[str],
        local_path: str | None = None,
        env: dict | None = None,
        running_extra_volume: dict | None = None,
        code_dump_file_py_name: Optional[str] = None,
    ):
        """
        Dump the code into the local path and run the code.
        """
        random_file_name = f"{uuid.uuid4()}.py" if code_dump_file_py_name is None else f"{code_dump_file_py_name}.py"
        with open(os.path.join(local_path, random_file_name), "w") as f:
            f.write(code)
        entry = f"python {random_file_name}"
        log_output = self.run(entry, local_path, env, running_extra_volume=running_extra_volume)
        results = []
        os.remove(os.path.join(local_path, random_file_name))
        for name in dump_file_names:
            if os.path.exists(os.path.join(local_path, f"{name}")):
                results.append(pickle.load(open(os.path.join(local_path, f"{name}"), "rb")))
                os.remove(os.path.join(local_path, f"{name}"))
            else:
                return log_output, None
        return log_output, results


class QTDockerEnv(DockerEnv):
    """Qlib运行环境，可选择Docker或本地环境"""

    def __init__(self, conf: DockerConf = QlibDockerConf(), is_local=False, timeout: Optional[int] = None):
        """
        初始化Qlib运行环境
        
        Args:
            conf: Docker配置（仅用于Docker模式）
            is_local: 是否使用本地环境（True）还是Docker（False）
            timeout: 超时时间（秒），如果为None则使用默认值（本地：3600秒，Docker：使用conf.running_timeout_period）
        """
        self.is_local = is_local
        if is_local:
            # 本地环境：使用传入的timeout或默认3600秒
            local_timeout = timeout if timeout is not None else 3600
            self.env = QlibLocalEnv(timeout=local_timeout)
        else:
            # Docker环境：如果传入了timeout，更新conf
            if timeout is not None:
                conf.running_timeout_period = timeout
            self.env = DockerEnv(conf)

    def prepare(self):
        """准备环境"""
        self.env.prepare()

    def run(self, local_path=None, entry=None, env=None, running_extra_volume=None, timeout: Optional[int] = None):
        """
        运行命令
        
        Args:
            local_path: 工作目录
            entry: 要执行的命令
            env: 环境变量
            running_extra_volume: Docker额外卷（仅用于Docker模式）
            timeout: 超时时间（秒），如果为None则使用初始化时的timeout
        """
        if self.is_local:
            # 本地环境：传递timeout参数
            return self.env.run(entry=entry, local_path=local_path, env=env, timeout=timeout)
        else:
            # Docker环境：timeout已经在初始化时设置到conf中
            return self.env.run(entry=entry, local_path=local_path, env=env, 
                              running_extra_volume=running_extra_volume)


class DMDockerEnv(DockerEnv):
    """Qlib Torch Docker"""

    def __init__(self, conf: DockerConf = DMDockerConf()):
        super().__init__(conf)

    def prepare(self, username: str, password: str):
        """
        Download image & data if it doesn't exist
        """
        super().prepare()
        data_path = next(iter(self.conf.extra_volumes.keys()))
        if not (Path(data_path)).exists():
            logger.info("We are downloading!")
            cmd = "wget -r -N -c -np --user={} --password={} -P ~/.rdagent/.data/ https://physionet.org/files/mimic-eicu-fiddle-feature/1.0.0/".format(
                username, password
            )
            os.system(cmd)
        else:
            logger.info("Data already exists. Download skipped.")


class KGDockerEnv(DockerEnv):
    """Kaggle Competition Docker"""

    def __init__(self, competition: str = None, conf: DockerConf = KGDockerConf()):
        super().__init__(conf)


class MLEBDockerEnv(DockerEnv):
    """MLEBench Docker"""

    def __init__(self, conf: DockerConf = MLEBDockerConf()):
        super().__init__(conf)
