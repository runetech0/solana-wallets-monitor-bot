# type: ignore
import os
import toml
from typing import TypeVar

# Type variable for type-safe dynamic class creation
T = TypeVar("T")

# Define the config file path
_CONFIG_FILE = "sample-config.toml"
_CONFIG_DATA = toml.load(_CONFIG_FILE)  # Load TOML data


def detect_type(value: object) -> str:
    """Returns the Python type as a string for strict typing."""
    if isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    elif isinstance(value, list):
        return "list"
    elif isinstance(value, dict):
        return "dict"
    return "object"  # Fallback for unknown types


def generate_section_class(name: str, values: dict) -> str:
    """Generates a dataclass for a TOML section with strict typing."""
    class_code = f"@dataclass\nclass {name}:\n"
    for key, value in values.items():
        attr_type = detect_type(value)
        class_code += f"    {key}: {attr_type} = {repr(value)}\n"
    class_code += "\n"
    return class_code


def generate_config_class(toml_data: dict) -> str:
    """Generates the main Config class with typed attributes."""
    class_code = "class Config:\n"
    for section in toml_data.keys():
        class_code += f"    {section}: '{section}'\n"
    class_code += "\n"

    # Auto-load function
    class_code += "    @classmethod\n"
    class_code += "    def load(cls) -> None:\n"
    for section, values in toml_data.items():
        class_code += f"        cls.{section} = {section}(\n"
        for key in values.keys():
            class_code += f"            {key}=_CONFIG_DATA['{section}']['{key}'],\n"
        class_code = class_code.rstrip(",\n") + "\n        )\n"
    class_code += "\nConfig.load()\n"

    return class_code


# Generate section classes
generated_code = "from dataclasses import dataclass\n\n"

# 🔥 Add `_CONFIG_DATA` definition inside the generated file
generated_code += "import toml\n\n"
generated_code += "_CONFIG_FILE = 'config.toml'\n"
generated_code += "_CONFIG_DATA = toml.load(_CONFIG_FILE)\n\n"

# Generate dataclasses for each section
for section, values in _CONFIG_DATA.items():
    generated_code += generate_section_class(section, values)

# Generate the main Config class
generated_code += generate_config_class(_CONFIG_DATA)

output_filename = "config_reader.py"
# Save to config_class.py
with open(output_filename, "w") as f:
    f.write(generated_code)

print(f"✅ Config class generated in {output_filename}")
os.rename(output_filename, f"app/{output_filename}")
