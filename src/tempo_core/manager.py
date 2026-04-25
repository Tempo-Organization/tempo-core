from tempo_binary_tool_manager import manager

from tempo_core import logger, settings


tools_cache = manager.ToolsCache(
    main_tool_author='Tempo-Organization',
    main_tool_name='tempo',
    logging_function=logger.log_message,
    cache_path=settings.settings_information.settings.get("cache", {}).get("cache_dir", None),
)
