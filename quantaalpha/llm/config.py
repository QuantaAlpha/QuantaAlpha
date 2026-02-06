"""
QuantaAlpha LLM 配置

所有 LLM 相关的配置参数。通过 Pydantic-settings 自动从环境变量读取。
环境变量名称 = 字段名称的大写形式（如 chat_model → CHAT_MODEL）
"""

from __future__ import annotations

from pathlib import Path

from quantaalpha.core.conf import ExtendedBaseSettings


class LLMSettings(ExtendedBaseSettings):
    # 日志
    log_llm_chat_content: bool = True

    # 重试配置
    max_retry: int = 30
    retry_wait_seconds: int = 15
    
    # 缓存配置
    dump_chat_cache: bool = False
    use_chat_cache: bool = False
    dump_embedding_cache: bool = False
    use_embedding_cache: bool = False
    prompt_cache_path: str = str(Path.cwd() / "prompt_cache.db")
    max_past_message_include: int = 10

    use_auto_chat_cache_seed_gen: bool = False
    init_chat_cache_seed: int = 42

    # Chat 配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    chat_openai_api_key: str = ""
    chat_model: str = "gpt-4-turbo"
    reasoning_model: str = ""
    chat_max_tokens: int = 3000
    chat_temperature: float = 0.5
    chat_stream: bool = True
    chat_seed: int | None = None
    chat_frequency_penalty: float = 0.0
    chat_presence_penalty: float = 0.0
    chat_token_limit: int = 100000
    default_system_prompt: str = "You are an AI assistant who helps to answer user's questions."
    factor_mining_timeout: int = 999999

    # Embedding 配置
    embedding_openai_api_key: str = ""
    embedding_model: str = ""
    embedding_max_str_num: int = 3
    embedding_batch_wait_seconds: float = 2.0
    embedding_api_key: str = ""
    embedding_base_url: str = ""

    # Azure 配置（可选）
    use_azure: bool = False
    chat_use_azure_token_provider: bool = False
    embedding_use_azure_token_provider: bool = False
    managed_identity_client_id: str | None = None
    chat_azure_api_base: str = ""
    chat_azure_api_version: str = ""
    embedding_azure_api_base: str = ""
    embedding_azure_api_version: str = ""

    # 离线/端点模式（通常不使用）
    use_llama2: bool = False
    use_gcr_endpoint: bool = False

    chat_model_map: str = "{}"


LLM_SETTINGS = LLMSettings()
