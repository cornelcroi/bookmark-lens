"""
Configuration management for bookmark-lens.

Loads configuration from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Central configuration for bookmark-lens."""

    # Database paths
    db_path: str
    lance_path: str

    # Embedding configuration
    embedding_model_name: str
    embedding_dimension: int

    # Content fetching
    fetch_timeout: int
    user_agent: str
    max_content_length: int

    # LLM configuration (Phase 2 - Smart Mode)
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_temperature: float = 0.3
    use_llm: bool = False


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Environment variables:
        BOOKMARK_LENS_DB_PATH: Path to DuckDB database file
        LANCE_DB_PATH: Path to LanceDB directory
        EMBEDDING_MODEL_NAME: Sentence-transformers model name
        EMBEDDING_DIMENSION: Vector dimension (must match model)
        BOOKMARK_LENS_FETCH_TIMEOUT: HTTP fetch timeout in seconds
        BOOKMARK_LENS_USER_AGENT: Custom User-Agent string
        MAX_CONTENT_LENGTH: Maximum characters to store per bookmark
        LLM_MODEL: LLM model name (optional, enables Smart Mode)
        LLM_API_KEY: LLM API key (optional, enables Smart Mode)
        LLM_API_BASE: Custom API endpoint (optional)
        LLM_TEMPERATURE: LLM temperature 0.0-1.0 (optional, default 0.3)

    Returns:
        Config instance with loaded or default values
    """
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Get or create default data directory
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    # Database paths
    db_path = os.getenv(
        "BOOKMARK_LENS_DB_PATH",
        str(data_dir / "bookmark_lens.db")
    )
    lance_path = os.getenv(
        "LANCE_DB_PATH",
        str(data_dir / "embeddings.lance")
    )

    # Ensure parent directories exist
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lance_path).parent.mkdir(parents=True, exist_ok=True)

    # Embedding configuration
    embedding_model_name = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "all-MiniLM-L6-v2"  # 384-dimensional, fast and good quality
    )

    # Dimension must match the model
    # all-MiniLM-L6-v2: 384, all-mpnet-base-v2: 768
    embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # Content fetching configuration
    fetch_timeout = int(os.getenv("BOOKMARK_LENS_FETCH_TIMEOUT", "30"))
    user_agent = os.getenv(
        "BOOKMARK_LENS_USER_AGENT",
        "bookmark-lens/0.1.0"
    )
    max_content_length = int(os.getenv("MAX_CONTENT_LENGTH", "50000"))

    # LLM configuration (Phase 2 - Smart Mode)
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_api_base = os.getenv("LLM_API_BASE")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    use_llm = bool(llm_model and llm_api_key)

    config = Config(
        db_path=db_path,
        lance_path=lance_path,
        embedding_model_name=embedding_model_name,
        embedding_dimension=embedding_dimension,
        fetch_timeout=fetch_timeout,
        user_agent=user_agent,
        max_content_length=max_content_length,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_api_base=llm_api_base,
        llm_temperature=llm_temperature,
        use_llm=use_llm,
    )

    # Validate configuration
    _validate_config(config)

    return config


def _validate_config(config: Config) -> None:
    """
    Validate configuration values.

    Args:
        config: Configuration to validate

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate embedding dimension
    valid_dimensions = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
    }

    if config.embedding_model_name in valid_dimensions:
        expected_dim = valid_dimensions[config.embedding_model_name]
        if config.embedding_dimension != expected_dim:
            raise ValueError(
                f"Model {config.embedding_model_name} produces {expected_dim}D vectors, "
                f"but EMBEDDING_DIMENSION is set to {config.embedding_dimension}"
            )

    # Validate timeout
    if config.fetch_timeout <= 0:
        raise ValueError(f"fetch_timeout must be positive, got {config.fetch_timeout}")

    # Validate max content length
    if config.max_content_length <= 0:
        raise ValueError(
            f"max_content_length must be positive, got {config.max_content_length}"
        )

    # Validate paths are not empty
    if not config.db_path:
        raise ValueError("db_path cannot be empty")
    if not config.lance_path:
        raise ValueError("lance_path cannot be empty")
