import tomllib
from enum import Enum
import os
import logging
import sys
from graphlib import TopologicalSorter
import subprocess

# TODO: Check if REPOSITORY_ROOT, EXTRACTED_FW_ROOT, PATCHES_ROOT and FW_VER exist

REPOSITORY_ROOT = os.getenv("REPOSITORY_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
EXTRACTED_FW_ROOT = os.getenv("EXTRACTED_FW_ROOT", os.path.join(REPOSITORY_ROOT, "unpacked"))
SQUASHFS_ROOT = os.getenv("SQUASHFS_ROOT", os.path.join(EXTRACTED_FW_ROOT, "squashfs-root"))
PATCHES_ROOT = os.getenv("PATCHES_ROOT", os.path.dirname(__file__))
FW_VER = ""

with open(os.path.join(PATCHES_ROOT, "patch_config")) as f:
    for line in f:
        items = line.strip().split("=", 1)
        if len(items) >= 2:
            key, value = items
            if key and value:
                os.environ[key] = value

class ExecutionPolicy(Enum):
    always = 1
    never = 2
    matchesenv = 3

class Patch:
    def __init__(self, toml : dict, dir : str):
        self.id : str = toml["id"] # Required
        self.name = toml["name"] # Required
        self.dir = dir
        self.before = toml["before"] if "before" in toml else []
        self.after = toml["after"] if "after" in toml else []
        self.requires = toml["requires"] if "requires" in toml else []
        self.execution_policy = ExecutionPolicy[toml["execution_policy"].lower()] if "execution_policy" in toml else ExecutionPolicy.matchesenv
        self.run = toml["run"] if "run" in toml else ["./patch.sh"]
        self.compatible_versions = toml["compatible_versions"] if "compatible_versions" in toml else []
        self.after.extend(self.requires)

    def can_execute(self) -> bool:
        if FW_VER not in self.compatible_versions and not (len(self.compatible_versions) == 1 and self.compatible_versions[0] == "*"):
            return False

        match self.execution_policy:
            case ExecutionPolicy.always:
                return True
            case ExecutionPolicy.never:
                return False
            case ExecutionPolicy.matchesenv:
                value = os.getenv(self.id.upper(), "false").lower()
                return value == "true" or value == "1"
            
        return False

    def strip_non_existing(self, patch_ids_that_exist : list[str]):
        if len(self.before) == 1 and self.before[0] == "*":
            self.before = patch_ids_that_exist
            self.before.remove(self.id)
        
        if len(self.after) == 1 and self.after[0] == "*":
            self.after = patch_ids_that_exist
            self.after.remove(self.id)

        self.before = [x for x in self.before if x in patch_ids_that_exist]
        self.after = [x for x in self.after if x in patch_ids_that_exist]
        if len([x for x in self.requires if x in patch_ids_that_exist]) != len(self.requires):
            logging.fatal(f"Patch '{self.id}' has dependencies that cannot be resolved. Cannot continue.")
            sys.exit(1)

    def execute(self):
        env = dict(os.environ)
        env["REPOSITORY_ROOT"] = REPOSITORY_ROOT
        env["EXTRACTED_FW_ROOT"] = EXTRACTED_FW_ROOT
        env["SQUASHFS_ROOT"] = SQUASHFS_ROOT
        env["PATCHES_ROOT"] = PATCHES_ROOT
        env["FW_VER"] = FW_VER
        env["CURRENT_PATCH_PATH"] = self.dir

        subprocess.run(self.run, shell=False, check=True, env=env, cwd=self.dir)


def load_toml(path : str) -> dict:
    with open(path, 'rb') as fp:
        return tomllib.load(fp)

def list_patches_dir() -> list[str]:
    return [os.path.join(PATCHES_ROOT, x) for x in os.listdir(PATCHES_ROOT)]

def load_patches() -> list[Patch]:
    folders = [x for x in list_patches_dir() if os.path.isdir(x) and os.path.isfile(os.path.join(x, "patch.toml"))]
    return [Patch(load_toml(os.path.join(x, "patch.toml")), x) for x in folders]

def add_to_dict(d : dict[str, list[str]], key : str, value : str):
    if key not in d:
        d[key] = []
    
    if value not in d[key]:
        d[key].append(value)

def find_by_id(patches : list[Patch], patch_id : str) -> Patch:
    for patch in patches:
        if patch.id == patch_id:
            return patch
    
    logging.fatal(f"Failed to find patch {patch_id}")
    exit(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout)])

    if len(sys.argv) <= 1:
        logging.fatal("Usage: python3 patch_planner.py <fw_version> [--dry-run]")
        sys.exit(1)

    FW_VER = sys.argv[1]

    available_patches = load_patches()
    executable_patches = [x for x in available_patches if x.can_execute()]
    executable_patch_ids = [x.id for x in executable_patches]
    for patch in executable_patches:
        patch.strip_non_existing(executable_patch_ids)

    graph = {}

    for patch in executable_patches:
        for before in patch.before:
            add_to_dict(graph, before, patch.id)
        
        for after in patch.after:
            add_to_dict(graph, patch.id, after)

    ts = TopologicalSorter(graph)
    patch_plan_ids = list(ts.static_order())
    patch_plan = [find_by_id(executable_patches, x) for x in patch_plan_ids]

    logging.info("Patch plan:")
    for patch in patch_plan:
        logging.info(f"- '{patch.name}'")
    
    if "--dry-run" in sys.argv:
        exit(0)

    logging.info("")

    for patch in patch_plan:
        logging.info(f"Applying patch '{patch.name}'...")
        patch.execute()