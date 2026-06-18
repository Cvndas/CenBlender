import os
import shutil
from pathlib import Path

addonDirectory_5_1 = "C:/Users/Thad9/AppData/Roaming/Blender Foundation/Blender/5.1/scripts/addons/"
latestDirectory = addonDirectory_5_1
repoDirectory = Path(__file__).parent


def main():
    for file in Path(latestDirectory).glob("Cen*"):
        if file.is_file():
            if file.name.startswith("Cen"):
                shutil.copy(file, repoDirectory)


if __name__ == "__main__":
    main()
