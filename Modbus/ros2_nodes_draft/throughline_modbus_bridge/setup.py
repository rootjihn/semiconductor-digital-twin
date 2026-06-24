from setuptools import setup
from glob import glob

package_name = "throughline_modbus_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Throughline Team",
    maintainer_email="maintainer@example.invalid",
    description="Interface-only ROS2 Modbus bridge node draft for the Throughline project.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "modbus_bridge_node = throughline_modbus_bridge.modbus_bridge_node:main",
        ],
    },
)
