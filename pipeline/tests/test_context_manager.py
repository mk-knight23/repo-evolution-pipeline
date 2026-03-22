from pipeline.core.context import ProjectContextManager

def test_context_manager_graph():
    source_files = {
        "src/utils/colors.ts": "export const PRIMARY = '#ff0000';",
        "src/components/Button.tsx": "import { PRIMARY } from '../utils/colors'; export function Button() {}",
        "src/screens/Home.tsx": "import { Button } from '../components/Button'; export function Home() {}"
    }
    
    manager = ProjectContextManager(source_files)
    
    # Check exports
    assert manager.export_map["PRIMARY"] == "src/utils/colors.ts"
    assert manager.export_map["Button"] == "src/components/Button.tsx"
    
    # Check context gathering
    context = manager.get_relevant_context("src/screens/Home.tsx", max_depth=1)
    assert "src/components/Button.tsx" in context
    assert "src/screens/Home.tsx" in context
    
    # Check deeper context
    deep_context = manager.get_relevant_context("src/screens/Home.tsx", max_depth=2)
    assert "src/utils/colors.ts" in deep_context
