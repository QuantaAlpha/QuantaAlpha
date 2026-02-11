"""
Runtime patches for rdagent Windows compatibility.

rdagent (v0.8.x) assumes a Linux environment in several places. Instead of
modifying rdagent's installed source in site-packages (which would be lost on
``pip install --upgrade``), this module monkey-patches the relevant classes at
runtime when the host OS is Windows.

Usage — call ``apply()`` once, early in any entry point::

    from quantaalpha.compat.rdagent_patches import apply
    apply()

All patches are guarded by ``sys.platform == "win32"`` and are idempotent.

Patches applied
---------------
1. ``LocalConf`` field default    — ``live_output = False`` (``select.poll``
                                    unavailable on Windows)
2. ``CondaConf.change_bin_path``  — ``grep`` → ``findstr``
3. ``LocalEnv.run``               — skip ``/bin/sh -c 'timeout …'`` wrapper;
                                    inline retry logic to avoid Python
                                    name-mangling issue with ``Env.__run_with_retry``
4. ``LocalEnv._run``              — ``symlink`` → ``CreateJunction``;
                                    PATH separator ``:`` → ``;``;
                                    inherit system PATH
"""

from __future__ import annotations

import contextlib
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from types import MappingProxyType
from typing import Generator, Mapping

_applied = False


def apply() -> None:
    """Apply all Windows patches to rdagent.  Safe to call multiple times."""
    global _applied
    if _applied or sys.platform != "win32":
        return
    _applied = True

    import rdagent.utils.env as _env_mod

    _patch_local_conf_defaults(_env_mod)
    _patch_conda_conf_validator(_env_mod)
    _patch_local_env_run(_env_mod)
    _patch_local_env__run(_env_mod)


# ---------------------------------------------------------------------------
# Patch 1 – LocalConf: live_output default → False on Windows
# ---------------------------------------------------------------------------

def _patch_local_conf_defaults(_env_mod) -> None:
    """``select.poll()`` is unavailable on Windows; disable live output."""
    _env_mod.LocalConf.model_fields["live_output"].default = False


# ---------------------------------------------------------------------------
# Patch 2 – CondaConf.change_bin_path: grep → findstr
# ---------------------------------------------------------------------------

def _patch_conda_conf_validator(_env_mod) -> None:
    """Replace ``grep '^PATH='`` with ``findstr "^PATH="`` on Windows."""
    from pydantic import model_validator
    from typing import Any

    CondaConf = _env_mod.CondaConf

    @model_validator(mode="after")
    def _win_change_bin_path(self: "CondaConf", **data: Any) -> "CondaConf":
        conda_path_result = subprocess.run(
            f'conda run -n {self.conda_env_name} --no-capture-output env | findstr "^PATH="',
            capture_output=True,
            text=True,
            shell=True,
        )
        self.bin_path = (
            conda_path_result.stdout.strip().split("=", 1)[1]
            if conda_path_result.returncode == 0
            else ""
        )
        return self

    # Replace the validator on the class.  Pydantic v2 stores validators in
    # ``__pydantic_decorators__``; the simplest reliable approach is to just
    # override the method.
    CondaConf.change_bin_path = _win_change_bin_path  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Patch 3 – Env.run: skip /bin/sh wrapper on Windows, inline retry logic
# ---------------------------------------------------------------------------

def _patch_local_env_run(_env_mod) -> None:
    """On Windows, run the entry command directly instead of wrapping it with
    ``/bin/sh -c 'timeout …'``.

    We inline the retry logic here instead of calling the private
    ``Env.__run_with_retry`` to avoid Python name-mangling issues across
    the class hierarchy (``_Env__run_with_retry`` is inaccessible from a
    free function patched onto ``LocalEnv``).
    """
    from rdagent.log import rdagent_logger as logger

    LocalEnv = _env_mod.LocalEnv

    def _win_run(
        self,
        entry: str | None = None,
        local_path: str = ".",
        env: dict | None = None,
        **kwargs,
    ):
        """Patched ``LocalEnv.run`` for Windows — skip /bin/sh wrapper."""
        from rdagent.utils.env import EnvResult

        running_extra_volume = kwargs.get("running_extra_volume", {})
        if entry is None:
            entry = self.conf.default_entry

        if "|" in entry:
            logger.warning(
                "You are using a command with a shell pipeline (i.e., '|'). "
                "The exit code ($exit_code) will reflect the result of "
                "the last command in the pipeline.",
            )

        # On Windows: run entry directly, no /bin/sh wrapper
        entry_add_timeout = entry

        if self.conf.enable_cache:
            result = self.cached_run(
                entry_add_timeout, local_path, env, running_extra_volume,
            )
        else:
            # Inline retry logic (mirrors Env.__run_with_retry but avoids
            # Python name-mangling which breaks across class hierarchy)
            result = None
            for retry_index in range(self.conf.retry_count + 1):
                try:
                    start = time.time()
                    log_output, return_code = self._run(
                        entry_add_timeout,
                        local_path,
                        env,
                        running_extra_volume=running_extra_volume,
                    )
                    end = time.time()
                    logger.info(f"Running time: {end - start} seconds")
                    if (
                        self.conf.running_timeout_period is not None
                        and end - start + 1 >= self.conf.running_timeout_period
                    ):
                        logger.warning(
                            f"The running time exceeds "
                            f"{self.conf.running_timeout_period} seconds, "
                            "so the process is killed."
                        )
                        log_output += (
                            f"\n\nThe running time exceeds "
                            f"{self.conf.running_timeout_period} seconds, "
                            "so the process is killed."
                        )
                    result = EnvResult(log_output, return_code, end - start)
                    break
                except Exception as e:
                    if retry_index == self.conf.retry_count:
                        raise
                    logger.warning(
                        f"Error while running: {e}, "
                        f"current try index: {retry_index + 1}, "
                        f"{self.conf.retry_count - retry_index - 1} retries left."
                    )
                    time.sleep(self.conf.retry_wait_seconds)
            if result is None:
                raise RuntimeError("All retries exhausted")

        return result

    LocalEnv.run = _win_run


# ---------------------------------------------------------------------------
# Patch 4 – LocalEnv._run: symlinks → junctions, PATH fixes
# ---------------------------------------------------------------------------

def _patch_local_env__run(_env_mod) -> None:
    """Patch ``LocalEnv._run`` to:
    - use ``_winapi.CreateJunction`` instead of ``os.symlink``
    - use ``;`` as PATH separator (not ``:``)
    - inherit the system PATH so ``python``/``qrun``/``conda`` are found
    """

    from rich import print as rprint
    from rich.console import Console
    from rich.rule import Rule
    from rich.table import Table

    LocalEnv = _env_mod.LocalEnv
    normalize_volumes = _env_mod.normalize_volumes

    def _win__run(
        self,
        entry: str | None = None,
        local_path: str | None = None,
        env: dict | None = None,
        running_extra_volume: Mapping = MappingProxyType({}),
        **kwargs,
    ) -> tuple[str, int]:

        from rdagent.utils.agent.tpl import T

        # --- Volume handling (same as original) ---
        volumes: dict = {}
        if self.conf.extra_volumes is not None:
            for lp, rp in self.conf.extra_volumes.items():
                volumes[lp] = rp["bind"] if isinstance(rp, dict) else rp
            cache_path = (
                "/tmp/sample"
                if "/sample/" in "".join(self.conf.extra_volumes.keys())
                else "/tmp/full"
            )
            Path(cache_path).mkdir(parents=True, exist_ok=True)
            volumes[cache_path] = T("scenarios.data_science.share:scen.cache_path").r()
        for lp, rp in running_extra_volume.items():
            volumes[lp] = rp

        assert local_path is not None, "local_path should not be None"
        volumes = normalize_volumes(volumes, local_path)

        # --- Windows-compatible symlink context (junctions) ---
        @contextlib.contextmanager
        def _symlink_ctx(vol_map: Mapping[str, str]) -> Generator[None, None, None]:
            created_links: list[Path] = []
            try:
                for real, link in vol_map.items():
                    link_path = Path(link)
                    real_path = Path(real)
                    if not link_path.parent.exists():
                        link_path.parent.mkdir(parents=True, exist_ok=True)
                    if link_path.exists() or link_path.is_symlink():
                        if link_path.is_dir() and not link_path.is_symlink():
                            import shutil
                            shutil.rmtree(link_path, ignore_errors=True)
                        else:
                            link_path.unlink()
                    if real_path.is_dir():
                        # Directory junction — no admin privilege required
                        import _winapi
                        _winapi.CreateJunction(
                            str(real_path.resolve()), str(link_path)
                        )
                    else:
                        link_path.symlink_to(real_path)
                    created_links.append(link_path)
                yield
            finally:
                for p in created_links:
                    try:
                        if p.is_dir() and not p.is_symlink():
                            p.rmdir()
                        elif p.is_symlink() or p.exists():
                            p.unlink()
                    except (FileNotFoundError, OSError):
                        pass

        with _symlink_ctx(volumes):
            # --- Environment / PATH setup (Windows-specific) ---
            if env is None:
                env = {}
            path_sep = ";"
            path_parts = [
                *self.conf.bin_path.split(path_sep),
                *env.get("PATH", "").split(path_sep),
                *os.environ.get("PATH", "").split(path_sep),  # inherit system PATH
            ]
            env["PATH"] = path_sep.join(p for p in path_parts if p)

            if entry is None:
                entry = self.conf.default_entry

            rprint(Rule("[bold green]LocalEnv Logs Begin[/bold green]", style="dark_orange"))
            table = Table(title="Run Info", show_header=False)
            table.add_column("Key", style="bold cyan")
            table.add_column("Value", style="bold magenta")
            table.add_row("Entry", entry)
            table.add_row("Local Path", local_path or "")
            table.add_row("Env", "\n".join(f"{k}:{v}" for k, v in env.items()))
            table.add_row("Volumes", "\n".join(f"{k}:\n  {v}" for k, v in volumes.items()))
            rprint(table)

            cwd = Path(local_path).resolve() if local_path else None
            env = {k: str(v) if isinstance(v, int) else v for k, v in env.items()}

            process = subprocess.Popen(
                entry,
                cwd=cwd,
                env={**os.environ, **env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                bufsize=1,
                universal_newlines=True,
            )

            if process.stdout is None or process.stderr is None:
                raise RuntimeError(
                    "The subprocess did not correctly create stdout/stderr pipes"
                )

            # On Windows: always use communicate() (select.poll unavailable)
            out, err = process.communicate()
            Console().print(out, end="", markup=False)
            Console().print(err, end="", markup=False)
            combined_output = out + err

            return_code = process.returncode
            rprint(Rule("[bold green]LocalEnv Logs End[/bold green]", style="dark_orange"))

            return combined_output, return_code

    LocalEnv._run = _win__run
