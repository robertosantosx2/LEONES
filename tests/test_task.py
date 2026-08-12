from leones.task import TaskIntelligence


def test_task_intelligence_detects_coding():
    requirements = TaskIntelligence().analyze("corrige el código Python y ejecuta los tests")
    assert requirements.task_type == "coding"
    assert "filesystem" in requirements.required_tools
    assert "shell" in requirements.required_tools


def test_task_intelligence_detects_research():
    requirements = TaskIntelligence().analyze("investiga modelos locales en la web")
    assert requirements.task_type == "research"
    assert "web" in requirements.required_tools
