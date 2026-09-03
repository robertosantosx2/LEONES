"""Small multilingual catalog for the standalone LEONES cleanup flow."""

TEXT = {
    "es": {
        "title": "LIMPIEZA / DESINSTALACIÓN",
        "intro": "Puedes seleccionar uno o varios componentes. También puedes ejecutar esta operación fuera del wizard.",
        "outside": "Fuera del wizard: bash scripts/uninstall.sh",
        "leones": "LEONES — estado local generado por LEONES",
        "ods": "ODS — recursos ODS de contenedores",
        "magnitude": "Magnitude — @magnitudedev/cli",
        "llms": "LLM cargados — todos los modelos locales de Ollama",
        "all": "TODO — LEONES + ODS + Magnitude + LLM",
        "keep": "Conservar instalación y finalizar",
        "exit": "Salir",
        "prompt": "Selecciona opciones separadas por comas: ",
        "invalid": "Opción no válida.",
        "next": "Siguiente: se ejecutará la limpieza seleccionada y solo esos componentes.",
    },
    "en": {
        "title": "CLEANUP / UNINSTALL",
        "intro": "You can select one or more components. This operation can also be run outside the wizard.",
        "outside": "Outside the wizard: bash scripts/uninstall.sh",
        "leones": "LEONES — locally generated state",
        "ods": "ODS — ODS container resources",
        "magnitude": "Magnitude — @magnitudedev/cli",
        "llms": "Loaded LLMs — all local Ollama models",
        "all": "ALL — LEONES + ODS + Magnitude + LLMs",
        "keep": "Keep installation and finish",
        "exit": "Exit",
        "prompt": "Select options separated by commas: ",
        "invalid": "Invalid option.",
        "next": "Next: the selected cleanup will run and only those components will be touched.",
    },
    "zh": {
        "title": "清理 / 卸载",
        "intro": "你可以选择一个或多个组件。也可以在向导之外执行此操作。",
        "outside": "在向导之外：bash scripts/uninstall.sh",
        "leones": "LEONES — LEONES 生成的本地状态",
        "ods": "ODS — ODS 容器资源",
        "magnitude": "Magnitude — @magnitudedev/cli",
        "llms": "已加载的 LLM — Ollama 中的所有本地模型",
        "all": "全部 — LEONES + ODS + Magnitude + LLM",
        "keep": "保留安装并结束",
        "exit": "退出",
        "prompt": "请输入选项（用逗号分隔）：",
        "invalid": "无效选项。",
        "next": "下一步：执行所选清理，只处理这些组件。",
    },
}


def get(language: str, key: str) -> str:
    return TEXT.get(language, TEXT["es"]).get(key, TEXT["es"].get(key, key))
