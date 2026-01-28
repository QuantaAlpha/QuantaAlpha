from __future__ import annotations

# TODO: use pydantic for other modules in Qlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class ExtendedEnvSettingsSource(EnvSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Dynamically gather prefixes from the current and parent classes
        prefixes = [self.config.get("env_prefix", "")]
        if hasattr(self.settings_cls, "__bases__"):
            for base in self.settings_cls.__bases__:
                if hasattr(base, "model_config"):
                    parent_prefix = base.model_config.get("env_prefix")
                    if parent_prefix and parent_prefix not in prefixes:
                        prefixes.append(parent_prefix)
        for prefix in prefixes:
            self.env_prefix = prefix
            env_val, field_key, value_is_complex = super().get_field_value(field, field_name)
            if env_val is not None:
                return env_val, field_key, value_is_complex

        return super().get_field_value(field, field_name)


class ExtendedSettingsConfigDict(SettingsConfigDict, total=False): ...


class ExtendedBaseSettings(BaseSettings):

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,  # noqa
        env_settings: PydanticBaseSettingsSource,  # noqa
        dotenv_settings: PydanticBaseSettingsSource,  # noqa
        file_secret_settings: PydanticBaseSettingsSource,  # noqa
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (ExtendedEnvSettingsSource(settings_cls),)


class QuantaAlphaSettings(ExtendedBaseSettings):
    """QuantaAlpha 核心配置"""
    # Log configs
    log_trace_path: str | None = None

    # azure document intelligence configs
    azure_document_intelligence_key: str = ""
    azure_document_intelligence_endpoint: str = ""
    # factor extraction conf
    max_input_duplicate_factor_group: int = 300
    max_output_duplicate_factor_group: int = 20
    max_kmeans_group_number: int = 40

    # workspace conf - 存储到 /mnt/DATA 以节省根目录空间
    workspace_path: Path = Path("/mnt/DATA/quantagent/AlphaAgent/QuantaAlpha_workspace")

    # multi processing conf
    multi_proc_n: int = 1

    # pickle cache conf - 存储到 /mnt/DATA 以节省根目录空间
    cache_with_pickle: bool = True  # whether to use pickle cache
    pickle_cache_folder_path_str: str = "/mnt/DATA/quantagent/AlphaAgent/pickle_cache"
    use_file_lock: bool = (
        True  # when calling the function with same parameters, whether to use file lock to avoid
        # executing the function multiple times
    )


# 保持向后兼容的别名
RDAgentSettings = QuantaAlphaSettings
QUANTA_ALPHA_SETTINGS = QuantaAlphaSettings()
RD_AGENT_SETTINGS = QUANTA_ALPHA_SETTINGS  # 向后兼容别名
