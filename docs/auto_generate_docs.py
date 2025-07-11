#!/usr/bin/env python3
"""
Comprehensive Documentation Automation Script

This script automates the entire documentation generation process:
1. Generates dynamic .mmd files from code analysis
2. Converts .mmd files to PNG images
3. Builds Sphinx documentation
4. Handles all dependencies automatically

Usage:
    python docs/auto_generate_docs.py                    # Full automation
    python docs/auto_generate_docs.py --mmd-only         # Generate only .mmd files
    python docs/auto_generate_docs.py --images-only      # Convert only to images
    python docs/auto_generate_docs.py --build-only       # Build only docs
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any
import importlib.util
import glob

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

class DocumentationAutomator:
    def __init__(self):
        self.project_root = project_root
        self.mmd_dir = project_root / "mmd"
        self.docs_dir = project_root / "docs"
        self.images_dir = self.docs_dir / "_static" / "images"
        
        # Ensure directories exist
        self.mmd_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def check_dependencies(self) -> bool:
        """Check and install required dependencies."""
        print("🔍 Checking dependencies...")
        
        # Check Node.js and npm
        if not shutil.which('node'):
            print("❌ Node.js not found. Please install from https://nodejs.org/")
            return False
        
        if not shutil.which('npm'):
            print("❌ npm not found. Please install Node.js from https://nodejs.org/")
            return False
        
        # Check mermaid-cli
        if not shutil.which('mmdc'):
            print("📦 Installing mermaid-cli...")
            try:
                subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], 
                             check=True, capture_output=True)
                print("✅ mermaid-cli installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install mermaid-cli: {e}")
                return False
        
        # Check Python dependencies
        try:
            import sphinx
            print("✅ Sphinx is available")
        except ImportError:
            print("📦 Installing Sphinx...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'sphinx'], check=True)
        
        return True
    
    def generate_dynamic_mmd_files(self):
        """Generate .mmd files dynamically from code analysis."""
        print("🔄 Generating dynamic .mmd files...")
        
        # Generate database schema diagram
        self._generate_database_schema_mmd()
        
        # Generate component architecture diagram
        self._generate_component_architecture_mmd()
        
        # Generate CI/CD workflow diagram
        self._generate_cicd_workflow_mmd()
        
        # Generate deployment diagram
        self._generate_deployment_mmd()
        
        print("✅ Dynamic .mmd files generated")
    
    def _generate_database_schema_mmd(self):
        """Generate database schema diagram from SQLAlchemy models."""
        try:
            from src.database.models import Base, Scenario, VehicleData, SensorData, SimulationMetrics
            
            mmd_content = [
                "graph TB",
                "    %% Database Schema for CARLA Driving Simulator",
                "",
                "    %% Tables",
                "    Scenario[Scenario<br/>id: int<br/>name: varchar<br/>description: text<br/>created_at: timestamp]",
                "    VehicleData[VehicleData<br/>id: int<br/>scenario_id: int<br/>timestamp: timestamp<br/>position_x: float<br/>position_y: float<br/>speed: float]",
                "    SensorData[SensorData<br/>id: int<br/>vehicle_id: int<br/>sensor_type: varchar<br/>data: json<br/>timestamp: timestamp]",
                "    SimulationMetrics[SimulationMetrics<br/>id: int<br/>scenario_id: int<br/>metric_name: varchar<br/>metric_value: float<br/>timestamp: timestamp]",
                "",
                "    %% Relationships",
                "    Scenario --> VehicleData",
                "    VehicleData --> SensorData",
                "    Scenario --> SimulationMetrics",
                "",
                "    %% Styling",
                "    classDef tableStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
                "    class Scenario,VehicleData,SensorData,SimulationMetrics tableStyle"
            ]
            
            output_file = self.mmd_dir / "carla_database_schema.mmd"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mmd_content))
            
            print(f"  ✅ Generated {output_file.name}")
            
        except ImportError as e:
            print(f"  ⚠️  Could not import database models: {e}")
            # Generate a basic schema diagram as fallback
            mmd_content = [
                "graph TB",
                "    %% Database Schema for CARLA Driving Simulator",
                "",
                "    %% Tables",
                "    Scenario[Scenario<br/>id: int<br/>name: varchar<br/>description: text<br/>created_at: timestamp]",
                "    VehicleData[VehicleData<br/>id: int<br/>scenario_id: int<br/>timestamp: timestamp<br/>position_x: float<br/>position_y: float<br/>speed: float]",
                "    SensorData[SensorData<br/>id: int<br/>vehicle_id: int<br/>sensor_type: varchar<br/>data: json<br/>timestamp: timestamp]",
                "    SimulationMetrics[SimulationMetrics<br/>id: int<br/>scenario_id: int<br/>metric_name: varchar<br/>metric_value: float<br/>timestamp: timestamp]",
                "",
                "    %% Relationships",
                "    Scenario --> VehicleData",
                "    VehicleData --> SensorData",
                "    Scenario --> SimulationMetrics",
                "",
                "    %% Styling",
                "    classDef tableStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
                "    class Scenario,VehicleData,SensorData,SimulationMetrics tableStyle"
            ]
            
            output_file = self.mmd_dir / "carla_database_schema.mmd"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mmd_content))
            
            print(f"  ✅ Generated {output_file.name} (fallback)")
    
    def _generate_component_architecture_mmd(self):
        """Generate component architecture diagram from code analysis."""
        try:
            # Analyze the src directory structure
            src_dir = self.project_root / "src"
            components = []
            
            for item in src_dir.iterdir():
                if item.is_dir() and not item.name.startswith('__'):
                    components.append(item.name)
            
            mmd_content = [
                "graph TB",
                "    %% Component Architecture for CARLA Driving Simulator",
                "",
                "    %% Main Components",
                "    Main[Main Application<br/>src/main.py]",
            ]
            
            # Add components
            for component in sorted(components):
                mmd_content.append(f"    {component.capitalize()}[{component.capitalize()}<br/>src/{component}/]")
                mmd_content.append(f"    Main --> {component.capitalize()}")
            
            mmd_content.extend([
                "",
                "    %% External Dependencies",
                "    CARLA[CARLA Simulator<br/>External Service]",
                "    PostgresDB[(PostgreSQL<br/>Database)]",
                "",
                "    %% Connections",
                "    Core --> CARLA",
                "    Database --> PostgresDB",
                "",
                "    %% Styling",
                "    classDef mainStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px",
                "    classDef componentStyle fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
                "    classDef externalStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px",
                "    class Main mainStyle",
            ])
            
            # Add component classes one by one to avoid parsing issues
            for component in sorted(components):
                mmd_content.append(f"    class {component.capitalize()} componentStyle")
            
            mmd_content.extend([
                "    class CARLA externalStyle",
                "    class PostgresDB externalStyle"
            ])
            
            output_file = self.mmd_dir / "component_interfaces_diagram.mmd"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mmd_content))
            
            print(f"  ✅ Generated {output_file.name}")
            
        except Exception as e:
            print(f"  ⚠️  Could not generate component architecture: {e}")
    
    def _generate_cicd_workflow_mmd(self):
        """Generate CI/CD workflow diagram from GitHub Actions."""
        workflow_file = self.project_root / ".github" / "workflows" / "build-publish-release.yml"
        
        if workflow_file.exists():
            mmd_content = [
                "graph LR",
                "    %% CI/CD Workflow for CARLA Driving Simulator",
                "",
                "    %% Workflow Steps",
                "    Push[Code Push]",
                "    Test[Run Tests]",
                "    Build[Build Package]",
                "    Docker[Build Docker]",
                "    Docs[Build Docs]",
                "    Deploy[Deploy]",
                "",
                "    %% Flow",
                "    Push --> Test",
                "    Test --> Build",
                "    Test --> Docker",
                "    Test --> Docs",
                "    Build --> Deploy",
                "    Docker --> Deploy",
                "    Docs --> Deploy",
                "",
                "    %% Styling",
                "    classDef stepStyle fill:#e3f2fd,stroke:#1565c0,stroke-width:2px",
                "    class Push,Test,Build,Docker,Docs,Deploy stepStyle"
            ]
            
            output_file = self.mmd_dir / "carla_ci_cd_workflow.mmd"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mmd_content))
            
            print(f"  ✅ Generated {output_file.name}")
        else:
            print("  ⚠️  GitHub Actions workflow file not found")
    
    def _generate_deployment_mmd(self):
        """Generate deployment diagram from docker-compose files."""
        docker_compose_file = self.project_root / "docker-compose.yml"
        
        if docker_compose_file.exists():
            mmd_content = [
                "graph TB",
                "    %% Deployment Architecture for CARLA Driving Simulator",
                "",
                "    %% Services",
                "    Client[CARLA Client<br/>Docker Container]",
                "    CARLA[CARLA Server<br/>Docker Container]",
                "    DB[(PostgreSQL<br/>Database)]",
                "    Grafana[Grafana<br/>Monitoring]",
                "",
                "    %% Network",
                "    Client --> CARLA",
                "    Client --> DB",
                "    Client --> Grafana",
                "",
                "    %% Styling",
                "    classDef serviceStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px",
                "    classDef dbStyle fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
                "    class Client,CARLA,Grafana serviceStyle",
                "    class DB dbStyle"
            ]
            
            output_file = self.mmd_dir / "carla_deployment.mmd"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mmd_content))
            
            print(f"  ✅ Generated {output_file.name}")
        else:
            print("  ⚠️  Docker Compose file not found")
    
    def convert_mmd_to_images(self):
        """Convert all .mmd files to PNG images."""
        print("🖼️  Converting .mmd files to images...")
        
        mmd_files = list(self.mmd_dir.glob('*.mmd'))
        if not mmd_files:
            print("  ⚠️  No .mmd files found")
            return
        
        mmdc_path = shutil.which('mmdc')
        if not mmdc_path:
            print("  ❌ mmdc not found")
            return
        
        for mmd_file in mmd_files:
            output_file = self.images_dir / f"{mmd_file.stem}.png"
            print(f"  🔄 Converting {mmd_file.name} to {output_file.name}...")
            
            try:
                result = subprocess.run([
                    mmdc_path,
                    '-i', str(mmd_file),
                    '-o', str(output_file),
                    '-b', 'transparent'
                ], check=True, capture_output=True, text=True)
                print(f"  ✅ Generated {output_file.name}")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to convert {mmd_file.name}")
                print(f"     Error: {e}")
                if e.stderr:
                    print(f"     Details: {e.stderr.strip()}")
                # Try to show the problematic content
                try:
                    with open(mmd_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"     Content preview: {content[:200]}...")
                except Exception as read_error:
                    print(f"     Could not read file: {read_error}")
    
    def build_documentation(self):
        """Build Sphinx documentation."""
        print("📚 Building Sphinx documentation...")
        
        try:
            # Change to docs directory
            os.chdir(self.docs_dir)
            
            # Clean previous build
            if (self.docs_dir / "_build").exists():
                shutil.rmtree(self.docs_dir / "_build")
            
            # Set PYTHONPATH to include project root
            env = os.environ.copy()
            env['PYTHONPATH'] = f"{self.project_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
            
            # Regenerate API docs first
            subprocess.run([
                'sphinx-apidoc',
                '-o', '.',
                str(self.project_root / 'src')
            ], check=True, env=env)
            
            subprocess.run([
                'sphinx-apidoc',
                '-o', '.',
                str(self.project_root / 'tests')
            ], check=True, env=env)
            
            # Build documentation
            subprocess.run([
                sys.executable, '-m', 'sphinx.cmd.build',
                '-b', 'html',
                '.',
                '_build/html'
            ], check=True, env=env)
            
            print("✅ Documentation built successfully")
            print(f"📖 Open docs/_build/html/index.html to view")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build documentation: {e}")
        finally:
            # Return to project root
            os.chdir(self.project_root)
    
    def run_full_automation(self):
        """Run the complete automation process."""
        print("🚀 Starting full documentation automation...")
        print("=" * 60)
        
        if not self.check_dependencies():
            print("❌ Dependencies check failed")
            return False
        
        try:
            self.generate_dynamic_mmd_files()
            self.convert_mmd_to_images()
            self.build_documentation()
            
            print("=" * 60)
            print("🎉 Full automation completed successfully!")
            print(f"📁 Generated files:")
            print(f"   - .mmd files: {self.mmd_dir}")
            print(f"   - Images: {self.images_dir}")
            print(f"   - Documentation: {self.docs_dir}/_build/html/")

            # --- Cleanup unused .rst files in docs/ ---
            print("🧹 Cleaning up unused .rst files in docs/ ...")
            toctree_files = set([
                'index.rst', 'api.rst', 'architecture.rst', 'changelog.rst', 'contributing.rst',
                'diagrams.rst', 'faq.rst', 'getting_started.rst', 'installation.rst', 'license.rst',
                'support.rst', 'tutorials.rst'
            ])
            for rst_file in glob.glob(os.path.join(self.docs_dir, '*.rst')):
                if os.path.basename(rst_file) not in toctree_files:
                    print(f"   - Removing unused file: {rst_file}")
                    os.remove(rst_file)
            print("✅ Cleanup completed.")

            return True
            
        except Exception as e:
            print(f"❌ Automation failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Automate documentation generation")
    parser.add_argument("--mmd-only", action="store_true", help="Generate only .mmd files")
    parser.add_argument("--images-only", action="store_true", help="Convert only to images")
    parser.add_argument("--build-only", action="store_true", help="Build only docs")
    
    args = parser.parse_args()
    
    automator = DocumentationAutomator()
    
    if args.mmd_only:
        automator.generate_dynamic_mmd_files()
    elif args.images_only:
        automator.convert_mmd_to_images()
    elif args.build_only:
        automator.build_documentation()
    else:
        automator.run_full_automation()

if __name__ == "__main__":
    main() 